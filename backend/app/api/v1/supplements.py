from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.supplements.schemas import (
    CreateSupplementRequest,
    ResolveSupplementRequest,
    RespondSupplementRequest,
    SupplementData,
)
from app.modules.supplements.service import SupplementService

router = APIRouter(
    prefix="/api/v1/dossiers/{dossier_id}/supplement-requests", tags=["supplements"]
)


async def get_supplement_service(
    session: SessionDependency,
) -> AsyncIterator[SupplementService]:
    yield SupplementService(session)


ServiceDependency = Annotated[SupplementService, Depends(get_supplement_service)]


@router.get("", response_model=SuccessEnvelope[list[SupplementData]])
async def list_requests(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[list[SupplementData]]:
    return SuccessEnvelope(
        data=list(await service.list(principal, dossier_id)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("", response_model=SuccessEnvelope[SupplementData], status_code=201)
async def create_request(
    dossier_id: UUID,
    payload: CreateSupplementRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[SupplementData]:
    row = await service.create(
        principal, dossier_id, **payload.model_dump(by_alias=False)
    )
    return SuccessEnvelope(
        data=row, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.put("/{request_id}/response", response_model=SuccessEnvelope[SupplementData])
async def respond(
    dossier_id: UUID,
    request_id: UUID,
    payload: RespondSupplementRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[SupplementData]:
    row = await service.respond(
        principal,
        dossier_id,
        request_id,
        expected_revision=payload.expected_revision,
        text=payload.text,
    )
    return SuccessEnvelope(
        data=row, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post("/{request_id}/resolve", response_model=SuccessEnvelope[SupplementData])
async def resolve(
    dossier_id: UUID,
    request_id: UUID,
    payload: ResolveSupplementRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[SupplementData]:
    row = await service.decide(
        principal,
        dossier_id,
        request_id,
        expected_revision=payload.expected_revision,
        resolution=payload.resolution,
        reopen=payload.reopen,
    )
    return SuccessEnvelope(
        data=row, meta=ResponseMeta(request_id=request.state.request_id)
    )
