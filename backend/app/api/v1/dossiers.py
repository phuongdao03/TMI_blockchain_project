from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

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
from app.modules.dossiers.dependencies import DossierServiceDependency
from app.modules.dossiers.models import DossierStatus
from app.modules.dossiers.schemas import (
    CreateDossierRequest,
    CreateEvidenceRequest,
    DossierActionData,
    DossierData,
    DossierDetailData,
    DossierStatusHistoryData,
    DossierVersionData,
    EvidenceData,
    PatchDossierRequest,
    PatchEvidenceRequest,
    SubmissionData,
)
from app.modules.dossiers.types import (
    CreateDossier,
    CreateEvidence,
    DossierChanges,
    DossierDetailView,
    DossierStatusHistoryView,
    DossierVersionView,
    DossierView,
    EvidenceChanges,
    EvidenceView,
    SubmissionView,
)

router = APIRouter(prefix="/api/v1/dossiers", tags=["dossiers"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Dossier access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Dossier or category not found.", "model": ErrorEnvelope},
    409: {"description": "Dossier state conflict.", "model": ErrorEnvelope},
    422: {"description": "Request validation failed.", "model": ErrorEnvelope},
}


def _dossier_data(view: DossierView) -> DossierData:
    return DossierData.model_validate(view)


def _evidence_data(view: EvidenceView) -> EvidenceData:
    return EvidenceData.model_validate(view)


def _version_data(view: DossierVersionView) -> DossierVersionData:
    return DossierVersionData.model_validate(view)


def _history_data(view: DossierStatusHistoryView) -> DossierStatusHistoryData:
    return DossierStatusHistoryData.model_validate(view)


def _submission_data(view: SubmissionView) -> SubmissionData:
    return SubmissionData(
        dossier=_dossier_data(view.dossier),
        version=_version_data(view.version),
    )


def _dossier_detail_data(view: DossierDetailView) -> DossierDetailData:
    dossier = _dossier_data(view.dossier)
    return DossierDetailData(
        **dossier.model_dump(),
        evidences=tuple(_evidence_data(item) for item in view.evidences),
    )


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
    response_model=SuccessEnvelope[DossierData],
    responses=PRIVATE_RESPONSES,
)
async def create_dossier(
    payload: CreateDossierRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[DossierData]:
    dossier = await service.create_dossier(
        principal,
        CreateDossier(
            category_id=payload.category_id,
            organization_id=payload.organization_id,
            title=payload.title,
            slug=payload.slug,
            summary=payload.summary,
            visibility=payload.visibility,
        ),
    )
    return SuccessEnvelope(
        data=_dossier_data(dossier),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[DossierData]],
    responses={401: PRIVATE_RESPONSES[401]},
)
async def list_dossiers(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: DossierServiceDependency,
    dossier_status: Annotated[
        DossierStatus | None,
        Query(alias="status"),
    ] = None,
    category_id: Annotated[UUID | None, Query(alias="categoryId")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[DossierData]]:
    result = await service.list_dossiers(
        principal,
        status=dossier_status,
        category_id=category_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_dossier_data(item) for item in result.items],
        meta=_list_meta(
            request,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/{dossier_id}",
    response_model=SuccessEnvelope[DossierDetailData],
    responses=PRIVATE_RESPONSES,
)
async def get_dossier(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[DossierDetailData]:
    dossier = await service.get_dossier_detail(principal, dossier_id)
    return SuccessEnvelope(
        data=_dossier_detail_data(dossier),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/{dossier_id}",
    response_model=SuccessEnvelope[DossierData],
    responses=PRIVATE_RESPONSES,
)
async def patch_dossier(
    dossier_id: UUID,
    payload: PatchDossierRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[DossierData]:
    dossier = await service.update_dossier(
        principal,
        dossier_id,
        DossierChanges(
            category_id=payload.category_id,
            organization_id=payload.organization_id,
            title=payload.title,
            slug=payload.slug,
            summary=payload.summary,
            visibility=payload.visibility,
            provided_fields=frozenset(payload.model_fields_set),
        ),
    )
    return SuccessEnvelope(
        data=_dossier_data(dossier),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{dossier_id}",
    response_model=SuccessEnvelope[DossierActionData],
    responses=PRIVATE_RESPONSES,
)
async def delete_dossier(
    dossier_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[DossierActionData]:
    await service.delete_dossier(principal, dossier_id)
    return SuccessEnvelope(
        data=DossierActionData(status="deleted"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{dossier_id}/evidences",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[EvidenceData],
    responses=PRIVATE_RESPONSES,
)
async def attach_evidence(
    dossier_id: UUID,
    payload: CreateEvidenceRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[EvidenceData]:
    evidence = await service.attach_evidence(
        principal,
        dossier_id,
        CreateEvidence(
            media_asset_id=payload.media_asset_id,
            evidence_type=payload.evidence_type,
            title=payload.title,
            description=payload.description,
            issued_at=payload.issued_at,
            display_order=payload.display_order,
            is_public=payload.is_public,
        ),
    )
    return SuccessEnvelope(
        data=_evidence_data(evidence),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/{dossier_id}/evidences/{evidence_id}",
    response_model=SuccessEnvelope[EvidenceData],
    responses=PRIVATE_RESPONSES,
)
async def patch_evidence(
    dossier_id: UUID,
    evidence_id: UUID,
    payload: PatchEvidenceRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[EvidenceData]:
    evidence = await service.update_evidence(
        principal,
        dossier_id,
        evidence_id,
        EvidenceChanges(
            evidence_type=payload.evidence_type,
            title=payload.title,
            description=payload.description,
            issued_at=payload.issued_at,
            display_order=payload.display_order,
            is_public=payload.is_public,
            provided_fields=frozenset(payload.model_fields_set),
        ),
    )
    return SuccessEnvelope(
        data=_evidence_data(evidence),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{dossier_id}/evidences/{evidence_id}",
    response_model=SuccessEnvelope[DossierActionData],
    responses=PRIVATE_RESPONSES,
)
async def remove_evidence(
    dossier_id: UUID,
    evidence_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[DossierActionData]:
    await service.remove_evidence(principal, dossier_id, evidence_id)
    return SuccessEnvelope(
        data=DossierActionData(status="removed"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{dossier_id}/submit",
    response_model=SuccessEnvelope[SubmissionData],
    responses=PRIVATE_RESPONSES,
)
async def submit_dossier(
    dossier_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[SubmissionData]:
    result = await service.submit_dossier(
        principal,
        dossier_id,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(
        data=_submission_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{dossier_id}/resubmit",
    response_model=SuccessEnvelope[SubmissionData],
    responses=PRIVATE_RESPONSES,
)
async def resubmit_dossier(
    dossier_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: DossierServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[SubmissionData]:
    result = await service.resubmit_dossier(
        principal,
        dossier_id,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(
        data=_submission_data(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{dossier_id}/versions",
    response_model=SuccessEnvelope[list[DossierVersionData]],
    responses=PRIVATE_RESPONSES,
)
async def list_versions(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[list[DossierVersionData]]:
    versions = await service.list_versions(principal, dossier_id)
    return SuccessEnvelope(
        data=[_version_data(version) for version in versions],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{dossier_id}/timeline",
    response_model=SuccessEnvelope[list[DossierStatusHistoryData]],
    responses=PRIVATE_RESPONSES,
)
async def get_timeline(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: DossierServiceDependency,
) -> SuccessEnvelope[list[DossierStatusHistoryData]]:
    timeline = await service.get_timeline(principal, dossier_id)
    return SuccessEnvelope(
        data=[_history_data(item) for item in timeline],
        meta=ResponseMeta(request_id=request.state.request_id),
    )
