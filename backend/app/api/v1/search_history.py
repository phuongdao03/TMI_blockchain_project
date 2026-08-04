from fastapi import APIRouter, Request, Response, status

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.search.history_dependencies import SearchHistoryServiceDependency
from app.modules.search.history_schemas import (
    SearchHistoryConsentRequest,
    SearchHistoryData,
    SearchHistoryRecordedData,
    SearchHistoryRecordRequest,
)

router = APIRouter(prefix="/api/v1/me/search-history", tags=["search-history"])


@router.get("", response_model=SuccessEnvelope[SearchHistoryData])
async def get_search_history(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SearchHistoryServiceDependency,
) -> SuccessEnvelope[SearchHistoryData]:
    state = await service.get(principal.user_id)
    return SuccessEnvelope(
        data=SearchHistoryData.from_state(state),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("", response_model=SuccessEnvelope[SearchHistoryData])
async def set_search_history_consent(
    payload: SearchHistoryConsentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: SearchHistoryServiceDependency,
) -> SuccessEnvelope[SearchHistoryData]:
    state = await service.set_consent(
        principal.user_id,
        enabled=payload.is_enabled,
    )
    return SuccessEnvelope(
        data=SearchHistoryData.from_state(state),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("", response_model=SuccessEnvelope[SearchHistoryRecordedData])
async def record_search_history(
    payload: SearchHistoryRecordRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: SearchHistoryServiceDependency,
) -> SuccessEnvelope[SearchHistoryRecordedData]:
    recorded = await service.record(principal.user_id, payload.query)
    return SuccessEnvelope(
        data=SearchHistoryRecordedData(recorded=recorded),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_search_history(
    principal: CsrfProtectedPrincipalDependency,
    service: SearchHistoryServiceDependency,
) -> Response:
    await service.clear(principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
