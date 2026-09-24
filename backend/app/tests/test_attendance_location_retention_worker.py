from app.workers.celery_app import celery_app


def test_location_evidence_purge_is_registered_as_a_daily_worker_task() -> None:
    schedule = celery_app.conf.beat_schedule["purge-expired-attendance-locations"]

    assert (
        schedule["task"]
        == "app.workers.attendance_location_tasks.purge_expired_attendance_locations"
    )
    assert schedule["schedule"] == 86_400.0
    assert "app.workers.attendance_location_tasks" in celery_app.conf.include
