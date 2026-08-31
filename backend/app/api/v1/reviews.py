from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.reviews.dependencies import (
    PrecheckServiceDependency,
    ReviewServiceDependency,
    SimilarityReviewServiceDependency,
)
from app.modules.reviews.models import ReviewAssignmentStatus, SimilarityCaseStatus
from app.modules.reviews.schemas import (
    AssignReviewersRequest,
    AssignSimilarityCaseRequest,
    ConflictDeclarationRequest,
    DossierTransitionData,
    ResolveSimilarityCaseRequest,
    ReviewAssignmentData,
    ReviewAssignmentDetailData,
    ReviewAssignmentSummaryData,
    ReviewData,
    ReviewDraftRequest,
    SimilarityCaseData,
    TransitionRequest,
)
from app.modules.reviews.types import (
    ReviewAssignmentDetailView,
    ReviewAssignmentSummaryView,
    ReviewDraft,
    ReviewFinding,
    ReviewView,
)

router = APIRouter(tags=["reviews"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Review access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Review resource not found.", "model": ErrorEnvelope},
    409: {"description": "Review state conflict.", "model": ErrorEnvelope},
    422: {"description": "Review request is invalid.", "model": ErrorEnvelope},
}


def _assignment_summary_data(
    view: ReviewAssignmentSummaryView,
) -> ReviewAssignmentSummaryData:
    return ReviewAssignmentSummaryData(
        assignment=ReviewAssignmentData.model_validate(view.assignment),
        dossier_code=view.dossier_code,
        dossier_title=view.dossier_title,
        version_no=view.version_no,
    )


def _review_data(view: ReviewView) -> ReviewData:
    return ReviewData.model_validate(view)


def _assignment_detail_data(
    view: ReviewAssignmentDetailView,
) -> ReviewAssignmentDetailData:
    return ReviewAssignmentDetailData(
        assignment=ReviewAssignmentData.model_validate(view.assignment),
        dossier_code=view.dossier_code,
        dossier_title=view.dossier_title,
        version_no=view.version_no,
        canonical_hash=view.canonical_hash,
        snapshot_json=(
            dict(view.snapshot_json) if view.snapshot_json is not None else None
        ),
        review=_review_data(view.review) if view.review is not None else None,
    )


def _meta(
    request: Request,
    *,
    page: int,
    page_size: int,
    total: int,
) -> ListResponseMeta:
    return ListResponseMeta(
        request_id=request.state.request_id,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/api/v1/admin/dossiers/{dossier_id}/precheck",
    response_model=SuccessEnvelope[DossierTransitionData],
    responses=PRIVATE_RESPONSES,
)
async def start_precheck(
    dossier_id: UUID,
    payload: TransitionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PrecheckServiceDependency,
) -> SuccessEnvelope[DossierTransitionData]:
    result = await service.start_precheck(
        principal,
        dossier_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=DossierTransitionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/dossiers/{dossier_id}/pass-precheck",
    response_model=SuccessEnvelope[DossierTransitionData],
    responses=PRIVATE_RESPONSES,
)
async def pass_precheck(
    dossier_id: UUID,
    payload: TransitionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PrecheckServiceDependency,
) -> SuccessEnvelope[DossierTransitionData]:
    result = await service.pass_precheck(
        principal,
        dossier_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=DossierTransitionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/dossiers/{dossier_id}/request-supplement",
    response_model=SuccessEnvelope[DossierTransitionData],
    responses=PRIVATE_RESPONSES,
)
async def request_supplement(
    dossier_id: UUID,
    payload: TransitionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PrecheckServiceDependency,
) -> SuccessEnvelope[DossierTransitionData]:
    result = await service.request_supplement(
        principal,
        dossier_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=DossierTransitionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/dossiers/{dossier_id}/assign-reviewers",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[list[ReviewAssignmentData]],
    responses=PRIVATE_RESPONSES,
)
async def assign_reviewers(
    dossier_id: UUID,
    payload: AssignReviewersRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ReviewServiceDependency,
) -> SuccessEnvelope[list[ReviewAssignmentData]]:
    assignments = await service.assign_reviewers(
        principal,
        dossier_id,
        reviewer_user_ids=tuple(payload.reviewer_user_ids),
        due_at=payload.due_at,
    )
    return SuccessEnvelope(
        data=[
            ReviewAssignmentData.model_validate(assignment)
            for assignment in assignments
        ],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/api/v1/reviewer/assignments",
    response_model=PaginatedSuccessEnvelope[list[ReviewAssignmentSummaryData]],
    responses=PRIVATE_RESPONSES,
)
async def list_reviewer_assignments(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ReviewServiceDependency,
    assignment_status: Annotated[
        ReviewAssignmentStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(alias="pageSize", ge=1, le=100),
    ] = 20,
) -> PaginatedSuccessEnvelope[list[ReviewAssignmentSummaryData]]:
    result = await service.list_assignments(
        principal,
        status=assignment_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_assignment_summary_data(item) for item in result.items],
        meta=_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/api/v1/reviewer/assignments/{assignment_id}",
    response_model=SuccessEnvelope[ReviewAssignmentDetailData],
    responses=PRIVATE_RESPONSES,
)
async def get_reviewer_assignment(
    assignment_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ReviewServiceDependency,
) -> SuccessEnvelope[ReviewAssignmentDetailData]:
    result = await service.get_assignment(principal, assignment_id)
    return SuccessEnvelope(
        data=_assignment_detail_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/reviewer/assignments/{assignment_id}/conflict",
    response_model=SuccessEnvelope[ReviewAssignmentData],
    responses=PRIVATE_RESPONSES,
)
async def declare_reviewer_conflict(
    assignment_id: UUID,
    payload: ConflictDeclarationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ReviewServiceDependency,
) -> SuccessEnvelope[ReviewAssignmentData]:
    result = await service.declare_conflict(
        principal,
        assignment_id,
        has_conflict=payload.has_conflict,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=ReviewAssignmentData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/api/v1/reviewer/assignments/{assignment_id}/draft",
    response_model=SuccessEnvelope[ReviewData],
    responses=PRIVATE_RESPONSES,
)
async def save_review_draft(
    assignment_id: UUID,
    payload: ReviewDraftRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ReviewServiceDependency,
) -> SuccessEnvelope[ReviewData]:
    result = await service.save_draft(
        principal,
        assignment_id,
        ReviewDraft(
            truth_score=payload.truth_score,
            transparency_score=payload.transparency_score,
            ownership_score=payload.ownership_score,
            professionalism_score=payload.professionalism_score,
            respect_score=payload.respect_score,
            criterion_comments=payload.criterion_comments,
            criterion_evidence={
                criterion: tuple(media_ids)
                for criterion, media_ids in payload.criterion_evidence.items()
            },
            findings=tuple(
                ReviewFinding(
                    id=item.id,
                    severity=item.severity,
                    criterion=item.criterion,
                    evidence_media_ids=tuple(item.evidence_media_ids),
                    title=item.title,
                    description=item.description,
                    action=item.action,
                )
                for item in payload.findings
            ),
            checklist_answers=payload.checklist_answers,
            applicant_feedback=payload.applicant_feedback,
            recommendation=payload.recommendation,
            private_note=payload.private_note,
            gate_answers={
                key: value.model_dump()
                for key, value in payload.gate_answers.items()
            },
            specialist_answers={
                key: value.model_dump()
                for key, value in payload.specialist_answers.items()
            },
        ),
    )
    return SuccessEnvelope(
        data=_review_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/reviewer/assignments/{assignment_id}/submit",
    response_model=SuccessEnvelope[ReviewData],
    responses=PRIVATE_RESPONSES,
)
async def submit_review(
    assignment_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ReviewServiceDependency,
) -> SuccessEnvelope[ReviewData]:
    result = await service.submit_review(principal, assignment_id)
    return SuccessEnvelope(
        data=_review_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/similarity-cases/{case_id}/assign",
    response_model=SuccessEnvelope[SimilarityCaseData],
    responses=PRIVATE_RESPONSES,
)
async def assign_similarity_case(
    case_id: UUID,
    payload: AssignSimilarityCaseRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: SimilarityReviewServiceDependency,
) -> SuccessEnvelope[SimilarityCaseData]:
    result = await service.assign_case(
        principal,
        case_id,
        payload.reviewer_user_id,
    )
    return SuccessEnvelope(
        data=SimilarityCaseData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/api/v1/admin/similarity-cases",
    response_model=PaginatedSuccessEnvelope[list[SimilarityCaseData]],
    responses=PRIVATE_RESPONSES,
)
async def list_admin_similarity_cases(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SimilarityReviewServiceDependency,
    case_status: Annotated[
        SimilarityCaseStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[SimilarityCaseData]]:
    result = await service.list_admin_cases(
        principal,
        status=case_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[SimilarityCaseData.model_validate(item) for item in result.items],
        meta=_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/api/v1/reviewer/similarity-cases",
    response_model=PaginatedSuccessEnvelope[list[SimilarityCaseData]],
    responses=PRIVATE_RESPONSES,
)
async def list_similarity_cases(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SimilarityReviewServiceDependency,
    case_status: Annotated[
        SimilarityCaseStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[SimilarityCaseData]]:
    result = await service.list_reviewer_cases(
        principal,
        status=case_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[SimilarityCaseData.model_validate(item) for item in result.items],
        meta=_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/api/v1/reviewer/similarity-cases/{case_id}",
    response_model=SuccessEnvelope[SimilarityCaseData],
    responses=PRIVATE_RESPONSES,
)
async def get_similarity_case(
    case_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SimilarityReviewServiceDependency,
) -> SuccessEnvelope[SimilarityCaseData]:
    result = await service.get_case(principal, case_id)
    return SuccessEnvelope(
        data=SimilarityCaseData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/reviewer/similarity-cases/{case_id}/resolve",
    response_model=SuccessEnvelope[SimilarityCaseData],
    responses=PRIVATE_RESPONSES,
)
async def resolve_similarity_case(
    case_id: UUID,
    payload: ResolveSimilarityCaseRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: SimilarityReviewServiceDependency,
) -> SuccessEnvelope[SimilarityCaseData]:
    result = await service.resolve_case(
        principal,
        case_id,
        disposition=payload.disposition,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=SimilarityCaseData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
