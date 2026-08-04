import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.public.editor_service import (
    PublicWorkEditorInput,
    PublicWorkEditorService,
)
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    PublicWorkMetadataValidationError,
    PublicWorkVersionConflictError,
)
from app.modules.public.models import PublicWorkSlugHistory
from app.tests.test_publication_workflow import _cipher, _principal, _seed


def test_editor_permissions_validation_version_slug_history_and_preview(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'editor.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            work_id, owner_id = await _seed(session)
            service = PublicWorkEditorService(
                session=session,
                audit=AuditService(session),
                payload_cipher=_cipher(),
            )
            applicant = _principal(owner_id, "APPLICANT")
            admin = _principal(owner_id, "CONTENT_ADMIN")
            with pytest.raises(PublicWorkForbiddenError):
                await service.list(
                    applicant, query=None, status=None, page=1, page_size=20
                )
            rows, total = await service.list(
                admin, query="approved", status=None, page=1, page_size=20
            )
            assert total == 1
            assert rows[0].id == work_id
            category_id = rows[0].category_id
            visibility = rows[0].visibility
            thumbnail_media_id = rows[0].thumbnail_media_id

            with pytest.raises(PublicWorkMetadataValidationError):
                await service.update(
                    admin,
                    work_id,
                    PublicWorkEditorInput(
                        expected_version=1,
                        slug="admin",
                        title="Approved work",
                        short_description="Approved public summary",
                        full_description=None,
                        author_display_name=None,
                        category_id=category_id,
                        tag_ids=(),
                        visibility=visibility,
                        thumbnail_media_id=thumbnail_media_id,
                    ),
                    request_id="invalid-slug",
                )
            updated = await service.update(
                admin,
                work_id,
                PublicWorkEditorInput(
                    expected_version=1,
                    slug="approved-work-curated",
                    title="Approved work — curated",
                    short_description="Public summary for catalog visitors.",
                    full_description="A plain-text editorial description.",
                    author_display_name="TMI Studio",
                    category_id=category_id,
                    tag_ids=(),
                    visibility=visibility,
                    thumbnail_media_id=thumbnail_media_id,
                ),
                request_id="editor-save",
            )
            assert updated.version == 2
            assert updated.slug == "approved-work-curated"
            assert await session.scalar(
                select(func.count()).select_from(PublicWorkSlugHistory)
            ) == 1
            await session.rollback()
            with pytest.raises(PublicWorkVersionConflictError):
                await service.update(
                    admin,
                    work_id,
                    PublicWorkEditorInput(
                        expected_version=1,
                        slug="stale-write",
                        title="Stale write",
                        short_description="This must not be persisted.",
                        full_description=None,
                        author_display_name=None,
                        category_id=category_id,
                        tag_ids=(),
                        visibility=visibility,
                        thumbnail_media_id=thumbnail_media_id,
                    ),
                    request_id="stale",
                )
            editor = await service.get(admin, work_id)
            assert editor.checklist
            preview = await service.preview(admin, work_id)
            serialized = repr(preview)
            assert "owner_user_id" not in serialized
            assert "cloudinary" not in serialized
            assert preview.title == "Approved work — curated"
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 1
        await engine.dispose()

    asyncio.run(exercise())
