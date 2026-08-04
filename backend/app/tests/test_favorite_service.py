import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.favorite_repository import FavoriteListRow
from app.modules.engagement.favorite_service import FavoriteService

USER_ID = UUID("50000000-0000-0000-0000-000000000001")
WORK_ID = UUID("50000000-0000-0000-0000-000000000002")


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeWorks:
    def __init__(self, work_id: UUID | None = WORK_ID) -> None:
        self.work_id = work_id

    async def find_published_public_id(self, _slug: str) -> UUID | None:
        return self.work_id


class FakeFavorites:
    def __init__(self, *, creates: bool = True, removes: bool = True) -> None:
        self.creates = creates
        self.removes = removes
        self.add_calls: list[tuple[UUID, UUID]] = []
        self.remove_calls: list[tuple[UUID, UUID]] = []
        self.rows = (
            FavoriteListRow(
                favorite_id=uuid4(),
                public_work_id=WORK_ID,
                slug="public-work",
                title="Public work",
                short_description="A public work.",
                created_at=datetime(2026, 8, 4, tzinfo=UTC),
            ),
        )

    async def add_if_absent(self, *, user_id: UUID, public_work_id: UUID) -> bool:
        self.add_calls.append((user_id, public_work_id))
        return self.creates

    async def remove(self, *, user_id: UUID, public_work_id: UUID) -> bool:
        self.remove_calls.append((user_id, public_work_id))
        return self.removes

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[tuple[FavoriteListRow, ...], int]:
        assert user_id == USER_ID
        assert offset == 20
        assert limit == 20
        return self.rows, 1


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record(self, **event: object) -> None:
        self.events.append(event)


def principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=USER_ID,
        session_id=uuid4(),
        email="member@example.test",
        roles=("MEMBER",),
    )


def _service(
    *,
    works: FakeWorks | None = None,
    favorites: FakeFavorites | None = None,
    audit: FakeAudit | None = None,
) -> tuple[FavoriteService, FakeFavorites, FakeAudit]:
    resolved_favorites = favorites or FakeFavorites()
    resolved_audit = audit or FakeAudit()
    return (
        FavoriteService(
            cast(AsyncSession, FakeSession()),
            audit=cast(object, resolved_audit),
            favorites=resolved_favorites,
            works=works or FakeWorks(),
        ),
        resolved_favorites,
        resolved_audit,
    )


def test_add_favorite_is_idempotent_and_audits_only_the_state_change() -> None:
    service, favorites, audit = _service()

    assert (
        asyncio.run(service.add(principal(), slug="public-work", request_id="r-1"))
        is True
    )
    favorites.creates = False
    assert (
        asyncio.run(service.add(principal(), slug="public-work", request_id="r-2"))
        is False
    )

    assert favorites.add_calls == [(USER_ID, WORK_ID), (USER_ID, WORK_ID)]
    assert [event["action"] for event in audit.events] == [
        "public_work.favorite_added"
    ]


def test_remove_favorite_is_idempotent_and_owned_by_the_caller() -> None:
    service, favorites, audit = _service()

    assert (
        asyncio.run(
            service.remove(principal(), slug="public-work", request_id="r-1")
        )
        is True
    )
    favorites.removes = False
    assert (
        asyncio.run(
            service.remove(principal(), slug="public-work", request_id="r-2")
        )
        is False
    )

    assert favorites.remove_calls == [(USER_ID, WORK_ID), (USER_ID, WORK_ID)]
    assert [event["action"] for event in audit.events] == [
        "public_work.favorite_removed"
    ]


def test_favorite_hides_unpublished_or_inaccessible_work_as_not_found() -> None:
    service, favorites, _audit = _service(works=FakeWorks(work_id=None))

    with pytest.raises(DomainError) as captured:
        asyncio.run(service.add(principal(), slug="private-work", request_id="r-1"))

    assert captured.value.code == "PUBLIC_WORK_NOT_FOUND"
    assert favorites.add_calls == []


def test_list_favorites_is_caller_private_and_paginates() -> None:
    service, _favorites, _audit = _service()

    rows, total = asyncio.run(
        service.list_for_user(principal(), page=2, page_size=20)
    )

    assert total == 1
    assert rows[0].public_work_id == WORK_ID
