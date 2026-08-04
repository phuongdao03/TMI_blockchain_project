from fastapi import APIRouter, Request

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import CurrentPrincipalDependency, SessionDependency
from app.modules.operations.schemas import OperationsMetricsData, ReviewerWorkloadData
from app.modules.operations.service import OperationsService

router = APIRouter(prefix="/api/v1/admin/operations", tags=["operations"])


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
                ReviewerWorkloadData(userId=user_id, activeAssignments=count)
                for user_id, count in result.reviewer_workload
            ],
            paymentFailures=result.payment_failures,
            blockchainFailures=result.blockchain_failures,
            publicCatalogCacheHitRatio=result.public_catalog_cache_hit_ratio,
            publicCatalogCacheOperations=result.public_catalog_cache_operations,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
