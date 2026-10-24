import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
    get_optional_current_principal,
)
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.admin_service import CommunityAdminService
from app.modules.community.errors import CommunityRateLimitedError
from app.modules.community.models import (
    CommunityBookmark,
    CommunityCategory,
    CommunityComment,
    CommunityCommentLike,
    CommunityLike,
    CommunityMemberRestriction,
    CommunityModerationAction,
    CommunityModerationEvent,
    CommunityModerationEventAction,
    CommunityModerationLog,
    CommunityPost,
    CommunityPostMedia,
    CommunityPostStatus,
    CommunityProfile,
    CommunityReport,
)
from app.modules.community.rate_limit import (
    enforce_community_content_write_rate_limit,
    enforce_community_engagement_write_rate_limit,
    enforce_community_report_write_rate_limit,
)
from app.modules.community.retention import CommunityMediaRetentionService
from app.modules.dossiers.models import Category
from app.modules.media.dependencies import get_media_service
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.types import MediaContentView
from app.modules.notifications.models import Notification
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.users.models import UserProfile

OWNER_ID = UUID("50000000-0000-0000-0000-000000000001")
OTHER_ID = UUID("50000000-0000-0000-0000-000000000002")
CATEGORY_ID = UUID("60000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)


class CommunityTestApp:
    def __init__(self, tmp_path: Path) -> None:
        database_path = tmp_path / f"community-{uuid4()}.sqlite3"
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path.as_posix()}",
            poolclass=NullPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.principal = _principal(OWNER_ID)
        self.viewer_principal: AuthPrincipal | None = None
        self.app = create_application()

        async def initialize() -> None:
            async with self.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with self.sessions() as session:
                session.add_all(
                    [
                        User(
                            id=OWNER_ID,
                            email="private-owner@example.test",
                            status=UserStatus.ACTIVE,
                        ),
                        User(
                            id=OTHER_ID,
                            email="private-other@example.test",
                            status=UserStatus.ACTIVE,
                        ),
                        UserProfile(
                            user_id=OWNER_ID,
                            full_name="Private legal name",
                            phone_encrypted=b"private-phone",
                            display_name="Public community name",
                        ),
                        CommunityProfile(
                            user_id=OWNER_ID,
                            username="community-owner",
                            display_name="Public community name",
                        ),
                        CommunityCategory(
                            id=CATEGORY_ID,
                            name="Thảo luận chung",
                            slug="general",
                            description="General topics.",
                            icon=None,
                            sort_order=0,
                            is_active=True,
                        ),
                    ]
                )
                await session.commit()

        asyncio.run(initialize())

        async def session_override() -> AsyncIterator[AsyncSession]:
            async with self.sessions() as session:
                yield session

        self.app.dependency_overrides[get_session] = session_override
        self.app.dependency_overrides[get_current_principal] = lambda: self.principal
        self.app.dependency_overrides[get_optional_current_principal] = lambda: (
            self.viewer_principal
        )
        self.app.dependency_overrides[get_csrf_protected_principal] = lambda: (
            self.principal
        )
        self.app.dependency_overrides[enforce_community_content_write_rate_limit] = (
            lambda: None
        )
        self.app.dependency_overrides[enforce_community_engagement_write_rate_limit] = (
            lambda: None
        )
        self.app.dependency_overrides[enforce_community_report_write_rate_limit] = (
            lambda: None
        )
        self.client = TestClient(self.app)

    def set_principal(
        self,
        user_id: UUID,
        *,
        roles: tuple[str, ...] = ("USER",),
        permissions: tuple[str, ...] = (),
    ) -> None:
        self.principal = _principal(user_id, roles=roles, permissions=permissions)

    def close(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()
        asyncio.run(self.engine.dispose())


class _NoopMediaAssetDeleter:
    async def delete_community_post_asset(
        self,
        _principal: AuthPrincipal,
        _media_id: UUID,
        *,
        owner_user_id: UUID,
    ) -> None:
        return None


def _principal(
    user_id: UUID,
    *,
    roles: tuple[str, ...] = ("USER",),
    permissions: tuple[str, ...] = (),
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email="must-not-be-public@example.test",
        roles=roles,
        permissions=permissions,
    )


def _insert_post(
    app: CommunityTestApp,
    *,
    slug: str,
    status: CommunityPostStatus,
    published_at: datetime | None = None,
    author_id: UUID = OWNER_ID,
    title: str | None = None,
    content: str | None = None,
    related_work_id: UUID | None = None,
) -> UUID:
    post_id = uuid4()

    async def insert() -> None:
        async with app.sessions() as session:
            session.add(
                CommunityPost(
                    id=post_id,
                    author_user_id=author_id,
                    category_id=CATEGORY_ID,
                    related_work_id=related_work_id,
                    title=title or slug.replace("-", " ").title(),
                    slug=slug,
                    content=content or f"Body for {slug}.",
                    excerpt=(content or f"Body for {slug}.")[:320],
                    status=status,
                    published_at=published_at,
                    submitted_at=NOW if status is CommunityPostStatus.PENDING else None,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            await session.commit()

    asyncio.run(insert())
    return post_id


def test_community_rate_limit_uses_standard_429_error_envelope(
    tmp_path: Path,
) -> None:
    app = CommunityTestApp(tmp_path)

    def limited() -> None:
        raise CommunityRateLimitedError(retry_after_seconds=17)

    app.app.dependency_overrides[enforce_community_content_write_rate_limit] = limited
    try:
        response = app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Rate limited draft",
                "content": "The write must stop before mutation.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "COMMUNITY_RATE_LIMITED"
        assert response.json()["error"]["details"] == {"retry_after_seconds": 17}
    finally:
        app.close()


def _insert_community_image(
    app: CommunityTestApp,
    *,
    owner_id: UUID = OWNER_ID,
    purpose: str | None = "COMMUNITY_POST",
    status: MediaStatus = MediaStatus.ACTIVE,
    mime_type: str = "image/png",
    size: int = 2_048,
    inspected: bool = True,
) -> UUID:
    media_id = uuid4()
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }.get(mime_type, "bin")

    async def insert() -> None:
        async with app.sessions() as session:
            session.add(
                MediaAsset(
                    id=media_id,
                    owner_user_id=owner_id,
                    purpose=purpose,
                    cloudinary_public_id=f"community-test/{media_id}",
                    resource_type="image",
                    access_mode="authenticated",
                    original_filename=f"post-image.{extension}",
                    mime_type=mime_type,
                    bytes=size,
                    width=640,
                    height=480,
                    sha256="a" * 64,
                    status=status,
                    inspected_at=NOW if inspected else None,
                )
            )
            await session.commit()

    asyncio.run(insert())
    return media_id


def _insert_public_work(
    app: CommunityTestApp,
    *,
    slug: str,
    status: PublicationStatus = PublicationStatus.PUBLISHED,
    visibility: PublicWorkVisibility = PublicWorkVisibility.PUBLIC,
) -> UUID:
    work_id = uuid4()
    category_id = uuid4()

    async def insert() -> None:
        async with app.sessions() as session:
            session.add_all(
                [
                    Category(
                        id=category_id,
                        code=f"COMM-{category_id.hex[:12]}",
                        name="Community linked work",
                        slug=f"community-{category_id.hex[:12]}",
                    ),
                    PublicWork(
                        id=work_id,
                        dossier_id=uuid4(),
                        owner_user_id=OWNER_ID,
                        category_id=category_id,
                        slug=slug,
                        title=f"Public title: {slug}",
                        short_description="Must never enter community DTO.",
                        full_description="Private nomination narrative.",
                        publication_status=status,
                        visibility=visibility,
                        published_at=(
                            NOW if status is PublicationStatus.PUBLISHED else None
                        ),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(insert())
    return work_id


def _moderation_logs(
    app: CommunityTestApp,
    post_id: UUID,
) -> tuple[CommunityModerationLog, ...]:
    async def query() -> tuple[CommunityModerationLog, ...]:
        async with app.sessions() as session:
            rows = await session.scalars(
                select(CommunityModerationLog)
                .where(CommunityModerationLog.post_id == post_id)
                .order_by(CommunityModerationLog.created_at)
            )
            return tuple(rows.all())

    return asyncio.run(query())


def test_public_categories_feed_and_detail_filter_status_and_private_fields(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        _insert_post(
            test_app,
            slug="older-published",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW - timedelta(days=1),
        )
        _insert_post(
            test_app,
            slug="newer-published",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        for status in (
            CommunityPostStatus.DRAFT,
            CommunityPostStatus.PENDING,
            CommunityPostStatus.REJECTED,
            CommunityPostStatus.HIDDEN,
            CommunityPostStatus.DELETED,
        ):
            _insert_post(
                test_app,
                slug=f"private-{status.value.lower()}",
                status=status,
            )

        categories = test_app.client.get("/api/v1/community/categories")
        assert categories.status_code == 200
        assert categories.json()["data"] == [
            {
                "id": str(CATEGORY_ID),
                "name": "Thảo luận chung",
                "slug": "general",
                "description": "General topics.",
                "icon": None,
                "sortOrder": 0,
            }
        ]

        page = test_app.client.get(
            "/api/v1/community/posts?page=1&pageSize=1&category=general"
        )
        assert page.status_code == 200
        assert page.json()["meta"] | {"requestId": "ignored"} == {
            "requestId": "ignored",
            "page": 1,
            "pageSize": 1,
            "total": 2,
        }
        item = page.json()["data"][0]
        assert item["slug"] == "newer-published"
        assert item["author"] == {
            "id": str(OWNER_ID),
            "username": "community-owner",
            "displayName": "Public community name",
            "avatarUrl": None,
            "roleLabel": None,
            "isAdmin": False,
            "membershipTier": "MEMBER",
        }
        serialized = str(page.json())
        assert "private-owner@example.test" not in serialized
        assert "private-phone" not in serialized
        assert "private legal name" not in serialized.lower()
        assert "employment" not in serialized.lower()
        assert set(item) == {
            "id",
            "slug",
            "title",
            "excerpt",
            "category",
            "author",
            "tags",
            "publishedAt",
            "viewCount",
            "isPinned",
            "likeCount",
            "commentCount",
            "viewerHasLiked",
            "viewerHasBookmarked",
            "relatedWork",
            "images",
        }
        assert item["viewCount"] == 0
        assert item["isPinned"] is False
        assert item["likeCount"] == 0
        assert item["commentCount"] == 0
        assert item["viewerHasLiked"] is False
        assert item["viewerHasBookmarked"] is False

        second_page = test_app.client.get(
            "/api/v1/community/posts?page=2&pageSize=1&category=general"
        )
        assert second_page.json()["data"][0]["slug"] == "older-published"

        detail = test_app.client.get("/api/v1/community/posts/newer-published")
        assert detail.status_code == 200
        assert detail.json()["data"]["content"] == "Body for newer-published."
        assert detail.json()["data"]["author"] == {
            "id": str(OWNER_ID),
            "username": "community-owner",
            "displayName": "Public community name",
            "avatarUrl": None,
            "roleLabel": None,
            "isAdmin": False,
            "membershipTier": "MEMBER",
        }

        for status in (
            "draft",
            "pending",
            "rejected",
            "hidden",
            "deleted",
        ):
            hidden = test_app.client.get(f"/api/v1/community/posts/private-{status}")
            assert hidden.status_code == 404
    finally:
        test_app.close()


def test_owner_draft_submit_publishes_immediately_and_can_be_edited(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    test_app.app.dependency_overrides[get_media_service] = lambda: (
        _NoopMediaAssetDeleter()
    )
    try:
        payload = {
            "title": "A community story",
            "content": "A plain text story with **Markdown**.",
            "categoryId": str(CATEGORY_ID),
        }
        unsafe = test_app.client.post(
            "/api/v1/community/posts",
            json={**payload, "content": "<script>alert(1)</script>"},
        )
        assert unsafe.status_code == 422
        created = test_app.client.post("/api/v1/community/posts", json=payload)
        assert created.status_code == 201, created.text
        data = created.json()["data"]
        assert data["status"] == "DRAFT"
        post_id = data["id"]
        slug = data["slug"]
        assert test_app.client.get(f"/api/v1/community/posts/{slug}").status_code == 404

        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200
        assert submitted.json()["data"]["status"] == "PUBLISHED"
        assert test_app.client.get(f"/api/v1/community/posts/{slug}").status_code == 200

        test_app.set_principal(OTHER_ID)
        denied = test_app.client.patch(
            f"/api/v1/community/posts/{post_id}",
            json={**payload, "title": "Changed by another member"},
        )
        assert denied.status_code == 403
        denied_delete = test_app.client.delete(f"/api/v1/community/posts/{post_id}")
        assert denied_delete.status_code == 403

        test_app.set_principal(OWNER_ID)
        owner_edit = test_app.client.patch(
            f"/api/v1/community/posts/{post_id}",
            json={**payload, "title": "Owner edit after publishing"},
        )
        assert owner_edit.status_code == 200
        assert owner_edit.json()["data"]["status"] == "PUBLISHED"
        published_slug = owner_edit.json()["data"]["slug"]
        assert (
            test_app.client.get(f"/api/v1/community/posts/{published_slug}").status_code
            == 200
        )

        test_app.set_principal(OWNER_ID)
        deleted = test_app.client.delete(f"/api/v1/community/posts/{post_id}")
        assert deleted.status_code == 204
        assert test_app.client.get(f"/api/v1/community/posts/{slug}").status_code == 404
        logs = _moderation_logs(test_app, UUID(post_id))
        assert logs == ()

        async def read_delete_event() -> CommunityModerationEvent:
            async with test_app.sessions() as session:
                events = await session.scalars(
                    select(CommunityModerationEvent).where(
                        CommunityModerationEvent.target_type == "POST",
                        CommunityModerationEvent.target_id == post_id,
                    )
                )
                rows = events.all()
                assert len(rows) == 1
                return rows[0]

        delete_event = asyncio.run(read_delete_event())
        assert delete_event.action == CommunityModerationEventAction.OWNER_DELETED
        assert delete_event.reason is None
        assert delete_event.event_data is None
        assert delete_event.request_id
    finally:
        test_app.close()


def test_moderation_requires_explicit_permission_after_publication(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        created = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Review me",
                "content": "A post for review.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        post_id = created.json()["data"]["id"]
        test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")

        test_app.set_principal(OTHER_ID, roles=("MODERATOR",))
        forbidden = test_app.client.get("/api/v1/admin/community/posts")
        assert forbidden.status_code == 403
        forbidden_hide = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/hide",
            json={"reason": "Confirmed abuse."},
        )
        assert forbidden_hide.status_code == 403

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        workspace = test_app.client.get(
            "/api/v1/admin/community/posts?status=PUBLISHED"
        )
        assert workspace.status_code == 200, workspace.text
        assert workspace.json()["meta"]["total"] == 1
        assert workspace.json()["data"][0]["id"] == post_id

        hidden = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/hide",
            json={"reason": "Confirmed abuse."},
        )
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["data"]["state"] == "HIDDEN"
        assert (
            test_app.client.get("/api/v1/community/posts/review-me").status_code == 404
        )
        history = test_app.client.get(
            "/api/v1/admin/community/moderation-history"
            f"?targetType=POST&targetId={post_id}"
        )
        assert history.status_code == 200, history.text
        assert "POST_HIDDEN" in {event["action"] for event in history.json()["data"]}
    finally:
        test_app.close()


def test_super_admin_can_remove_a_published_post(tmp_path: Path) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        created = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Super admin review",
                "content": "Ready for publication.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        post_id = created.json()["data"]["id"]
        test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        test_app.set_principal(OTHER_ID, roles=("SUPER_ADMIN",))
        response = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/hide",
            json={"reason": "Policy violation confirmed."},
        )
        assert response.status_code == 200
        assert response.json()["data"]["state"] == "HIDDEN"
        assert (
            test_app.client.get(
                "/api/v1/community/posts/super-admin-review"
            ).status_code
            == 404
        )
    finally:
        test_app.close()


def test_reports_deduplicate_and_moderator_hide_restore_is_audited(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="reportable-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        test_app.set_principal(OTHER_ID)
        first = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/reports",
            json={"reason": "SPAM", "details": "Contains prohibited content."},
        )
        assert first.status_code == 201, first.text
        assert first.json()["data"]["status"] == "OPEN"
        assert first.json()["data"]["reason"] == "SPAM"
        assert first.json()["data"]["details"] == "Contains prohibited content."
        repeated = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/reports",
            json={"reason": "OTHER", "details": "Repeated report."},
        )
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["data"]["id"] == first.json()["data"]["id"]

        test_app.set_principal(OWNER_ID, roles=("MODERATOR",))
        forbidden_queue = test_app.client.get(
            "/api/v1/admin/community/reports?status=OPEN"
        )
        assert forbidden_queue.status_code == 403
        forbidden_resolution = test_app.client.post(
            f"/api/v1/admin/community/reports/{first.json()['data']['id']}/resolve",
            json={"action": "HIDE", "reason": "Confirmed abuse."},
        )
        assert forbidden_resolution.status_code == 403

        test_app.set_principal(OWNER_ID, permissions=("community.moderate",))
        queue = test_app.client.get(
            "/api/v1/admin/community/reports?status=OPEN&page=1&pageSize=20"
        )
        assert queue.status_code == 200, queue.text
        assert queue.json()["meta"]["total"] == 1
        item = queue.json()["data"][0]
        assert item["reporter"]["id"] == str(OTHER_ID)
        assert item["reporter"]["username"] == f"member-{OTHER_ID.hex}"
        assert item["targetPreview"]["type"] == "POST"
        assert item["targetPreview"]["id"] == str(post_id)
        assert "private-other@example.test" not in str(queue.json())

        invalid_restore = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/restore",
            json={"reason": "Restore before hide."},
        )
        assert invalid_restore.status_code == 409

        resolved = test_app.client.post(
            f"/api/v1/admin/community/reports/{first.json()['data']['id']}/resolve",
            json={"action": "HIDE", "reason": "Confirmed abuse."},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["data"]["status"] == "RESOLVED"
        assert resolved.json()["data"]["resolutionAction"] == "HIDE"
        assert (
            test_app.client.get("/api/v1/community/posts/reportable-post").status_code
            == 404
        )
        test_app.set_principal(OWNER_ID)
        author_notifications = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=20"
        ).json()["data"]
        removed_notification = next(
            item
            for item in author_notifications
            if item["type"] == "COMMUNITY_POST_REMOVED"
        )
        assert "Confirmed abuse." in removed_notification["body"]
        assert removed_notification["data"] == {"actionPath": "/community/mine"}
        test_app.set_principal(OWNER_ID, permissions=("community.moderate",))
        repeated_resolution = test_app.client.post(
            f"/api/v1/admin/community/reports/{first.json()['data']['id']}/resolve",
            json={"action": "DISMISS", "reason": "Already handled."},
        )
        assert repeated_resolution.status_code == 409

        restored = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/restore",
            json={"reason": "Appeal accepted."},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["data"]["state"] == "VISIBLE"
        hidden_again = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/hide",
            json={"reason": "New report confirmed."},
        )
        assert hidden_again.status_code == 200
        assert hidden_again.json()["data"]["state"] == "HIDDEN"
        visible_again = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/restore",
            json={"reason": "Second appeal accepted."},
        )
        assert visible_again.json()["data"]["state"] == "VISIBLE"
        assert (
            test_app.client.get("/api/v1/community/posts/reportable-post").status_code
            == 200
        )

        history = test_app.client.get(
            "/api/v1/admin/community/moderation-history"
            f"?targetType=POST&targetId={post_id}&page=1&pageSize=20"
        )
        assert history.status_code == 200, history.text
        actions = [event["action"] for event in history.json()["data"]]
        assert "POST_HIDDEN" in actions
        assert "POST_RESTORED" in actions
        assert all(event["requestId"] for event in history.json()["data"])
        hidden_event = next(
            event
            for event in history.json()["data"]
            if event["action"] == "POST_HIDDEN"
        )
        assert hidden_event["actor"]["id"] == str(OWNER_ID)
        assert hidden_event["actor"]["username"] == "community-owner"
        assert "private-owner@example.test" not in str(history.json())
    finally:
        test_app.close()


def test_reported_comment_uses_tombstone_and_can_be_restored(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="reported-comment-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        comment = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "Comment subject to moderation."},
        )
        assert comment.status_code == 201
        comment_id = comment.json()["data"]["id"]
        test_app.set_principal(OTHER_ID)
        report = test_app.client.post(
            f"/api/v1/community/comments/{comment_id}/reports",
            json={"reason": "HARASSMENT", "details": "Targeted abuse."},
        )
        assert report.status_code == 201, report.text
        hidden_report = test_app.client.post(
            f"/api/v1/admin/community/reports/{report.json()['data']['id']}/resolve",
            json={"action": "HIDE", "reason": "Confirmed harassment."},
        )
        assert hidden_report.status_code == 403

        test_app.set_principal(OWNER_ID, permissions=("community.moderate",))
        hidden = test_app.client.post(
            f"/api/v1/admin/community/reports/{report.json()['data']['id']}/resolve",
            json={"action": "HIDE", "reason": "Confirmed harassment."},
        )
        assert hidden.status_code == 200, hidden.text
        thread = test_app.client.get(f"/api/v1/community/posts/{post_id}/comments")
        item = thread.json()["data"][0]
        assert item["content"] == "Bình luận đã bị ẩn."
        assert item["author"] is None
        assert item["isDeleted"] is True

        restored = test_app.client.post(
            f"/api/v1/admin/community/comments/{comment_id}/restore",
            json={"reason": "Moderation appeal accepted."},
        )
        assert restored.status_code == 200, restored.text
        thread = test_app.client.get(f"/api/v1/community/posts/{post_id}/comments")
        assert thread.json()["data"][0]["content"] == ("Comment subject to moderation.")
    finally:
        test_app.close()


def test_community_admin_categories_use_manage_permission_and_submissions_publish(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        test_app.set_principal(OWNER_ID, roles=("MODERATOR",))
        forbidden = test_app.client.get("/api/v1/admin/community/categories")
        assert forbidden.status_code == 403

        test_app.set_principal(OWNER_ID, permissions=("community.moderate",))
        forbidden_manage = test_app.client.post(
            "/api/v1/admin/community/categories",
            json={
                "name": "No permission",
                "slug": "no-permission",
                "description": "This request must be forbidden.",
                "sortOrder": 1,
                "reason": "Check the manage permission.",
            },
        )
        assert forbidden_manage.status_code == 403

        test_app.set_principal(OWNER_ID, permissions=("community.manage",))
        invalid_order = test_app.client.post(
            "/api/v1/admin/community/categories",
            json={
                "name": "Invalid category",
                "slug": "invalid-category",
                "description": "Must reject negative order.",
                "sortOrder": -1,
                "reason": "Constraint check.",
            },
        )
        assert invalid_order.status_code == 422
        payload = {
            "name": "Local topics",
            "slug": "local-topics",
            "description": "Community topics.",
            "sortOrder": 5,
            "reason": "Add a category for local topics.",
        }
        created = test_app.client.post(
            "/api/v1/admin/community/categories",
            json=payload,
        )
        assert created.status_code == 201, created.text
        category_id = created.json()["data"]["id"]
        duplicate = test_app.client.post(
            "/api/v1/admin/community/categories",
            json=payload,
        )
        assert duplicate.status_code == 409

        deactivated = test_app.client.patch(
            f"/api/v1/admin/community/categories/{category_id}",
            json={"isActive": False, "reason": "Pause this category."},
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["data"]["isActive"] is False

        created_post = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Auto-publish community post",
                "content": "This post should be public after submit.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        post_id = created_post.json()["data"]["id"]
        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200
        assert submitted.json()["data"]["status"] == "PUBLISHED"

        hidden_category_posts = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Inactive category draft",
                "content": "Must not publish into an inactive category.",
                "categoryId": category_id,
            },
        )
        assert hidden_category_posts.status_code == 404
        test_app.set_principal(OWNER_ID, permissions=("community.moderate",))
        history = test_app.client.get(
            "/api/v1/admin/community/moderation-history"
            f"?targetType=CATEGORY&targetId={category_id}"
        )
        assert history.status_code == 200
        category_event = next(
            event
            for event in history.json()["data"]
            if event["action"] == "CATEGORY_UPDATED"
        )
        assert category_event["actor"]["username"] == "community-owner"
        assert category_event["requestId"]
    finally:
        test_app.close()


def test_community_comment_threads_are_public_only_and_flatten_deeper_replies(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="commentable-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        draft_id = _insert_post(
            test_app,
            slug="private-comment-post",
            status=CommunityPostStatus.DRAFT,
        )

        root_response = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "A top-level comment."},
        )
        assert root_response.status_code == 201, root_response.text
        root_id = root_response.json()["data"]["id"]
        assert root_response.json()["data"]["isDeleted"] is False
        assert root_response.json()["data"]["author"]["id"] == str(OWNER_ID)
        assert root_response.json()["data"]["author"]["username"] == "community-owner"
        assert (
            root_response.json()["data"]["author"]["displayName"]
            == "Public community name"
        )

        test_app.set_principal(OTHER_ID)
        denied_edit = test_app.client.patch(
            f"/api/v1/community/comments/{root_id}",
            json={"content": "Not the owner."},
        )
        assert denied_edit.status_code == 403
        denied_delete = test_app.client.delete(f"/api/v1/community/comments/{root_id}")
        assert denied_delete.status_code == 403

        test_app.set_principal(OWNER_ID)
        edited = test_app.client.patch(
            f"/api/v1/community/comments/{root_id}",
            json={"content": "Updated top-level comment."},
        )
        assert edited.status_code == 200
        assert edited.json()["data"]["content"] == "Updated top-level comment."

        test_app.set_principal(OTHER_ID)
        reply_response = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "A direct reply.", "parentId": root_id},
        )
        assert reply_response.status_code == 201, reply_response.text
        reply_id = reply_response.json()["data"]["id"]

        deep_reply = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "A reply to a reply.", "parentId": reply_id},
        )
        assert deep_reply.status_code == 201, deep_reply.text
        deep_reply_id = deep_reply.json()["data"]["id"]

        test_app.set_principal(OWNER_ID)
        deleted_root = test_app.client.delete(f"/api/v1/community/comments/{root_id}")
        assert deleted_root.status_code == 204

        hidden = test_app.client.get(f"/api/v1/community/posts/{draft_id}/comments")
        assert hidden.status_code == 404

        unsafe = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "<script>alert(1)</script>"},
        )
        assert unsafe.status_code == 422

        thread_page = test_app.client.get(
            f"/api/v1/community/posts/{post_id}/comments?page=1&pageSize=20"
        )
        assert thread_page.status_code == 200
        assert thread_page.json()["meta"]["total"] == 1
        root = thread_page.json()["data"][0]
        assert root["id"] == root_id
        assert root["parentId"] is None
        assert root["content"] == "Bình luận đã bị xóa."
        assert root["isDeleted"] is True
        assert root["author"] is None
        assert len(root["replies"]) == 2
        assert root["replies"][0]["id"] == reply_id
        assert "replies" not in root["replies"][0]
        assert root["replies"][0]["author"]["id"] == str(OTHER_ID)
        assert root["replies"][1]["id"] == deep_reply_id
        assert root["replies"][1]["parentId"] == reply_id
        serialized = str(thread_page.json()).lower()
        assert "private-owner@example.test" not in serialized
        assert "private-phone" not in serialized
        assert "employment" not in serialized
        post_detail = test_app.client.get("/api/v1/community/posts/commentable-post")
        assert post_detail.status_code == 200
        assert post_detail.json()["data"]["commentCount"] == 2

        async def deleted_content() -> str | None:
            async with test_app.sessions() as session:
                return await session.scalar(
                    select(CommunityComment.content).where(
                        CommunityComment.id == UUID(root_id)
                    )
                )

        assert asyncio.run(deleted_content()) == "Bình luận đã bị xóa."
    finally:
        test_app.close()


def test_likes_bookmarks_follows_and_member_reads_use_safe_profiles(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="member-public-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        _insert_post(
            test_app,
            slug="member-private-post",
            status=CommunityPostStatus.DRAFT,
        )

        first_like = test_app.client.put(f"/api/v1/community/posts/{post_id}/like")
        assert first_like.status_code == 200, first_like.text
        assert first_like.json()["data"] == {
            "postId": str(post_id),
            "likeCount": 1,
            "isLiked": True,
        }
        repeated_like = test_app.client.put(f"/api/v1/community/posts/{post_id}/like")
        assert repeated_like.json()["data"]["likeCount"] == 1
        test_app.viewer_principal = _principal(OWNER_ID)
        personalized_post = test_app.client.get(
            "/api/v1/community/posts/member-public-post"
        )
        assert personalized_post.status_code == 200
        assert personalized_post.json()["data"]["viewerHasLiked"] is True
        assert personalized_post.json()["data"]["viewerHasBookmarked"] is False
        test_app.viewer_principal = None

        test_app.set_principal(OTHER_ID)
        second_like = test_app.client.put(f"/api/v1/community/posts/{post_id}/like")
        assert second_like.json()["data"]["likeCount"] == 2
        removed_other_like = test_app.client.delete(
            f"/api/v1/community/posts/{post_id}/like"
        )
        assert removed_other_like.json()["data"] == {
            "postId": str(post_id),
            "likeCount": 1,
            "isLiked": False,
        }

        test_app.set_principal(OWNER_ID)
        bookmark = test_app.client.put(f"/api/v1/community/posts/{post_id}/bookmark")
        assert bookmark.status_code == 200
        assert bookmark.json()["data"] == {
            "postId": str(post_id),
            "isBookmarked": True,
        }
        test_app.client.put(f"/api/v1/community/posts/{post_id}/bookmark")
        bookmarks = test_app.client.get(
            "/api/v1/community/members/me/bookmarks?page=1&pageSize=20"
        )
        assert bookmarks.status_code == 200
        assert bookmarks.json()["meta"]["total"] == 1
        assert [item["id"] for item in bookmarks.json()["data"]] == [str(post_id)]

        own_profile = test_app.client.get("/api/v1/community/members/me")
        assert own_profile.status_code == 200
        own_data = own_profile.json()["data"]
        assert own_data["id"] == str(OWNER_ID)
        assert own_data["username"] == "community-owner"
        assert own_data["displayName"] == "Public community name"
        assert own_data["avatarUrl"] is None
        assert own_data["bio"] is None
        assert own_data["viewerIsFollowing"] is False
        assert "private-owner@example.test" not in str(own_data)
        assert "private-phone" not in str(own_data)
        assert "employment" not in str(own_data).lower()

        member_posts = test_app.client.get(
            "/api/v1/community/members/community-owner/posts?page=1&pageSize=20"
        )
        assert member_posts.status_code == 200
        assert member_posts.json()["meta"]["total"] == 1
        assert member_posts.json()["data"][0]["slug"] == "member-public-post"

        followed = test_app.client.put(f"/api/v1/community/members/{OTHER_ID}/follow")
        assert followed.status_code == 200
        assert followed.json()["data"] == {
            "memberId": str(OTHER_ID),
            "isFollowing": True,
            "followerCount": 1,
        }
        test_app.client.put(f"/api/v1/community/members/{OTHER_ID}/follow")
        test_app.viewer_principal = _principal(OWNER_ID)
        other_profile = test_app.client.get(
            f"/api/v1/community/members/member-{OTHER_ID.hex}"
        )
        assert other_profile.status_code == 200
        assert other_profile.json()["data"]["followerCount"] == 1
        assert other_profile.json()["data"]["displayName"] == "Thành viên"
        assert other_profile.json()["data"]["viewerIsFollowing"] is True
        test_app.viewer_principal = None

        self_follow = test_app.client.put(
            f"/api/v1/community/members/{OWNER_ID}/follow"
        )
        assert self_follow.status_code == 409
        unfollowed = test_app.client.delete(
            f"/api/v1/community/members/{OTHER_ID}/follow"
        )
        assert unfollowed.json()["data"]["followerCount"] == 0

        unbookmark = test_app.client.delete(
            f"/api/v1/community/posts/{post_id}/bookmark"
        )
        assert unbookmark.json()["data"]["isBookmarked"] is False
        empty_bookmarks = test_app.client.get("/api/v1/community/members/me/bookmarks")
        assert empty_bookmarks.json()["meta"]["total"] == 0
    finally:
        test_app.close()


def test_public_author_identity_uses_shared_profile_and_persisted_role(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="official-admin-identity",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        _insert_post(
            test_app,
            slug="official-moderator-identity",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
            author_id=OTHER_ID,
        )
        avatar_id = _insert_community_image(
            test_app,
            purpose="AVATAR",
            mime_type="image/png",
        )

        async def update_identity() -> None:
            async with test_app.sessions() as session:
                role = Role(id=uuid4(), code="SUPER_ADMIN")
                moderator_role = Role(id=uuid4(), code="MODERATOR")
                session.add(role)
                session.add(moderator_role)
                await session.flush()
                session.add(UserRole(user_id=OWNER_ID, role_id=role.id))
                session.add(UserRole(user_id=OTHER_ID, role_id=moderator_role.id))
                profile = await session.get(UserProfile, OWNER_ID)
                assert profile is not None
                profile.display_name = "User supplied administrator name"
                profile.avatar_media_id = avatar_id
                session.add(
                    CommunityComment(
                        id=uuid4(),
                        post_id=post_id,
                        author_user_id=OWNER_ID,
                        content="Administrator comment identity.",
                        created_at=NOW,
                    )
                )
                await session.commit()

        asyncio.run(update_identity())
        response = test_app.client.get(
            "/api/v1/community/posts/official-admin-identity"
        )

        assert response.status_code == 200
        author = response.json()["data"]["author"]
        assert author == {
            "id": str(OWNER_ID),
            "username": "community-owner",
            "displayName": "Quản trị viên THV",
            "avatarUrl": f"/api/v1/community/avatars/{avatar_id}",
            "roleLabel": "Quản trị viên",
            "isAdmin": True,
            "membershipTier": "MEMBER",
        }
        assert "private-owner@example.test" not in str(author)

        comments = test_app.client.get(f"/api/v1/community/posts/{post_id}/comments")
        assert comments.status_code == 200, comments.text
        assert comments.json()["data"][0]["author"] == author
        member = test_app.client.get("/api/v1/community/members/community-owner")
        assert member.status_code == 200, member.text
        assert member.json()["data"]["displayName"] == "Quản trị viên THV"
        assert member.json()["data"]["roleLabel"] == "Quản trị viên"
        assert member.json()["data"]["isAdmin"] is True
        assert member.json()["data"]["membershipTier"] == "MEMBER"

        moderator_post = test_app.client.get(
            "/api/v1/community/posts/official-moderator-identity"
        )
        assert moderator_post.status_code == 200, moderator_post.text
        assert moderator_post.json()["data"]["author"]["roleLabel"] == (
            "Thẩm định viên"
        )
    finally:
        test_app.close()


def test_related_work_link_requires_current_public_visibility_and_is_allowlisted(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        public_work_id = _insert_public_work(test_app, slug="community-linked-work")
        hidden_work_id = _insert_public_work(
            test_app,
            slug="community-hidden-work",
            status=PublicationStatus.HIDDEN,
            visibility=PublicWorkVisibility.PUBLIC,
        )
        post = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Post with a public work link",
                "content": "Safe linked work summary.",
                "categoryId": str(CATEGORY_ID),
                "relatedWorkId": str(public_work_id),
            },
        )
        assert post.status_code == 201, post.text
        post_id = post.json()["data"]["id"]
        post_slug = post.json()["data"]["slug"]
        assert post.json()["data"]["relatedWork"] == {
            "id": str(public_work_id),
            "title": "Public title: community-linked-work",
            "slug": "community-linked-work",
        }
        assert "Private nomination narrative" not in post.text
        assert "Must never enter community DTO" not in post.text

        rejected_link = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Post with hidden work link",
                "content": "This relation must be rejected.",
                "categoryId": str(CATEGORY_ID),
                "relatedWorkId": str(hidden_work_id),
            },
        )
        assert rejected_link.status_code == 404

        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["data"]["status"] == "PUBLISHED"
        public_detail = test_app.client.get(f"/api/v1/community/posts/{post_slug}")
        assert public_detail.status_code == 200, public_detail.text
        assert public_detail.json()["data"]["relatedWork"]["id"] == str(public_work_id)

        async def hide_work() -> None:
            async with test_app.sessions() as session:
                async with session.begin():
                    work = await session.get(PublicWork, public_work_id)
                    assert work is not None
                    work.publication_status = PublicationStatus.HIDDEN

        asyncio.run(hide_work())
        no_longer_public = test_app.client.get(f"/api/v1/community/posts/{post_slug}")
        assert no_longer_public.status_code == 200
        assert no_longer_public.json()["data"]["relatedWork"] is None
        serialized = str(no_longer_public.json())
        assert "Private nomination narrative" not in serialized
        assert "Must never enter community DTO" not in serialized
    finally:
        test_app.close()


def test_community_notifications_cover_events_without_self_or_duplicate_alerts(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="community-notification-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        test_app.set_principal(OTHER_ID)
        root = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "A public root comment."},
        )
        assert root.status_code == 201, root.text
        root_id = root.json()["data"]["id"]

        test_app.set_principal(OWNER_ID)
        owner_before_self_comment = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["meta"]["total"]
        own_comment = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "An author's own comment."},
        )
        assert own_comment.status_code == 201
        owner_after_self_comment = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["meta"]["total"]
        assert owner_after_self_comment == owner_before_self_comment
        reply = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "A reply to the root.", "parentId": root_id},
        )
        assert reply.status_code == 201

        test_app.set_principal(OTHER_ID)
        author_notifications = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["data"]
        assert [item["type"] for item in author_notifications] == ["COMMUNITY_REPLY"]
        reply_action_path = (
            "/community/posts/community-notification-post#community-comments-title"
        )
        assert author_notifications[0]["data"] == {"actionPath": reply_action_path}

        liked = test_app.client.put(f"/api/v1/community/posts/{post_id}/like")
        assert liked.status_code == 200
        test_app.client.put(f"/api/v1/community/posts/{post_id}/like")
        owner_likes = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["meta"]["total"]
        assert owner_likes == 1
        test_app.client.delete(f"/api/v1/community/posts/{post_id}/like")
        test_app.client.put(f"/api/v1/community/posts/{post_id}/like")

        followed = test_app.client.put(f"/api/v1/community/members/{OWNER_ID}/follow")
        assert followed.status_code == 200
        test_app.set_principal(OWNER_ID)
        owner_notifications = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["data"]
        assert [item["type"] for item in owner_notifications].count(
            "COMMUNITY_COMMENT"
        ) == 1
        assert [item["type"] for item in owner_notifications].count(
            "COMMUNITY_POST_LIKED"
        ) == 2
        follow_notification = next(
            item for item in owner_notifications if item["type"] == "COMMUNITY_FOLLOW"
        )
        assert follow_notification["data"] == {
            "actionPath": f"/community/members/member-{OTHER_ID.hex}"
        }
        assert "private-owner@example.test" not in str(owner_notifications)
        assert "private-other@example.test" not in str(owner_notifications)
        assert "private-phone" not in str(owner_notifications)

    finally:
        test_app.close()


def test_post_attachments_require_owned_inspected_community_images(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        invalid_media = (
            _insert_community_image(test_app, owner_id=OTHER_ID),
            _insert_community_image(test_app, purpose="AVATAR"),
            _insert_community_image(test_app, purpose=None),
            _insert_community_image(test_app, status=MediaStatus.QUARANTINED),
            _insert_community_image(test_app, status=MediaStatus.REJECTED),
            _insert_community_image(test_app, mime_type="image/gif"),
            _insert_community_image(test_app, size=5_242_881),
            _insert_community_image(test_app, inspected=False),
        )
        for index, media_id in enumerate(invalid_media):
            response = test_app.client.post(
                "/api/v1/community/posts",
                json={
                    "title": f"Rejected image {index}",
                    "content": "Attachment must satisfy all safety checks.",
                    "categoryId": str(CATEGORY_ID),
                    "imageMediaIds": [str(media_id)],
                },
            )
            assert response.status_code == 404, response.text

        first = _insert_community_image(test_app)
        second = _insert_community_image(test_app, mime_type="image/webp")
        response = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Post with inspected images",
                "content": "Images preserve the submitted order.",
                "categoryId": str(CATEGORY_ID),
                "imageMediaIds": [str(second), str(first)],
            },
        )
        assert response.status_code == 201, response.text
        post = response.json()["data"]
        assert [image["id"] for image in post["images"]] == [
            str(second),
            str(first),
        ]
        assert post["images"][0]["url"] == (
            f"/api/v1/community/posts/{post['slug']}/media/{second}"
        )

        too_many = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Too many images",
                "content": "At most five images may be attached.",
                "categoryId": str(CATEGORY_ID),
                "imageMediaIds": [str(first)] * 6,
            },
        )
        assert too_many.status_code == 422

        post_id = post["id"]
        updated = test_app.client.patch(
            f"/api/v1/community/posts/{post_id}",
            json={
                "title": "Updated attachment order",
                "content": "Only one image remains.",
                "categoryId": str(CATEGORY_ID),
                "imageMediaIds": [str(first)],
            },
        )
        assert updated.status_code == 200, updated.text
        assert [image["id"] for image in updated.json()["data"]["images"]] == [
            str(first)
        ]
    finally:
        test_app.close()


class _CommunityImageReader:
    async def download_community_post_image(self, media_id: UUID) -> MediaContentView:
        _ = media_id
        return MediaContentView(
            content=b"\x89PNG\r\n\x1a\ncommunity image",
            mime_type="image/png",
            filename="community-image.png",
        )


def test_community_image_delivery_checks_public_association_and_owner_preview(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        test_app.app.dependency_overrides[get_media_service] = lambda: (
            _CommunityImageReader()
        )
        media_id = _insert_community_image(test_app)
        created = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Draft with image",
                "content": "Private until moderation.",
                "categoryId": str(CATEGORY_ID),
                "imageMediaIds": [str(media_id)],
            },
        )
        assert created.status_code == 201, created.text
        post = created.json()["data"]
        image_path = post["images"][0]["url"]

        anonymous_draft = test_app.client.get(image_path)
        assert anonymous_draft.status_code == 404
        test_app.viewer_principal = _principal(OTHER_ID)
        non_owner_preview = test_app.client.get(image_path)
        assert non_owner_preview.status_code == 404
        test_app.viewer_principal = _principal(OWNER_ID)
        owner_preview = test_app.client.get(image_path)
        assert owner_preview.status_code == 200
        assert owner_preview.content.startswith(b"\x89PNG")
        assert owner_preview.headers["content-type"] == "image/png"
        assert owner_preview.headers["x-content-type-options"] == "nosniff"
        assert owner_preview.headers["cache-control"] == "private, no-store"

        submitted = test_app.client.post(f"/api/v1/community/posts/{post['id']}/submit")
        assert submitted.status_code == 200
        assert submitted.json()["data"]["status"] == "PUBLISHED"
        test_app.viewer_principal = None
        public_image = test_app.client.get(image_path)
        assert public_image.status_code == 200

        async def hide_post() -> None:
            async with test_app.sessions() as session:
                async with session.begin():
                    record = await session.get(CommunityPost, UUID(post["id"]))
                    assert record is not None
                    record.status = CommunityPostStatus.HIDDEN

        asyncio.run(hide_post())
        hidden_image = test_app.client.get(image_path)
        assert hidden_image.status_code == 404

        async def change_visibility(*, post_status=None, media_status=None) -> None:
            async with test_app.sessions() as session:
                async with session.begin():
                    if post_status is not None:
                        record = await session.get(CommunityPost, UUID(post["id"]))
                        assert record is not None
                        record.status = post_status
                    if media_status is not None:
                        asset = await session.get(MediaAsset, media_id)
                        assert asset is not None
                        asset.status = media_status
                        asset.deleted_at = (
                            NOW if media_status is MediaStatus.DELETED else None
                        )

        asyncio.run(change_visibility(post_status=CommunityPostStatus.HIDDEN))
        assert test_app.client.get(image_path).status_code == 404
        asyncio.run(change_visibility(post_status=CommunityPostStatus.PUBLISHED))
        asyncio.run(change_visibility(media_status=MediaStatus.QUARANTINED))
        assert test_app.client.get(image_path).status_code == 404
        asyncio.run(change_visibility(media_status=MediaStatus.REJECTED))
        assert test_app.client.get(image_path).status_code == 404
        asyncio.run(change_visibility(media_status=MediaStatus.DELETED))
        assert test_app.client.get(image_path).status_code == 404
        asyncio.run(change_visibility(media_status=MediaStatus.ACTIVE))
        asyncio.run(change_visibility(post_status=CommunityPostStatus.DELETED))
        assert test_app.client.get(image_path).status_code == 404
        asyncio.run(change_visibility(post_status=CommunityPostStatus.PUBLISHED))

        async def detach_image() -> None:
            async with test_app.sessions() as session:
                async with session.begin():
                    association = await session.get(
                        CommunityPostMedia,
                        (UUID(post["id"]), media_id),
                    )
                    assert association is not None
                    await session.delete(association)

        asyncio.run(detach_image())
        assert test_app.client.get(image_path).status_code == 404
    finally:
        test_app.close()


def test_post_tags_are_persisted_projected_and_filter_the_public_feed(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        untagged_id = _insert_post(
            test_app,
            slug="untagged-public",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        payload = {
            "title": "Taggable post",
            "content": "A searchable public community entry.",
            "categoryId": str(CATEGORY_ID),
            "tags": ["  Community   Design ", "Accessibility"],
        }
        created = test_app.client.post("/api/v1/community/posts", json=payload)
        assert created.status_code == 201, created.text
        post_id = created.json()["data"]["id"]
        post_slug = created.json()["data"]["slug"]
        tags = created.json()["data"]["tags"]
        assert [tag["name"] for tag in tags] == ["Accessibility", "Community Design"]
        assert [tag["slug"] for tag in tags] == [
            "accessibility",
            "community-design",
        ]
        assert all(set(tag) == {"id", "name", "slug"} for tag in tags)

        duplicate_tags = test_app.client.post(
            "/api/v1/community/posts",
            json={**payload, "tags": ["Community Design", " community   design "]},
        )
        assert duplicate_tags.status_code == 422
        too_many_tags = test_app.client.post(
            "/api/v1/community/posts",
            json={**payload, "tags": [f"tag-{index}" for index in range(11)]},
        )
        assert too_many_tags.status_code == 422

        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["data"]["status"] == "PUBLISHED"

        feed = test_app.client.get("/api/v1/community/posts?tag=community-design")
        assert feed.status_code == 200, feed.text
        assert [item["id"] for item in feed.json()["data"]] == [post_id]
        assert feed.json()["data"][0]["tags"] == tags
        detail = test_app.client.get(f"/api/v1/community/posts/{post_slug}")
        assert detail.status_code == 200
        assert detail.json()["data"]["tags"] == tags
        empty = test_app.client.get("/api/v1/community/posts?tag=unknown-tag")
        assert empty.status_code == 200
        assert empty.json()["data"] == []
        assert empty.json()["meta"]["total"] == 0
        assert untagged_id not in {item["id"] for item in feed.json()["data"]}
    finally:
        test_app.close()


def test_feed_search_sorts_following_and_rejects_unbounded_queries(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        recent_id = _insert_post(
            test_app,
            slug="recent-match",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
            title="Recent result",
            content="Needle Search matches here.",
        )
        popular_id = _insert_post(
            test_app,
            slug="popular-match",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW - timedelta(days=2),
            title="Popular result",
        )
        discussed_id = _insert_post(
            test_app,
            slug="discussed-match",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW - timedelta(days=1),
            title="Discussed result",
        )
        followed_id = _insert_post(
            test_app,
            slug="followed-author-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW - timedelta(hours=1),
            author_id=OTHER_ID,
        )

        async def add_counts() -> None:
            async with test_app.sessions() as session:
                session.add_all(
                    [
                        CommunityLike(
                            post_id=popular_id,
                            user_id=OWNER_ID,
                            created_at=NOW,
                            updated_at=NOW,
                        ),
                        CommunityLike(
                            post_id=popular_id,
                            user_id=OTHER_ID,
                            created_at=NOW,
                            updated_at=NOW,
                        ),
                        CommunityLike(
                            post_id=discussed_id,
                            user_id=OWNER_ID,
                            created_at=NOW,
                            updated_at=NOW,
                        ),
                        CommunityComment(
                            id=uuid4(),
                            post_id=discussed_id,
                            author_user_id=OWNER_ID,
                            content="One discussion reply.",
                            created_at=NOW,
                        ),
                        CommunityComment(
                            id=uuid4(),
                            post_id=discussed_id,
                            author_user_id=OTHER_ID,
                            content="Another discussion reply.",
                            created_at=NOW,
                        ),
                    ]
                )
                await session.commit()

        asyncio.run(add_counts())

        search = test_app.client.get("/api/v1/community/posts?q=needle%20sEaRcH")
        assert search.status_code == 200, search.text
        assert [item["id"] for item in search.json()["data"]] == [str(recent_id)]
        assert (
            test_app.client.get(f"/api/v1/community/posts?q={'x' * 121}").status_code
            == 422
        )
        assert (
            test_app.client.get("/api/v1/community/posts?pageSize=51").status_code
            == 422
        )

        recent = test_app.client.get("/api/v1/community/posts?sort=recent")
        popular = test_app.client.get("/api/v1/community/posts?sort=popular")
        discussed = test_app.client.get("/api/v1/community/posts?sort=discussed")
        assert [item["id"] for item in recent.json()["data"]][:3] == [
            str(recent_id),
            str(followed_id),
            str(discussed_id),
        ]
        assert popular.json()["data"][0]["id"] == str(popular_id)
        assert discussed.json()["data"][0]["id"] == str(discussed_id)

        anonymous_following = test_app.client.get(
            "/api/v1/community/posts?sort=following"
        )
        assert anonymous_following.status_code == 401
        test_app.set_principal(OWNER_ID)
        test_app.viewer_principal = _principal(OWNER_ID)
        followed = test_app.client.put(f"/api/v1/community/members/{OTHER_ID}/follow")
        assert followed.status_code == 200, followed.text
        following = test_app.client.get("/api/v1/community/posts?sort=following")
        assert following.status_code == 200, following.text
        assert [item["id"] for item in following.json()["data"]] == [str(followed_id)]
    finally:
        test_app.close()


def test_owner_post_list_and_read_include_only_owned_manageable_statuses(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        own_posts = {
            status: _insert_post(
                test_app,
                slug=f"owner-{status.value.lower()}",
                status=status,
                published_at=(NOW if status is CommunityPostStatus.PUBLISHED else None),
            )
            for status in (
                CommunityPostStatus.DRAFT,
                CommunityPostStatus.PENDING,
                CommunityPostStatus.REJECTED,
                CommunityPostStatus.PUBLISHED,
                CommunityPostStatus.HIDDEN,
                CommunityPostStatus.DELETED,
            )
        }
        _insert_post(
            test_app,
            slug="other-owner-draft",
            status=CommunityPostStatus.DRAFT,
            author_id=OTHER_ID,
        )

        listing = test_app.client.get("/api/v1/community/members/me/posts")
        assert listing.status_code == 200, listing.text
        listed_ids = {item["id"] for item in listing.json()["data"]}
        assert listed_ids == {
            str(own_posts[status])
            for status in (
                CommunityPostStatus.DRAFT,
                CommunityPostStatus.PENDING,
                CommunityPostStatus.REJECTED,
                CommunityPostStatus.PUBLISHED,
                CommunityPostStatus.HIDDEN,
            )
        }
        assert listing.json()["meta"]["total"] == 5
        pending = test_app.client.get(
            "/api/v1/community/members/me/posts?status=PENDING"
        )
        assert [item["id"] for item in pending.json()["data"]] == [
            str(own_posts[CommunityPostStatus.PENDING])
        ]
        hidden = test_app.client.get("/api/v1/community/members/me/posts?status=HIDDEN")
        assert hidden.status_code == 200
        assert hidden.json()["meta"]["total"] == 1

        for status in (
            CommunityPostStatus.DRAFT,
            CommunityPostStatus.PENDING,
            CommunityPostStatus.REJECTED,
            CommunityPostStatus.PUBLISHED,
            CommunityPostStatus.HIDDEN,
        ):
            response = test_app.client.get(
                f"/api/v1/community/members/me/posts/{own_posts[status]}"
            )
            assert response.status_code == 200
            assert response.json()["data"]["status"] == status.value
            assert "private-owner@example.test" not in response.text
            assert "private legal name" not in response.text.lower()

        test_app.set_principal(OTHER_ID)
        private_read = test_app.client.get(
            f"/api/v1/community/members/me/posts/{own_posts[CommunityPostStatus.DRAFT]}"
        )
        assert private_read.status_code == 404
        test_app.set_principal(OWNER_ID)
        assert (
            test_app.client.get(
                f"/api/v1/community/members/me/posts/{own_posts[CommunityPostStatus.HIDDEN]}"
            ).status_code
            == 200
        )
        assert (
            test_app.client.get(
                f"/api/v1/community/members/me/posts/{own_posts[CommunityPostStatus.DELETED]}"
            ).status_code
            == 404
        )
    finally:
        test_app.close()


def test_public_feed_related_work_filter_rechecks_public_visibility(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        public_work_id = _insert_public_work(test_app, slug="related-public-work")
        hidden_work_id = _insert_public_work(
            test_app,
            slug="related-hidden-work",
            status=PublicationStatus.DRAFT,
        )
        linked_post_id = _insert_post(
            test_app,
            slug="post-linked-to-public-work",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
            related_work_id=public_work_id,
        )
        _insert_post(
            test_app,
            slug="post-linked-to-hidden-work",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
            related_work_id=hidden_work_id,
        )
        _insert_post(
            test_app,
            slug="unrelated-public-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )

        visible = test_app.client.get(
            f"/api/v1/community/posts?relatedWorkId={public_work_id}"
        )
        assert visible.status_code == 200, visible.text
        assert [item["id"] for item in visible.json()["data"]] == [str(linked_post_id)]
        assert visible.json()["data"][0]["relatedWork"] == {
            "id": str(public_work_id),
            "title": "Public title: related-public-work",
            "slug": "related-public-work",
        }
        hidden = test_app.client.get(
            f"/api/v1/community/posts?relatedWorkId={hidden_work_id}"
        )
        assert hidden.status_code == 200
        assert hidden.json()["data"] == []
        assert hidden.json()["meta"]["total"] == 0
        assert "Private nomination narrative" not in hidden.text
    finally:
        test_app.close()


def test_post_images_publish_immediately_and_hide_removes_public_access(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        test_app.viewer_principal = _principal(OWNER_ID)
        test_app.app.dependency_overrides[get_media_service] = lambda: (
            _CommunityImageReader()
        )
        media_id = _insert_community_image(test_app)
        created = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Private image draft",
                "content": "This image is not public yet.",
                "categoryId": str(CATEGORY_ID),
                "imageMediaIds": [str(media_id)],
            },
        )
        assert created.status_code == 201, created.text
        post_id = created.json()["data"]["id"]
        slug = created.json()["data"]["slug"]
        image_url = created.json()["data"]["images"][0]["url"]
        assert test_app.client.get(image_url).status_code == 200
        owner_detail = test_app.client.get(
            f"/api/v1/community/members/me/posts/{post_id}"
        )
        assert owner_detail.status_code == 200
        assert owner_detail.json()["data"]["images"][0]["url"] == image_url
        owner_list = test_app.client.get("/api/v1/community/members/me/posts")
        assert image_url in str(owner_list.json())

        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200
        assert submitted.json()["data"]["status"] == "PUBLISHED"
        assert test_app.client.get(image_url).status_code == 200
        test_app.viewer_principal = None
        assert test_app.client.get(image_url).status_code == 200
        test_app.viewer_principal = _principal(OTHER_ID)
        assert test_app.client.get(image_url).status_code == 200
        test_app.viewer_principal = _principal(OWNER_ID)

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        hidden = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/hide",
            json={"reason": "Please revise the image caption."},
        )
        assert hidden.status_code == 200
        test_app.viewer_principal = None
        assert test_app.client.get(image_url).status_code == 404
        test_app.set_principal(OWNER_ID)
        test_app.viewer_principal = _principal(OWNER_ID)
        owner_detail = test_app.client.get(
            f"/api/v1/community/members/me/posts/{post_id}"
        )
        assert owner_detail.status_code == 200
        assert owner_detail.json()["data"]["status"] == "HIDDEN"
        assert test_app.client.get(image_url).status_code == 200
        assert test_app.client.get(f"/api/v1/community/posts/{slug}").status_code == 404
    finally:
        test_app.close()


def test_comment_likes_and_ordered_thread_projection(tmp_path: Path) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="comment-like-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        root_old = uuid4()
        root_new = uuid4()
        reply_old = uuid4()
        reply_new = uuid4()

        async def insert_comments() -> None:
            async with test_app.sessions() as session:
                session.add_all(
                    [
                        CommunityComment(
                            id=root_old,
                            post_id=post_id,
                            author_user_id=OWNER_ID,
                            content="Older root",
                            created_at=NOW - timedelta(minutes=3),
                        ),
                        CommunityComment(
                            id=root_new,
                            post_id=post_id,
                            author_user_id=OTHER_ID,
                            content="Newer root",
                            created_at=NOW - timedelta(minutes=1),
                        ),
                        CommunityComment(
                            id=reply_old,
                            post_id=post_id,
                            author_user_id=OTHER_ID,
                            parent_id=root_old,
                            content="Older reply",
                            created_at=NOW - timedelta(minutes=2),
                        ),
                        CommunityComment(
                            id=reply_new,
                            post_id=post_id,
                            author_user_id=OWNER_ID,
                            parent_id=root_old,
                            content="Newer reply",
                            created_at=NOW - timedelta(seconds=30),
                        ),
                    ]
                )
                await session.commit()

        asyncio.run(insert_comments())
        comment_like_url = f"/api/v1/community/comments/{root_old}/like"
        first_like = test_app.client.put(comment_like_url)
        assert first_like.status_code == 200, first_like.text
        assert first_like.json()["data"] == {
            "commentId": str(root_old),
            "likeCount": 1,
            "isLiked": True,
        }
        repeated_like = test_app.client.put(comment_like_url)
        assert repeated_like.json()["data"]["likeCount"] == 1
        reply_like = test_app.client.put(f"/api/v1/community/comments/{reply_new}/like")
        assert reply_like.json()["data"]["likeCount"] == 1

        test_app.viewer_principal = _principal(OWNER_ID)
        oldest = test_app.client.get(
            f"/api/v1/community/posts/{post_id}/comments?sort=oldest"
        )
        newest = test_app.client.get(
            f"/api/v1/community/posts/{post_id}/comments?sort=newest"
        )
        assert oldest.status_code == 200, oldest.text
        assert newest.status_code == 200, newest.text
        assert [item["id"] for item in oldest.json()["data"]] == [
            str(root_old),
            str(root_new),
        ]
        assert [item["id"] for item in newest.json()["data"]] == [
            str(root_new),
            str(root_old),
        ]
        oldest_thread = oldest.json()["data"][0]
        assert oldest_thread["likeCount"] == 1
        assert oldest_thread["viewerHasLiked"] is True
        assert [reply["id"] for reply in oldest_thread["replies"]] == [
            str(reply_old),
            str(reply_new),
        ]
        assert oldest_thread["replies"][1]["likeCount"] == 1
        assert oldest_thread["replies"][1]["viewerHasLiked"] is True
        newest_thread = newest.json()["data"][1]
        assert [reply["id"] for reply in newest_thread["replies"]] == [
            str(reply_new),
            str(reply_old),
        ]

        test_app.set_principal(OWNER_ID)
        unlike = test_app.client.delete(comment_like_url)
        assert unlike.status_code == 200, unlike.text
        assert unlike.json()["data"] == {
            "commentId": str(root_old),
            "likeCount": 0,
            "isLiked": False,
        }
    finally:
        test_app.close()


def test_member_profile_edit_and_public_follower_lists_are_safe(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:

        async def add_other_profile() -> None:
            async with test_app.sessions() as session:
                session.add(
                    CommunityProfile(
                        user_id=OTHER_ID,
                        username="other-member",
                        display_name="Other public name",
                    )
                )
                await session.commit()

        asyncio.run(add_other_profile())
        updated = test_app.client.patch(
            "/api/v1/community/members/me",
            json={
                "username": "New_User-1",
                "displayName": "Edited community name",
                "avatarUrl": "https://cdn.example.test/avatar.png",
                "bio": "A public community biography.",
            },
        )
        assert updated.status_code == 200, updated.text
        profile = updated.json()["data"]
        assert profile["username"] == "new_user-1"
        assert profile["displayName"] == "Edited community name"
        assert profile["avatarUrl"] == "https://cdn.example.test/avatar.png"
        assert profile["bio"] == "A public community biography."
        assert "private-owner@example.test" not in updated.text
        assert "private-phone" not in updated.text

        duplicate = test_app.client.patch(
            "/api/v1/community/members/me",
            json={"username": "OTHER-MEMBER"},
        )
        assert duplicate.status_code == 409
        invalid_avatar = test_app.client.patch(
            "/api/v1/community/members/me",
            json={"avatarUrl": "http://unsafe.example.test/avatar.png"},
        )
        assert invalid_avatar.status_code == 422
        reserved = test_app.client.patch(
            "/api/v1/community/members/me",
            json={"username": "me"},
        )
        assert reserved.status_code == 422

        assert (
            test_app.client.put(
                f"/api/v1/community/members/{OTHER_ID}/follow"
            ).status_code
            == 200
        )
        test_app.set_principal(OTHER_ID)
        assert (
            test_app.client.put(
                f"/api/v1/community/members/{OWNER_ID}/follow"
            ).status_code
            == 200
        )

        test_app.viewer_principal = _principal(OWNER_ID)
        followers = test_app.client.get(
            "/api/v1/community/members/new_user-1/followers?page=1&pageSize=20"
        )
        following = test_app.client.get(
            "/api/v1/community/members/new_user-1/following?page=1&pageSize=20"
        )
        assert followers.status_code == 200, followers.text
        assert following.status_code == 200, following.text
        assert followers.json()["meta"]["total"] == 1
        assert following.json()["meta"]["total"] == 1
        for page in (followers.json(), following.json()):
            assert page["data"][0] == {
                "id": str(OTHER_ID),
                "username": "other-member",
                "displayName": "Other public name",
                "avatarUrl": None,
                "roleLabel": None,
                "isAdmin": False,
                "membershipTier": "MEMBER",
                "viewerIsFollowing": True,
            }
            assert "private-other@example.test" not in str(page)
        assert (
            test_app.client.get(
                "/api/v1/community/members/new_user-1/followers?pageSize=51"
            ).status_code
            == 422
        )
    finally:
        test_app.close()


class _ViewDedupRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.keys: set[str] = set()

    async def eval(
        self,
        _script: str,
        _key_count: int,
        key: str,
        _window: int,
    ) -> list[int]:
        count = self.counts.get(key, 0) + 1
        self.counts[key] = count
        return [count, 60]

    async def set(self, key: str, _value: str, *, ex: int, nx: bool) -> bool:
        assert ex > 0
        assert nx is True
        if key in self.keys:
            return False
        self.keys.add(key)
        return True

    async def aclose(self) -> None:
        return None


def test_post_views_use_signed_visitor_dedup_and_stay_public_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    redis_client = _ViewDedupRedis()
    monkeypatch.setattr(Redis, "from_url", lambda _url: redis_client)
    test_app.app.state.settings.engagement_visitor_hmac_secret = SecretStr(
        "community-test-secret-long-enough"
    )
    try:
        published_id = _insert_post(
            test_app,
            slug="viewable-community-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        draft_id = _insert_post(
            test_app,
            slug="private-view-community-post",
            status=CommunityPostStatus.DRAFT,
        )
        before = test_app.client.get("/api/v1/community/posts/viewable-community-post")
        assert before.status_code == 200, before.text
        assert before.json()["data"]["viewCount"] == 0

        view_url = f"/api/v1/community/posts/{published_id}/views"
        first_view = test_app.client.post(view_url)
        assert first_view.status_code == 204, first_view.text
        assert "cns_engagement_visitor" in first_view.headers.get("set-cookie", "")
        repeated_view = test_app.client.post(view_url)
        assert repeated_view.status_code == 204
        after = test_app.client.get("/api/v1/community/posts/viewable-community-post")
        assert after.json()["data"]["viewCount"] == 1

        private_view = test_app.client.post(f"/api/v1/community/posts/{draft_id}/views")
        assert private_view.status_code == 404
    finally:
        test_app.close()


def test_admin_post_workspace_and_reversible_moderation_states(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    test_app.app.dependency_overrides[get_media_service] = lambda: (
        _NoopMediaAssetDeleter()
    )
    try:
        post_id = _insert_post(
            test_app,
            slug="admin-workspace-searchable-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
            title="Searchable moderation workspace",
            content="Search this admin post body.",
        )
        comment_id = uuid4()

        async def insert_comment() -> None:
            async with test_app.sessions() as session:
                session.add(
                    CommunityComment(
                        id=comment_id,
                        post_id=post_id,
                        author_user_id=OWNER_ID,
                        content="Owner comment remains editable while locked.",
                        created_at=NOW,
                    )
                )
                await session.commit()

        asyncio.run(insert_comment())
        test_app.set_principal(OTHER_ID, roles=("MODERATOR",))
        forbidden = test_app.client.get("/api/v1/admin/community/posts")
        assert forbidden.status_code == 403

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        workspace = test_app.client.get(
            "/api/v1/admin/community/posts?q=Searchable&status=PUBLISHED"
        )
        assert workspace.status_code == 200, workspace.text
        item = workspace.json()["data"][0]
        assert item["id"] == str(post_id)
        assert item["status"] == "PUBLISHED"
        assert item["isPinned"] is False
        assert item["commentsLocked"] is False
        assert item["deletedAt"] is None
        assert item["preDeleteStatus"] is None
        assert item["author"]["username"] == "community-owner"
        assert "private-owner@example.test" not in workspace.text

        pinned = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/pin",
            json={"reason": "Feature this public community post."},
        )
        assert pinned.status_code == 200, pinned.text
        assert pinned.json()["data"] == {
            "postId": str(post_id),
            "isPinned": True,
        }
        public_detail = test_app.client.get(
            "/api/v1/community/posts/admin-workspace-searchable-post"
        )
        assert public_detail.json()["data"]["isPinned"] is True
        unpinned = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/unpin",
            json={"reason": "Remove the featured marker."},
        )
        assert unpinned.json()["data"]["isPinned"] is False

        locked = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/comments/lock",
            json={"reason": "Pause new replies during review."},
        )
        assert locked.status_code == 200, locked.text
        assert locked.json()["data"] == {
            "postId": str(post_id),
            "commentsLocked": True,
        }
        test_app.set_principal(OWNER_ID)
        blocked_comment = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "This write is blocked by the lock."},
        )
        assert blocked_comment.status_code == 409
        edited = test_app.client.patch(
            f"/api/v1/community/comments/{comment_id}",
            json={"content": "Edits remain allowed while the thread is locked."},
        )
        assert edited.status_code == 200, edited.text
        deleted_comment = test_app.client.delete(
            f"/api/v1/community/comments/{comment_id}"
        )
        assert deleted_comment.status_code == 204

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        unlocked = test_app.client.post(
            f"/api/v1/admin/community/posts/{post_id}/comments/unlock",
            json={"reason": "Review is complete."},
        )
        assert unlocked.json()["data"]["commentsLocked"] is False

        admin_media_id = _insert_community_image(test_app)

        async def attach_admin_media() -> None:
            async with test_app.sessions() as session:
                session.add(
                    CommunityPostMedia(
                        post_id=post_id,
                        media_asset_id=admin_media_id,
                        sort_order=0,
                    )
                )
                await session.commit()

        asyncio.run(attach_admin_media())
        deleted_admin_media: list[UUID] = []

        class _AdminAssetDeleter:
            async def delete_community_post_asset(
                self,
                _principal: AuthPrincipal,
                media_id: UUID,
                *,
                owner_user_id: UUID,
            ) -> None:
                assert owner_user_id == OWNER_ID
                deleted_admin_media.append(media_id)

        test_app.app.dependency_overrides[get_media_service] = lambda: (
            _AdminAssetDeleter()
        )
        deleted = test_app.client.request(
            "DELETE",
            f"/api/v1/admin/community/posts/{post_id}",
            json={"reason": "Remove policy-violating material."},
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted_admin_media == [admin_media_id]
        assert deleted.json()["data"] == {
            "postId": str(post_id),
            "isDeleted": True,
            "deletedAt": deleted.json()["data"]["deletedAt"],
            "restoredStatus": None,
        }
        assert (
            test_app.client.get(
                "/api/v1/community/posts/admin-workspace-searchable-post"
            ).status_code
            == 404
        )

        async def assert_admin_content_purged() -> None:
            async with test_app.sessions() as session:
                assert await session.get(CommunityPost, post_id) is None
                assert await session.get(MediaAsset, admin_media_id) is None

        asyncio.run(assert_admin_content_purged())
        assert (
            test_app.client.post(
                f"/api/v1/admin/community/posts/{post_id}/restore",
                json={"reason": "A deleted post cannot be restored."},
            ).status_code
            == 404
        )

        hidden_post_id = _insert_post(
            test_app,
            slug="admin-hidden-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        hidden = test_app.client.post(
            f"/api/v1/admin/community/posts/{hidden_post_id}/hide",
            json={"reason": "Keep this post hidden pending review."},
        )
        assert hidden.status_code == 200
        hidden_pin = test_app.client.post(
            f"/api/v1/admin/community/posts/{hidden_post_id}/pin",
            json={"reason": "Must reject pinning hidden content."},
        )
        assert hidden_pin.status_code == 409
        admin_delete_hidden = test_app.client.request(
            "DELETE",
            f"/api/v1/admin/community/posts/{hidden_post_id}",
            json={"reason": "Remove while keeping hidden status."},
        )
        assert admin_delete_hidden.status_code == 200
        hidden_restore = test_app.client.post(
            f"/api/v1/admin/community/posts/{hidden_post_id}/restore",
            json={"reason": "Restore to its prior hidden state."},
        )
        assert hidden_restore.status_code == 404

        owner_deleted_post = _insert_post(
            test_app,
            slug="owner-deleted-post-not-restorable",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        test_app.set_principal(OWNER_ID)
        owner_delete = test_app.client.delete(
            f"/api/v1/community/posts/{owner_deleted_post}"
        )
        assert owner_delete.status_code == 204
        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        assert (
            test_app.client.request(
                "DELETE",
                f"/api/v1/admin/community/posts/{owner_deleted_post}",
                json={"reason": "Cannot convert an owner deletion."},
            ).status_code
            == 404
        )
        assert (
            test_app.client.post(
                f"/api/v1/admin/community/posts/{owner_deleted_post}/restore",
                json={"reason": "Owner deletion cannot be reversed by admin."},
            ).status_code
            == 404
        )
        history = test_app.client.get(
            "/api/v1/admin/community/moderation-history"
            f"?targetType=POST&targetId={post_id}"
        )
        assert history.status_code == 200
        assert [item["action"] for item in history.json()["data"]] == [
            "POST_ADMIN_DELETED"
        ]
    finally:
        test_app.close()


def test_admin_comment_workspace_preserves_visibility_and_owner_deletes(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="admin-comment-search-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        visible_comment_id = uuid4()
        owner_deleted_comment_id = uuid4()

        async def insert_comments() -> None:
            async with test_app.sessions() as session:
                session.add_all(
                    [
                        CommunityComment(
                            id=visible_comment_id,
                            post_id=post_id,
                            author_user_id=OWNER_ID,
                            content="Searchable content for comment moderation.",
                            created_at=NOW,
                        ),
                        CommunityComment(
                            id=owner_deleted_comment_id,
                            post_id=post_id,
                            author_user_id=OWNER_ID,
                            content="Comment deleted by its owner.",
                            created_at=NOW,
                        ),
                    ]
                )
                await session.commit()

        asyncio.run(insert_comments())
        test_app.set_principal(OWNER_ID)
        owner_deleted = test_app.client.delete(
            f"/api/v1/community/comments/{owner_deleted_comment_id}"
        )
        assert owner_deleted.status_code == 204

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        hidden = test_app.client.post(
            f"/api/v1/admin/community/comments/{visible_comment_id}/hide",
            json={"reason": "Hide this comment during review."},
        )
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["data"] == {
            "commentId": str(visible_comment_id),
            "visibility": "HIDDEN",
        }
        workspace = test_app.client.get(
            "/api/v1/admin/community/comments?q=Searchable"
            "&authorUsername=community-owner&visibility=HIDDEN"
        )
        assert workspace.status_code == 200, workspace.text
        item = workspace.json()["data"][0]
        assert item["visibility"] == "HIDDEN"
        assert item["post"] == {
            "id": str(post_id),
            "slug": "admin-comment-search-post",
            "title": "Admin Comment Search Post",
        }
        assert item["author"]["username"] == "community-owner"
        assert "private-owner@example.test" not in workspace.text

        deleted = test_app.client.post(
            f"/api/v1/admin/community/comments/{visible_comment_id}/delete",
            json={"reason": "Remove this comment while retaining state."},
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["data"]["visibility"] == "DELETED"
        deleted_workspace = test_app.client.get(
            "/api/v1/admin/community/comments?visibility=DELETED&q=Searchable%20content"
        )
        deleted_item = next(
            item
            for item in deleted_workspace.json()["data"]
            if item["id"] == str(visible_comment_id)
        )
        assert deleted_item["content"] == "Searchable content for comment moderation."
        assert deleted_item["author"]["username"] == "community-owner"
        assert "private-owner@example.test" not in deleted_workspace.text
        restored = test_app.client.post(
            f"/api/v1/admin/community/comments/{visible_comment_id}/restore",
            json={"reason": "Restore the hidden state for continued review."},
        )
        assert restored.status_code == 200
        assert restored.json()["data"]["visibility"] == "HIDDEN"
        unhidden = test_app.client.post(
            f"/api/v1/admin/community/comments/{visible_comment_id}/restore",
            json={"reason": "Make the reviewed comment visible again."},
        )
        assert unhidden.json()["data"]["visibility"] == "VISIBLE"
        owner_restore = test_app.client.post(
            f"/api/v1/admin/community/comments/{owner_deleted_comment_id}/restore",
            json={"reason": "Owner-deleted content cannot be revived."},
        )
        assert owner_restore.status_code == 409
    finally:
        test_app.close()


def test_admin_member_finder_and_time_bounded_restrictions(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    test_app.app.dependency_overrides[get_media_service] = lambda: (
        _NoopMediaAssetDeleter()
    )
    try:
        draft_ids = [
            _insert_post(
                test_app,
                slug=f"restricted-draft-{index}",
                status=CommunityPostStatus.DRAFT,
            )
            for index in range(3)
        ]
        post_id = _insert_post(
            test_app,
            slug="restriction-target-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        comment_id = uuid4()

        async def insert_comment() -> None:
            async with test_app.sessions() as session:
                session.add(
                    CommunityComment(
                        id=comment_id,
                        post_id=post_id,
                        author_user_id=OWNER_ID,
                        content="A comment to edit or delete.",
                        created_at=NOW,
                    )
                )
                await session.commit()

        asyncio.run(insert_comment())
        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        post_restriction = test_app.client.post(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions",
            json={
                "scope": "POSTS",
                "durationMinutes": 60,
                "reason": "Pause post creation while account is reviewed.",
            },
        )
        assert post_restriction.status_code == 201, post_restriction.text
        post_restriction_id = post_restriction.json()["data"]["id"]
        assert post_restriction.json()["data"]["scope"] == "POSTS"
        invalid_duration = test_app.client.post(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions",
            json={"scope": "COMMENTS", "durationMinutes": 0, "reason": "Invalid."},
        )
        assert invalid_duration.status_code == 422

        test_app.set_principal(OWNER_ID)
        blocked_create = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Restricted new post",
                "content": "Must not be created.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        assert blocked_create.status_code == 403
        blocked_update = test_app.client.patch(
            f"/api/v1/community/posts/{draft_ids[0]}",
            json={
                "title": "Restricted draft edit",
                "content": "Must not be updated.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        assert blocked_update.status_code == 403
        blocked_submit = test_app.client.post(
            f"/api/v1/community/posts/{draft_ids[1]}/submit"
        )
        assert blocked_submit.status_code == 403
        allowed_post_delete = test_app.client.delete(
            f"/api/v1/community/posts/{draft_ids[2]}"
        )
        assert allowed_post_delete.status_code == 204

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        comment_restriction = test_app.client.post(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions",
            json={
                "scope": "COMMENTS",
                "durationMinutes": 30,
                "reason": "Pause comment activity temporarily.",
            },
        )
        assert comment_restriction.status_code == 201
        restriction_id = comment_restriction.json()["data"]["id"]
        history = test_app.client.get(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions"
        )
        assert history.status_code == 200
        assert {item["status"] for item in history.json()["data"]} == {"ACTIVE"}
        finder = test_app.client.get(
            "/api/v1/admin/community/members?q=community-owner"
        )
        assert finder.status_code == 200, finder.text
        member = finder.json()["data"][0]
        assert member["member"] == {
            "id": str(OWNER_ID),
            "username": "community-owner",
            "displayName": "Public community name",
            "avatarUrl": None,
            "email": "private-owner@example.test",
            "hasPublicProfile": True,
        }
        assert member["publishedPostCount"] >= 1
        assert member["commentCount"] >= 1
        assert len(member["activeRestrictions"]) == 2
        assert "private-owner@example.test" in finder.text

        test_app.set_principal(OWNER_ID)
        blocked_comment = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={"content": "Restricted comment."},
        )
        assert blocked_comment.status_code == 403
        blocked_edit = test_app.client.patch(
            f"/api/v1/community/comments/{comment_id}",
            json={"content": "Restricted edit."},
        )
        assert blocked_edit.status_code == 403
        allowed_comment_delete = test_app.client.delete(
            f"/api/v1/community/comments/{comment_id}"
        )
        assert allowed_comment_delete.status_code == 204

        test_app.set_principal(OTHER_ID, permissions=("community.moderate",))
        revoked = test_app.client.request(
            "DELETE",
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions/{restriction_id}",
            json={"reason": "The temporary restriction is no longer needed."},
        )
        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["data"]["status"] == "REVOKED"

        expiring = test_app.client.post(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions",
            json={
                "scope": "POSTS",
                "durationMinutes": 1,
                "reason": "Short test restriction for expiry behavior.",
            },
        )
        assert expiring.status_code == 201, expiring.text
        expiring_id = UUID(expiring.json()["data"]["id"])

        async def expire_restrictions() -> None:
            async with test_app.sessions() as session:
                async with session.begin():
                    expired_at = datetime.now(UTC) - timedelta(minutes=1)
                    for restriction_id_to_expire in (
                        UUID(post_restriction_id),
                        expiring_id,
                    ):
                        restriction = await session.get(
                            CommunityMemberRestriction,
                            restriction_id_to_expire,
                        )
                        assert restriction is not None
                        restriction.starts_at = expired_at - timedelta(minutes=1)
                        restriction.expires_at = expired_at

        asyncio.run(expire_restrictions())
        history = test_app.client.get(
            f"/api/v1/admin/community/members/{OWNER_ID}/restrictions"
        )
        statuses = {item["status"] for item in history.json()["data"]}
        assert statuses >= {"EXPIRED", "REVOKED"}
        member_events = test_app.client.get(
            "/api/v1/admin/community/moderation-history"
            f"?targetType=MEMBER&targetId={OWNER_ID}"
        )
        assert member_events.status_code == 200, member_events.text
        member_actions = {item["action"] for item in member_events.json()["data"]}
        assert member_actions >= {"MEMBER_RESTRICTED", "MEMBER_RESTRICTION_REVOKED"}
        assert all(item["requestId"] for item in member_events.json()["data"])

        test_app.set_principal(OWNER_ID)
        after_expiry = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Post restriction expired",
                "content": "Expired restrictions no longer block writes.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        assert after_expiry.status_code == 201, after_expiry.text
    finally:
        test_app.close()


def test_community_comment_mentions_create_safe_deduplicated_notifications(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        post_id = _insert_post(
            test_app,
            slug="community-mention-post",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        test_app.set_principal(OTHER_ID)
        created = test_app.client.post(
            f"/api/v1/community/posts/{post_id}/comments",
            json={
                "content": (
                    "Please see @COMMUNITY-OWNER, @community-owner, and @unknown-user."
                )
            },
        )
        assert created.status_code == 201, created.text

        test_app.set_principal(OWNER_ID)
        notifications = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["data"]
        assert len(notifications) == 1
        assert notifications[0]["type"] == "COMMUNITY_MENTION"
        assert notifications[0]["data"] == {
            "actionPath": "/community/posts/community-mention-post"
        }
        assert "private-owner@example.test" not in str(notifications)
        assert "private-other@example.test" not in str(notifications)

        test_app.set_principal(OTHER_ID)
        assert (
            test_app.client.get("/api/v1/notifications?page=1&pageSize=50").json()[
                "meta"
            ]["total"]
            == 0
        )
    finally:
        test_app.close()


def test_community_post_mentions_notify_on_immediate_publication(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    try:
        test_app.set_principal(OTHER_ID)
        created = test_app.client.post(
            "/api/v1/community/posts",
            json={
                "title": "Community mention post",
                "content": "A public story for @community-owner.",
                "categoryId": str(CATEGORY_ID),
            },
        )
        assert created.status_code == 201, created.text
        post_id = created.json()["data"]["id"]
        submitted = test_app.client.post(f"/api/v1/community/posts/{post_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["data"]["status"] == "PUBLISHED"

        test_app.set_principal(OWNER_ID)
        notifications = test_app.client.get(
            "/api/v1/notifications?page=1&pageSize=50"
        ).json()["data"]
        assert [item["type"] for item in notifications] == ["COMMUNITY_MENTION"]
        assert notifications[0]["data"]["actionPath"] == (
            f"/community/posts/{submitted.json()['data']['slug']}"
        )
    finally:
        test_app.close()


def test_owner_delete_permanently_cleans_post_dependencies_and_keeps_audit(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    deleted_media: list[UUID] = []

    class _AssetDeleter:
        async def delete_community_post_asset(
            self,
            _principal: AuthPrincipal,
            media_id: UUID,
            *,
            owner_user_id: UUID,
        ) -> None:
            assert owner_user_id == OWNER_ID
            deleted_media.append(media_id)

    try:
        post_id = _insert_post(
            test_app,
            slug="permanent-delete-target",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        other_post_id = _insert_post(
            test_app,
            slug="permanent-delete-unrelated",
            status=CommunityPostStatus.PUBLISHED,
            published_at=NOW,
        )
        media_id = _insert_community_image(test_app)
        foreign_media_id = _insert_community_image(test_app, owner_id=OTHER_ID)
        other_media_id = _insert_community_image(test_app)
        parent_id, reply_id = uuid4(), uuid4()
        post_report_id, comment_report_id = uuid4(), uuid4()
        post_event_id, comment_event_id = uuid4(), uuid4()

        async def add_dependents() -> None:
            async with test_app.sessions() as session:
                session.add_all(
                    [
                        CommunityPostMedia(
                            post_id=post_id,
                            media_asset_id=media_id,
                            sort_order=0,
                        ),
                        CommunityPostMedia(
                            post_id=post_id,
                            media_asset_id=foreign_media_id,
                            sort_order=1,
                        ),
                        CommunityPostMedia(
                            post_id=other_post_id,
                            media_asset_id=other_media_id,
                            sort_order=0,
                        ),
                        CommunityComment(
                            id=parent_id,
                            post_id=post_id,
                            author_user_id=OWNER_ID,
                            content="Parent comment to delete.",
                            created_at=NOW,
                        ),
                        CommunityComment(
                            id=reply_id,
                            post_id=post_id,
                            author_user_id=OTHER_ID,
                            parent_id=parent_id,
                            content="Reply to delete.",
                            created_at=NOW,
                        ),
                        CommunityLike(post_id=post_id, user_id=OWNER_ID),
                        CommunityLike(post_id=post_id, user_id=OTHER_ID),
                        CommunityBookmark(post_id=post_id, user_id=OTHER_ID),
                        CommunityCommentLike(comment_id=reply_id, user_id=OWNER_ID),
                        CommunityModerationLog(
                            post_id=post_id,
                            actor_user_id=OWNER_ID,
                            action=CommunityModerationAction.PUBLISHED,
                            request_id="publish-request",
                        ),
                        CommunityReport(
                            id=post_report_id,
                            reporter_user_id=OTHER_ID,
                            post_id=post_id,
                            reason="OTHER",
                            request_id="post-report-request",
                        ),
                        CommunityReport(
                            id=comment_report_id,
                            reporter_user_id=OTHER_ID,
                            comment_id=reply_id,
                            reason="OTHER",
                            request_id="comment-report-request",
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        CommunityModerationEvent(
                            id=post_event_id,
                            target_type="POST",
                            target_id=str(post_id),
                            action=CommunityModerationEventAction.PUBLISHED.value,
                            actor_user_id=OWNER_ID,
                            request_id="publish-request",
                        ),
                        CommunityModerationEvent(
                            id=comment_event_id,
                            target_type="COMMENT",
                            target_id=str(reply_id),
                            action=CommunityModerationEventAction.REPORT_DISMISSED.value,
                            actor_user_id=OWNER_ID,
                            report_id=comment_report_id,
                            request_id="comment-report-request",
                        ),
                        Notification(
                            user_id=OTHER_ID,
                            source_event_id=post_event_id,
                            type="COMMUNITY_MENTION",
                            title="Community post",
                            body="A notification referencing this post.",
                            data_json={
                                "actionPath": "/community/posts/permanent-delete-target"
                            },
                            created_at=NOW,
                        ),
                    ]
                )
                await session.commit()

        asyncio.run(add_dependents())
        test_app.app.dependency_overrides[get_media_service] = lambda: _AssetDeleter()

        response = test_app.client.delete(f"/api/v1/community/posts/{post_id}")

        assert response.status_code == 204, response.text
        assert deleted_media == [media_id]
        assert (
            test_app.client.get(
                "/api/v1/community/posts/permanent-delete-target"
            ).status_code
            == 404
        )

        async def assert_database_cleanup() -> None:
            async with test_app.sessions() as session:
                assert await session.get(CommunityPost, post_id) is None
                assert await session.get(MediaAsset, media_id) is None
                assert await session.get(CommunityPost, other_post_id) is not None
                foreign_media = await session.get(MediaAsset, foreign_media_id)
                other_media = await session.get(MediaAsset, other_media_id)
                assert foreign_media is not None
                assert foreign_media.status is MediaStatus.ACTIVE
                assert other_media is not None
                assert other_media.status is MediaStatus.ACTIVE
                assert (
                    await session.scalar(
                        select(CommunityPostMedia).where(
                            CommunityPostMedia.post_id == other_post_id,
                            CommunityPostMedia.media_asset_id == other_media_id,
                        )
                    )
                ) is not None
                assert (
                    await session.scalars(
                        select(CommunityComment).where(
                            CommunityComment.post_id == post_id
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityLike).where(CommunityLike.post_id == post_id)
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityBookmark).where(
                            CommunityBookmark.post_id == post_id
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityCommentLike).where(
                            CommunityCommentLike.comment_id.in_((parent_id, reply_id))
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityPostMedia).where(
                            CommunityPostMedia.post_id == post_id
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityReport).where(
                            (CommunityReport.post_id == post_id)
                            | (CommunityReport.comment_id.in_((parent_id, reply_id)))
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(Notification).where(
                            Notification.source_event_id == post_event_id
                        )
                    )
                ).all() == []
                assert (
                    await session.scalars(
                        select(CommunityModerationLog).where(
                            CommunityModerationLog.post_id == post_id
                        )
                    )
                ).all() == []
                owner_delete_events = (
                    await session.scalars(
                        select(CommunityModerationEvent).where(
                            CommunityModerationEvent.target_type == "POST",
                            CommunityModerationEvent.target_id == str(post_id),
                        )
                    )
                ).all()
                assert len(owner_delete_events) == 1
                assert owner_delete_events[0].action == "OWNER_DELETED"

        asyncio.run(assert_database_cleanup())

        legacy_deleted_media_id = _insert_community_image(test_app)
        deleted_assets: list[UUID] = []

        class _DeletedAssetProvider:
            async def delete_community_post_asset(
                self,
                principal: AuthPrincipal,
                media_id: UUID,
                *,
                owner_user_id: UUID,
            ) -> None:
                assert principal.user_id == owner_user_id == OWNER_ID
                deleted_assets.append(media_id)

        async def purge_legacy_deleted_media() -> None:
            async with test_app.sessions() as session:
                legacy_asset = await session.get(MediaAsset, legacy_deleted_media_id)
                assert legacy_asset is not None
                legacy_asset.status = MediaStatus.DELETED
                legacy_asset.deleted_at = NOW
                await session.commit()

            async with test_app.sessions() as session:
                assert (
                    await CommunityMediaRetentionService(session).purge_deleted_assets(
                        _DeletedAssetProvider()
                    )
                ) == 1
                assert await session.get(MediaAsset, legacy_deleted_media_id) is None

        asyncio.run(purge_legacy_deleted_media())
        assert deleted_assets == [legacy_deleted_media_id]
    finally:
        test_app.close()


def test_retention_purges_legacy_admin_deleted_posts_and_images(
    tmp_path: Path,
) -> None:
    test_app = CommunityTestApp(tmp_path)
    deleted_media: list[UUID] = []

    class _AssetDeleter:
        async def delete_community_post_asset(
            self,
            principal: AuthPrincipal,
            media_id: UUID,
            *,
            owner_user_id: UUID,
        ) -> None:
            assert principal.user_id == OTHER_ID
            assert owner_user_id == OWNER_ID
            deleted_media.append(media_id)

    try:
        post_id = _insert_post(
            test_app,
            slug="legacy-admin-deleted-post",
            status=CommunityPostStatus.DELETED,
            published_at=NOW,
        )
        media_id = _insert_community_image(test_app)
        event_id = uuid4()

        async def add_legacy_deleted_content() -> None:
            async with test_app.sessions() as session:
                post = await session.get(CommunityPost, post_id)
                assert post is not None
                post.admin_deleted = True
                post.pre_delete_status = CommunityPostStatus.PUBLISHED.value
                post.deleted_at = NOW
                session.add(
                    CommunityPostMedia(
                        post_id=post_id,
                        media_asset_id=media_id,
                        sort_order=0,
                    )
                )
                session.add(
                    CommunityModerationEvent(
                        id=event_id,
                        target_type="POST",
                        target_id=str(post_id),
                        action="POST_ADMIN_DELETED",
                        actor_user_id=OTHER_ID,
                        reason="Old moderation reason.",
                        request_id="legacy-delete-request",
                        event_data={"restoredStatus": "PUBLISHED"},
                    )
                )
                await session.flush()
                session.add(
                    Notification(
                        user_id=OWNER_ID,
                        source_event_id=event_id,
                        type="COMMUNITY_POST_REMOVED",
                        title="Bài viết đã bị gỡ",
                        body="Lý do gỡ bài cũ.",
                        data_json={
                            "actionPath": "/community/posts/legacy-admin-deleted-post"
                        },
                        created_at=NOW,
                    )
                )
                await session.commit()

        asyncio.run(add_legacy_deleted_content())

        async def purge_legacy_content() -> None:
            async with test_app.sessions() as session:
                assert (
                    await CommunityAdminService(session).purge_legacy_deleted_posts(
                        _AssetDeleter()
                    )
                ) == 1
            async with test_app.sessions() as session:
                assert await session.get(CommunityPost, post_id) is None
                assert await session.get(MediaAsset, media_id) is None
                tombstone = await session.get(CommunityModerationEvent, event_id)
                assert tombstone is not None
                assert tombstone.action == "POST_ADMIN_DELETED"
                assert tombstone.reason is None
                assert tombstone.event_data is None
                assert (
                    await session.scalars(
                        select(Notification).where(
                            Notification.source_event_id == event_id
                        )
                    )
                ).all() == []

        asyncio.run(purge_legacy_content())
        assert deleted_media == [media_id]
    finally:
        test_app.close()
