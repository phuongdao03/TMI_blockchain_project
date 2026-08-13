import asyncio
from uuid import UUID, uuid4

import pytest

from app.workers import media_inspection_tasks
from app.workers.celery_app import celery_app
from app.workers.media_inspection_tasks import (
    backfill_media_provenance,
    inspect_media_asset,
    reverify_media_asset,
)


def test_provenance_backfill_enqueues_legacy_private_media_for_encryption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    untrusted_id = uuid4()
    legacy_private_id = uuid4()
    reverifications: list[str] = []
    inspections: list[str] = []

    class SessionContext:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Repository:
        def __init__(self, _session: object) -> None:
            pass

        async def list_untrusted_active_ids(self, *, limit: int) -> tuple[UUID, ...]:
            assert limit == 25
            return (untrusted_id,)

        async def list_legacy_private_ids(self, *, limit: int) -> tuple[UUID, ...]:
            assert limit == 25
            return (legacy_private_id,)

    monkeypatch.setattr(
        media_inspection_tasks,
        "get_session_factory",
        lambda: lambda: SessionContext(),
    )
    monkeypatch.setattr(media_inspection_tasks, "MediaAssetRepository", Repository)
    monkeypatch.setattr(
        media_inspection_tasks.reverify_media_asset,
        "delay",
        lambda media_id: reverifications.append(media_id),
    )
    monkeypatch.setattr(
        media_inspection_tasks.inspect_media_asset,
        "delay",
        lambda media_id: inspections.append(media_id),
    )

    asyncio.run(media_inspection_tasks._enqueue_provenance_backfill())

    assert reverifications == [str(untrusted_id)]
    assert inspections == [str(legacy_private_id)]


def test_media_inspection_worker_is_registered_and_retryable() -> None:
    assert "app.workers.media_inspection_tasks" in celery_app.conf.include
    assert inspect_media_asset.name in celery_app.tasks
    assert inspect_media_asset.max_retries == 5
    assert reverify_media_asset.name in celery_app.tasks
    assert reverify_media_asset.max_retries == 5
    assert backfill_media_provenance.name in celery_app.tasks
    assert (
        celery_app.conf.beat_schedule["backfill-media-provenance"]["task"]
        == backfill_media_provenance.name
    )
