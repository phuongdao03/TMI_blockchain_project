import csv
from io import StringIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.db.session import get_session_factory
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.promotions.admin_access import require_promotion_access
from app.modules.promotions.distribution import PromotionDistributionService
from app.modules.promotions.distribution_models import PromotionDistributionJob
from app.modules.promotions.models import VoucherClaim
from app.modules.promotions.rate_limit import enforce_promotion_rate_limit

router = APIRouter(
    prefix="/api/v1/admin/promotions",
    tags=["promotion-distribution"],
    dependencies=[Depends(enforce_promotion_rate_limit)],
)


class DistributionInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    user_ids: list[str] | None = Field(default=None, alias="userIds", max_length=50_000)


class IssueInput(DistributionInput):
    reason: str = Field(min_length=5, max_length=255)
    idempotency_key: str = Field(alias="idempotencyKey", min_length=8, max_length=128)
    preview_token: UUID = Field(alias="previewToken")


def get_distribution_service(
    session: SessionDependency,
) -> PromotionDistributionService:
    return PromotionDistributionService(session)


ServiceDependency = Annotated[
    PromotionDistributionService, Depends(get_distribution_service)
]


def job_data(job: PromotionDistributionJob) -> dict[str, object]:
    return {
        "id": str(job.id),
        "campaignId": str(job.campaign_id),
        "status": job.status,
        "total": job.total,
        "processed": job.cursor,
        "issuedCount": job.issued_count,
        "issued": job.issued_count,
        "skippedCount": job.skipped_count,
        "failedCount": job.failed_count,
        "failed": job.failed_count,
        "errors": [
            {**item, "reason": item.get("reason", item.get("code", ""))}
            for item in job.errors_json
        ],
        "createdAt": job.created_at.isoformat(),
        "updatedAt": job.updated_at.isoformat(),
    }


async def drain_distribution_job(job_id: UUID) -> None:
    # The persisted job is the source of truth. A process interruption leaves
    # its cursor available to the scheduled worker, without losing a batch.
    for _ in range(20):
        async with get_session_factory()() as session:
            if await PromotionDistributionService(session).run_batch(job_id):
                return


@router.post("/{campaign_id}/audience-preview")
async def audience_preview(
    campaign_id: UUID,
    payload: DistributionInput,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal)
    data = await service.preview(
        campaign_id, actor_id=principal.user_id, user_ids=payload.user_ids
    )
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post("/{campaign_id}/audience-csv")
async def audience_csv(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal)
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 3_000_000:
            raise DomainError(
                code="PROMOTION_CSV_TOO_LARGE",
                message="CSV vượt giới hạn 3 MB.",
                status_code=413,
            )
    try:
        rows = list(csv.reader(StringIO(bytes(content).decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error) as error:
        raise DomainError(
            code="PROMOTION_CSV_INVALID",
            message="CSV phải có mã hóa UTF-8 và cột userId.",
            status_code=422,
        ) from error
    if (
        not rows
        or len(rows) > 50_001
        or not rows[0]
        or rows[0][0].strip().casefold() not in {"userid", "user_id", "id"}
    ):
        raise DomainError(
            code="PROMOTION_CSV_INVALID",
            message="Cần cột đầu userId, tối đa 50.000 dòng.",
            status_code=422,
        )
    user_ids = [row[0].strip() if row else "" for row in rows[1:]]
    data = await service.preview(
        campaign_id, actor_id=principal.user_id, user_ids=user_ids
    )
    data["userIds"] = user_ids
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post("/{campaign_id}/issue")
async def issue(
    campaign_id: UUID,
    payload: IssueInput,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
    background: BackgroundTasks,
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal)
    job = await service.issue(
        campaign_id,
        actor_id=principal.user_id,
        user_ids=payload.user_ids,
        preview_token=payload.preview_token,
        idempotency_key=payload.idempotency_key,
        reason=payload.reason,
    )
    if job.status in {"PENDING", "RUNNING"}:
        background.add_task(drain_distribution_job, job.id)
    return SuccessEnvelope(
        data=job_data(job), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("/{campaign_id}/distribution-jobs")
async def jobs(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal, write=False)
    rows, total = await service.jobs(campaign_id, page=page, page_size=page_size)
    return SuccessEnvelope(
        data={
            "items": [job_data(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        },
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/{campaign_id}/recipient-search")
async def search_recipients(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    q: str = Query(min_length=2, max_length=120),
) -> SuccessEnvelope[dict[str, object]]:
    from app.modules.auth.models import User
    from app.modules.promotions.admin_service import CampaignService
    from app.modules.promotions.audience import recipient_eligibility
    from app.modules.promotions.schemas import PromotionPolicy

    require_promotion_access(principal)
    campaign = await CampaignService(session).required(campaign_id)
    policy = PromotionPolicy.model_validate(campaign.policy_json)
    predicates = [User.email.icontains(q.strip(), autoescape=True)]
    try:
        predicates.append(User.id == UUID(q.strip()))
    except ValueError:
        pass
    candidates = await session.scalars(
        select(User).where(or_(*predicates)).order_by(User.email).limit(20)
    )
    items = []
    for user in candidates:
        eligible, reason = await recipient_eligibility(session, user.id, policy)
        items.append(
            {
                "id": str(user.id),
                "email": user.email,
                "eligible": eligible,
                "reason": reason,
            }
        )
    return SuccessEnvelope(
        data={"items": items}, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("/{campaign_id}/recipients")
async def recipients(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal, write=False)
    total = await session.scalar(
        select(func.count())
        .select_from(VoucherClaim)
        .where(VoucherClaim.campaign_id == campaign_id)
    )
    rows = await session.scalars(
        select(VoucherClaim)
        .where(VoucherClaim.campaign_id == campaign_id)
        .order_by(VoucherClaim.claimed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return SuccessEnvelope(
        data={
            "items": [
                {
                    "id": str(row.id),
                    "userId": str(row.user_id),
                    "status": row.status,
                    "amountVnd": row.amount_vnd,
                    "claimedAt": row.claimed_at.isoformat(),
                    "expiresAt": row.expires_at.isoformat(),
                }
                for row in rows
            ],
            "total": int(total or 0),
            "page": page,
            "pageSize": page_size,
        },
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/{campaign_id}/distribution-results.csv")
async def export_distribution(
    campaign_id: UUID, principal: CurrentPrincipalDependency, session: SessionDependency
) -> object:
    from fastapi.responses import Response

    require_promotion_access(principal, write=False)
    result = StringIO()
    writer = csv.writer(result)
    writer.writerow(["voucherId", "userId", "status", "amountVnd", "claimedAt"])
    rows = await session.stream_scalars(
        select(VoucherClaim)
        .where(VoucherClaim.campaign_id == campaign_id)
        .order_by(VoucherClaim.id)
        .execution_options(yield_per=500)
    )
    async for row in rows:
        writer.writerow(
            [
                str(row.id),
                str(row.user_id),
                row.status,
                row.amount_vnd,
                row.claimed_at.isoformat(),
            ]
        )
    return Response(
        content="\ufeff" + result.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="promotion-{campaign_id}-recipients.csv"'
            ),
            "Cache-Control": "private, no-store",
        },
    )
