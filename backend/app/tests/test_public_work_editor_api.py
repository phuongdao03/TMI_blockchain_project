from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.editor_service import (
    ChecklistItem,
    PublicWorkEditorInput,
    PublicWorkEditorView,
    PublicWorkPreviewView,
)
from app.modules.public.media_service import PublicMediaView
from app.modules.public.models import (
    PublicationStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.publication_dependencies import get_public_work_editor_service


class StubEditorService:
    def __init__(self) -> None:
        self.work = PublicWork(
            id=uuid4(),
            dossier_id=uuid4(),
            certificate_id=uuid4(),
            owner_user_id=uuid4(),
            slug="api-editor-work",
            title="API editor work",
            short_description="An approved public work description.",
            full_description="Editorial copy safe for public preview.",
            author_display_name="TMI Studio",
            category_id=uuid4(),
            publication_status=PublicationStatus.DRAFT,
            visibility=PublicWorkVisibility.PUBLIC,
            published_at=None,
            version=3,
        )
        self.updated: PublicWorkEditorInput | None = None

    async def list(
        self, _principal: object, **_filters: object
    ) -> tuple[tuple[PublicWork, ...], int]:
        return (self.work,), 1

    async def get(
        self, _principal: object, _work_id: UUID
    ) -> PublicWorkEditorView:
        return PublicWorkEditorView(
            work=self.work,
            category_name="Digital Art",
            tag_ids=(),
            checklist=(ChecklistItem("TITLE_REQUIRED", True),),
        )

    async def update(
        self,
        _principal: object,
        _work_id: UUID,
        data: PublicWorkEditorInput,
        **_context: object,
    ) -> PublicWork:
        self.updated = data
        self.work.slug = data.slug
        self.work.title = data.title
        self.work.version += 1
        return self.work

    async def preview(
        self, _principal: object, _work_id: UUID
    ) -> PublicWorkPreviewView:
        return PublicWorkPreviewView(
            slug=self.work.slug,
            title=self.work.title,
            short_description=self.work.short_description,
            full_description=self.work.full_description,
            author_display_name=self.work.author_display_name,
            category_name="Digital Art",
            media=(
                PublicMediaView(
                    id=uuid4(),
                    kind=PublicMediaKind.IMAGE,
                    sort_order=0,
                    caption="Public caption",
                    alt_text="Artwork",
                    url="https://cdn.example.test/public/art.webp",
                    mime_type="image/webp",
                    width=1200,
                    height=800,
                    duration_ms=None,
                    is_thumbnail=True,
                ),
            ),
            can_publish=True,
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="content-admin@example.test",
        roles=("CONTENT_ADMIN",),
    )


def test_editor_api_contract_and_preview_privacy() -> None:
    service = StubEditorService()
    app = create_application()
    app.dependency_overrides[get_public_work_editor_service] = lambda: service
    app.dependency_overrides[get_current_principal] = _principal
    app.dependency_overrides[get_csrf_protected_principal] = _principal
    try:
        with TestClient(app) as client:
            listed = client.get(
                "/api/v1/admin/public-works",
                params={"status": "DRAFT", "pageSize": 10},
            )
            assert listed.status_code == 200
            assert listed.json()["meta"]["total"] == 1

            detail = client.get(
                f"/api/v1/admin/public-works/{service.work.id}"
            )
            assert detail.status_code == 200
            assert detail.json()["data"]["checklist"] == [
                {"code": "TITLE_REQUIRED", "passed": True}
            ]

            updated = client.patch(
                f"/api/v1/admin/public-works/{service.work.id}",
                json={
                    "expectedVersion": 3,
                    "slug": "curated-work",
                    "title": "Curated work",
                    "shortDescription": service.work.short_description,
                    "fullDescription": service.work.full_description,
                    "authorDisplayName": "TMI Studio",
                    "categoryId": str(service.work.category_id),
                    "visibility": "PUBLIC",
                    "thumbnailMediaId": None,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["version"] == 4
            assert service.updated is not None

            preview = client.get(
                f"/api/v1/admin/public-works/{service.work.id}/preview"
            )
            assert preview.status_code == 200
            preview_data = preview.json()["data"]
            assert preview_data["canPublish"] is True
            assert preview_data["media"][0]["url"].endswith("art.webp")
            serialized = str(preview_data).lower()
            assert "owner_user_id" not in serialized
            assert "public_id" not in serialized

        paths = app.openapi()["paths"]
        assert "/api/v1/admin/public-works" in paths
        assert "/api/v1/admin/public-works/{work_id}/preview" in paths
    finally:
        app.dependency_overrides.clear()


def test_editor_api_rejects_invalid_payload_before_service() -> None:
    service = StubEditorService()
    app = create_application()
    app.dependency_overrides[get_public_work_editor_service] = lambda: service
    app.dependency_overrides[get_current_principal] = _principal
    app.dependency_overrides[get_csrf_protected_principal] = _principal
    try:
        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/admin/public-works/{service.work.id}",
                json={
                    "expectedVersion": 0,
                    "slug": "x",
                    "title": "x",
                    "shortDescription": "short",
                    "categoryId": str(service.work.category_id),
                    "visibility": "PUBLIC",
                },
            )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert service.updated is None
    finally:
        app.dependency_overrides.clear()
