from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cns_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.proof_registry_tasks",
        "app.workers.certificate_tasks",
        "app.workers.notification_tasks",
        "app.workers.payment_tasks",
        "app.workers.media_inspection_tasks",
        "app.workers.similarity_tasks",
        "app.workers.public_work_tasks",
        "app.workers.public_media_tasks",
        "app.workers.trending_tasks",
        "app.workers.search_history_tasks",
        "app.workers.search_discovery_tasks",
        "app.workers.engagement_tasks",
        "app.workers.engagement_velocity_tasks",
        "app.workers.attendance_location_tasks",
        "app.workers.community_retention_tasks",
        "app.workers.advertising_tasks",
        "app.workers.promotion_tasks",
    ],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_serializer="json",
    task_serializer="json",
    timezone="UTC",
    beat_schedule={
        "resume-promotion-distribution": {
            "task": "app.workers.promotion_tasks.distribute_promotions",
            "schedule": 30.0,
        },
        "notify-expiring-promotions": {
            "task": "app.workers.promotion_tasks.notify_expiring_promotions",
            "schedule": 3600.0,
        },
        "reconcile-blockchain-transactions": {
            "task": "app.workers.proof_registry_tasks.reconcile_proof_registry_transactions",  # noqa: E501
            "schedule": 30.0,
        },
        "repair-certificate-publication": {
            "task": ("app.workers.certificate_tasks.repair_certificate_publication"),
            "schedule": 60.0,
        },
        "process-notification-outbox": {
            "task": "app.workers.notification_tasks.process_notification_outbox",
            "schedule": 5.0,
        },
        "reconcile-pending-payments": {
            "task": "app.workers.payment_tasks.reconcile_pending_payments_scheduled",
            "schedule": 60.0,
        },
        "expire-advertising-reservations": {
            "task": "app.workers.advertising_tasks.expire_advertising_reservations",
            "schedule": 60.0,
        },
        "advance-advertising-campaigns": {
            "task": "app.workers.advertising_tasks.advance_advertising_campaigns",
            "schedule": 60.0,
        },
        "notify-available-advertising-waitlists": {
            "task": (
                "app.workers.advertising_tasks.notify_available_advertising_waitlists"
            ),
            "schedule": 60.0,
        },
        "backfill-media-provenance": {
            "task": "app.workers.media_inspection_tasks.backfill_media_provenance",
            "schedule": 300.0,
        },
        "publish-scheduled-public-works": {
            "task": "app.workers.public_work_tasks.publish_scheduled_public_works",
            "schedule": 30.0,
        },
        "reconcile-pending-public-media": {
            "task": "app.workers.public_media_tasks.reconcile_pending_public_media",
            "schedule": 30.0,
        },
        "rebuild-public-sitemap-fallback": {
            "task": "app.workers.public_work_tasks.rebuild_public_sitemap",
            "schedule": 3600.0,
        },
        "purge-expired-search-history": {
            "task": "app.workers.search_history_tasks.purge_expired_search_history",
            "schedule": 86400.0,
        },
        "purge-expired-attendance-locations": {
            "task": (
                "app.workers.attendance_location_tasks."
                "purge_expired_attendance_locations"
            ),
            "schedule": 86400.0,
        },
        "purge-deleted-community-media": {
            "task": (
                "app.workers.community_retention_tasks.purge_deleted_community_media"
            ),
            "schedule": 300.0,
        },
        "materialize-hourly-search-discovery": {
            "task": (
                "app.workers.search_discovery_tasks.materialize_hourly_search_discovery"
            ),
            "schedule": 3600.0,
        },
        "materialize-daily-search-discovery": {
            "task": (
                "app.workers.search_discovery_tasks.materialize_daily_search_discovery"
            ),
            "schedule": 86400.0,
        },
        "generate-trending-snapshot": {
            "task": "app.workers.trending_tasks.generate_trending_snapshot",
            "schedule": 3600.0,
        },
        "generate-daily-engagement-snapshot": {
            "task": ("app.workers.engagement_tasks.generate_daily_engagement_snapshot"),
            "schedule": 86400.0,
        },
        "generate-engagement-velocity-snapshot": {
            "task": (
                "app.workers.engagement_velocity_tasks.generate_engagement_velocity_snapshot"
            ),
            "schedule": 86400.0,
        },
    },
)
