from sqlalchemy.exc import OperationalError

from app.workers.celery_app import celery_app
from app.workers.engagement_tasks import generate_daily_engagement_snapshot


def test_daily_engagement_snapshot_is_registered_in_celery() -> None:
    assert (
        "app.workers.engagement_tasks.generate_daily_engagement_snapshot"
        in celery_app.conf.beat_schedule["generate-daily-engagement-snapshot"]["task"]
    )
    assert "app.workers.engagement_tasks" in celery_app.conf.include
    assert OperationalError in generate_daily_engagement_snapshot.autoretry_for
    assert generate_daily_engagement_snapshot.max_retries == 5
