"""Application service for human-signed THV proof registry writes.

This is intentionally parallel to the legacy certificate blockchain flow.  It
only prepares a constrained MetaMask-compatible request after a dossier has a
server-side approval signal; it never receives a wallet private key or sends a
transaction itself.
"""

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainUnavailableError,
)
from app.modules.blockchain.gateway import BlockchainGatewayError
from app.modules.blockchain.human_signing import normalize_wallet_address
from app.modules.blockchain.models import (
    BlockchainWalletLink,
    BlockchainWalletLinkStatus,
)
from app.modules.blockchain.proof_registry_gateway import (
    THVProofRecord,
    THVProofRegistryGateway,
)
from app.modules.dossiers.errors import DossierNotFoundError
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion

_ASSET_ID_DOMAIN = b"THVProofRegistry:asset:v1:"
_HEX_BYTES32 = re.compile(r"0x[0-9a-fA-F]{64}")
_CANONICAL_HASH = re.compile(r"[0-9a-fA-F]{64}")


@dataclass(frozen=True, slots=True)
class THVProofRegistryIntentView:
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    asset_id: str
    proof_hash: str
    network: str
    chain_id: int
    contract_address: str
    transaction_request: dict[str, str]
    estimated_gas: int
    gas_price_wei: int
    wallet_balance_wei: int


@dataclass(frozen=True, slots=True)
class THVProofRegistryProofView:
    asset_id: str
    proof_hash: str
    version: int
    recorded_at: int
    signer: str
    exists: bool


@dataclass(frozen=True, slots=True)
class THVProofRegistryVerificationView:
    asset_id: str
    version: int
    expected_hash: str
    verified: bool


@dataclass(frozen=True, slots=True)
class _ApprovedVersionContext:
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    canonical_hash: str


def derive_thv_asset_id(dossier_id: UUID) -> bytes:
    """Create a stable opaque asset ID without placing dossier data on-chain."""
    return hashlib.sha256(_ASSET_ID_DOMAIN + dossier_id.bytes).digest()


class THVProofRegistryService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: THVProofRegistryGateway,
        network: str,
        chain_id: int,
        contract_address: str,
        signing_enabled: bool,
    ) -> None:
        if gateway.contract_address.lower() != contract_address.lower():
            raise ValueError("THV proof registry contract address is inconsistent.")
        self._session = session
        self._gateway = gateway
        self._network = network
        self._chain_id = chain_id
        self._contract_address = contract_address.lower()
        self._signing_enabled = signing_enabled

    async def prepare_record_proof_intent(
        self,
        principal: AuthPrincipal,
        *,
        dossier_id: UUID,
        version_no: int,
        connected_wallet: str,
    ) -> THVProofRegistryIntentView:
        """Prepare only an approved, role-authorized ``recordProof`` call."""
        self._require_signer(principal)
        self._require_enabled()
        wallet = await self._require_active_wallet(principal, connected_wallet)
        await self._require_verifier_role(wallet.wallet_address)
        context = await self._approved_version_context(dossier_id, version_no)
        asset_id = derive_thv_asset_id(context.dossier_id)
        proof_hash = bytes.fromhex(context.canonical_hash)
        existing = await self._read_proof(asset_id, context.version)
        if existing.exists:
            raise BlockchainConflictError(
                "This approved dossier version already has an immutable proof."
            )

        try:
            payload = self._gateway.encode_record_proof(
                asset_id=asset_id,
                proof_hash=proof_hash,
                version=context.version,
            )
            estimated_gas = await self._gateway.estimate_gas(
                signer=wallet.wallet_address,
                payload=payload,
            )
            gas_price = await self._gateway.gas_price()
            balance = await self._gateway.balance(wallet.wallet_address)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for signing."
            ) from exc

        return THVProofRegistryIntentView(
            dossier_id=context.dossier_id,
            dossier_code=context.dossier_code,
            dossier_title=context.dossier_title,
            version=context.version,
            asset_id=self._as_hex(asset_id),
            proof_hash=self._as_hex(proof_hash),
            network=self._network,
            chain_id=self._chain_id,
            contract_address=self._contract_address,
            transaction_request={
                "to": self._contract_address,
                "data": self._as_hex(payload),
                "chainId": str(self._chain_id),
                "value": "0",
            },
            estimated_gas=estimated_gas,
            gas_price_wei=gas_price,
            wallet_balance_wei=balance,
        )

    async def get_proof(
        self,
        *,
        asset_id: str,
        version: int,
    ) -> THVProofRegistryProofView:
        normalized_asset_id = self._require_hex_bytes32(asset_id, "Asset ID")
        normalized_version = self._require_version(version)
        proof = await self._read_proof(normalized_asset_id, normalized_version)
        return self._proof_view(proof)

    async def verify_proof(
        self,
        *,
        asset_id: str,
        version: int,
        expected_hash: str,
    ) -> THVProofRegistryVerificationView:
        normalized_asset_id = self._require_hex_bytes32(asset_id, "Asset ID")
        normalized_expected_hash = self._require_hex_bytes32(
            expected_hash,
            "Expected proof hash",
            require_nonzero=False,
        )
        normalized_version = self._require_version(version)
        try:
            verified = await self._gateway.verify_proof(
                asset_id=normalized_asset_id,
                version=normalized_version,
                expected_hash=normalized_expected_hash,
            )
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for verification."
            ) from exc
        return THVProofRegistryVerificationView(
            asset_id=self._as_hex(normalized_asset_id),
            version=normalized_version,
            expected_hash=self._as_hex(normalized_expected_hash),
            verified=verified,
        )

    async def _approved_version_context(
        self,
        dossier_id: UUID,
        version_no: int,
    ) -> _ApprovedVersionContext:
        normalized_version = self._require_version(version_no)
        async with self._session.begin():
            dossier = await self._session.get(Dossier, dossier_id)
            if dossier is None:
                raise DossierNotFoundError()
            if dossier.status is not DossierStatus.APPROVED:
                raise BlockchainConflictError(
                    "A THV proof can be recorded only after dossier approval."
                )
            if dossier.current_version_no != normalized_version:
                raise BlockchainConflictError(
                    "Only the current approved dossier version can be recorded."
                )
            version = await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.dossier_id == dossier.id,
                    DossierVersion.version_no == normalized_version,
                )
            )
            if version is None:
                raise DossierNotFoundError("Dossier version was not found.")
            canonical_hash = version.canonical_hash
            if _CANONICAL_HASH.fullmatch(canonical_hash) is None:
                raise BlockchainConflictError(
                    "Approved dossier proof hash is unavailable."
                )
            return _ApprovedVersionContext(
                dossier_id=dossier.id,
                dossier_code=dossier.code,
                dossier_title=dossier.title,
                version=version.version_no,
                canonical_hash=canonical_hash.lower(),
            )

    async def _require_active_wallet(
        self,
        principal: AuthPrincipal,
        connected_wallet: str,
    ) -> BlockchainWalletLink:
        address = self._require_address(connected_wallet)
        async with self._session.begin():
            link = await self._session.scalar(
                select(BlockchainWalletLink).where(
                    BlockchainWalletLink.user_id == principal.user_id,
                    BlockchainWalletLink.wallet_address == address,
                    BlockchainWalletLink.chain_id == self._chain_id,
                    BlockchainWalletLink.is_active.is_(True),
                    BlockchainWalletLink.status == BlockchainWalletLinkStatus.ACTIVE,
                )
            )
            if link is None:
                raise BlockchainForbiddenError()
            return link

    async def _require_verifier_role(self, wallet_address: str) -> None:
        try:
            is_verifier = await self._gateway.has_verifier_role(wallet_address)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry signer role is unavailable."
            ) from exc
        if not is_verifier:
            raise BlockchainForbiddenError()

    async def _read_proof(self, asset_id: bytes, version: int) -> THVProofRecord:
        try:
            return await self._gateway.get_proof(asset_id, version)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for reading."
            ) from exc

    def _require_signer(self, principal: AuthPrincipal) -> None:
        if "SUPER_ADMIN" not in principal.roles:
            raise BlockchainForbiddenError()
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="blockchain.sign",
                allow_super_admin=False,
            ),
            BlockchainForbiddenError,
        )

    def _require_enabled(self) -> None:
        if not self._signing_enabled:
            raise BlockchainConflictError("Blockchain signing is disabled.")

    @staticmethod
    def _require_address(value: str) -> str:
        address = normalize_wallet_address(value)
        if address is None:
            raise BlockchainConflictError("Wallet address is invalid.")
        return address

    @staticmethod
    def _require_version(value: int) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 2**64 - 1
        ):
            raise BlockchainConflictError("Proof version is invalid.")
        return value

    @staticmethod
    def _require_hex_bytes32(
        value: str,
        label: str,
        *,
        require_nonzero: bool = True,
    ) -> bytes:
        if _HEX_BYTES32.fullmatch(value) is None:
            raise BlockchainConflictError(f"{label} must be a bytes32 hex value.")
        decoded = bytes.fromhex(value.removeprefix("0x"))
        if require_nonzero and decoded == bytes(32):
            raise BlockchainConflictError(f"{label} must not be zero.")
        return decoded

    @staticmethod
    def _as_hex(value: bytes) -> str:
        return "0x" + value.hex()

    @classmethod
    def _proof_view(cls, proof: THVProofRecord) -> THVProofRegistryProofView:
        return THVProofRegistryProofView(
            asset_id=cls._as_hex(proof.asset_id),
            proof_hash=cls._as_hex(proof.proof_hash),
            version=proof.version,
            recorded_at=proof.recorded_at,
            signer=proof.signer,
            exists=proof.exists,
        )
