from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.hr.dashboard_service import HrDashboardService
from app.modules.hr.models import (
    AttendanceLocationExceptionStatus,
    AttendanceStatus,
    AttendanceWorksiteStatus,
    EmploymentStatus,
    LeaveRequestStatus,
    OvertimeRequestStatus,
)
from app.modules.hr.payroll_service import PayrollService
from app.modules.hr.report_service import HrReportService
from app.modules.hr.schemas import (
    AdminAttendanceData,
    AdminAttendanceLocationExceptionData,
    AdminLeaveRequestData,
    AdminOvertimeRequestData,
    AttendanceAssignmentData,
    AttendanceData,
    AttendanceLocationEvidenceReviewData,
    AttendanceLocationExceptionData,
    AttendanceLocationExceptionDecisionRequest,
    AttendanceWorkdayContextData,
    AttendanceWorksiteData,
    AttendanceWorksitePolicyData,
    CheckInRequest,
    CheckOutRequest,
    CreateAttendanceAssignmentRequest,
    CreateAttendanceWorksitePolicyRequest,
    CreateAttendanceWorksiteRequest,
    CreateDepartmentRequest,
    CreateEmployeeRequest,
    CreateLeaveRequest,
    CreateOvertimeRequest,
    CreatePayrollPeriodRequest,
    DepartmentData,
    EmployeeData,
    HrDashboardSummaryData,
    LeaveDecisionRequest,
    LeaveRequestData,
    ModeratorHrDashboardSummaryData,
    OvertimeDecisionRequest,
    OvertimeRequestData,
    PayrollEntryData,
    PayrollPeriodData,
    PayrollPeriodDetailData,
    UpdateAttendanceRequest,
    UpdateAttendanceWorksiteRequest,
    UpdateDepartmentRequest,
    UpdateEmployeeRequest,
    UpdatePayrollEntryRequest,
)
from app.modules.hr.service import HrService
from app.modules.tasks.models import TaskPriority, TaskStatus

router = APIRouter(prefix="/api/v1/admin/hr", tags=["human resources"])
self_router = APIRouter(prefix="/api/v1/me/hr", tags=["human resources"])
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _private_location_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/dashboard-summary",
    response_model=SuccessEnvelope[HrDashboardSummaryData],
)
async def get_hr_dashboard_summary(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[HrDashboardSummaryData]:
    summary = await HrDashboardService(session).summary(principal)
    _private_location_response(response)
    return SuccessEnvelope(
        data=HrDashboardSummaryData.model_validate(summary),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/attendance-worksites",
    response_model=PaginatedSuccessEnvelope[list[AttendanceWorksiteData]],
)
async def list_attendance_worksites(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    worksite_status: Annotated[
        AttendanceWorksiteStatus | None, Query(alias="status")
    ] = None,
) -> PaginatedSuccessEnvelope[list[AttendanceWorksiteData]]:
    rows, total = await HrService(session).list_attendance_worksites(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        worksite_status=worksite_status,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/attendance-worksites",
    response_model=SuccessEnvelope[AttendanceWorksiteData],
    status_code=status.HTTP_201_CREATED,
)
async def create_attendance_worksite(
    payload: CreateAttendanceWorksiteRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceWorksiteData]:
    data = await HrService(session).create_attendance_worksite(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.patch(
    "/attendance-worksites/{worksite_id}",
    response_model=SuccessEnvelope[AttendanceWorksiteData],
)
async def update_attendance_worksite(
    worksite_id: UUID,
    payload: UpdateAttendanceWorksiteRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceWorksiteData]:
    data = await HrService(session).update_attendance_worksite(
        principal,
        worksite_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/attendance-worksites/{worksite_id}/policies",
    response_model=PaginatedSuccessEnvelope[list[AttendanceWorksitePolicyData]],
)
async def list_attendance_worksite_policies(
    worksite_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[AttendanceWorksitePolicyData]]:
    rows, total = await HrService(session).list_attendance_worksite_policies(
        principal,
        worksite_id,
        page=page,
        page_size=page_size,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/attendance-worksites/{worksite_id}/policies",
    response_model=SuccessEnvelope[AttendanceWorksitePolicyData],
    status_code=status.HTTP_201_CREATED,
)
async def create_attendance_worksite_policy(
    worksite_id: UUID,
    payload: CreateAttendanceWorksitePolicyRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceWorksitePolicyData]:
    data = await HrService(session).create_attendance_worksite_policy(
        principal,
        worksite_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/attendance-assignments",
    response_model=PaginatedSuccessEnvelope[list[AttendanceAssignmentData]],
)
async def list_attendance_assignments(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    employee_id: Annotated[UUID | None, Query(alias="employeeId")] = None,
    worksite_id: Annotated[UUID | None, Query(alias="worksiteId")] = None,
) -> PaginatedSuccessEnvelope[list[AttendanceAssignmentData]]:
    rows, total = await HrService(session).list_attendance_assignments(
        principal,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        worksite_id=worksite_id,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/attendance-assignments",
    response_model=SuccessEnvelope[AttendanceAssignmentData],
    status_code=status.HTTP_201_CREATED,
)
async def create_attendance_assignment(
    payload: CreateAttendanceAssignmentRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceAssignmentData]:
    data = await HrService(session).create_attendance_assignment(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.get(
    "/leave-requests",
    response_model=PaginatedSuccessEnvelope[list[LeaveRequestData]],
)
async def list_personal_leave_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[LeaveRequestData]]:
    rows, total = await HrService(session).list_personal_leave_requests(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@self_router.post(
    "/leave-requests",
    response_model=SuccessEnvelope[LeaveRequestData],
    status_code=status.HTTP_201_CREATED,
)
async def create_leave_request(
    payload: CreateLeaveRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[LeaveRequestData]:
    data = await HrService(session).create_leave_request(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.post(
    "/leave-requests/{leave_request_id}/cancel",
    response_model=SuccessEnvelope[LeaveRequestData],
)
async def cancel_leave_request(
    leave_request_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[LeaveRequestData]:
    data = await HrService(session).cancel_leave_request(
        principal,
        leave_request_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.get(
    "/overtime-requests",
    response_model=PaginatedSuccessEnvelope[list[OvertimeRequestData]],
)
async def list_personal_overtime_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[OvertimeRequestData]]:
    rows, total = await HrService(session).list_personal_overtime_requests(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@self_router.post(
    "/overtime-requests",
    response_model=SuccessEnvelope[OvertimeRequestData],
    status_code=status.HTTP_201_CREATED,
)
async def create_overtime_request(
    payload: CreateOvertimeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[OvertimeRequestData]:
    data = await HrService(session).create_overtime_request(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.post(
    "/overtime-requests/{overtime_request_id}/cancel",
    response_model=SuccessEnvelope[OvertimeRequestData],
)
async def cancel_overtime_request(
    overtime_request_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[OvertimeRequestData]:
    data = await HrService(session).cancel_overtime_request(
        principal,
        overtime_request_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.get(
    "/attendance",
    response_model=PaginatedSuccessEnvelope[list[AttendanceData]],
)
async def list_personal_attendance(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[AttendanceData]]:
    rows, total = await HrService(session).list_personal_attendance(
        principal,
        page=page,
        page_size=page_size,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@self_router.get(
    "/attendance/workday-context",
    response_model=SuccessEnvelope[AttendanceWorkdayContextData],
)
async def get_personal_attendance_workday_context(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceWorkdayContextData]:
    data = await HrService(session).get_personal_attendance_workday_context(principal)
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.get(
    "/dashboard-summary",
    response_model=SuccessEnvelope[ModeratorHrDashboardSummaryData],
)
async def get_moderator_hr_dashboard_summary(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[ModeratorHrDashboardSummaryData]:
    summary = await HrDashboardService(session).moderator_summary(principal)
    _private_location_response(response)
    return SuccessEnvelope(
        data=ModeratorHrDashboardSummaryData.model_validate(summary),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@self_router.get(
    "/attendance/{attendance_id}/location-evidence",
    response_model=SuccessEnvelope[list[AttendanceLocationEvidenceReviewData]],
)
async def list_personal_attendance_location_evidence(
    attendance_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[AttendanceLocationEvidenceReviewData]]:
    rows = await HrService(session).list_personal_attendance_location_evidence(
        principal, attendance_id
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=list(rows), meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.post(
    "/attendance/check-in",
    response_model=SuccessEnvelope[AttendanceData],
    status_code=status.HTTP_201_CREATED,
)
async def check_in(
    payload: CheckInRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceData]:
    data = await HrService(session).check_in(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@self_router.post(
    "/attendance/check-out",
    response_model=SuccessEnvelope[AttendanceData],
)
async def check_out(
    payload: CheckOutRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceData]:
    data = await HrService(session).check_out(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/attendance",
    response_model=PaginatedSuccessEnvelope[list[AdminAttendanceData]],
)
async def list_admin_attendance(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    attendance_status: Annotated[AttendanceStatus | None, Query(alias="status")] = None,
    work_date_from: Annotated[date | None, Query(alias="workDateFrom")] = None,
    work_date_to: Annotated[date | None, Query(alias="workDateTo")] = None,
) -> PaginatedSuccessEnvelope[list[AdminAttendanceData]]:
    rows, total = await HrService(session).list_admin_attendance(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        attendance_status=attendance_status,
        work_date_from=work_date_from,
        work_date_to=work_date_to,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch(
    "/attendance-location-exceptions/{exception_id}",
    response_model=SuccessEnvelope[AttendanceLocationExceptionData],
)
async def decide_attendance_location_exception(
    exception_id: UUID,
    payload: AttendanceLocationExceptionDecisionRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AttendanceLocationExceptionData]:
    data = await HrService(session).decide_attendance_location_exception(
        principal,
        exception_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/attendance-location-exceptions",
    response_model=PaginatedSuccessEnvelope[list[AdminAttendanceLocationExceptionData]],
)
async def list_attendance_location_exceptions(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    exception_status: Annotated[
        AttendanceLocationExceptionStatus | None, Query(alias="status")
    ] = None,
) -> PaginatedSuccessEnvelope[list[AdminAttendanceLocationExceptionData]]:
    rows, total = await HrService(session).list_attendance_location_exceptions(
        principal,
        page=page,
        page_size=page_size,
        exception_status=exception_status,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/attendance/{attendance_id}/location-evidence",
    response_model=SuccessEnvelope[list[AttendanceLocationEvidenceReviewData]],
)
async def list_admin_attendance_location_evidence(
    attendance_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[AttendanceLocationEvidenceReviewData]]:
    rows = await HrService(session).list_admin_attendance_location_evidence(
        principal, attendance_id
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=list(rows), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/attendance/{attendance_id}", response_model=SuccessEnvelope[AdminAttendanceData]
)
async def get_admin_attendance(
    attendance_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminAttendanceData]:
    data = await HrService(session).get_admin_attendance(principal, attendance_id)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.patch(
    "/attendance/{attendance_id}", response_model=SuccessEnvelope[AdminAttendanceData]
)
async def update_attendance(
    attendance_id: UUID,
    payload: UpdateAttendanceRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminAttendanceData]:
    data = await HrService(session).update_attendance(
        principal,
        attendance_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/leave-requests",
    response_model=PaginatedSuccessEnvelope[list[AdminLeaveRequestData]],
)
async def list_admin_leave_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    leave_status: Annotated[LeaveRequestStatus | None, Query(alias="status")] = None,
    start_date_from: Annotated[date | None, Query(alias="startDateFrom")] = None,
    start_date_to: Annotated[date | None, Query(alias="startDateTo")] = None,
) -> PaginatedSuccessEnvelope[list[AdminLeaveRequestData]]:
    rows, total = await HrService(session).list_admin_leave_requests(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        leave_status=leave_status,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


async def _decide_leave_request(
    leave_request_id: UUID,
    decision: LeaveRequestStatus,
    payload: LeaveDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminLeaveRequestData]:
    data = await HrService(session).decide_leave_request(
        principal,
        leave_request_id,
        decision,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/leave-requests/{leave_request_id}/approve",
    response_model=SuccessEnvelope[AdminLeaveRequestData],
)
async def approve_leave_request(
    leave_request_id: UUID,
    payload: LeaveDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminLeaveRequestData]:
    return await _decide_leave_request(
        leave_request_id,
        LeaveRequestStatus.APPROVED,
        payload,
        request,
        principal,
        session,
    )


@router.post(
    "/leave-requests/{leave_request_id}/reject",
    response_model=SuccessEnvelope[AdminLeaveRequestData],
)
async def reject_leave_request(
    leave_request_id: UUID,
    payload: LeaveDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminLeaveRequestData]:
    return await _decide_leave_request(
        leave_request_id,
        LeaveRequestStatus.REJECTED,
        payload,
        request,
        principal,
        session,
    )


@router.get(
    "/overtime-requests",
    response_model=PaginatedSuccessEnvelope[list[AdminOvertimeRequestData]],
)
async def list_admin_overtime_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    overtime_status: Annotated[
        OvertimeRequestStatus | None, Query(alias="status")
    ] = None,
    start_at_from: Annotated[datetime | None, Query(alias="startAtFrom")] = None,
    start_at_to: Annotated[datetime | None, Query(alias="startAtTo")] = None,
) -> PaginatedSuccessEnvelope[list[AdminOvertimeRequestData]]:
    rows, total = await HrService(session).list_admin_overtime_requests(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        overtime_status=overtime_status,
        start_at_from=start_at_from,
        start_at_to=start_at_to,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


async def _decide_overtime_request(
    overtime_request_id: UUID,
    decision: OvertimeRequestStatus,
    payload: OvertimeDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminOvertimeRequestData]:
    data = await HrService(session).decide_overtime_request(
        principal,
        overtime_request_id,
        decision,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/overtime-requests/{overtime_request_id}/approve",
    response_model=SuccessEnvelope[AdminOvertimeRequestData],
)
async def approve_overtime_request(
    overtime_request_id: UUID,
    payload: OvertimeDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminOvertimeRequestData]:
    return await _decide_overtime_request(
        overtime_request_id,
        OvertimeRequestStatus.APPROVED,
        payload,
        request,
        principal,
        session,
    )


@router.post(
    "/overtime-requests/{overtime_request_id}/reject",
    response_model=SuccessEnvelope[AdminOvertimeRequestData],
)
async def reject_overtime_request(
    overtime_request_id: UUID,
    payload: OvertimeDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminOvertimeRequestData]:
    return await _decide_overtime_request(
        overtime_request_id,
        OvertimeRequestStatus.REJECTED,
        payload,
        request,
        principal,
        session,
    )


@router.get(
    "/departments",
    response_model=PaginatedSuccessEnvelope[list[DepartmentData]],
)
async def list_departments(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
) -> PaginatedSuccessEnvelope[list[DepartmentData]]:
    rows, total = await HrService(session).list_departments(
        principal, page=page, page_size=page_size, search=search
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/departments",
    response_model=SuccessEnvelope[DepartmentData],
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    payload: CreateDepartmentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DepartmentData]:
    data = await HrService(session).create_department(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.patch(
    "/departments/{department_id}",
    response_model=SuccessEnvelope[DepartmentData],
)
async def update_department(
    department_id: UUID,
    payload: UpdateDepartmentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DepartmentData]:
    data = await HrService(session).update_department(
        principal,
        department_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("/employees", response_model=PaginatedSuccessEnvelope[list[EmployeeData]])
async def list_employees(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    employment_status: Annotated[
        EmploymentStatus | None, Query(alias="employmentStatus")
    ] = None,
) -> PaginatedSuccessEnvelope[list[EmployeeData]]:
    rows, total = await HrService(session).list_employees(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        employment_status=employment_status,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/reports/tasks.xlsx", response_class=Response)
async def export_tasks_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
) -> Response:
    content = await HrReportService(session).tasks(
        principal,
        search=search,
        task_status=task_status,
        priority=priority,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-tasks.xlsx")


@router.get(
    "/reports/payroll-periods/{payroll_period_id}/xlsx", response_class=Response
)
async def export_payroll_xlsx(
    payroll_period_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> Response:
    content = await HrReportService(session).payroll(
        principal,
        payroll_period_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-payroll.xlsx")


@router.get("/reports/departments.xlsx", response_class=Response)
async def export_departments_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
) -> Response:
    content = await HrReportService(session).departments(
        principal,
        search=search,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-departments.xlsx")


@router.get("/reports/employees.xlsx", response_class=Response)
async def export_employees_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    employment_status: Annotated[
        EmploymentStatus | None, Query(alias="employmentStatus")
    ] = None,
) -> Response:
    content = await HrReportService(session).employees(
        principal,
        search=search,
        department_id=department_id,
        employment_status=employment_status,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-employees.xlsx")


@router.get("/reports/attendance.xlsx", response_class=Response)
async def export_attendance_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    attendance_status: Annotated[AttendanceStatus | None, Query(alias="status")] = None,
    work_date_from: Annotated[date | None, Query(alias="workDateFrom")] = None,
    work_date_to: Annotated[date | None, Query(alias="workDateTo")] = None,
) -> Response:
    content = await HrReportService(session).attendance(
        principal,
        search=search,
        department_id=department_id,
        attendance_status=attendance_status,
        work_date_from=work_date_from,
        work_date_to=work_date_to,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-attendance.xlsx")


@router.get("/reports/leave.xlsx", response_class=Response)
async def export_leave_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    leave_status: Annotated[LeaveRequestStatus | None, Query(alias="status")] = None,
    start_date_from: Annotated[date | None, Query(alias="startDateFrom")] = None,
    start_date_to: Annotated[date | None, Query(alias="startDateTo")] = None,
) -> Response:
    content = await HrReportService(session).leave(
        principal,
        search=search,
        department_id=department_id,
        leave_status=leave_status,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-leave.xlsx")


@router.get("/reports/overtime.xlsx", response_class=Response)
async def export_overtime_xlsx(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
    department_id: Annotated[UUID | None, Query(alias="departmentId")] = None,
    overtime_status: Annotated[
        OvertimeRequestStatus | None, Query(alias="status")
    ] = None,
    start_at_from: Annotated[datetime | None, Query(alias="startAtFrom")] = None,
    start_at_to: Annotated[datetime | None, Query(alias="startAtTo")] = None,
) -> Response:
    content = await HrReportService(session).overtime(
        principal,
        search=search,
        department_id=department_id,
        overtime_status=overtime_status,
        start_at_from=start_at_from,
        start_at_to=start_at_to,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return _xlsx_response(content, "hr-overtime.xlsx")


@router.post(
    "/employees",
    response_model=SuccessEnvelope[EmployeeData],
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    payload: CreateEmployeeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EmployeeData]:
    data = await HrService(session).create_employee(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("/employees/{employee_id}", response_model=SuccessEnvelope[EmployeeData])
async def get_employee(
    employee_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EmployeeData]:
    data = await HrService(session).get_employee(principal, employee_id)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.patch("/employees/{employee_id}", response_model=SuccessEnvelope[EmployeeData])
async def update_employee(
    employee_id: UUID,
    payload: UpdateEmployeeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EmployeeData]:
    data = await HrService(session).update_employee(
        principal,
        employee_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/payroll-periods",
    response_model=PaginatedSuccessEnvelope[list[PayrollPeriodData]],
)
async def list_payroll_periods(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    worksite_id: Annotated[UUID | None, Query(alias="worksiteId")] = None,
    period_month: Annotated[date | None, Query(alias="periodMonth")] = None,
) -> PaginatedSuccessEnvelope[list[PayrollPeriodData]]:
    rows, total = await PayrollService(session).list_periods(
        principal,
        page=page,
        page_size=page_size,
        worksite_id=worksite_id,
        period_month=period_month,
    )
    _private_location_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/payroll-periods",
    response_model=SuccessEnvelope[PayrollPeriodData],
    status_code=status.HTTP_201_CREATED,
)
async def create_payroll_period(
    payload: CreatePayrollPeriodRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PayrollPeriodData]:
    data = await PayrollService(session).create_period(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/payroll-periods/{payroll_period_id}",
    response_model=SuccessEnvelope[PayrollPeriodDetailData],
)
async def get_payroll_period(
    payroll_period_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PayrollPeriodDetailData]:
    data = await PayrollService(session).get_period(principal, payroll_period_id)
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.patch(
    "/payroll-periods/{payroll_period_id}/entries/{payroll_entry_id}",
    response_model=SuccessEnvelope[PayrollEntryData],
)
async def update_payroll_entry(
    payroll_period_id: UUID,
    payroll_entry_id: UUID,
    payload: UpdatePayrollEntryRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PayrollEntryData]:
    data = await PayrollService(session).update_entry(
        principal,
        payroll_period_id,
        payroll_entry_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/payroll-periods/{payroll_period_id}/calculations",
    response_model=SuccessEnvelope[list[PayrollEntryData]],
)
async def recalculate_payroll_period(
    payroll_period_id: UUID,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[PayrollEntryData]]:
    rows = await PayrollService(session).recalculate_period_data(
        principal,
        payroll_period_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=list(rows), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/payroll-periods/{payroll_period_id}/confirmation",
    response_model=SuccessEnvelope[PayrollPeriodData],
)
async def confirm_payroll_period(
    payroll_period_id: UUID,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PayrollPeriodData]:
    data = await PayrollService(session).confirm_period(
        principal,
        payroll_period_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/payroll-periods/{payroll_period_id}/payment",
    response_model=SuccessEnvelope[PayrollPeriodData],
)
async def mark_payroll_period_paid(
    payroll_period_id: UUID,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PayrollPeriodData]:
    data = await PayrollService(session).mark_period_paid(
        principal,
        payroll_period_id,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_location_response(response)
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )
