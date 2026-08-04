import asyncio
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.notifications.email import (
    EmailDeliveryService,
    EmailMessage,
    render_email,
)
from app.modules.notifications.models import DeliveryStatus
from app.modules.notifications.service import NotificationService


class FailingOnceGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def send(self, message: EmailMessage) -> str:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("provider unavailable")
        return "provider-42"


def test_notification_event_is_idempotent_and_unread_count_changes(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'notifications.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        async with factory() as session:
            session.add(
                User(
                    id=user_id,
                    email="owner@tmigroup.vn",
                    password_hash="hash",
                    status=UserStatus.ACTIVE,
                )
            )
            await session.commit()
            service = NotificationService(session)
            event_id = uuid4()
            first = await service.consume(
                event_id=event_id,
                user_id=user_id,
                event_type="dossier.submitted",
                title="Hồ sơ đã gửi",
                body="Hồ sơ đang chờ thẩm định.",
                data={"dossierId": str(uuid4())},
            )
            second = await service.consume(
                event_id=event_id,
                user_id=user_id,
                event_type="dossier.submitted",
                title="Không tạo bản sao",
                body="Ignored",
                data={},
            )
            assert first.id == second.id
            assert await service.unread_count(user_id) == 1
            await service.mark_read(user_id=user_id, notification_id=first.id)
            assert await service.unread_count(user_id) == 0
        await engine.dispose()

    asyncio.run(exercise())


def test_email_delivery_retries_without_duplicate_delivery(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'email.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        async with factory() as session:
            session.add(User(id=user_id, email="owner@tmigroup.vn", password_hash="h"))
            await session.commit()
            notification = await NotificationService(session).consume(
                event_id=uuid4(),
                user_id=user_id,
                event_type="certificate.issued",
                title="Chứng thư đã phát hành",
                body="Chứng thư đã sẵn sàng.",
                data={},
            )
            gateway = FailingOnceGateway()
            service = EmailDeliveryService(session=session, gateway=gateway)
            first = await service.deliver(notification.id)
            first_status = first.status
            second = await service.deliver(notification.id)
            third = await service.deliver(notification.id)
            assert first_status is DeliveryStatus.RETRY_PENDING
            assert second.status is DeliveryStatus.SENT
            assert third.id == second.id
            assert gateway.calls == 2
            assert second.destination_masked == "o***r@tmigroup.vn"
        await engine.dispose()

    asyncio.run(exercise())


def test_verification_email_contains_escaped_single_use_action_url() -> None:
    text, html = render_email(
        title="Xác minh tài khoản",
        body="Hoàn tất xác minh email.",
        action_url="https://app.tmigroup.vn/verify-email?token=a&next=b",
    )
    assert "token=a&next=b" in text
    assert "token=a&amp;next=b" in html
    assert "Tiếp tục xác minh" in html
