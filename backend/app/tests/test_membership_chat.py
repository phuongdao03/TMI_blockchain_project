import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.errors import DomainError
from app.main import create_application  # noqa: F401
from app.modules.auth.session_service import AuthPrincipal
from app.modules.memberships.chat_cursor import (
    MembershipChatCursorCodec,
    MembershipChatCursorInvalidError,
)
from app.modules.memberships.models import CommunityChatMessage
from app.modules.memberships.service import MembershipService
from app.modules.payments.errors import (
    PaymentConflictError,
    PaymentForbiddenError,
    PaymentNotFoundError,
)
from app.tests.test_payment_service import ADMIN_ID, _service


def test_chat_history_uses_stable_room_bound_cursor_pages() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        try:
            async with payment._session.begin():
                timestamp = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
                payment._session.add_all(
                    [
                        CommunityChatMessage(
                            id=UUID(int=message_id),
                            user_id=owner.user_id,
                            room="MEMBER",
                            body=f"Message {message_id}",
                            tier_snapshot="MEMBER",
                            created_at=timestamp,
                        )
                        for message_id in range(1, 121)
                    ]
                )
            service = MembershipService(payment._session)

            newest = await service.chat_history(owner, "MEMBER", limit=100)
            decoded_cursor = MembershipChatCursorCodec().decode(
                newest["next_cursor"], expected_room="MEMBER"
            )
            assert decoded_cursor.message_id == UUID(int=21)
            assert decoded_cursor.created_at == timestamp
            older = await service.chat_history(
                owner,
                "MEMBER",
                limit=100,
                cursor=newest["next_cursor"],
            )

            ids = [item["id"] for item in (*older["items"], *newest["items"])]
            assert len(newest["items"]) == 100
            assert newest["has_more"] is True
            assert older["has_more"] is False
            assert older["next_cursor"] is None
            assert len(older["items"]) == 20
            assert ids == [UUID(int=message_id) for message_id in range(1, 121)]

            admin = AuthPrincipal(
                user_id=ADMIN_ID,
                session_id=owner.session_id,
                email="admin@example.vn",
                roles=("SUPER_ADMIN",),
            )
            with pytest.raises(MembershipChatCursorInvalidError):
                await service.chat_history(
                    admin,
                    "COMPANION",
                    cursor=newest["next_cursor"],
                )
            with pytest.raises(DomainError) as limit_error:
                await service.chat_history(owner, "MEMBER", limit=101)
            assert limit_error.value.status_code == 422
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_chat_edit_is_owner_only_and_removed_messages_are_immutable() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        try:
            service = MembershipService(payment._session)
            message = await service.send_chat(owner, "MEMBER", "Original message")
            assert message["can_edit"] is True

            other = AuthPrincipal(
                user_id=ADMIN_ID,
                session_id=owner.session_id,
                email="other@example.vn",
                roles=(),
            )
            with pytest.raises(PaymentForbiddenError):
                await service.edit_chat_message(other, message["id"], "Changed")

            edited = await service.edit_chat_message(
                owner, message["id"], "Updated message"
            )
            assert edited["body"] == "Updated message"
            assert edited["edited_at"] is not None

            moderator = AuthPrincipal(
                user_id=ADMIN_ID,
                session_id=owner.session_id,
                email="moderator@example.vn",
                roles=(),
                permissions=("community.moderate",),
            )
            await service.remove_message(moderator, message["id"])
            with pytest.raises(PaymentNotFoundError):
                await service.edit_chat_message(owner, message["id"], "Too late")
            with pytest.raises(PaymentNotFoundError):
                await service.remove_message(owner, message["id"])
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_chat_send_and_edit_reject_blank_or_oversized_messages() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        try:
            service = MembershipService(payment._session)
            with pytest.raises(PaymentConflictError):
                await service.send_chat(owner, "MEMBER", "   ")
            message = await service.send_chat(owner, "MEMBER", "Valid")
            with pytest.raises(PaymentConflictError):
                await service.edit_chat_message(owner, message["id"], " " * 2001)
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
