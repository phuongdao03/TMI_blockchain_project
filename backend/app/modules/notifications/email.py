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
        '<p style="margin:28px 0 8px">'
        f'<a href="{escape(action_url, quote=True)}" '
        'style="display:inline-block;padding:12px 18px;border-radius:8px;'
        'background:#5f0010;color:#ffffff;font-weight:700;text-decoration:none">'
        "Tiếp tục xác minh</a></p>"
        if action_url
        else ""
    )
    signature = (
        "Đề cử Tinh Hoa Việt\nPhát triển bởi Trung tâm an ninh công nghệ số - CNS"
    )
    text = f"{title}\n\n{body}{action_text}\n\n{signature}"
    html = (
        '<div style="margin:0;background:#f7f3ed;padding:32px 16px;'
        'font-family:Arial,sans-serif;color:#241818">'
        '<div style="max-width:640px;margin:0 auto;border:1px solid #eaded7;'
        'border-radius:12px;background:#ffffff;overflow:hidden">'
        '<div style="height:6px;background:#720014"></div>'
        '<div style="padding:32px">'
        '<p style="margin:0 0 18px;color:#720014;font-size:12px;font-weight:700;'
        'letter-spacing:1.8px;text-transform:uppercase">Đề cử Tinh Hoa Việt</p>'
        f'<h1 style="margin:0 0 16px;font-size:28px;line-height:1.25">'
        f"{escape(title)}</h1>"
        f'<p style="margin:0;color:#5f5552;font-size:16px;line-height:1.65">'
        f"{escape(body)}</p>{action_html}"
        '<p style="margin:32px 0 0;padding-top:20px;border-top:1px solid #eaded7;'
        'color:#766b67;font-size:13px;line-height:1.55">'
        "Đề cử Tinh Hoa Việt<br>"
        "Phát triển bởi Trung tâm an ninh công nghệ số - CNS</p>"
        "</div></div></div>"
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

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
        use_ssl: bool = False,
        timeout_seconds: int = 20,
    ) -> None:
        if use_tls and use_ssl:
            raise ValueError("SMTP TLS and SSL cannot both be enabled.")
        if bool(username) != bool(password):
            raise ValueError("SMTP username and password must be configured together.")
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._use_ssl = use_ssl
        self._timeout_seconds = timeout_seconds

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
            client_type = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
            with client_type(
                self._host,
                self._port,
                timeout=self._timeout_seconds,
            ) as client:
                if self._use_tls:
                    client.ehlo()
                    client.starttls()
                    client.ehlo()
                if self._username and self._password:
                    client.login(self._username, self._password)
                client.send_message(smtp_message)

        await asyncio.to_thread(_send)
        return str(uuid4())
