import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import BlockchainForbiddenError
from app.modules.blockchain.proof_registry_gateway import THVProofRegistryGateway
from app.modules.blockchain.wallet_link_service import WalletLinkService
from app.modules.dossiers.models import Category  # noqa: F401
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class VerifierRoleGateway:
    def __init__(self) -> None:
        self.allowed_wallet = ""

    async def has_verifier_role(self, wallet_address: str) -> bool:
        return wallet_address == self.allowed_wallet


def test_wallet_link_requires_thv_verifier_role() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        user = User(
            id=uuid4(),
            email="proof-signer@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        async with sessions() as session:
            session.add(user)
            await session.commit()

        account = Account.create()
        gateway = VerifierRoleGateway()
        principal = AuthPrincipal(
            user_id=user.id,
            session_id=uuid4(),
            email=user.email,
            roles=("SUPER_ADMIN",),
            permissions=("blockchain.sign",),
        )
        async with sessions() as session:
            service = WalletLinkService(
                session=session,
                gateway=cast(THVProofRegistryGateway, gateway),
                chain_id=137,
                challenge_ttl_seconds=300,
                audit=AuditService(
                    session,
                    settings=cast(
                        object,
                        SimpleNamespace(
                            audit_integrity_key=None,
                            audit_integrity_key_id="test",
                            audit_integrity_verification_keys={},
                            audit_retention_days=365,
                        ),
                    ),  # type: ignore[arg-type]
                ),
                clock=lambda: NOW,
                nonce_factory=lambda: "thv-verifier-role-test",
            )
            challenge = await service.create_wallet_challenge(
                principal,
                wallet_address=account.address,
                chain_id=137,
            )
            signature = Account.sign_message(
                encode_defunct(text=challenge.message), account.key
            ).signature.hex()

            with pytest.raises(BlockchainForbiddenError):
                await service.verify_wallet_link(
                    principal,
                    challenge_id=challenge.id,
                    nonce=challenge.nonce,
                    signature=signature,
                )

            gateway.allowed_wallet = account.address
            linked = await service.verify_wallet_link(
                principal,
                challenge_id=challenge.id,
                nonce=challenge.nonce,
                signature=signature,
            )
            assert linked.wallet_address == account.address
            assert linked.chain_id == 137

        await engine.dispose()

    asyncio.run(exercise())


def test_active_signing_api_does_not_import_legacy_human_signing() -> None:
    source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "api"
        / "v1"
        / "blockchain_signing.py"
    ).read_text(encoding="utf-8")

    assert "human_signing_dependencies" not in source
    assert "HumanSigningServiceDependency" not in source
