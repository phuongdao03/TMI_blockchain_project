from app.workers.celery_app import celery_app


def test_certificate_publication_recovery_runs_without_polygon_rpc() -> None:
    schedule = celery_app.conf.beat_schedule["repair-certificate-publication"]

    assert schedule["task"] == (
        "app.workers.certificate_tasks.repair_certificate_publication"
    )
    assert schedule["schedule"] <= 60.0
