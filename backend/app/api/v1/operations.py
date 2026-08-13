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
    SessionDependency,
)
from app.modules.operations.job_models import JobExecution, JobExecutionStatus
from app.modules.operations.job_operations_service import JobOperationsService
from app.modules.operations.schemas import (
    JobActionRequest,
    JobAttemptData,
    JobDetailData,
    JobSummaryData,
    OperationsMetricsData,
    ReviewerWorkloadData,
)
from app.modules.operations.service import OperationsService
from app.workers.dispatcher import replay_durable_job

router = APIRouter(prefix="/api/v1/admin/operations", tags=["operations"])


def _job_detail(
    job: JobExecution,
    attempts: list[JobAttemptData],
) -> JobDetailData:
    return JobDetailData(
        **JobSummaryData.model_validate(job).model_dump(),
        correlationId=job.correlation_id,
        intent=dict(job.intent_json),
        cancelRequestedAt=job.cancel_requested_at,
        completedAt=job.completed_at,
        attempts=attempts,
    )


@router.get("/metrics", response_model=SuccessEnvelope[OperationsMetricsData])
async def metrics(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[OperationsMetricsData]:
    result = await OperationsService(session).metrics(principal)
    return SuccessEnvelope(
        data=OperationsMetricsData(
            dossierFunnel=result.dossier_funnel,
            overdueReviews=result.overdue_reviews,
            reviewerWorkload=[
                ReviewerWorkloadData(
                    reviewerEmail=reviewer_email,
                    activeAssignments=count,
                )
                for reviewer_email, count in result.reviewer_workload
            ],
            paymentFailures=result.payment_failures,
            blockchainFailures=result.blockchain_failures,
            publicCatalogCacheHitRatio=result.public_catalog_cache_hit_ratio,
            publicCatalogCacheOperations=result.public_catalog_cache_operations,
            jobStatusCounts=result.job_status_counts,
            oldestQueuedJobAgeSeconds=result.oldest_queued_job_age_seconds,
            jobRetryFailures=result.job_retry_failures,
            deadLetteredJobsByTask=result.dead_lettered_jobs_by_task,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/jobs", response_model=PaginatedSuccessEnvelope[list[JobSummaryData]])
async def list_jobs(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    status: JobExecutionStatus | None = None,
    task_name: Annotated[
        str | None,
        Query(alias="taskName", min_length=1, max_length=128),
    ] = None,
) -> PaginatedSuccessEnvelope[list[JobSummaryData]]:
    rows, total = await JobOperationsService(session).list_jobs(
        principal,
        page=page,
        page_size=page_size,
        status=status.value if status is not None else None,
        task_name=task_name,
    )
    return PaginatedSuccessEnvelope(
        data=[JobSummaryData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/jobs/{job_id}", response_model=SuccessEnvelope[JobDetailData])
async def job_detail(
    job_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[JobDetailData]:
    job, attempts = await JobOperationsService(session).detail(principal, job_id)
    return SuccessEnvelope(
        data=_job_detail(
            job,
            [JobAttemptData.model_validate(attempt) for attempt in attempts],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/jobs/{job_id}/replays",
    response_model=SuccessEnvelope[JobDetailData],
)
async def replay_job(
    job_id: UUID,
    payload: JobActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[JobDetailData]:
    service = JobOperationsService(session, replay_publisher=replay_durable_job)
    await service.replay_job(
        principal,
        job_id,
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    job, attempts = await service.detail(principal, job_id)
    return SuccessEnvelope(
        data=_job_detail(
            job,
            [JobAttemptData.model_validate(attempt) for attempt in attempts],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/jobs/{job_id}/cancellations",
    response_model=SuccessEnvelope[JobDetailData],
)
async def cancel_job(
    job_id: UUID,
    payload: JobActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[JobDetailData]:
    service = JobOperationsService(session)
    await service.cancel_job(
        principal,
        job_id,
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    job, attempts = await service.detail(principal, job_id)
    return SuccessEnvelope(
        data=_job_detail(
            job,
            [JobAttemptData.model_validate(attempt) for attempt in attempts],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
