import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.activity import (
    ActivityCursor,
    ActivityCursorCodec,
    ActivityCursorInvalidError,
    ActivityKind,
)
from app.modules.engagement.activity_repository import ActivityListRow
from app.modules.engagement.activity_service import ActivityService

USER_ID = UUID("50000000-0000-0000-0000-000000000011")


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeActivityRepository:
    def __init__(self) -> None:
        self.user_id: UUID | None = None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[tuple[ActivityListRow, ...], str | None]:
        self.user_id = user_id
        assert cursor == "opaque-cursor"
        assert limit == 10
        return (
            (
                ActivityListRow(
                    activity_id=uuid4(),
                    kind=ActivityKind.SHARE,
                    public_work_id=uuid4(),
                    slug="public-work",
                    title="Public work",
                    short_description="A public work.",
                    channel="NATIVE",
                    created_at=datetime.now(UTC),
                ),
            ),
            "next-cursor",
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=USER_ID,
        session_id=uuid4(),
        email="member@example.test",
        roles=("MEMBER",),
    )


def test_activity_cursor_is_opaque_and_rejects_tampering() -> None:
    codec = ActivityCursorCodec()
    value = codec.encode(
        ActivityCursor(
            created_at=datetime(2026, 8, 4, 10, 0, tzinfo=UTC),
            activity_id=USER_ID,
        )
    )
    decoded = codec.decode(value)
    assert decoded.activity_id == USER_ID
    assert decoded.created_at == datetime(2026, 8, 4, 10, 0, tzinfo=UTC)

    try:
        codec.decode("tampered")
    except ActivityCursorInvalidError:
        pass
    else:
        raise AssertionError("tampered cursor must be rejected")


def test_activity_service_scopes_query_to_authenticated_user() -> None:
    repository = FakeActivityRepository()
    service = ActivityService(
        cast(AsyncSession, FakeSession()),
        repository=repository,
    )

    rows, next_cursor = asyncio.run(
        service.list_for_user(_principal(), cursor="opaque-cursor", limit=10)
    )

    assert repository.user_id == USER_ID
    assert rows[0].kind is ActivityKind.SHARE
    assert next_cursor == "next-cursor"
