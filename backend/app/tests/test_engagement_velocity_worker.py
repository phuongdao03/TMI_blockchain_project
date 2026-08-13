from sqlalchemy.exc import OperationalError

from app.workers.celery_app import celery_app
from app.workers.engagement_velocity_tasks import generate_engagement_velocity_snapshot


def test_engagement_velocity_worker_is_scheduled_and_retryable() -> None:
    assert (
        celery_app.conf.beat_schedule["generate-engagement-velocity-snapshot"]["task"]
        == "app.workers.engagement_velocity_tasks.generate_engagement_velocity_snapshot"
    )
    assert "app.workers.engagement_velocity_tasks" in celery_app.conf.include
    assert OperationalError in generate_engagement_velocity_snapshot.autoretry_for
    assert generate_engagement_velocity_snapshot.max_retries == 5
