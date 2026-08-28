import asyncio
import smtplib
from pathlib import Path
from types import TracebackType
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.notifications.email import (
    EmailDeliveryService,
    EmailMessage,
    SmtpEmailGateway,
    render_email,
)
from app.modules.notifications.models import DeliveryStatus
from app.modules.notifications.service import NotificationService
from app.workers.notification_tasks import (
    EMAIL_EVENTS,
    EVENT_ROLE_RECIPIENTS,
    _action_path,
    staff_invitation_message,
)


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

            await service.consume(
                event_id=uuid4(),
                user_id=user_id,
                event_type="dossier.supplement_requested",
                title="Cần bổ sung hồ sơ",
                body="Hồ sơ có yêu cầu bổ sung mới.",
                data={},
            )
            await service.consume(
                event_id=uuid4(),
                user_id=user_id,
                event_type="certificate.issued",
                title="Chứng thư đã phát hành",
                body="Chứng thư số đã sẵn sàng.",
                data={},
            )
            unread_rows, unread_total = await service.list(
                user_id, page=1, page_size=20, unread_only=True
            )
            assert len(unread_rows) == unread_total == 2
            assert await service.mark_all_read(user_id) == 2
            assert await service.mark_all_read(user_id) == 0
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
    assert "Trung tâm an ninh công nghệ số - CNS" in text
    assert "TMI Group" not in text
    assert "TMI Group" not in html
    assert "Tiếp tục xác minh" in html


def test_staff_invitation_email_uses_english_route_and_encodes_token() -> None:
    message = staff_invitation_message(
        email="reviewer@example.com",
        invitation_token="a/b+c",
        app_base_url="https://app.tmigroup.vn/",
    )

    assert message.to == "reviewer@example.com"
    assert "/staff-invitation?token=a%2Fb%2Bc" in message.text
    assert "/staff-invitation?token=a%2Fb%2Bc" in message.html


def test_smtp_gateway_uses_starttls_and_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, *, timeout: int) -> None:
            calls.append(("connect", (host, port, timeout)))

        def __enter__(self) -> "FakeSmtp":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

        def ehlo(self) -> None:
            calls.append(("ehlo", None))

        def starttls(self) -> None:
            calls.append(("starttls", None))

        def login(self, username: str, password: str) -> None:
            calls.append(("login", (username, password)))

        def send_message(self, _message: object) -> None:
            calls.append(("send", None))

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    gateway = SmtpEmailGateway(
        host="smtp.example.vn",
        port=587,
        sender="no-reply@tinhhoaviet.org.vn",
        username="mailer",
        password="secret",
        use_tls=True,
        timeout_seconds=12,
    )

    asyncio.run(
        gateway.send(
            EmailMessage(
                to="owner@example.vn",
                subject="Thông báo",
                text="Nội dung",
                html="<p>Nội dung</p>",
            )
        )
    )

    assert calls == [
        ("connect", ("smtp.example.vn", 587, 12)),
        ("ehlo", None),
        ("starttls", None),
        ("ehlo", None),
        ("login", ("mailer", "secret")),
        ("send", None),
    ]


def test_smtp_gateway_rejects_partial_credentials_and_conflicting_tls() -> None:
    try:
        SmtpEmailGateway(
            host="smtp.example.vn",
            port=587,
            sender="no-reply@example.vn",
            username="mailer",
        )
    except ValueError as error:
        assert "username and password" in str(error)
    else:
        raise AssertionError("Partial SMTP credentials must be rejected")

    try:
        SmtpEmailGateway(
            host="smtp.example.vn",
            port=465,
            sender="no-reply@example.vn",
            use_tls=True,
            use_ssl=True,
        )
    except ValueError as error:
        assert "TLS and SSL" in str(error)
    else:
        raise AssertionError("Conflicting SMTP transports must be rejected")


def test_critical_workflow_events_are_delivered_by_email() -> None:
    assert {
        "dossier.submitted",
        "dossier.supplement_requested",
        "review.assignment_created",
        "council.decided",
        "payment.paid",
        "certificate.issued",
        "certificate.revoked",
        "blockchain.anchored",
    }.issubset(EMAIL_EVENTS)


def test_role_notifications_and_action_paths_are_explicit() -> None:
    assert EVENT_ROLE_RECIPIENTS["dossier.submitted"] == frozenset({"SUPER_ADMIN"})
    assert (
        _action_path(
            "review.assignment_created",
            {"assignment_id": "4b6fe80a-1c87-4cc2-ad03-88decb6ebfab"},
        )
        == "/reviews/4b6fe80a-1c87-4cc2-ad03-88decb6ebfab"
    )
    assert _action_path("content_report.created", {}) == "/admin/content"
    assert _action_path("unknown.event", {"url": "https://evil.example"}) is None
