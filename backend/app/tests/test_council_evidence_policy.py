import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.modules.billing import models as billing_models  # noqa: F401
from app.modules.council.errors import CouncilConflictError
from app.modules.council.models import (
    CouncilCase,
    CouncilCaseDecision,
    CouncilSession,
    CouncilSessionStatus,
    CouncilVoteChoice,
)
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion
from app.modules.reviews.models import (
    Review,
    ReviewAssignment,
    ReviewAssignmentStatus,
    ReviewRecommendation,
)
from app.tests.test_council_session_service import (
    NOW,
    _open_two_member_case,
    _principal,
    _setup,
)


async def _policy(sessions, version_id: UUID, *, minimum: int = 1) -> None:
    async with sessions() as session:
        version = await session.get(DossierVersion, version_id)
        snapshot = dict(version.snapshot_json)
        media_id = snapshot["evidences"][0]["mediaAssetId"]
        snapshot["dossier"] = {
            **snapshot["dossier"],
            "dossierType": {
                "reviewRubric": {
                    "version": "2026.3",
                    "title": "Council evidence policy",
                    "assessmentMethod": "VERDICT",
                    "evidencePolicyVersion": "2026.1",
                    "minimumIndependentReviews": minimum,
                    "gates": [],
                    "criteria": [
                        {
                            "key": "identity",
                            "label": "Identity",
                            "description": "Compare identity with archived record.",
                        }
                    ],
                }
            },
        }
        version.snapshot_json = snapshot
        version.canonical_hash = snapshot_sha256(snapshot)
        review = await session.scalar(select(Review))
        if review is not None:
            review.criterion_verdicts = {
                "identity": {
                    "outcome": "MEETS",
                    "rationale": "The submitted identity matches the archived record.",
                    "evidence_media_ids": [media_id],
                }
            }
            review.evidence_assessments = {media_id: {"status": "VALID", "note": ""}}
        await session.commit()


@pytest.mark.parametrize("actor", ["owner", "reviewer"])
def test_policy_rejects_owner_and_reviewer_final_decision(actor: str) -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        with pytest.raises(CouncilConflictError, match="independent"):
            await service.record_admin_decision(
                _principal(users[actor], "SUPER_ADMIN", "MODERATOR"),
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="All requirements appear met.",
                confirm_no_conflict=True,
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "status", [ReviewAssignmentStatus.CONFLICTED, ReviewAssignmentStatus.CANCELLED]
)
def test_current_conflict_blocks_decision_but_cancelled_assignment_is_not_review(
    status: ReviewAssignmentStatus,
) -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        async with sessions() as session:
            session.add(
                ReviewAssignment(
                    id=uuid4(),
                    dossier_id=dossier.id,
                    dossier_version_id=version.id,
                    reviewer_user_id=users["member1"].id,
                    assigned_by=users["secretary"].id,
                    status=status,
                    conflict_declared_at=NOW
                    if status is ReviewAssignmentStatus.CONFLICTED
                    else None,
                    conflict_reason="Declared financial relationship"
                    if status is ReviewAssignmentStatus.CONFLICTED
                    else None,
                )
            )
            await session.commit()

        async def decide():
            return await service.record_admin_decision(
                _principal(users["member1"], "SUPER_ADMIN"),
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="No completed personal expert review.",
                confirm_no_conflict=True,
            )

        if status is ReviewAssignmentStatus.CONFLICTED:
            with pytest.raises(CouncilConflictError, match="independent"):
                await decide()
        else:
            assert (await decide()).status is DossierStatus.APPROVED
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "recommendation", [ReviewRecommendation.SUPPLEMENT, ReviewRecommendation.REJECT]
)
def test_policy_rejects_approval_over_unresolved_expert_report(
    recommendation: ReviewRecommendation,
) -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        async with sessions() as session:
            review = await session.scalar(select(Review))
            review.recommendation = recommendation
            await session.commit()
        with pytest.raises(CouncilConflictError, match="unresolved"):
            await service.record_admin_decision(
                _principal(users["secretary"], "SUPER_ADMIN"),
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="Attempt to override unresolved report.",
                confirm_no_conflict=True,
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_minimum_independent_reviews_is_configurable_not_universal() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id, minimum=2)
        secretary = _principal(users["secretary"], "SUPER_ADMIN")
        with pytest.raises(CouncilConflictError, match="independent reviews"):
            await service.record_admin_decision(
                secretary,
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="Insufficient independent reviewers.",
                confirm_no_conflict=True,
            )
        await _policy(sessions, version.id, minimum=1)
        result = await service.record_admin_decision(
            secretary,
            dossier.id,
            decision=CouncilCaseDecision.APPROVE,
            reason="Independent review is complete.",
            confirm_no_conflict=True,
        )
        assert result.status is DossierStatus.APPROVED
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_two_independent_reports_satisfy_configured_minimum() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id, minimum=2)
        async with sessions() as session:
            first = await session.scalar(select(Review))
            assignment = ReviewAssignment(
                id=uuid4(),
                dossier_id=dossier.id,
                dossier_version_id=version.id,
                reviewer_user_id=users["member1"].id,
                assigned_by=users["secretary"].id,
                status=ReviewAssignmentStatus.SUBMITTED,
            )
            session.add(assignment)
            await session.flush()
            session.add(
                Review(
                    id=uuid4(),
                    assignment_id=assignment.id,
                    recommendation=ReviewRecommendation.APPROVE,
                    submitted_at=NOW,
                    criterion_verdicts=first.criterion_verdicts,
                    evidence_assessments=first.evidence_assessments,
                )
            )
            await session.commit()
        result = await service.record_admin_decision(
            _principal(users["secretary"], "SUPER_ADMIN"),
            dossier.id,
            decision=CouncilCaseDecision.APPROVE,
            reason="Two independent expert reports support approval.",
            confirm_no_conflict=True,
        )
        assert result.status is DossierStatus.APPROVED
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("involvement", ["owner", "reviewer"])
def test_policy_rejects_involved_council_member_vote(involvement: str) -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        async with sessions() as session:
            if involvement == "owner":
                stored = await session.get(Dossier, dossier.id)
                stored.owner_user_id = users["member1"].id
            else:
                assignment = await session.scalar(select(ReviewAssignment))
                assignment.reviewer_user_id = users["member1"].id
            await session.commit()
        _, case = await _open_two_member_case(service, users, dossier)
        member = _principal(users["member1"], "SUPER_ADMIN")
        await service.declare_conflict(member, case.id, has_conflict=False, reason=None)
        with pytest.raises(CouncilConflictError, match="independent"):
            await service.cast_vote(
                member,
                case.id,
                choice=CouncilVoteChoice.APPROVE,
                reason="Self-declaration does not waive conflict.",
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("change", ["recommendation", "reviewer", "version"])
def test_close_rechecks_policy_and_rolls_back_decision(change: str) -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        secretary, case = await _open_two_member_case(service, users, dossier)
        for name in ("member1", "member2"):
            principal = _principal(users[name], "SUPER_ADMIN")
            await service.declare_conflict(
                principal, case.id, has_conflict=False, reason=None
            )
            await service.cast_vote(
                principal,
                case.id,
                choice=CouncilVoteChoice.APPROVE,
                reason="Independent report supported approval.",
            )
        async with sessions() as session:
            if change == "recommendation":
                review = await session.scalar(select(Review))
                review.recommendation = ReviewRecommendation.SUPPLEMENT
            elif change == "reviewer":
                assignment = await session.scalar(select(ReviewAssignment))
                assignment.reviewer_user_id = users["member1"].id
            else:
                stored_dossier = await session.get(Dossier, dossier.id)
                stored_dossier.current_version_no = 2
            await session.commit()
        with pytest.raises(CouncilConflictError):
            await service.close_session(secretary, case.session_id)
        async with sessions() as session:
            stored_case = await session.get(CouncilCase, case.id)
            stored_session = await session.get(CouncilSession, case.session_id)
            stored_dossier = await session.get(Dossier, dossier.id)
            assert stored_case.decision is None
            assert stored_session.status is CouncilSessionStatus.OPEN
            assert stored_dossier.status is DossierStatus.COUNCIL_REVIEW
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_unrelated_contradiction_does_not_automatically_block_approval() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        async with sessions() as session:
            review = await session.scalar(select(Review))
            review.evidence_assessments = {
                **review.evidence_assessments,
                "unrelated-file": {
                    "status": "NOT_RELEVANT",
                    "verification": {
                        "outcome": "CONTRADICTED",
                        "method": "Compared archival dates",
                        "source": "Archive B",
                        "scope": "An unrelated work",
                        "limitations": "Not relevant to this dossier's criteria",
                    },
                },
            }
            await session.commit()
        result = await service.record_admin_decision(
            _principal(users["secretary"], "SUPER_ADMIN"),
            dossier.id,
            decision=CouncilCaseDecision.APPROVE,
            reason="The unrelated file does not contradict the reviewed criteria.",
            confirm_no_conflict=True,
        )
        assert result.status is DossierStatus.APPROVED
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_relevant_uncited_contradiction_blocks_council_approval() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        await _policy(sessions, version.id)
        async with sessions() as session:
            review = await session.scalar(select(Review))
            review.evidence_assessments = {
                "uncited-file": {
                    "status": "VALID",
                    "verification": {"outcome": "CONTRADICTED"},
                }
            }
            await session.commit()
        with pytest.raises(CouncilConflictError, match="unresolved"):
            await service.record_admin_decision(
                _principal(users["secretary"], "SUPER_ADMIN"),
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="Cannot ignore a relevant contradiction.",
                confirm_no_conflict=True,
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
