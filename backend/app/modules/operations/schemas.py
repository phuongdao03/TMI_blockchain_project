from pydantic import BaseModel, ConfigDict, Field


class ReviewerWorkloadData(BaseModel):
    user_id: str = Field(alias="userId")
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
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
