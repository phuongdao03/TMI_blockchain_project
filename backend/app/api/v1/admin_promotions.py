import csv
from datetime import datetime
from io import StringIO
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.audit.models import AuditLog
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.promotions.admin_access import require_promotion_access
from app.modules.promotions.admin_service import (
    SERVICES,
    CampaignService,
    campaign_data,
)
from app.modules.promotions.rate_limit import enforce_promotion_rate_limit
from app.modules.promotions.reporting import analytics
from app.modules.promotions.schemas import CampaignData, CampaignInput

router = APIRouter(
    prefix="/api/v1/admin/promotions",
    tags=["promotion-management"],
    dependencies=[Depends(enforce_promotion_rate_limit)],
)


def get_campaign_service(session: SessionDependency) -> CampaignService:
    return CampaignService(session)


Service = Annotated[CampaignService, Depends(get_campaign_service)]


def envelope(request: Request, data: Any) -> SuccessEnvelope[Any]:
    return SuccessEnvelope(
        data=data, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("")
async def campaigns(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    search: str = Query("", max_length=100),
    status: str | None = None,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    return envelope(
        request,
        await service.list(
            page=page, page_size=page_size, search=search, status=status
        ),
    )


@router.get("/services")
async def services(
    request: Request, principal: CurrentPrincipalDependency
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    return envelope(request, SERVICES)


@router.get("/settings")
async def settings(
    request: Request, principal: CurrentPrincipalDependency
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    configured = get_settings()
    return envelope(
        request,
        {
            "mediaMaxBytes": configured.promotion_media_max_bytes,
            "maxImageBytes": configured.promotion_media_max_bytes,
            "mediaMaxPixels": configured.promotion_media_max_pixels,
            "timezone": "Asia/Ho_Chi_Minh",
            "currency": "VND",
            "eligibleRoles": ["USER"],
            "excludeEmployees": True,
            "excludedEmployees": True,
            "allowCashConversion": False,
            "stackingDefault": "NONE",
            "maxPerAccountPerCampaign": 100,
            "defaultPerAccountPerCampaign": 1,
            "budgetWarningThresholds": [50, 80, 95, 100],
        },
    )


@router.get("/analytics")
async def report(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
    campaign_id: Annotated[UUID | None, Query(alias="campaignId")] = None,
    start: Annotated[datetime | None, Query(alias="startDate")] = None,
    end: Annotated[datetime | None, Query(alias="endDate")] = None,
    service_code: Annotated[str | None, Query(alias="serviceCode")] = None,
    status: str | None = None,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    return envelope(
        request,
        await analytics(service.session, campaign_id, start, end, service_code, status),
    )


def transaction_csv(data: dict[str, object]) -> Response:
    output = StringIO()
    columns = [
        "id",
        "orderReference",
        "orderId",
        "campaignId",
        "voucherId",
        "serviceCode",
        "status",
        "originalVnd",
        "discountVnd",
        "payableVnd",
        "revenueVnd",
        "createdAt",
        "redeemedAt",
    ]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    rows = data["transactions"]
    if isinstance(rows, list):
        writer.writerows(item for item in rows if isinstance(item, dict))
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=promotion-transactions.csv",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/analytics.csv")
async def export_report(
    principal: CurrentPrincipalDependency,
    service: Service,
    campaign_id: Annotated[UUID | None, Query(alias="campaignId")] = None,
    start: Annotated[datetime | None, Query(alias="startDate")] = None,
    end: Annotated[datetime | None, Query(alias="endDate")] = None,
    service_code: Annotated[str | None, Query(alias="serviceCode")] = None,
    status: str | None = None,
) -> Response:
    require_promotion_access(principal, write=False)
    return transaction_csv(
        await analytics(
            service.session,
            campaign_id,
            start,
            end,
            service_code,
            status,
            transaction_limit=None,
        )
    )


@router.get("/audit")
async def audit(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    where = AuditLog.action.like("promotion.%")
    count = await service.session.scalar(
        select(func.count()).select_from(AuditLog).where(where)
    )
    rows = await service.session.scalars(
        select(AuditLog)
        .where(where)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return envelope(
        request,
        {
            "items": [
                {
                    "id": str(row.id),
                    "action": row.action,
                    "actorId": str(row.actor_user_id) if row.actor_user_id else None,
                    "actorUserId": str(row.actor_user_id)
                    if row.actor_user_id
                    else None,
                    "campaignId": row.resource_id,
                    "entityId": row.resource_id,
                    "before": row.before_json,
                    "after": row.after_json,
                    "createdAt": row.created_at.isoformat(),
                }
                for row in rows
            ],
            "page": page,
            "pageSize": page_size,
            "total": count or 0,
        },
    )


@router.post("", response_model=SuccessEnvelope[CampaignData])
async def create(
    payload: CampaignInput,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: Service,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal)
    return envelope(
        request, campaign_data(await service.save(payload, principal.user_id))
    )


@router.get("/{campaign_id}", response_model=SuccessEnvelope[CampaignData])
async def detail(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    return envelope(request, campaign_data(await service.required(campaign_id)))


@router.patch("/{campaign_id}", response_model=SuccessEnvelope[CampaignData])
async def update(
    campaign_id: UUID,
    payload: CampaignInput,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: Service,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal)
    return envelope(
        request,
        campaign_data(await service.save(payload, principal.user_id, campaign_id)),
    )


@router.post("/{campaign_id}/copy", response_model=SuccessEnvelope[CampaignData])
async def copy(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: Service,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal)
    return envelope(
        request, campaign_data(await service.copy(campaign_id, principal.user_id))
    )


@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
    start: Annotated[datetime | None, Query(alias="startDate")] = None,
    end: Annotated[datetime | None, Query(alias="endDate")] = None,
) -> SuccessEnvelope[Any]:
    require_promotion_access(principal, write=False)
    await service.required(campaign_id)
    return envelope(request, await analytics(service.session, campaign_id, start, end))


@router.get("/{campaign_id}/redemptions")
async def redemptions(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: Service,
    format: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, alias="pageSize", ge=1, le=100),
) -> Any:
    require_promotion_access(principal, write=False)
    await service.required(campaign_id)
    data = await analytics(
        service.session,
        campaign_id,
        transaction_limit=None if format == "csv" else page_size,
        transaction_offset=0 if format == "csv" else (page - 1) * page_size,
    )
    if format != "csv":
        return envelope(
            request,
            {
                "items": data["transactions"],
                "page": page,
                "pageSize": page_size,
                "total": data["transactionCount"],
            },
        )
    return transaction_csv(data)


@router.post("/{campaign_id}/publish", response_model=SuccessEnvelope[CampaignData])
@router.post("/{campaign_id}/pause", response_model=SuccessEnvelope[CampaignData])
@router.post("/{campaign_id}/end", response_model=SuccessEnvelope[CampaignData])
@router.post("/{campaign_id}/archive", response_model=SuccessEnvelope[CampaignData])
async def transition(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: Service,
) -> SuccessEnvelope[Any]:
    action = request.url.path.rsplit("/", 1)[-1]
    require_promotion_access(principal)
    return envelope(
        request,
        campaign_data(await service.transition(campaign_id, action, principal.user_id)),
    )
