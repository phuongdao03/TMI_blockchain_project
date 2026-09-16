import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.dossiers.models import Dossier, DossierVersion
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.editor_service import (
    PublicWorkEditorInput,
    PublicWorkEditorService,
)
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    PublicWorkMetadataValidationError,
    PublicWorkVersionConflictError,
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
    PublicWorkSlugHistory,
)
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
            async with session.begin():
                work = await session.get(PublicWork, work_id)
                assert work is not None
                dossier = await session.get(Dossier, work.dossier_id)
                assert dossier is not None
                dossier.current_version_no = 1
                session.add(
                    DossierVersion(
                        dossier_id=dossier.id,
                        version_no=1,
                        snapshot_json={
                            "dossier": {
                                "title": "Tiêu đề người dùng",
                                "summary": "Mô tả người dùng",
                                "dossierType": {
                                    "formData": {"privateId": "must-not-leak"},
                                    "publicFields": [
                                        {
                                            "key": "artistName",
                                            "label": "Tác giả",
                                            "value": "Nguyễn Văn A",
                                        }
                                    ],
                                },
                            }
                        },
                        canonical_hash="a" * 64,
                        submitted_by=owner_id,
                    )
                )
                video = MediaAsset(
                    owner_user_id=owner_id,
                    cloudinary_public_id="private/owner/editor-video-cover",
                    resource_type="video",
                    access_mode="authenticated",
                    original_filename="cover.mp4",
                    mime_type="video/mp4",
                    bytes=4096,
                    status=MediaStatus.ACTIVE,
                )
                session.add(video)
                await session.flush()
                video_id = video.id
                session.add(
                    PublicWorkMedia(
                        public_work_id=work_id,
                        media_asset_id=video_id,
                        media_kind=PublicMediaKind.VIDEO,
                        sort_order=0,
                        derivative_status=DerivativeStatus.READY,
                        derivative_url=(
                            "https://res.cloudinary.com/demo/video/upload/"
                            "public/editor-video-cover.mp4"
                        ),
                        derivative_mime_type="video/mp4",
                    )
                )
            service = PublicWorkEditorService(
                session=session,
                audit=AuditService(session),
                payload_cipher=_cipher(),
            )
            applicant = _principal(owner_id, "USER")
            admin = _principal(owner_id, "SUPER_ADMIN")
            with pytest.raises(PublicWorkForbiddenError):
                await service.list(
                    applicant, query=None, status=None, page=1, page_size=20
                )
            rows, total = await service.list(
                admin, query="approved", status=None, page=1, page_size=20
            )
            assert total == 1
            assert rows[0].work.id == work_id
            assert rows[0].dossier_code == "DOS-1502"
            category_id = rows[0].work.category_id
            visibility = rows[0].work.visibility
            thumbnail_media_id = rows[0].work.thumbnail_media_id

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
                    thumbnail_media_id=video_id,
                ),
                request_id="editor-save",
            )
            assert updated.version == 2
            assert updated.slug == "approved-work-curated"
            assert updated.thumbnail_media_id == video_id
            assert (
                await session.scalar(
                    select(func.count()).select_from(PublicWorkSlugHistory)
                )
                == 1
            )
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
            assert editor.source_version_no == 1
            assert editor.source_fields[0].label == "Tiêu đề hồ sơ"
            assert editor.source_fields[0].value == "Tiêu đề người dùng"
            assert editor.source_fields[-1].value == "Nguyễn Văn A"
            assert "must-not-leak" not in repr(editor)
            preview = await service.preview(admin, work_id)
            assert preview.certificate is not None
            assert preview.certificate.certificate_number
            serialized = repr(preview)
            assert "owner_user_id" not in serialized
            assert "private/owner" not in serialized
            assert preview.media[0].is_thumbnail is True
            assert preview.media[0].poster_url is not None
            assert preview.title == "Approved work — curated"
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 1
        await engine.dispose()

    asyncio.run(exercise())
