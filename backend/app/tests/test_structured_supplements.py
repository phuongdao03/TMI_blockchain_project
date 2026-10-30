import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion
from app.modules.supplements.models import SupplementRequest, SupplementResponse
from app.modules.supplements.service import (
    SupplementService,
    require_answered,
    require_resolved,
)
from app.tests.test_review_scoring import NOW, _principal, _setup


def test_request_response_resolution_preserves_history_and_enforces_scope() -> None:
    async def exercise() -> None:
        reviews, factory, engine, users, assignment, _ = await _setup()
        reviewer = _principal(users["reviewer"])
        owner = _principal(users["owner"], "USER")
        outsider = _principal(users["other"], "USER")
        await reviews.declare_conflict(
            reviewer, assignment.id, has_conflict=False, reason=None
        )
        async with factory() as session:
            version = await session.get(DossierVersion, assignment.dossier_version_id)
            snapshot = dict(version.snapshot_json)
            snapshot["dossier"] = {
                **snapshot["dossier"],
                "dossierType": {
                    "reviewRubric": {
                        "criteria": [{"key": "origin", "label": "Nguồn gốc"}]
                    }
                },
            }
            version.snapshot_json = snapshot
            await session.commit()
        service = SupplementService(factory(), clock=lambda: NOW)
        try:
            with pytest.raises(DomainError) as unauthorized:
                await service.create(
                    outsider,
                    assignment.dossier_id,
                    criterion_key="origin",
                    expected_version_id=assignment.dossier_version_id,
                    requested_information="Provide a dated manuscript or source.",
                    reason="The declared chronology is not supported.",
                )
            assert unauthorized.value.status_code == 404
            row = await service.create(
                reviewer,
                assignment.dossier_id,
                criterion_key="origin",
                expected_version_id=assignment.dossier_version_id,
                requested_information="Provide a dated manuscript or source.",
                reason="The declared chronology is not supported.",
            )
            assert await service.list(owner, assignment.dossier_id) == ()
            with pytest.raises(DomainError):
                await service.respond(
                    owner,
                    assignment.dossier_id,
                    row.id,
                    expected_revision=0,
                    text="Archive reference 2024-A now supplied.",
                )
            async with factory() as session:
                dossier = await session.get(Dossier, assignment.dossier_id)
                dossier._set_status_from_workflow(DossierStatus.NEEDS_SUPPLEMENT)
                await session.commit()
            assert len(await service.list(owner, assignment.dossier_id)) == 1
            async with factory() as session:
                with pytest.raises(DomainError):
                    await require_answered(session, assignment.dossier_id)
            with pytest.raises(DomainError):
                await service.respond(
                    outsider,
                    assignment.dossier_id,
                    row.id,
                    expected_revision=0,
                    text="Archive reference 2024-A now supplied.",
                )
            answered = await service.respond(
                owner,
                assignment.dossier_id,
                row.id,
                expected_revision=0,
                text="Archive reference 2024-A now supplied.",
            )
            assert answered.status == "ANSWERED"
            with pytest.raises(DomainError) as stale:
                await service.respond(
                    owner,
                    assignment.dossier_id,
                    row.id,
                    expected_revision=0,
                    text="Attempt to replace the previous response.",
                )
            assert stale.value.status_code == 409
            async with factory() as session:
                await require_answered(session, assignment.dossier_id)
                with pytest.raises(DomainError):
                    await require_resolved(session, assignment.dossier_id)
            resolved = await service.decide(
                reviewer,
                assignment.dossier_id,
                row.id,
                expected_revision=1,
                resolution="The archive record resolves the requested chronology.",
                reopen=False,
            )
            assert resolved.status == "RESOLVED"
            async with factory() as session:
                await require_resolved(session, assignment.dossier_id)
                history = (
                    await session.scalars(
                        select(SupplementResponse).where(
                            SupplementResponse.kind == "RESPONSE"
                        )
                    )
                ).all()
                assert (
                    len(history) == 1
                    and history[0].text == "Archive reference 2024-A now supplied."
                )
            reopened = await service.decide(
                reviewer,
                assignment.dossier_id,
                row.id,
                expected_revision=2,
                resolution="A contradiction was found and needs further explanation.",
                reopen=True,
            )
            assert reopened.status == "OPEN"
            async with factory() as session:
                assert (
                    len((await session.scalars(select(SupplementResponse))).all()) == 3
                )
        finally:
            await service.close()
            await reviews.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_request_rejects_unknown_criterion_and_foreign_claim() -> None:
    async def exercise() -> None:
        reviews, factory, engine, users, assignment, _ = await _setup()
        reviewer = _principal(users["reviewer"])
        await reviews.declare_conflict(
            reviewer, assignment.id, has_conflict=False, reason=None
        )
        async with factory() as session:
            version = await session.get(DossierVersion, assignment.dossier_version_id)
            snapshot = dict(version.snapshot_json)
            snapshot["dossier"] = {
                **snapshot["dossier"],
                "dossierType": {
                    "reviewRubric": {
                        "criteria": [{"key": "origin", "label": "Nguồn gốc"}]
                    }
                },
            }
            version.snapshot_json = snapshot
            await session.commit()
        service = SupplementService(factory(), clock=lambda: NOW)
        try:
            with pytest.raises(DomainError) as invalid:
                await service.create(
                    reviewer,
                    assignment.dossier_id,
                    criterion_key="missing",
                    expected_version_id=assignment.dossier_version_id,
                    requested_information="Provide a dated manuscript or source.",
                    reason="The declared chronology is not supported.",
                    claim_id=uuid4(),
                )
            assert invalid.value.status_code == 422
            common = dict(
                criterion_key="origin",
                expected_version_id=assignment.dossier_version_id,
                requested_information="Provide a dated manuscript or source.",
                reason="The declared chronology is not supported.",
            )
            with pytest.raises(DomainError, match="claim"):
                await service.create(
                    reviewer, assignment.dossier_id, **common, claim_id=uuid4()
                )
            with pytest.raises(DomainError) as self_review:
                await service.create(
                    _principal(users["owner"], "SUPER_ADMIN"),
                    assignment.dossier_id,
                    **common,
                )
            assert self_review.value.status_code == 404
            with pytest.raises(DomainError) as removed_role:
                await service.list(
                    _principal(users["reviewer"], "USER"), assignment.dossier_id
                )
            assert removed_role.value.status_code == 404
            with pytest.raises(DomainError, match="version changed"):
                await service.create(
                    reviewer,
                    assignment.dossier_id,
                    **{**common, "expected_version_id": uuid4()},
                )
            with pytest.raises(DomainError, match="deadline"):
                await service.create(
                    reviewer,
                    assignment.dossier_id,
                    **common,
                    due_at=NOW.replace(tzinfo=None),
                )
        finally:
            await service.close()
            await reviews.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_resubmission_guard_runs_before_snapshot_or_financial_changes() -> None:
    from app.tests.test_dossier_submission import _build_service, _draft_with_evidence
    from app.tests.test_dossier_submission import _principal as owner_principal

    async def exercise() -> None:
        service, factory, engine, user, media = await _build_service()
        owner = owner_principal(user)
        dossier, _ = await _draft_with_evidence(service, owner, media)
        first = await service.submit_dossier(
            owner, dossier.id, idempotency_key="supp-first"
        )
        async with factory() as session:
            row = await session.get(Dossier, dossier.id)
            row._set_status_from_workflow(DossierStatus.NEEDS_SUPPLEMENT)
            session.add(
                SupplementRequest(
                    dossier_id=dossier.id,
                    requested_version_id=first.version.id,
                    criterion_key="origin",
                    criterion_label="Nguồn gốc",
                    requested_information="Supply the dated archive record.",
                    reason="The declared chronology needs support.",
                    priority="NORMAL",
                    created_by=user.id,
                    status="OPEN",
                    revision=0,
                )
            )
            await session.commit()
        with pytest.raises(DomainError, match="Respond to all open"):
            await service.resubmit_dossier(
                owner, dossier.id, idempotency_key="supp-second"
            )
        async with factory() as session:
            row = await session.get(Dossier, dossier.id)
            assert row.current_version_no == 1
            assert row.status is DossierStatus.NEEDS_SUPPLEMENT
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_council_cannot_ignore_an_unresolved_structured_request() -> None:
    from app.modules.council.models import CouncilCaseDecision
    from app.tests.test_council_session_service import _principal as council_principal
    from app.tests.test_council_session_service import _setup as council_setup

    async def exercise() -> None:
        service, factory, engine, users, dossier, version = await council_setup()
        async with factory() as session:
            session.add(
                SupplementRequest(
                    dossier_id=dossier.id,
                    requested_version_id=version.id,
                    criterion_key="origin",
                    criterion_label="Nguồn gốc",
                    requested_information="Supply the dated archive record.",
                    reason="The declared chronology needs support.",
                    priority="NORMAL",
                    created_by=users["secretary"].id,
                    status="ANSWERED",
                    revision=1,
                )
            )
            await session.commit()
        with pytest.raises(DomainError, match="Resolve all supplement"):
            await service.record_admin_decision(
                council_principal(users["secretary"], "SUPER_ADMIN"),
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="A submitted review is complete.",
                confirm_no_conflict=True,
            )
        async with factory() as session:
            row = await session.get(Dossier, dossier.id)
            assert row.status is DossierStatus.UNDER_REVIEW
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
