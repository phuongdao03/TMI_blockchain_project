import asyncio
from copy import deepcopy
from uuid import uuid4

import pytest

from app.modules.billing import models as billing_models  # noqa: F401
from app.modules.dossiers.dynamic_schema import (
    DynamicSchemaError,
    validate_dynamic_schema,
)
from app.modules.reviews.errors import ReviewValidationError
from app.modules.reviews.models import Review, ReviewRecommendation
from app.modules.reviews.schemas import EvidenceAssessmentData
from app.modules.reviews.service import ReviewService
from app.modules.reviews.types import ReviewDraft
from app.tests.test_review_scoring import NOW, _principal, _setup


def _verification(outcome: str = "VERIFIED") -> dict[str, object]:
    return {
        "outcome": outcome,
        "method": "Compared the dated manuscript against the original archive.",
        "source": "Archive record A-2024, pages 3-5.",
        "scope": "Authorship and chronology of the submitted work.",
        "limitations": "No examination of material outside this archive.",
    }


def _case() -> tuple[Review, dict[str, object], str]:
    media_id = str(uuid4())
    review = Review(id=uuid4(), assignment_id=uuid4())
    review.recommendation = ReviewRecommendation.APPROVE
    review.criterion_verdicts = {
        "originality": {
            "outcome": "MEETS",
            "rationale": "Manuscript dates and archive records agree in scope.",
            "evidence_media_ids": [media_id],
        }
    }
    review.evidence_assessments = {
        media_id: {"status": "VALID", "note": "", "verification": _verification()}
    }
    rubric: dict[str, object] = {
        "version": "2026.3",
        "title": "Evidence-based review",
        "assessmentMethod": "VERDICT",
        "evidencePolicyVersion": "2026.1",
        "gates": [],
        "criteria": [
            {
                "key": "originality",
                "label": "Originality",
                "description": "Compare provenance.",
                "verificationRequired": True,
                "allowNotApplicable": False,
            }
        ],
    }
    return review, rubric, media_id


@pytest.mark.parametrize(
    "status", ["NOT_RELEVANT", "NEEDS_CLARIFICATION", "UNREVIEWED"]
)
def test_meets_cannot_cite_unsuitable_evidence(status: str) -> None:
    review, rubric, media_id = _case()
    review.evidence_assessments[media_id]["status"] = status
    with pytest.raises(ReviewValidationError, match="relevant"):
        ReviewService._validate_verdict_decision(review, rubric)


@pytest.mark.parametrize(
    "outcome", ["UNVERIFIED", "PARTIAL", "INSUFFICIENT", "CONTRADICTED", "UNVERIFIABLE"]
)
def test_required_verification_cannot_be_bypassed(outcome: str) -> None:
    review, rubric, media_id = _case()
    review.evidence_assessments[media_id]["verification"] = _verification(outcome)
    with pytest.raises(ReviewValidationError, match="verification"):
        ReviewService._validate_verdict_decision(review, rubric)


def test_policy_is_frozen_and_legacy_does_not_invent_verification() -> None:
    review, rubric, _ = _case()
    review.evidence_assessments = {}
    del rubric["evidencePolicyVersion"]
    ReviewService._validate_verdict_decision(review, rubric)


def test_not_applicable_requires_explicit_policy_permission() -> None:
    review, rubric, _ = _case()
    review.criterion_verdicts["originality"]["outcome"] = "NOT_APPLICABLE"
    with pytest.raises(ReviewValidationError, match="not applicable"):
        ReviewService._validate_verdict_decision(review, rubric)


def test_insufficient_basis_requires_supplement_and_can_be_saved() -> None:
    review, rubric, media_id = _case()
    review.criterion_verdicts["originality"]["outcome"] = "INSUFFICIENT_BASIS"
    review.criterion_verdicts["originality"]["evidence_media_ids"] = []
    draft = ReviewService._validated_draft(
        ReviewDraft(
            criterion_verdicts={
                "originality": {
                    **review.criterion_verdicts["originality"],
                    "evidence_media_ids": (uuid4(),),
                }
            }
        )
    )
    assert draft.criterion_verdicts["originality"]["outcome"] == "INSUFFICIENT_BASIS"
    with pytest.raises(ReviewValidationError, match="SUPPLEMENT"):
        ReviewService._validate_verdict_decision(review, rubric)
    review.recommendation = ReviewRecommendation.SUPPLEMENT
    review.applicant_feedback = (
        "Please provide a dated source for the authorship claim."
    )
    ReviewService._validate_verdict_decision(review, rubric)
    assert media_id in review.evidence_assessments


@pytest.mark.parametrize("field", ["method", "source", "scope", "limitations"])
def test_incomplete_verification_is_draftable_but_not_submittable(field: str) -> None:
    review, _, media_id = _case()
    verification = _verification()
    verification[field] = ""
    normalized = ReviewService._validated_evidence_assessments(
        {media_id: {"status": "VALID", "verification": verification}}
    )
    assert normalized[media_id]["verification"] == verification
    review.evidence_assessments = normalized
    with pytest.raises(ReviewValidationError, match="verification"):
        ReviewService._validate_complete_evidence_assessments(
            review,
            {"schemaVersion": 2, "evidences": [{"mediaAssetId": media_id}]},
        )


def test_verification_attribution_is_server_owned_and_stable_on_unchanged_save() -> (
    None
):
    async def exercise() -> None:
        service, _, engine, users, assignment, _ = await _setup()
        reviewer = _principal(users["reviewer"])
        await service.declare_conflict(
            reviewer, assignment.id, has_conflict=False, reason=None
        )
        detail = await service.get_assignment(reviewer, assignment.id)
        media_id = detail.snapshot_json["evidences"][0]["mediaAssetId"]
        forged = {**_verification(), "verified_by": str(uuid4()), "verified_at": "fake"}
        draft = ReviewDraft(
            evidence_assessments={media_id: {"status": "VALID", "verification": forged}}
        )
        saved = await service.save_draft(reviewer, assignment.id, draft)
        verification = saved.evidence_assessments[media_id]["verification"]
        assert verification["verified_by"] == str(reviewer.user_id)
        assert verification["verified_at"] == NOW.isoformat()
        again = await service.save_draft(reviewer, assignment.id, draft)
        assert again.evidence_assessments == saved.evidence_assessments
        legacy_save = await service.save_draft(
            reviewer,
            assignment.id,
            ReviewDraft(evidence_assessments={media_id: {"status": "VALID"}}),
        )
        assert legacy_save.evidence_assessments == saved.evidence_assessments
        omitted_save = await service.save_draft(reviewer, assignment.id, ReviewDraft())
        assert omitted_save.evidence_assessments == saved.evidence_assessments
        # The API serializer must return the persisted record without rejecting fields.
        dto = EvidenceAssessmentData.model_validate(
            saved.evidence_assessments[media_id]
        )
        assert (
            dto.model_dump(by_alias=True)["verification"]["verifiedBy"]
            == reviewer.user_id
        )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_uncited_relevant_contradiction_blocks_approval() -> None:
    review, rubric, _ = _case()
    review.evidence_assessments[str(uuid4())] = {
        "status": "VALID",
        "verification": _verification("CONTRADICTED"),
    }
    with pytest.raises(ReviewValidationError, match="contradiction"):
        ReviewService._validate_verdict_decision(review, rubric)


def test_new_verification_flags_cannot_be_published_without_their_policy() -> None:
    _, rubric, _ = _case()
    del rubric["evidencePolicyVersion"]
    rubric["minimumIndependentReviews"] = 2
    with pytest.raises(DynamicSchemaError, match="evidencePolicyVersion"):
        validate_dynamic_schema({"fields": [], "reviewRubric": rubric})


def test_policy_requires_criterion_specific_approval_rationales() -> None:
    review, rubric, _ = _case()
    rubric["criteria"].append(
        {"key": "impact", "label": "Tác động", "description": "Assess impact."}
    )
    review.criterion_verdicts["impact"] = dict(review.criterion_verdicts["originality"])
    with pytest.raises(ReviewValidationError, match="criterion-specific"):
        ReviewService._validate_verdict_decision(review, rubric)
    del rubric["evidencePolicyVersion"]
    ReviewService._validate_verdict_decision(review, rubric)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("evidencePolicyVersion", "future"),
        ("verificationRequired", "yes"),
        ("allowNotApplicable", "yes"),
        ("minimumIndependentReviews", 0),
        ("minimumIndependentReviews", 11),
        ("minimumIndependentReviews", True),
        ("minimumIndependentReviews", "2"),
    ],
)
def test_policy_schema_rejects_unsupported_or_untyped_configuration(
    key: str, value: object
) -> None:
    _, rubric, _ = _case()
    rubric = deepcopy(rubric)
    if key in {"evidencePolicyVersion", "minimumIndependentReviews"}:
        rubric[key] = value
    else:
        rubric["criteria"][0][key] = value
    with pytest.raises(DynamicSchemaError, match=key):
        validate_dynamic_schema({"fields": [], "reviewRubric": rubric})
