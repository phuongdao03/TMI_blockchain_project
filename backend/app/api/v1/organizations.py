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
from app.modules.organizations.dependencies import OrganizationServiceDependency
from app.modules.organizations.schemas import (
    AddOrganizationMemberRequest,
    CreateOrganizationRequest,
    OrganizationActionData,
    OrganizationData,
    OrganizationMemberData,
    PatchOrganizationRequest,
)
from app.modules.organizations.types import (
    CreateOrganization,
    MemberView,
    OrganizationChanges,
    OrganizationView,
    UpsertMember,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Organization access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Organization or member not found.", "model": ErrorEnvelope},
    409: {"description": "Organization state conflict.", "model": ErrorEnvelope},
    422: {"description": "Request validation failed.", "model": ErrorEnvelope},
}


def _organization_data(view: OrganizationView) -> OrganizationData:
    return OrganizationData.model_validate(view)


def _member_data(view: MemberView) -> OrganizationMemberData:
    return OrganizationMemberData.model_validate(view)


def _list_meta(
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
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[OrganizationData],
    responses=PRIVATE_RESPONSES,
)
async def create_organization(
    payload: CreateOrganizationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationData]:
    organization = await service.create_organization(
        principal,
        CreateOrganization(
            code=payload.code,
            legal_name=payload.legal_name,
            display_name=payload.display_name,
            tax_code=payload.tax_code,
        ),
    )
    return SuccessEnvelope(
        data=_organization_data(organization),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[OrganizationData]],
    responses={401: PRIVATE_RESPONSES[401]},
)
async def list_organizations(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: OrganizationServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[OrganizationData]]:
    result = await service.list_organizations(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_organization_data(item) for item in result.items],
        meta=_list_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/{organization_id}",
    response_model=SuccessEnvelope[OrganizationData],
    responses=PRIVATE_RESPONSES,
)
async def get_organization(
    organization_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationData]:
    organization = await service.get_organization(principal, organization_id)
    return SuccessEnvelope(
        data=_organization_data(organization),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/{organization_id}",
    response_model=SuccessEnvelope[OrganizationData],
    responses=PRIVATE_RESPONSES,
)
async def patch_organization(
    organization_id: UUID,
    payload: PatchOrganizationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationData]:
    organization = await service.update_organization(
        principal,
        organization_id,
        OrganizationChanges(
            legal_name=payload.legal_name,
            display_name=payload.display_name,
            tax_code=payload.tax_code,
            provided_fields=frozenset(payload.model_fields_set),
        ),
    )
    return SuccessEnvelope(
        data=_organization_data(organization),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{organization_id}",
    response_model=SuccessEnvelope[OrganizationActionData],
    responses=PRIVATE_RESPONSES,
)
async def archive_organization(
    organization_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationActionData]:
    await service.archive_organization(principal, organization_id)
    return SuccessEnvelope(
        data=OrganizationActionData(status="archived"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{organization_id}/members",
    response_model=PaginatedSuccessEnvelope[list[OrganizationMemberData]],
    responses=PRIVATE_RESPONSES,
)
async def list_members(
    organization_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: OrganizationServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[OrganizationMemberData]]:
    result = await service.list_members(
        principal,
        organization_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_member_data(item) for item in result.items],
        meta=_list_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.post(
    "/{organization_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[OrganizationMemberData],
    responses=PRIVATE_RESPONSES,
)
async def add_member(
    organization_id: UUID,
    payload: AddOrganizationMemberRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationMemberData]:
    member = await service.add_member(
        principal,
        organization_id=organization_id,
        member=UpsertMember(
            email=str(payload.email),
            role_code=payload.role_code,
            status=payload.status,
        ),
    )
    return SuccessEnvelope(
        data=_member_data(member),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{organization_id}/members/{user_id}",
    response_model=SuccessEnvelope[OrganizationActionData],
    responses=PRIVATE_RESPONSES,
)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: OrganizationServiceDependency,
) -> SuccessEnvelope[OrganizationActionData]:
    await service.remove_member(
        principal,
        organization_id=organization_id,
        user_id=user_id,
    )
    return SuccessEnvelope(
        data=OrganizationActionData(status="removed"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
