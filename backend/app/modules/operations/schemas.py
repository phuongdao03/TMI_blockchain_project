from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.operations.job_models import JobAttemptStatus, JobExecutionStatus


class ReviewerWorkloadData(BaseModel):
    reviewer_email: str = Field(alias="reviewerEmail")
    active_assignments: int = Field(alias="activeAssignments")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class OperationsMetricsData(BaseModel):
    dossier_funnel: dict[str, int] = Field(alias="dossierFunnel")
    overdue_reviews: int = Field(alias="overdueReviews")
    reviewer_workload: list[ReviewerWorkloadData] = Field(alias="reviewerWorkload")
    payment_failures: int = Field(alias="paymentFailures")
    blockchain_failures: int = Field(alias="blockchainFailures")
    public_catalog_cache_hit_ratio: float = Field(alias="publicCatalogCacheHitRatio")
    public_catalog_cache_operations: dict[str, int] = Field(
        alias="publicCatalogCacheOperations"
    )
    job_status_counts: dict[str, int] = Field(alias="jobStatusCounts")
    oldest_queued_job_age_seconds: int = Field(alias="oldestQueuedJobAgeSeconds")
    job_retry_failures: int = Field(alias="jobRetryFailures")
    dead_lettered_jobs_by_task: dict[str, int] = Field(alias="deadLetteredJobsByTask")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class JobAttemptData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    attempt_no: int = Field(alias="attemptNo")
    status: JobAttemptStatus
    safe_error_code: str | None = Field(alias="safeErrorCode")
    started_at: datetime = Field(alias="startedAt")
    finished_at: datetime | None = Field(alias="finishedAt")


class JobSummaryData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    task_name: str = Field(alias="taskName")
    queue_name: str = Field(alias="queueName")
    resource_type: str = Field(alias="resourceType")
    resource_id: str = Field(alias="resourceId")
    status: JobExecutionStatus
    total_attempts: int = Field(alias="totalAttempts")
    max_attempts: int = Field(alias="maxAttempts")
    replay_count: int = Field(alias="replayCount")
    version: int
    scheduled_at: datetime = Field(alias="scheduledAt")
    last_error_code: str | None = Field(alias="lastErrorCode")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class JobDetailData(JobSummaryData):
    correlation_id: str = Field(alias="correlationId")
    intent: dict[str, object]
    cancel_requested_at: datetime | None = Field(alias="cancelRequestedAt")
    completed_at: datetime | None = Field(alias="completedAt")
    attempts: list[JobAttemptData]


class JobActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    expected_version: Annotated[int, Field(alias="expectedVersion", ge=1)]
    reason: Annotated[str, Field(min_length=10, max_length=500)]
