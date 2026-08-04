from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.workers import trending_tasks
from app.workers.celery_app import celery_app


def test_trending_job_rejects_invalid_window_timestamp() -> None:
    with pytest.raises(ValueError, match="window_end"):
        trending_tasks.generate_trending_snapshot("not-a-datetime")


def test_trending_snapshot_is_scheduled_hourly() -> None:
    schedule = celery_app.conf.beat_schedule["generate-trending-snapshot"]

    assert schedule["task"] == "app.workers.trending_tasks.generate_trending_snapshot"
    assert schedule["schedule"] == 3600.0


def test_trending_job_returns_snapshot_id_and_redacts_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_id = UUID("65000000-0000-0000-0000-000000000001")

    async def fake_generate(window_end: datetime | None) -> UUID:
        assert window_end == datetime(2026, 8, 3, 8, tzinfo=UTC)
        return snapshot_id

    monkeypatch.setattr(trending_tasks, "_generate_trending_snapshot", fake_generate)

    assert trending_tasks.generate_trending_snapshot(
        "2026-08-03T08:00:00+00:00"
    ) == str(snapshot_id)
