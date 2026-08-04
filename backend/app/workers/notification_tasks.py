import asyncio
import json
from urllib.parse import quote
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.db.outbox import OutboxEvent
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.notifications.email import EmailDeliveryService, SmtpEmailGateway
from app.modules.notifications.service import NotificationService
from app.modules.public.cache_events import CatalogCacheEventHandler
from app.modules.public.catalog_cache import RedisPublicCatalogCache
from app.workers.celery_app import celery_app

EMAIL_EVENTS = frozenset(
    {
        "user.registered",
        "dossier.supplement_requested",
        "council.decided",
        "payment.paid",
        "certificate.issued",
        "certificate.revoked",
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
    "review.assigned": ("Phân công thẩm định", "Bạn có một hồ sơ thẩm định mới."),
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
        user_id_value = payload.get("user_id") or payload.get("owner_user_id")
        copy = EVENT_COPY.get(event_type)
        if isinstance(user_id_value, str) and copy is not None:
            notification = await NotificationService(session).consume(
                event_id=event_id,
                user_id=UUID(user_id_value),
                event_type=event_type,
                title=copy[0],
                body=copy[1],
                data={
                    key: value
                    for key, value in payload.items()
                    if key not in {"email", "verification_token", "token"}
                },
            )
            verification_token = payload.get("verification_token")
            if event_type == "user.registered" and isinstance(verification_token, str):
                token = quote(verification_token, safe="")
                action_url = (
                    f"{settings.app_base_url.rstrip('/')}/verify-email?token={token}"
                )
                await _deliver(notification.id, action_url=action_url)
            elif event_type in EMAIL_EVENTS:
                deliver_notification_email.delay(str(notification.id))
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
            ),
        ).deliver(notification_id, action_url=action_url)
        if delivery.status.value == "RETRY_PENDING":
            raise RuntimeError("Email provider unavailable")


@celery_app.task  # type: ignore[misc]
def process_notification_outbox() -> None:
    asyncio.run(_poll())


@celery_app.task  # type: ignore[misc]
def consume_notification_event(event_id: str) -> None:
    asyncio.run(_consume(UUID(event_id)))


@celery_app.task(
    autoretry_for=(RuntimeError,), max_retries=5, retry_backoff=True, retry_jitter=True
)  # type: ignore[misc]
def deliver_notification_email(notification_id: str) -> None:
    asyncio.run(_deliver(UUID(notification_id)))
