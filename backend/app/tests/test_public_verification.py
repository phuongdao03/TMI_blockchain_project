import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.blockchain.gateway import CertificateRecord
from app.modules.blockchain.models import CertificateStatus
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.public.verification import (
    PublicVerificationService,
    VerificationContext,
    VerificationEvaluator,
    VerificationStatus,
)


def _record(*, metadata_hash: bytes, revoked: bool = False) -> CertificateRecord:
    now = datetime.now(UTC)
    return CertificateRecord(
        dossier_hash=bytes.fromhex("11" * 32),
        metadata_hash=metadata_hash,
        revocation_reason_hash=bytes(32),
        issued_at=int((now - timedelta(days=1)).timestamp()),
        expires_at=int((now + timedelta(days=1)).timestamp()),
        version=1,
        revoked=revoked,
    )


def test_verification_is_valid_only_when_chain_and_database_match() -> None:
    digest = bytes.fromhex("22" * 32)

    status = VerificationEvaluator.evaluate(
        local_status=CertificateStatus.ACTIVE,
        local_metadata_hash=digest.hex(),
        local_dossier_hash="11" * 32,
        local_version=1,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        chain_record=_record(metadata_hash=digest),
        now=datetime.now(UTC),
    )

    assert status is VerificationStatus.VALID


def test_verification_detects_mismatch_before_reporting_valid() -> None:
    status = VerificationEvaluator.evaluate(
        local_status=CertificateStatus.ACTIVE,
        local_metadata_hash="22" * 32,
        local_dossier_hash="11" * 32,
        local_version=1,
        expires_at=None,
        chain_record=_record(metadata_hash=bytes.fromhex("33" * 32)),
        now=datetime.now(UTC),
    )

    assert status is VerificationStatus.MISMATCH


def test_verification_prioritizes_revocation_and_expiry() -> None:
    now = datetime.now(UTC)
    digest = bytes.fromhex("22" * 32)

    revoked = VerificationEvaluator.evaluate(
        local_status=CertificateStatus.ACTIVE,
        local_metadata_hash=digest.hex(),
        local_dossier_hash="11" * 32,
        local_version=1,
        expires_at=now + timedelta(days=1),
        chain_record=_record(metadata_hash=digest, revoked=True),
        now=now,
    )
    expired = VerificationEvaluator.evaluate(
        local_status=CertificateStatus.ACTIVE,
        local_metadata_hash=digest.hex(),
        local_dossier_hash="11" * 32,
        local_version=1,
        expires_at=now - timedelta(seconds=1),
        chain_record=_record(metadata_hash=digest),
        now=now,
    )

    assert revoked is VerificationStatus.REVOKED
    assert expired is VerificationStatus.EXPIRED


def test_verification_recomputes_metadata_instead_of_trusting_stored_hash() -> None:
    async def scenario() -> None:
        original_metadata = {"schemaVersion": 1, "asset": {"title": "Original"}}
        snapshot: dict[str, object] = {"dossier": {"code": "TMI-1"}}
        chain_metadata_hash = bytes.fromhex("22" * 32)

        class Gateway:
            async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
                del certificate_id
                return CertificateRecord(
                    dossier_hash=bytes.fromhex(snapshot_sha256(snapshot)),
                    metadata_hash=chain_metadata_hash,
                    revocation_reason_hash=bytes(32),
                    issued_at=1,
                    expires_at=0,
                    version=1,
                    revoked=False,
                )

        context = VerificationContext(
            certificate_id=UUID("7eaec2d2-c99a-42c9-8f1e-71462ba01ea0"),
            certificate_number="TMI-2026-7EAEC2D2C99A",
            certificate_status=CertificateStatus.ACTIVE,
            asset_title="Tampered",
            category_name="Brand",
            issued_at=datetime.now(UTC),
            expires_at=None,
            metadata_hash=chain_metadata_hash.hex(),
            dossier_hash=snapshot_sha256(snapshot),
            metadata=original_metadata,
            dossier_snapshot=snapshot,
            version=1,
            network="local",
            contract_address="0x" + "12" * 20,
            transaction_hash="0x" + "34" * 32,
            confirmations=1,
            confirmed_at=datetime.now(UTC),
        )

        async def find(value: str) -> VerificationContext:
            del value
            return context

        service = PublicVerificationService(
            gateway=Gateway(),
            find_by_token=find,
            find_by_number=find,
            find_by_transaction=find,
        )

        result = await service.verify_number(context.certificate_number)

        assert result.status is VerificationStatus.MISMATCH

    asyncio.run(scenario())
