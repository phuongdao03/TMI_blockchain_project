import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.main import create_application
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category
from app.modules.public.catalog_cache import public_catalog_cache_key
from app.modules.public.dependencies import enforce_public_rate_limit
from app.modules.public.detail_service import PublicWorkDetailService
from app.modules.public.editor_service import PublicWorkEditorService
from app.modules.public.errors import PublicWorkForbiddenError
from app.modules.public.media_service import PublicMediaService
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkSlugHistory,
    PublicWorkVisibility,
)
from app.modules.public.publication_dependencies import get_public_work_detail_service
from app.modules.public.publication_service import PublicationService
from app.modules.public.report_service import ContentReportService
from app.modules.public.schemas import (
    ContentReportAcceptedData,
    PublicMediaData,
    PublicSitemapEntryData,
    PublicWorkCardData,
    PublicWorkDetailProjectionData,
)
from app.modules.public.service import PublicCatalogService
from app.modules.public.taxonomy_service import TaxonomyService

BANNED_PUBLIC_NAMES = {
    "ownerUserId",
    "dossierId",
    "mediaAssetId",
    "cloudinaryPublicId",
    "objectKey",
    "reporterEmail",
    "reviewerNote",
    "identityDocument",
    "passwordHash",
    "privateKey",
}
PUBLIC_RESPONSE_MODELS = (
    PublicWorkCardData,
    PublicWorkDetailProjectionData,
    PublicMediaData,
    PublicSitemapEntryData,
    ContentReportAcceptedData,
)


class MissingDetailService:
    async def get(self, slug: str) -> None:
        del slug
        return None


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="security-gate@example.test",
        roles=roles,
    )


def test_public_contracts_are_strict_allowlists_and_metadata_is_filtered() -> None:
    for model in PUBLIC_RESPONSE_MODELS:
        schema_text = json.dumps(model.model_json_schema(), sort_keys=True)
        assert model.model_config.get("extra") == "forbid"
        assert BANNED_PUBLIC_NAMES.isdisjoint(schema_text.split('"'))

    with pytest.raises(ValidationError):
        PublicMediaData.model_validate(
            {
                "id": str(uuid4()),
                "kind": "IMAGE",
                "sortOrder": 0,
                "caption": None,
                "altText": "Safe public image",
                "url": "https://cdn.example.test/public/safe.webp",
                "mimeType": "image/webp",
                "width": 640,
                "height": 480,
                "durationMs": None,
                "isThumbnail": True,
                "objectKey": "restricted/source-object-key",
            }
        )

    metadata = PublicCatalogService._public_metadata(
        {
            "schemaVersion": 1,
            "asset": {"title": "Public title"},
            "ownerUserId": "restricted-owner",
            "reviewerNote": "restricted-review",
            "privateKey": "restricted-secret",
        }
    )
    assert metadata == {
        "schemaVersion": 1,
        "asset": {"title": "Public title"},
    }

    cache_key = public_catalog_cache_key(
        {"query": "private-person@example.test", "page": 1}
    )
    assert "private-person" not in cache_key
    assert "@" not in cache_key


def test_unknown_uuid_slug_enumeration_is_indistinguishable_and_bounded() -> None:
    app = create_application()
    app.dependency_overrides[get_public_work_detail_service] = MissingDetailService
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    request_id = "8fe11734-553b-4447-ad8b-a9c2a858f075"
    candidates = (str(uuid4()), "unknown-public-slug")
    try:
        with (
            patch("app.core.middleware.logger.info") as log_info,
            TestClient(app) as client,
        ):
            responses = [
                client.get(
                    f"/api/v1/public/works/{candidate}",
                    headers={"X-Request-ID": request_id},
                )
                for candidate in candidates
            ]
            oversized = client.get(
                f"/api/v1/public/works/{'a' * 181}",
                headers={"X-Request-ID": request_id},
            )
        assert [response.status_code for response in responses] == [404, 404]
        assert responses[0].json() == responses[1].json()
        assert all(
            response.headers["Cache-Control"] == "no-store" for response in responses
        )
        assert oversized.status_code == 422
        actions = [call.kwargs["extra"]["action"] for call in log_info.call_args_list]
        assert actions == ["GET /api/v1/public/works/{slug}"] * 3
        assert all(candidate not in " ".join(actions) for candidate in candidates)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "guard",
    (
        PublicationService._require_admin,
        PublicWorkEditorService._require_editor,
        TaxonomyService._require_admin,
        PublicMediaService._require_admin,
        ContentReportService._require_admin,
    ),
)
def test_public_catalog_admin_rbac_matrix(guard: object) -> None:
    assert callable(guard)
    for role in ("VIEWER", "USER", "MODERATOR"):
        with pytest.raises(PublicWorkForbiddenError):
            guard(_principal(role))
    guard(_principal("SUPER_ADMIN"))
    guard(_principal("SUPER_ADMIN"))


def test_serializer_snapshot_contains_only_public_detail_fields() -> None:
    data = PublicWorkDetailProjectionData.model_validate(
        {
            "id": str(uuid4()),
            "slug": "safe-work",
            "title": "Safe work",
            "shortDescription": "Approved public description",
            "fullDescription": None,
            "authorDisplayName": None,
            "organizationDisplayName": None,
            "categoryName": "Art",
            "categorySlug": "art",
            "tags": [],
            "publishedAt": datetime(2026, 8, 1, tzinfo=UTC).isoformat(),
            "visibility": "PUBLIC",
            "certificate": None,
            "proof": None,
            "media": [],
            "relatedWorks": [],
            "canonicalSlug": "safe-work",
            "redirected": False,
        }
    ).model_dump(mode="json", by_alias=True)
    assert set(data) == {
        "id",
        "slug",
        "title",
        "shortDescription",
        "fullDescription",
        "authorDisplayName",
        "organizationDisplayName",
        "categoryName",
        "categorySlug",
        "tags",
        "publishedAt",
        "visibility",
        "certificate",
        "proof",
        "media",
        "relatedWorks",
        "canonicalSlug",
        "redirected",
    }


def test_every_status_visibility_combination_and_cached_suspend_is_safe(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = (tmp_path / "visibility.sqlite3").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        slugs: dict[tuple[PublicationStatus, PublicWorkVisibility], str] = {}
        work_ids: dict[tuple[PublicationStatus, PublicWorkVisibility], UUID] = {}
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="SECURITY",
                        name="Security",
                        slug="security",
                    )
                )
                for status in PublicationStatus:
                    for visibility in PublicWorkVisibility:
                        slug = f"{status.value.lower()}-{visibility.value.lower()}"
                        slugs[(status, visibility)] = slug
                        work_id = uuid4()
                        work = PublicWork(
                            id=work_id,
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug=slug,
                            title=f"Visibility {slug}",
                            short_description="Approved public description",
                            category_id=category_id,
                            publication_status=status,
                            visibility=visibility,
                            published_at=datetime(2026, 8, 1, tzinfo=UTC),
                        )
                        work_ids[(status, visibility)] = work_id
                        session.add(work)
                        if (
                            status is PublicationStatus.PUBLISHED
                            and visibility is PublicWorkVisibility.PUBLIC
                        ):
                            session.add(
                                PublicWorkSlugHistory(
                                    public_work_id=work.id,
                                    slug="historical-public-slug",
                                )
                            )

            cache = MemoryCache()
            service = PublicWorkDetailService(session, cache=cache)
            for combination, slug in slugs.items():
                detail = await service.get(slug)
                expected = combination[0] is PublicationStatus.PUBLISHED and (
                    combination[1]
                    in {PublicWorkVisibility.PUBLIC, PublicWorkVisibility.UNLISTED}
                )
                assert (detail is not None) is expected

            old = await service.get("historical-public-slug")
            assert old is not None and old.redirected
            public_slug = slugs[
                (PublicationStatus.PUBLISHED, PublicWorkVisibility.PUBLIC)
            ]
            cached = await service.get(public_slug)
            assert cached is not None
            async with session.begin():
                stored_work = await session.get(
                    PublicWork,
                    work_ids[
                        (PublicationStatus.PUBLISHED, PublicWorkVisibility.PUBLIC)
                    ],
                )
                assert stored_work is not None
                stored_work.publication_status = PublicationStatus.SUSPENDED
                stored_work.visibility = PublicWorkVisibility.PRIVATE
            assert await service.get(public_slug) is None
        await engine.dispose()

    asyncio.run(exercise())
