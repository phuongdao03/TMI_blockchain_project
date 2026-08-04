from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage as SmtpMessage
from html import escape
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    DeliveryStatus,
    NotificationChannel,
    NotificationDelivery,
)
from app.modules.notifications.repository import NotificationRepository


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


class EmailGateway(Protocol):
    async def send(self, message: EmailMessage) -> str: ...


def mask_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    if len(local) <= 2:
        masked = local[0] + "***" if local else "***"
    else:
        masked = f"{local[0]}***{local[-1]}"
    return f"{masked}@{domain}"


def render_email(
    *, title: str, body: str, action_url: str | None = None, version: str = "v1"
) -> tuple[str, str]:
    if version != "v1":
        raise ValueError("Unsupported email template version.")
    action_text = f"\n\n{action_url}" if action_url else ""
    action_html = (
        f'<p><a href="{escape(action_url, quote=True)}">Tiếp tục xác minh</a></p>'
        if action_url
        else ""
    )
    text = f"{title}\n\n{body}{action_text}\n\nTMI Certificate Platform"
    html = (
        '<div style="font-family:Arial,sans-serif;color:#18202b">'
        f"<h1>{escape(title)}</h1><p>{escape(body)}</p>{action_html}"
        "<p>TMI Certificate Platform</p></div>"
    )
    return text, html


class EmailDeliveryService:
    def __init__(self, *, session: AsyncSession, gateway: EmailGateway) -> None:
        self._session = session
        self._repository = NotificationRepository(session)
        self._gateway = gateway

    async def deliver(
        self, notification_id: UUID, *, action_url: str | None = None
    ) -> NotificationDelivery:
        async with self._session.begin():
            delivery = await self._repository.get_delivery(
                notification_id, NotificationChannel.EMAIL, for_update=True
            )
            item = await self._repository.notification_with_email(notification_id)
            if item is None:
                raise LookupError("Notification was not found.")
            notification, destination = item
            if delivery is not None and delivery.status is DeliveryStatus.SENT:
                return delivery
            if delivery is None:
                delivery = NotificationDelivery(
                    notification_id=notification_id,
                    channel=NotificationChannel.EMAIL,
                    destination_masked=mask_email(destination),
                    status=DeliveryStatus.PENDING,
                    attempt_count=0,
                    template_version="v1",
                )
                self._repository.add_delivery(delivery)
            delivery.attempt_count += 1
            text, html = render_email(
                title=notification.title,
                body=notification.body,
                action_url=action_url,
            )
            try:
                provider_id = await self._gateway.send(
                    EmailMessage(
                        to=destination,
                        subject=notification.title,
                        text=text,
                        html=html,
                    )
                )
            except Exception:
                delivery.status = (
                    DeliveryStatus.RETRY_PENDING
                    if delivery.attempt_count < 5
                    else DeliveryStatus.FAILED
                )
                delivery.last_error_code = "PROVIDER_UNAVAILABLE"
            else:
                delivery.status = DeliveryStatus.SENT
                delivery.provider_message_id = provider_id
                delivery.last_error_code = None
                delivery.sent_at = datetime.now(UTC)
            await self._session.flush()
            return delivery


class SmtpEmailGateway:
    """SMTP adapter. Network I/O is invoked only by a worker."""

    def __init__(self, *, host: str, port: int, sender: str) -> None:
        self._host = host
        self._port = port
        self._sender = sender

    async def send(self, message: EmailMessage) -> str:
        import asyncio
        import smtplib
        from uuid import uuid4

        smtp_message = SmtpMessage()
        smtp_message["From"] = self._sender
        smtp_message["To"] = message.to
        smtp_message["Subject"] = message.subject
        smtp_message.set_content(message.text)
        smtp_message.add_alternative(message.html, subtype="html")

        def _send() -> None:
            with smtplib.SMTP(self._host, self._port, timeout=20) as client:
                client.send_message(smtp_message)

        await asyncio.to_thread(_send)
        return str(uuid4())
