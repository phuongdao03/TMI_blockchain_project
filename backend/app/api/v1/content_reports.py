from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.public.errors import ContentReportTransitionError
from app.modules.public.models import ContentReportStatus
from app.modules.public.publication_dependencies import (
    ContentReportServiceDependency,
    PublicationServiceDependency,
)
from app.modules.public.report_repository import ContentReportRow
from app.modules.public.schemas import (
    ContentReportAdminData,
    ContentReportSuspendRequest,
    ContentReportTransitionRequest,
)

router = APIRouter(prefix="/api/v1/admin/content-reports", tags=["content-reports"])


def _data(row: ContentReportRow) -> ContentReportAdminData:
    report = row.report
    return ContentReportAdminData(
        id=report.id,
        public_work_id=report.public_work_id,
        work_title=row.work_title,
        work_slug=row.work_slug,
        work_version=row.work_version,
        reason=report.reason,
        description=report.description,
        status=report.status,
        reporter_type="USER" if report.reporter_user_id else "ANONYMOUS",
        has_contact_email=report.reporter_email_encrypted is not None,
        assigned_to_user_id=report.assigned_to_user_id,
        resolution_note=report.resolution_note,
        resolved_at=report.resolved_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("", response_model=PaginatedSuccessEnvelope[list[ContentReportAdminData]])
async def list_content_reports(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ContentReportServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    report_status: Annotated[ContentReportStatus | None, Query(alias="status")] = None,
) -> PaginatedSuccessEnvelope[list[ContentReportAdminData]]:
    rows, total = await service.list_admin(
        principal,
        status=report_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_data(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch("/{report_id}", response_model=SuccessEnvelope[ContentReportAdminData])
async def transition_content_report(
    report_id: UUID,
    payload: ContentReportTransitionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ContentReportServiceDependency,
) -> SuccessEnvelope[ContentReportAdminData]:
    row = await service.transition(
        principal,
        report_id,
        status=payload.status,
        resolution_note=payload.resolution_note,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_data(row), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/{report_id}/suspend", response_model=SuccessEnvelope[ContentReportAdminData]
)
async def suspend_from_content_report(
    report_id: UUID,
    payload: ContentReportSuspendRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    reports: ContentReportServiceDependency,
    publication: PublicationServiceDependency,
) -> SuccessEnvelope[ContentReportAdminData]:
    report = await reports.get_admin(principal, report_id)
    if report.report.status is not ContentReportStatus.UNDER_REVIEW:
        raise ContentReportTransitionError()
    await publication.suspend(
        principal,
        report.report.public_work_id,
        expected_version=payload.expected_work_version,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    row = await reports.transition(
        principal,
        report_id,
        status=ContentReportStatus.SUSPENDED,
        resolution_note=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_data(row), meta=ResponseMeta(request_id=request.state.request_id)
    )
