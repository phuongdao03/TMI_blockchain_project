from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.workers import ranking_tasks
from app.workers.celery_app import celery_app


def test_ranking_job_is_registered_with_database_retry_policy() -> None:
    assert ranking_tasks.generate_ranking_snapshot.name in celery_app.tasks
    assert ranking_tasks.generate_ranking_snapshot.max_retries == 5
    assert ranking_tasks.generate_ranking_snapshot.autoretry_for == (OperationalError,)


def test_ranking_recount_job_is_registered_with_database_retry_policy() -> None:
    assert ranking_tasks.recount_ranking_snapshot.name in celery_app.tasks
    assert ranking_tasks.recount_ranking_snapshot.max_retries == 5
    assert ranking_tasks.recount_ranking_snapshot.autoretry_for == (OperationalError,)


def test_ranking_job_validates_campaign_id_before_database_access() -> None:
    with pytest.raises(ValueError, match="campaign_id"):
        ranking_tasks.generate_ranking_snapshot.run("not-a-uuid")


def test_ranking_job_returns_created_snapshot_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign_id = uuid4()
    snapshot_id = uuid4()

    async def fake_generate(received_campaign_id: UUID) -> UUID | None:
        assert received_campaign_id == campaign_id
        return snapshot_id

    monkeypatch.setattr(ranking_tasks, "_generate_ranking_snapshot", fake_generate)

    assert ranking_tasks.generate_ranking_snapshot.run(str(campaign_id)) == str(
        snapshot_id
    )


def test_ranking_recount_job_validates_identifiers_before_database_access() -> None:
    with pytest.raises(ValueError, match="identifiers"):
        ranking_tasks.recount_ranking_snapshot.run("not-a-uuid")
    with pytest.raises(ValueError, match="identifiers"):
        ranking_tasks.recount_ranking_snapshot.run(
            str(uuid4()), actor_user_id="not-a-uuid"
        )


def test_ranking_recount_job_returns_created_snapshot_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign_id = uuid4()
    expected_actor_user_id = uuid4()
    snapshot_id = uuid4()

    async def fake_recount(
        received_campaign_id: UUID,
        *,
        actor_user_id: UUID | None,
        request_id: str | None,
    ) -> UUID:
        assert received_campaign_id == campaign_id
        assert actor_user_id == expected_actor_user_id
        assert request_id == "request-1812"
        return snapshot_id

    monkeypatch.setattr(ranking_tasks, "_recount_ranking_snapshot", fake_recount)

    assert ranking_tasks.recount_ranking_snapshot.run(
        str(campaign_id),
        actor_user_id=str(expected_actor_user_id),
        request_id="request-1812",
    ) == str(snapshot_id)


def test_campaign_ended_event_enqueues_only_valid_campaign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign_id = uuid4()
    queued: list[str] = []
    monkeypatch.setattr(
        ranking_tasks.generate_ranking_snapshot,
        "delay",
        lambda value: queued.append(value),
    )

    accepted = ranking_tasks.enqueue_ranking_for_campaign_event(
        event_type="voting.campaign.ended",
        payload={"campaign_id": str(campaign_id), "status": "ENDED"},
    )
    ignored_status = ranking_tasks.enqueue_ranking_for_campaign_event(
        event_type="voting.campaign.activated",
        payload={"campaign_id": str(campaign_id), "status": "ACTIVE"},
    )
    ignored_identifier = ranking_tasks.enqueue_ranking_for_campaign_event(
        event_type="voting.campaign.ended",
        payload={"campaign_id": "invalid", "status": "ENDED"},
    )

    assert accepted is True
    assert ignored_status is False
    assert ignored_identifier is False
    assert queued == [str(campaign_id)]
