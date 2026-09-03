import asyncio
import json
from urllib.parse import quote
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.outbox import OutboxEvent
from app.db.session import get_session_factory
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.notifications.email import (
    EmailDeliveryService,
    EmailMessage,
    SmtpEmailGateway,
    render_email,
)
from app.modules.notifications.service import NotificationService
from app.modules.public.cache_events import CatalogCacheEventHandler
from app.modules.public.catalog_cache import RedisPublicCatalogCache
from app.workers.celery_app import celery_app

EMAIL_EVENTS = frozenset(
    {
        "user.registered",
        "dossier.submitted",
        "dossier.supplement_requested",
        "review.assignment_created",
        "council.decided",
        "payment.paid",
        "certificate.issued",
        "certificate.revoked",
        "blockchain.anchored",
    }
)

EVENT_COPY: dict[str, tuple[str, str]] = {
    "user.registered": (
        "Xác minh tài khoản",
        "Vui lòng hoàn tất xác minh email để kích hoạt tài khoản.",
    ),
    "dossier.submitted": ("Hồ sơ đã gửi", "Hồ sơ đang chờ kiểm tra và thẩm định."),
    "dossier.supplement_requested": (
        "Cần bổ sung hồ sơ",
        "Hồ sơ có yêu cầu bổ sung mới.",
    ),
    "review.assignment_created": (
        "Phân công thẩm định",
        "Bạn có một hồ sơ thẩm định mới.",
    ),
    "review.completed": (
        "Đã hoàn tất thẩm định",
        "Kết quả thẩm định đã được ghi nhận.",
    ),
    "council.decided": (
        "Hội đồng đã quyết định",
        "Quyết định hội đồng đã được cập nhật.",
    ),
    "payment.paid": ("Thanh toán thành công", "Khoản thanh toán đã được xác nhận."),
    "certificate.issued": ("Chứng thư đã phát hành", "Chứng thư số đã sẵn sàng."),
    "certificate.revoked": ("Chứng thư đã thu hồi", "Chứng thư số đã được thu hồi."),
    "blockchain.anchored": (
        "Blockchain đã xác nhận",
        "Bản ghi blockchain đã được xác nhận.",
    ),
    "content_report.created": (
        "Báo cáo nội dung mới",
        "Một tài sản công khai vừa nhận được báo cáo cần kiểm tra.",
    ),
}

EVENT_ROLE_RECIPIENTS: dict[str, frozenset[str]] = {
    "dossier.submitted": frozenset({"SUPER_ADMIN"}),
    "review.completed": frozenset({"SUPER_ADMIN"}),
}


def _action_path(event_type: str, payload: dict[str, object]) -> str | None:
    dossier_id = payload.get("dossier_id") or payload.get("dossierId")
    assignment_id = payload.get("assignment_id") or payload.get("assignmentId")
    certificate_id = payload.get("certificate_id") or payload.get("certificateId")
    if event_type == "review.assignment_created" and isinstance(assignment_id, str):
        return f"/reviews/{assignment_id}"
    if event_type in {
        "dossier.submitted",
        "dossier.supplement_requested",
        "review.completed",
        "council.decided",
        "payment.paid",
    } and isinstance(dossier_id, str):
        return f"/dossiers/{dossier_id}"
    if event_type in {"certificate.issued", "certificate.revoked"}:
        return (
            f"/certificates/{certificate_id}"
            if isinstance(certificate_id, str)
            else "/certificates"
        )
    if event_type == "blockchain.anchored":
        return "/blockchain"
    if event_type == "content_report.created":
        return "/admin/content"
    return None


async def _role_recipient_ids(
    session: AsyncSession, role_codes: frozenset[str]
) -> tuple[UUID, ...]:
    if not role_codes:
        return ()
    async with session.begin():
        statement = (
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(Role.code.in_(role_codes), User.status == UserStatus.ACTIVE)
            .distinct()
            .order_by(UserRole.user_id)
        )
        return tuple((await session.scalars(statement)).all())


def staff_invitation_message(
    *, email: str, invitation_token: str, app_base_url: str
) -> EmailMessage:
    token = quote(invitation_token, safe="")
    action_url = f"{app_base_url.rstrip('/')}/staff-invitation?token={token}"
    title = "Lời mời tham gia Đề cử Tinh Hoa Việt"
    body = (
        "Bạn được mời tham gia đội ngũ vận hành. "
        "Hãy xác minh đúng địa chỉ email nhận lời mời để tiếp tục."
    )
    text, html = render_email(title=title, body=body, action_url=action_url)
    return EmailMessage(
        to=email,
        subject=title,
        text=text,
        html=html,
    )


async def _consume(event_id: UUID) -> None:
    settings = get_settings()
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    async with get_session_factory()() as session:
        async with session.begin():
            event = await session.scalar(
                select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update()
            )
            if event is None or event.processed_at is not None:
                return
            payload = json.loads(
                cipher.decrypt(
                    nonce=event.payload_nonce,
                    ciphertext=event.payload_ciphertext,
                    event_type=event.event_type,
                    aggregate_id=event.aggregate_id,
                )
            )
            event_type = event.event_type
            aggregate_type = event.aggregate_type
        user_id_value = (
            payload.get("recipient_user_id")
            or payload.get("user_id")
            or payload.get("owner_user_id")
        )
        copy = EVENT_COPY.get(event_type)
        if event_type == "staff.invited":
            email = payload.get("email")
            invitation_token = payload.get("invitation_token")
            if not isinstance(email, str) or not isinstance(invitation_token, str):
                raise RuntimeError("Invalid staff invitation payload")
            message = staff_invitation_message(
                email=email,
                invitation_token=invitation_token,
                app_base_url=settings.app_base_url,
            )
            await SmtpEmailGateway(
                host=settings.smtp_host,
                port=settings.smtp_port,
                sender=settings.smtp_sender,
                username=settings.smtp_username,
                password=(
                    settings.smtp_password.get_secret_value()
                    if settings.smtp_password is not None
                    else None
                ),
                use_tls=settings.smtp_use_tls,
                use_ssl=settings.smtp_use_ssl,
                timeout_seconds=settings.smtp_timeout_seconds,
            ).send(message)
        if event_type == "blockchain.anchored":
            dossier_id = payload.get("dossier_id")
            certificate_version_id = payload.get("certificate_version_id")
            from app.workers.certificate_tasks import (
                issue_certificate,
                render_certificate_version,
            )

            if isinstance(dossier_id, str):
                issue_certificate.delay(dossier_id)
            if isinstance(certificate_version_id, str):
                render_certificate_version.delay(certificate_version_id)
        direct_recipient_id: UUID | None = None
        recipient_ids: set[UUID] = set()
        if isinstance(user_id_value, str):
            direct_recipient_id = UUID(user_id_value)
            recipient_ids.add(direct_recipient_id)
        recipient_ids.update(
            await _role_recipient_ids(
                session, EVENT_ROLE_RECIPIENTS.get(event_type, frozenset())
            )
        )
        if recipient_ids and copy is not None:
            safe_data = {
                key: value
                for key, value in payload.items()
                if key not in {"email", "verification_token", "token"}
            }
            action_path = _action_path(event_type, payload)
            if action_path is not None:
                safe_data["actionPath"] = action_path
            notifications = [
                await NotificationService(session).consume(
                    event_id=event_id,
                    user_id=recipient_id,
                    event_type=event_type,
                    title=copy[0],
                    body=copy[1],
                    data=safe_data,
                )
                for recipient_id in sorted(recipient_ids, key=str)
            ]
            verification_token = payload.get("verification_token")
            if event_type == "user.registered" and isinstance(verification_token, str):
                token = quote(verification_token, safe="")
                action_url = (
                    f"{settings.app_base_url.rstrip('/')}/verify-email?token={token}"
                )
                await _deliver(notifications[0].id, action_url=action_url)
            elif event_type in EMAIL_EVENTS and direct_recipient_id is not None:
                direct_notification = next(
                    notification
                    for notification in notifications
                    if notification.user_id == direct_recipient_id
                )
                deliver_notification_email.delay(str(direct_notification.id))
        if aggregate_type in {"public_work", "public_category", "public_tag"}:
            redis_client: Redis = Redis.from_url(settings.redis_url)
            try:
                await CatalogCacheEventHandler(
                    RedisPublicCatalogCache(
                        redis_client,
                        ttl_seconds=settings.public_catalog_cache_ttl_seconds,
                    )
                ).handle(
                    aggregate_type=aggregate_type,
                    event_type=event_type,
                    payload=payload,
                )
            finally:
                await redis_client.aclose()
        if aggregate_type == "public_work":
            from app.workers.public_work_tasks import rebuild_public_sitemap

            rebuild_public_sitemap.delay()
        if aggregate_type in {"vote", "voting_campaign", "public_work"}:
            from app.workers.voting_aggregate_tasks import (
                handle_voting_aggregate_event,
            )

            await handle_voting_aggregate_event(
                aggregate_type=aggregate_type,
                payload=payload,
                settings=settings,
            )
        if aggregate_type == "voting_campaign":
            from app.workers.ranking_tasks import (
                enqueue_ranking_for_campaign_event,
            )

            enqueue_ranking_for_campaign_event(
                event_type=event_type,
                payload=payload,
            )
        async with session.begin():
            event = await session.get(OutboxEvent, event_id)
            if event is not None:
                from datetime import UTC, datetime

                event.processed_at = datetime.now(UTC)


async def _poll() -> None:
    async with get_session_factory()() as session:
        async with session.begin():
            ids = tuple(
                (
                    await session.scalars(
                        select(OutboxEvent.id)
                        .where(OutboxEvent.processed_at.is_(None))
                        .order_by(OutboxEvent.occurred_at)
                        .limit(100)
                    )
                ).all()
            )
    for event_id in ids:
        consume_notification_event.delay(str(event_id))


async def _deliver(notification_id: UUID, *, action_url: str | None = None) -> None:
    settings = get_settings()
    async with get_session_factory()() as session:
        delivery = await EmailDeliveryService(
            session=session,
            gateway=SmtpEmailGateway(
                host=settings.smtp_host,
                port=settings.smtp_port,
                sender=settings.smtp_sender,
                username=settings.smtp_username,
                password=(
                    settings.smtp_password.get_secret_value()
                    if settings.smtp_password is not None
                    else None
                ),
                use_tls=settings.smtp_use_tls,
                use_ssl=settings.smtp_use_ssl,
                timeout_seconds=settings.smtp_timeout_seconds,
            ),
        ).deliver(notification_id, action_url=action_url)
        if delivery.status.value == "RETRY_PENDING":
            raise RuntimeError("Email provider unavailable")


@celery_app.task  # type: ignore[untyped-decorator]
def process_notification_outbox() -> None:
    asyncio.run(_poll())


@celery_app.task  # type: ignore[untyped-decorator]
def consume_notification_event(event_id: str) -> None:
    asyncio.run(_consume(UUID(event_id)))


@celery_app.task(  # type: ignore[untyped-decorator]
    autoretry_for=(RuntimeError,), max_retries=5, retry_backoff=True, retry_jitter=True
)
def deliver_notification_email(notification_id: str) -> None:
    asyncio.run(_deliver(UUID(notification_id)))
