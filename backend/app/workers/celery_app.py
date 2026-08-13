from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tmi_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.blockchain_tasks",
        "app.workers.certificate_tasks",
        "app.workers.notification_tasks",
        "app.workers.payment_tasks",
        "app.workers.media_inspection_tasks",
        "app.workers.similarity_tasks",
        "app.workers.public_work_tasks",
        "app.workers.public_media_tasks",
        "app.workers.ranking_tasks",
        "app.workers.trending_tasks",
        "app.workers.search_history_tasks",
        "app.workers.search_discovery_tasks",
        "app.workers.engagement_tasks",
        "app.workers.engagement_velocity_tasks",
        "app.workers.voting_lifecycle_tasks",
        "app.workers.voting_aggregate_tasks",
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
        "reconcile-blockchain-transactions": {
            "task": ("app.workers.blockchain_tasks.reconcile_blockchain_transactions"),
            "schedule": 30.0,
        },
        "process-notification-outbox": {
            "task": "app.workers.notification_tasks.process_notification_outbox",
            "schedule": 5.0,
        },
        "reconcile-pending-payments": {
            "task": "app.workers.payment_tasks.reconcile_pending_payments",
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
        "rebuild-public-sitemap-fallback": {
            "task": "app.workers.public_work_tasks.rebuild_public_sitemap",
            "schedule": 3600.0,
        },
        "purge-expired-search-history": {
            "task": "app.workers.search_history_tasks.purge_expired_search_history",
            "schedule": 86400.0,
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
        "reconcile-voting-campaign-lifecycle": {
            "task": (
                "app.workers.voting_lifecycle_tasks.reconcile_voting_campaign_lifecycle"
            ),
            "schedule": 15.0,
        },
        "reconcile-vote-aggregates": {
            "task": "app.workers.voting_aggregate_tasks.reconcile_vote_aggregates",
            "schedule": 300.0,
        },
        "reconcile-monthly-rankings": {
            "task": "app.workers.ranking_tasks.reconcile_monthly_rankings",
            "schedule": 3600.0,
        },
        "reconcile-quarterly-rankings": {
            "task": "app.workers.ranking_tasks.reconcile_quarterly_rankings",
            "schedule": 3600.0,
        },
        "reconcile-yearly-rankings": {
            "task": "app.workers.ranking_tasks.reconcile_yearly_rankings",
            "schedule": 3600.0,
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
