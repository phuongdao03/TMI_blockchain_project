import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.errors import (
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
    DossierVersion,
    EvidenceVisibility,
)
from app.modules.dossiers.service import DossierService
from app.modules.dossiers.types import CreateDossier, CreateEvidence
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION
from app.modules.reviews.precheck_service import PrecheckService

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
OUTBOX_KEY = b"review-outbox-encryption-key!!!!"


async def _setup() -> tuple[
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    User,
    User,
    MediaAsset,
    UUID,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    owner = User(
        id=uuid4(),
        email="owner@tmigroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    admin = User(
        id=uuid4(),
        email="admin@tmigroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    media = MediaAsset(
        id=uuid4(),
        owner_user_id=owner.id,
        cloudinary_public_id="evidence/precheck",
        cloudinary_version=1,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="ownership.pdf",
        mime_type="application/pdf",
        bytes=2048,
        sha256="a" * 64,
        hash_algorithm="SHA-256",
        hash_byte_length=2048,
        inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
        hash_storage_version=1,
        hash_computed_at=NOW,
        status=MediaStatus.ACTIVE,
    )
    async with session_factory() as session:
        session.add_all(
            [
                owner,
                admin,
                media,
                Category(
                    id=CATEGORY_ID,
                    code="DIGITAL_INTELLECTUAL_ASSET",
                    name="Tài sản trí tuệ số",
                ),
            ]
        )
        await session.commit()

    applicant = AuthPrincipal(
        user_id=owner.id,
        session_id=uuid4(),
        email=owner.email,
        roles=("USER",),
    )
    dossier_service = DossierService(session=session_factory(), clock=lambda: NOW)
    dossier = await dossier_service.create_dossier(
        applicant,
        CreateDossier(category_id=CATEGORY_ID, title="Tác phẩm tiền kiểm"),
    )
    await dossier_service.attach_evidence(
        applicant,
        dossier.id,
        CreateEvidence(
            media_asset_id=media.id,
            evidence_type="OWNERSHIP_DOCUMENT",
            title="Chứng cứ quyền sở hữu",
        ),
    )
    await dossier_service.submit_dossier(
        applicant,
        dossier.id,
        idempotency_key="submit-before-precheck",
    )
    await dossier_service.close()
    return session_factory, engine, owner, admin, media, dossier.id


def _principal(user: User, role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=(role,),
    )


def _cipher() -> OutboxPayloadCipher:
    return OutboxPayloadCipher(key=OUTBOX_KEY, key_id="test-review-key")


def test_precheck_and_supplement_clone_version_evidence_and_emit_event() -> None:
    async def exercise() -> None:
        session_factory, engine, owner, admin, _, dossier_id = await _setup()
        # A supplement draft must retain the server-owned role and visibility
        # of the submitted evidence it is derived from.
        async with session_factory() as session:
            async with session.begin():
                submitted_evidence = await session.scalar(
                    select(DossierEvidence).where(
                        DossierEvidence.dossier_id == dossier_id,
                        DossierEvidence.dossier_version_id.is_not(None),
                    )
                )
                assert submitted_evidence is not None
                submitted_evidence.evidence_role = "PUBLIC_PRESENTATION"
                submitted_evidence.access_scope = EvidenceVisibility.PUBLIC_PREVIEW
                submitted_evidence.is_public = True
        service = PrecheckService(
            session=session_factory(),
            payload_cipher=_cipher(),
            clock=lambda: NOW,
        )
        admin_principal = _principal(admin, "SUPER_ADMIN")

        precheck = await service.start_precheck(
            admin_principal,
            dossier_id,
            reason="Hồ sơ đã vào hàng tiền kiểm.",
        )
        supplemented = await service.request_supplement(
            admin_principal,
            dossier_id,
            reason="Cần tài liệu nguồn rõ hơn.",
        )

        assert precheck.status is DossierStatus.PRECHECK
        assert supplemented.status is DossierStatus.NEEDS_SUPPLEMENT

        async with session_factory() as session:
            evidences = tuple(
                (
                    await session.scalars(
                        select(DossierEvidence)
                        .where(DossierEvidence.dossier_id == dossier_id)
                        .order_by(DossierEvidence.dossier_version_id)
                    )
                ).all()
            )
            event = (await session.scalars(select(OutboxEvent))).one()
            history_count = await session.scalar(
                select(func.count()).select_from(DossierStatusHistory)
            )
            assert len(evidences) == 2
            assert {row.dossier_version_id is None for row in evidences} == {
                False,
                True,
            }
            draft_evidence = next(
                row for row in evidences if row.dossier_version_id is None
            )
            assert draft_evidence.evidence_role == "PUBLIC_PRESENTATION"
            assert draft_evidence.access_scope is EvidenceVisibility.PUBLIC_PREVIEW
            assert draft_evidence.is_public is True
            assert event.event_type == "dossier.supplement_requested"
            assert history_count == 3
            payload = json.loads(
                _cipher().decrypt(
                    nonce=event.payload_nonce,
                    ciphertext=event.payload_ciphertext,
                    event_type=event.event_type,
                    aggregate_id=event.aggregate_id,
                )
            )
            assert payload["recipient_user_id"] == str(owner.id)
            assert payload["reason"] == "Cần tài liệu nguồn rõ hơn."

        applicant_service = DossierService(
            session=session_factory(),
            clock=lambda: NOW,
        )
        resubmitted = await applicant_service.resubmit_dossier(
            _principal(owner, "USER"),
            dossier_id,
            idempotency_key="resubmit-after-supplement",
        )
        assert resubmitted.version.version_no == 2
        resubmitted_evidences = resubmitted.version.snapshot_json["evidences"]
        assert isinstance(resubmitted_evidences, list)
        assert len(resubmitted_evidences) == 1

        await applicant_service.close()
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_precheck_rejects_wrong_role_reason_and_invalid_transition_atomically() -> None:
    async def exercise() -> None:
        session_factory, engine, owner, admin, _, dossier_id = await _setup()
        service = PrecheckService(
            session=session_factory(),
            payload_cipher=_cipher(),
            clock=lambda: NOW,
        )

        with pytest.raises(DossierForbiddenError):
            await service.start_precheck(
                _principal(owner, "USER"),
                dossier_id,
                reason="Applicant cannot precheck.",
            )
        with pytest.raises(DossierValidationError):
            await service.start_precheck(
                _principal(admin, "SUPER_ADMIN"),
                dossier_id,
                reason=" ",
            )

        await service.start_precheck(
            _principal(admin, "SUPER_ADMIN"),
            dossier_id,
            reason="Start precheck.",
        )
        await service.pass_precheck(
            _principal(admin, "SUPER_ADMIN"),
            dossier_id,
            reason="Checklist passed.",
        )
        with pytest.raises(DossierInvalidStateError):
            await service.start_precheck(
                _principal(admin, "SUPER_ADMIN"),
                dossier_id,
                reason="Duplicate transition.",
            )

        async with session_factory() as session:
            history_count = await session.scalar(
                select(func.count()).select_from(DossierStatusHistory)
            )
            event_count = await session.scalar(
                select(func.count()).select_from(OutboxEvent)
            )
            version_count = await session.scalar(
                select(func.count()).select_from(DossierVersion)
            )
            assert history_count == 3
            assert event_count == 0
            assert version_count == 1

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
