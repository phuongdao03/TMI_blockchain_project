import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.blockchain.gateway import BlockchainGatewayError, CertificateRecord
from app.modules.blockchain.models import CertificateStatus
from app.modules.certificates.metadata import CertificateMetadataBuilder
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.public.verification import (
    PublicEvidenceProof,
    PublicVerificationService,
    VerificationContext,
    VerificationEvaluator,
    VerificationStatus,
    public_evidence_proofs,
)


def _audit_dependencies() -> tuple[Mock, AsyncMock]:
    return Mock(spec=AuditService), AsyncMock()


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


def test_public_evidence_projection_is_an_explicit_valid_hash_allowlist() -> None:
    metadata: dict[str, object] = {
        "publicEvidences": [
            {
                "title": "Public PDF",
                "type": "OWNERSHIP",
                "sha256": "ab" * 32,
                "accessScope": "PUBLIC",
            },
            {
                "title": "Public preview",
                "type": "IMAGE",
                "sha256": "bc" * 32,
                "accessScope": "PUBLIC_PREVIEW",
            },
            {
                "title": "Legacy public flag",
                "type": "LEGACY",
                "sha256": "cd" * 32,
                "isPublic": True,
            },
            {
                "title": "Internal document",
                "type": "IDENTITY",
                "sha256": "de" * 32,
                "accessScope": "INTERNAL",
            },
            {
                "title": "Invalid",
                "type": "IMAGE",
                "sha256": "not-a-digest",
                "accessScope": "PUBLIC",
            },
            {
                "title": "Missing type",
                "sha256": "ef" * 32,
                "accessScope": "PUBLIC",
            },
        ],
        "privateEvidence": {"sha256": "ef" * 32},
        "ownerUserId": "private-user",
    }

    assert public_evidence_proofs(metadata) == (
        PublicEvidenceProof(
            title="Public PDF",
            evidence_type="OWNERSHIP",
            sha256="ab" * 32,
        ),
        PublicEvidenceProof(
            title="Public preview",
            evidence_type="IMAGE",
            sha256="bc" * 32,
        ),
    )


def test_verification_reports_not_found_and_temporary_chain_unavailability() -> None:
    async def scenario() -> None:
        metadata: dict[str, object] = {"schemaVersion": 1}
        snapshot: dict[str, object] = {}

        class UnavailableGateway:
            async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
                del certificate_id
                raise BlockchainGatewayError("offline")

        context = VerificationContext(
            certificate_id=UUID("7eaec2d2-c99a-42c9-8f1e-71462ba01ea0"),
            certificate_number="TMI-2026-7EAEC2D2C99A",
            certificate_status=CertificateStatus.ACTIVE,
            asset_title="TMI",
            category_name="Brand",
            issued_at=datetime.now(UTC),
            expires_at=None,
            metadata_hash=hashlib.sha256(
                CertificateMetadataBuilder.canonical_bytes(metadata)
            ).hexdigest(),
            dossier_hash=snapshot_sha256(snapshot),
            metadata=metadata,
            dossier_snapshot=snapshot,
            version=1,
            network="polygon",
            contract_address=None,
            transaction_hash=None,
            confirmations=0,
            confirmed_at=None,
        )

        async def missing(value: str) -> None:
            del value
            return None

        async def found(value: str) -> VerificationContext:
            del value
            return context

        missing_audit, missing_audit_session = _audit_dependencies()
        missing_service = PublicVerificationService(
            gateway=UnavailableGateway(),
            find_by_token=missing,
            find_by_number=missing,
            find_by_transaction=missing,
            audit=missing_audit,
            audit_session=missing_audit_session,
        )
        pending_audit, pending_audit_session = _audit_dependencies()
        pending_service = PublicVerificationService(
            gateway=UnavailableGateway(),
            find_by_token=found,
            find_by_number=found,
            find_by_transaction=found,
            audit=pending_audit,
            audit_session=pending_audit_session,
        )

        missing_result = await missing_service.verify_number("missing")
        pending_result = await pending_service.verify_number("TMI-2026-7EAEC2D2C99A")
        assert missing_result.status is VerificationStatus.NOT_FOUND
        assert pending_result.status is VerificationStatus.PENDING

    asyncio.run(scenario())


def test_public_verification_persists_only_allowlisted_result_metadata() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(cast(Table, AuditLog.__table__).create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        session = sessions()

        class Gateway:
            async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
                del certificate_id
                raise AssertionError("The gateway must not run for an unknown lookup.")

        async def missing(value: str) -> None:
            del value
            return None

        service = PublicVerificationService(
            gateway=Gateway(),
            find_by_token=missing,
            find_by_number=missing,
            find_by_transaction=missing,
            audit=AuditService(session),
            audit_session=session,
        )

        result = await service.verify_token("private-verification-token")

        assert result.status is VerificationStatus.NOT_FOUND
        async with sessions() as reader:
            audit = (await reader.scalars(select(AuditLog))).one()
            assert audit.action == "public.verification.completed"
            assert audit.resource_type == "certificate_verification"
            assert audit.resource_id == "unresolved"
            assert audit.after_json == {
                "lookup_type": "token",
                "status": "NOT_FOUND",
            }
            serialized = str(audit.after_json)
            assert "private-verification-token" not in serialized

        await session.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_public_verification_fails_closed_when_audit_cannot_be_written() -> None:
    async def scenario() -> None:
        class Gateway:
            async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
                del certificate_id
                raise AssertionError("The gateway must not run for an unknown lookup.")

        class FailingAudit:
            def record(self, **values: object) -> None:
                del values
                raise RuntimeError("audit unavailable")

        class Session:
            async def commit(self) -> None:
                raise AssertionError("Commit must not run after an audit failure.")

        async def missing(value: str) -> None:
            del value
            return None

        service = PublicVerificationService(
            gateway=Gateway(),
            find_by_token=missing,
            find_by_number=missing,
            find_by_transaction=missing,
            audit=FailingAudit(),  # type: ignore[arg-type]
            audit_session=Session(),  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="audit unavailable"):
            await service.verify_number("TMI-UNKNOWN")

    asyncio.run(scenario())


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

        audit, audit_session = _audit_dependencies()
        service = PublicVerificationService(
            gateway=Gateway(),
            find_by_token=find,
            find_by_number=find,
            find_by_transaction=find,
            audit=audit,
            audit_session=audit_session,
        )

        result = await service.verify_number(context.certificate_number)

        assert result.status is VerificationStatus.MISMATCH

    asyncio.run(scenario())


def test_historical_qr_reads_its_immutable_chain_version() -> None:
    async def scenario() -> None:
        metadata: dict[str, object] = {"schemaVersion": 2, "certificateVersion": 1}
        snapshot: dict[str, object] = {"dossier": {"code": "THV-HISTORY-1"}}
        metadata_hash = hashlib.sha256(
            CertificateMetadataBuilder.canonical_bytes(metadata)
        ).hexdigest()
        dossier_hash = snapshot_sha256(snapshot)

        class Gateway:
            async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
                del certificate_id
                raise AssertionError(
                    "A historical QR must not read the current version."
                )

            async def get_certificate_version(
                self,
                certificate_id: bytes,
                version: int,
            ) -> CertificateRecord:
                assert len(certificate_id) == 32
                assert version == 1
                return CertificateRecord(
                    dossier_hash=bytes.fromhex(dossier_hash),
                    metadata_hash=bytes.fromhex(metadata_hash),
                    revocation_reason_hash=bytes(32),
                    issued_at=1,
                    expires_at=0,
                    version=1,
                    revoked=False,
                )

        context = VerificationContext(
            certificate_id=UUID("7eaec2d2-c99a-42c9-8f1e-71462ba01ea0"),
            certificate_number="TMI-2026-HISTORY",
            certificate_status=CertificateStatus.ACTIVE,
            asset_title="Historical version",
            category_name="Brand",
            issued_at=datetime.now(UTC),
            expires_at=None,
            metadata_hash=metadata_hash,
            dossier_hash=dossier_hash,
            metadata=metadata,
            dossier_snapshot=snapshot,
            version=1,
            network="local",
            contract_address="0x" + "12" * 20,
            transaction_hash="0x" + "34" * 32,
            confirmations=1,
            confirmed_at=datetime.now(UTC),
            is_current_version=False,
        )

        async def find(value: str) -> VerificationContext:
            del value
            return context

        audit, audit_session = _audit_dependencies()
        service = PublicVerificationService(
            gateway=Gateway(),
            find_by_token=find,
            find_by_number=find,
            find_by_transaction=find,
            audit=audit,
            audit_session=audit_session,
        )

        result = await service.verify_token("historical-qr-token")
        assert result.status is VerificationStatus.VALID
        assert result.version == 1

    asyncio.run(scenario())
