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
from app.modules.council.dependencies import CouncilServiceDependency
from app.modules.council.models import CouncilSessionStatus
from app.modules.council.schemas import (
    AddCouncilCaseRequest,
    CouncilCaseData,
    CouncilCaseDetailData,
    CouncilCaseResultData,
    CouncilConflictData,
    CouncilConflictRequest,
    CouncilMemberData,
    CouncilMinutesData,
    CouncilSessionData,
    CouncilSessionDetailData,
    CouncilSessionListItemData,
    CouncilVoteData,
    CouncilVoteRequest,
    CreateCouncilSessionRequest,
)
from app.modules.council.types import (
    CouncilCaseDetailView,
    CouncilCaseResultView,
    CouncilMinutesView,
    CouncilSessionDetailView,
    CouncilSessionListItemView,
)

router = APIRouter(tags=["council"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Council access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Council resource not found.", "model": ErrorEnvelope},
    409: {"description": "Council state conflict.", "model": ErrorEnvelope},
    422: {"description": "Council request is invalid.", "model": ErrorEnvelope},
}


def _result_data(view: CouncilCaseResultView) -> CouncilCaseResultData:
    return CouncilCaseResultData.model_validate(view)


def _list_item_data(
    view: CouncilSessionListItemView,
) -> CouncilSessionListItemData:
    return CouncilSessionListItemData(
        session=CouncilSessionData.model_validate(view.session),
        my_attendance_confirmed_at=view.my_attendance_confirmed_at,
    )


def _case_detail_data(view: CouncilCaseDetailView) -> CouncilCaseDetailData:
    return CouncilCaseDetailData(
        case=CouncilCaseData.model_validate(view.case),
        my_conflict=(
            CouncilConflictData.model_validate(view.my_conflict)
            if view.my_conflict is not None
            else None
        ),
        my_vote=(
            CouncilVoteData.model_validate(view.my_vote)
            if view.my_vote is not None
            else None
        ),
        result=_result_data(view.result) if view.result is not None else None,
    )


def _detail_data(view: CouncilSessionDetailView) -> CouncilSessionDetailData:
    return CouncilSessionDetailData(
        session=CouncilSessionData.model_validate(view.session),
        my_attendance_confirmed_at=view.my_attendance_confirmed_at,
        cases=[_case_detail_data(item) for item in view.cases],
    )


def _minutes_data(view: CouncilMinutesView) -> CouncilMinutesData:
    return CouncilMinutesData(
        session_id=view.session_id,
        session_code=view.session_code,
        closed_at=view.closed_at,
        quorum_required=view.quorum_required,
        minutes_hash=view.minutes_hash,
        cases=[_result_data(item) for item in view.cases],
    )


@router.post(
    "/api/v1/admin/council/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CouncilSessionData],
    responses=PRIVATE_RESPONSES,
)
async def create_council_session(
    payload: CreateCouncilSessionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilSessionData]:
    result = await service.create_session(
        principal,
        code=payload.code,
        title=payload.title,
        scheduled_at=payload.scheduled_at,
        quorum_required=payload.quorum_required,
        member_user_ids=tuple(payload.member_user_ids),
    )
    return SuccessEnvelope(
        data=CouncilSessionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/council/sessions/{session_id}/cases",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CouncilCaseData],
    responses=PRIVATE_RESPONSES,
)
async def add_council_case(
    session_id: UUID,
    payload: AddCouncilCaseRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilCaseData]:
    result = await service.add_case(principal, session_id, payload.dossier_id)
    return SuccessEnvelope(
        data=CouncilCaseData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/council/sessions/{session_id}/open",
    response_model=SuccessEnvelope[CouncilSessionData],
    responses=PRIVATE_RESPONSES,
)
async def open_council_session(
    session_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilSessionData]:
    result = await service.open_session(principal, session_id)
    return SuccessEnvelope(
        data=CouncilSessionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/admin/council/sessions/{session_id}/close",
    response_model=SuccessEnvelope[CouncilSessionData],
    responses=PRIVATE_RESPONSES,
)
async def close_council_session(
    session_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilSessionData]:
    result = await service.close_session(principal, session_id)
    return SuccessEnvelope(
        data=CouncilSessionData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/api/v1/council/sessions",
    response_model=PaginatedSuccessEnvelope[list[CouncilSessionListItemData]],
    responses=PRIVATE_RESPONSES,
)
async def list_council_sessions(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CouncilServiceDependency,
    session_status: Annotated[
        CouncilSessionStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(alias="pageSize", ge=1, le=100),
    ] = 20,
) -> PaginatedSuccessEnvelope[list[CouncilSessionListItemData]]:
    result = await service.list_sessions(
        principal,
        status=session_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_list_item_data(item) for item in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/api/v1/council/sessions/{session_id}",
    response_model=SuccessEnvelope[CouncilSessionDetailData],
    responses=PRIVATE_RESPONSES,
)
async def get_council_session(
    session_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilSessionDetailData]:
    result = await service.get_session(principal, session_id)
    return SuccessEnvelope(
        data=_detail_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/council/sessions/{session_id}/attendance",
    response_model=SuccessEnvelope[CouncilMemberData],
    responses=PRIVATE_RESPONSES,
)
async def confirm_council_attendance(
    session_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilMemberData]:
    result = await service.confirm_attendance(principal, session_id)
    return SuccessEnvelope(
        data=CouncilMemberData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/council/cases/{case_id}/conflict",
    response_model=SuccessEnvelope[CouncilConflictData],
    responses=PRIVATE_RESPONSES,
)
async def declare_council_conflict(
    case_id: UUID,
    payload: CouncilConflictRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilConflictData]:
    result = await service.declare_conflict(
        principal,
        case_id,
        has_conflict=payload.has_conflict,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=CouncilConflictData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/api/v1/council/cases/{case_id}/vote",
    response_model=SuccessEnvelope[CouncilVoteData],
    responses=PRIVATE_RESPONSES,
)
async def cast_council_vote(
    case_id: UUID,
    payload: CouncilVoteRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilVoteData]:
    result = await service.cast_vote(
        principal,
        case_id,
        choice=payload.choice,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=CouncilVoteData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/api/v1/council/sessions/{session_id}/minutes",
    response_model=SuccessEnvelope[CouncilMinutesData],
    responses=PRIVATE_RESPONSES,
)
async def get_council_minutes(
    session_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CouncilServiceDependency,
) -> SuccessEnvelope[CouncilMinutesData]:
    result = await service.get_minutes(principal, session_id)
    return SuccessEnvelope(
        data=_minutes_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
