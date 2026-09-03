"""Wallet ownership and THV ``VERIFIER_ROLE`` binding.

This module deliberately has no dependency on the archived CertificateRegistry
signing flow.  It preserves the existing wallet API and database records while
authorizing the wallet against THVProofRegistry.
"""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainNotFoundError,
    BlockchainUnavailableError,
)
from app.modules.blockchain.human_signing import (
    build_wallet_challenge_message,
    normalize_wallet_address,
    recover_wallet_address,
)
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionIntent,
    BlockchainTransactionIntentStatus,
    BlockchainTransactionStatus,
    BlockchainWalletChallenge,
    BlockchainWalletLink,
    BlockchainWalletLinkStatus,
)
from app.modules.blockchain.proof_registry_gateway import THVProofRegistryGateway
from app.modules.blockchain.transport import BlockchainGatewayError


@dataclass(frozen=True, slots=True)
class WalletChallengeView:
    id: UUID
    message: str
    nonce: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class WalletLinkView:
    id: UUID
    wallet_address: str
    chain_id: int
    status: BlockchainWalletLinkStatus
    verified_at: datetime


class WalletLinkService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: THVProofRegistryGateway,
        chain_id: int,
        challenge_ttl_seconds: int,
        audit: AuditService | None = None,
        clock: Callable[[], datetime] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._chain_id = chain_id
        self._challenge_ttl = timedelta(seconds=challenge_ttl_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(32))
        self._audit = audit or AuditService(session)

    async def create_wallet_challenge(
        self,
        principal: AuthPrincipal,
        *,
        wallet_address: str,
        chain_id: int,
    ) -> WalletChallengeView:
        self._require_signer(principal)
        address = self._require_address(wallet_address)
        if chain_id != self._chain_id:
            raise BlockchainConflictError("Wallet chain does not match THV network.")
        nonce = self._nonce_factory()
        now = self._clock()
        expires_at = now + self._challenge_ttl
        challenge = BlockchainWalletChallenge(
            id=uuid4(),
            user_id=principal.user_id,
            wallet_address=address,
            chain_id=chain_id,
            nonce_hash=hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
        async with self._session.begin():
            self._session.add(challenge)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.challenge_issued",
                resource_type="blockchain_wallet_challenge",
                resource_id=str(challenge.id),
                after={"wallet": address, "chain_id": chain_id},
            )
        return WalletChallengeView(
            id=challenge.id,
            message=build_wallet_challenge_message(
                user_id=principal.user_id,
                wallet_address=address,
                chain_id=chain_id,
                nonce=nonce,
                expires_at=expires_at,
            ),
            nonce=nonce,
            expires_at=expires_at,
        )

    async def verify_wallet_link(
        self,
        principal: AuthPrincipal,
        *,
        challenge_id: UUID,
        nonce: str,
        signature: str,
    ) -> WalletLinkView:
        self._require_signer(principal)
        now = self._clock()
        async with self._session.begin():
            challenge = await self._session.scalar(
                select(BlockchainWalletChallenge)
                .where(
                    BlockchainWalletChallenge.id == challenge_id,
                    BlockchainWalletChallenge.user_id == principal.user_id,
                )
                .with_for_update()
            )
            if challenge is None:
                raise BlockchainNotFoundError()
            supplied_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            if (
                challenge.consumed_at is not None
                or self._as_utc(challenge.expires_at) <= now
                or not secrets.compare_digest(challenge.nonce_hash, supplied_hash)
            ):
                raise BlockchainConflictError(
                    "Wallet verification challenge has expired."
                )
            message = build_wallet_challenge_message(
                user_id=principal.user_id,
                wallet_address=challenge.wallet_address,
                chain_id=int(challenge.chain_id),
                nonce=nonce,
                expires_at=self._as_utc(challenge.expires_at),
            )
            recovered = recover_wallet_address(message, signature)
            if recovered != challenge.wallet_address:
                raise BlockchainConflictError(
                    "Wallet signature does not match challenge."
                )
            try:
                has_verifier_role = await self._gateway.has_verifier_role(recovered)
            except BlockchainGatewayError as exc:
                raise BlockchainUnavailableError(
                    "Could not verify the wallet VERIFIER_ROLE."
                ) from exc
            if not has_verifier_role:
                raise BlockchainForbiddenError()

            challenge.consumed_at = now
            current = await self._active_wallet_link(for_update=True)
            if current is not None:
                if (
                    current.user_id == principal.user_id
                    and current.wallet_address == recovered
                ):
                    return self._wallet_view(current)
                raise BlockchainConflictError(
                    "An active blockchain signer wallet is already configured."
                )
            existing = await self._session.scalar(
                select(BlockchainWalletLink)
                .where(BlockchainWalletLink.wallet_address == recovered)
                .with_for_update()
            )
            if existing is not None:
                raise BlockchainConflictError(
                    "This wallet cannot be linked to this user."
                )
            link = BlockchainWalletLink(
                id=uuid4(),
                user_id=principal.user_id,
                wallet_address=recovered,
                chain_id=challenge.chain_id,
                status=BlockchainWalletLinkStatus.ACTIVE,
                is_active=True,
                verified_at=now,
            )
            self._session.add(link)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.linked",
                resource_type="blockchain_wallet_link",
                resource_id=str(link.id),
                after={
                    "wallet": recovered,
                    "chain_id": int(link.chain_id),
                    "contract_role": "VERIFIER_ROLE",
                },
            )
            await self._session.flush()
            return self._wallet_view(link)

    async def current_wallet(self, principal: AuthPrincipal) -> WalletLinkView | None:
        self._require_signer(principal)
        async with self._session.begin():
            link = await self._session.scalar(
                select(BlockchainWalletLink).where(
                    BlockchainWalletLink.user_id == principal.user_id,
                    BlockchainWalletLink.is_active.is_(True),
                )
            )
            return self._wallet_view(link) if link is not None else None

    async def revoke_current_wallet(self, principal: AuthPrincipal) -> WalletLinkView:
        """Deactivate a signer wallet and cancel unbroadcast signing intents."""
        self._require_signer(principal)
        now = self._clock()
        async with self._session.begin():
            link = await self._active_wallet_link(for_update=True)
            if link is None or link.user_id != principal.user_id:
                raise BlockchainForbiddenError()
            link.status = BlockchainWalletLinkStatus.REVOKED
            link.is_active = False
            link.revoked_at = now
            intents = await self._session.scalars(
                select(BlockchainTransactionIntent)
                .where(
                    BlockchainTransactionIntent.signer_user_id == principal.user_id,
                    BlockchainTransactionIntent.status
                    == BlockchainTransactionIntentStatus.PREPARED,
                )
                .with_for_update()
            )
            for intent in intents:
                intent.status = BlockchainTransactionIntentStatus.CANCELLED
                transaction = await self._session.get(
                    BlockchainTransaction,
                    intent.transaction_id,
                    with_for_update=True,
                )
                if (
                    transaction is not None
                    and transaction.status is BlockchainTransactionStatus.SIGNING
                    and transaction.tx_hash is None
                ):
                    transaction.status = BlockchainTransactionStatus.CREATED
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.revoked",
                resource_type="blockchain_wallet_link",
                resource_id=str(link.id),
                before={"wallet": link.wallet_address},
                after={"reason": "signer_rotation"},
            )
            await self._session.flush()
            return self._wallet_view(link)

    async def _active_wallet_link(
        self, *, for_update: bool
    ) -> BlockchainWalletLink | None:
        statement = select(BlockchainWalletLink).where(
            BlockchainWalletLink.is_active.is_(True)
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(
            BlockchainWalletLink | None,
            await self._session.scalar(statement),
        )

    @staticmethod
    def _require_signer(principal: AuthPrincipal) -> None:
        if "SUPER_ADMIN" not in principal.roles:
            raise BlockchainForbiddenError()
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="blockchain.sign",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            BlockchainForbiddenError,
        )

    @staticmethod
    def _require_address(value: str) -> str:
        address = normalize_wallet_address(value)
        if address is None:
            raise BlockchainConflictError("Wallet address is invalid.")
        return address

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    @staticmethod
    def _wallet_view(link: BlockchainWalletLink) -> WalletLinkView:
        return WalletLinkView(
            id=link.id,
            wallet_address=link.wallet_address,
            chain_id=int(link.chain_id),
            status=link.status,
            verified_at=link.verified_at,
        )
