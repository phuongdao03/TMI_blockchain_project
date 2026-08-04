import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.blockchain.models import Certificate, CertificateStatus
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.public.backfill import PublicWorkDraftBackfill
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkSlugHistory,
    PublicWorkVisibility,
)


def test_public_work_repository_and_draft_backfill_are_safe(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-work.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        owner_id = uuid4()
        category_id = uuid4()
        eligible_dossier_id = uuid4()
        incomplete_dossier_id = uuid4()
        certificate_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="owner@catalog.test",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    )
                )
                session.add(
                    Category(
                        id=category_id,
                        code="PUBLIC_WORK",
                        name="Public work",
                    )
                )
                session.add_all(
                    [
                        Dossier(
                            id=eligible_dossier_id,
                            code="DOS-ELIGIBLE",
                            owner_user_id=owner_id,
                            category_id=category_id,
                            title="Tác phẩm đủ điều kiện",
                            slug="tac-pham-du-dieu-kien",
                            summary="Mô tả công khai đã được duyệt.",
                            _status=DossierStatus.CERTIFICATE_ISSUED,
                        ),
                        Dossier(
                            id=incomplete_dossier_id,
                            code="DOS-INCOMPLETE",
                            owner_user_id=owner_id,
                            category_id=category_id,
                            title="Thiếu mô tả",
                            slug=None,
                            summary=None,
                            _status=DossierStatus.CERTIFICATE_ISSUED,
                        ),
                    ]
                )
                session.add(
                    Certificate(
                        id=certificate_id,
                        certificate_number="TMI-2026-1501",
                        dossier_id=eligible_dossier_id,
                        current_version_no=1,
                        status=CertificateStatus.ACTIVE,
                        issued_at=datetime(2026, 7, 31, tzinfo=UTC),
                        public_token_hash="a" * 64,
                        qr_payload="https://example.test/verify/public",
                    )
                )

            backfill = PublicWorkDraftBackfill(session, batch_size=1)
            dry_run = await backfill.run(dry_run=True)
            assert dry_run.scanned == 2
            assert dry_run.eligible == 1
            assert dry_run.created == 0
            assert dry_run.skipped == 1
            assert dry_run.skip_reasons == {"missing_public_description": 1}
            assert (
                await session.scalar(select(func.count()).select_from(PublicWork)) == 0
            )

            applied = await backfill.run(dry_run=False)
            assert applied.created == 1
            work = await PublicWorkRepository(session).get_by_dossier_id(
                eligible_dossier_id
            )
            assert work is not None
            assert work.publication_status is PublicationStatus.DRAFT
            assert work.visibility is PublicWorkVisibility.PRIVATE
            assert work.certificate_id == certificate_id
            assert work.published_at is None
            assert work.slug == "tac-pham-du-dieu-kien"

            history = PublicWorkSlugHistory(
                public_work_id=work.id,
                slug="slug-cu",
            )
            PublicWorkRepository(session).add_slug_history(history)
            await session.commit()
            resolved = await PublicWorkRepository(session).resolve_slug("slug-cu")
            assert resolved is not None
            assert resolved[0].id == work.id
            assert resolved[1] is True

        await engine.dispose()

    asyncio.run(exercise())
