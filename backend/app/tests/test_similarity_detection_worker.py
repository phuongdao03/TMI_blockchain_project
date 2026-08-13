from app.workers.celery_app import celery_app
from app.workers.similarity_tasks import detect_near_duplicate_candidates


def test_similarity_detection_worker_is_registered_and_retryable() -> None:
    assert "app.workers.similarity_tasks" in celery_app.conf.include
    assert detect_near_duplicate_candidates.name in celery_app.tasks
    assert detect_near_duplicate_candidates.max_retries == 5
