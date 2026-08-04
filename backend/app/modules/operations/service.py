from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.operations.repository import OperationsRepository
from app.modules.public.telemetry import (
    CatalogMetricSnapshot,
    InProcessCatalogTelemetry,
    catalog_telemetry,
)

OPERATIONS_ROLES = frozenset({"FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"})


@dataclass(frozen=True, slots=True)
class OperationsMetrics:
    dossier_funnel: dict[str, int]
    overdue_reviews: int
    reviewer_workload: tuple[tuple[str, int], ...]
    payment_failures: int
    blockchain_failures: int
    public_catalog_cache_hit_ratio: float
    public_catalog_cache_operations: dict[str, int]


class OperationsReader(Protocol):
    async def dossier_funnel(self) -> dict[str, int]: ...

    async def overdue_reviews(self, now: datetime) -> int: ...

    async def reviewer_workload(self) -> tuple[tuple[str, int], ...]: ...

    async def payment_failures(self) -> int: ...

    async def blockchain_failures(self) -> int: ...


class OperationsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: OperationsReader | None = None,
        catalog_metrics: InProcessCatalogTelemetry = catalog_telemetry,
    ) -> None:
        self._session = session
        self._repository = repository or OperationsRepository(session)
        self._catalog_metrics = catalog_metrics

    async def metrics(self, principal: AuthPrincipal) -> OperationsMetrics:
        if OPERATIONS_ROLES.isdisjoint(principal.roles):
            raise DomainError(
                code="OPERATIONS_FORBIDDEN",
                message="Operations metrics are forbidden.",
                status_code=403,
            )
        async with self._session.begin():
            catalog = self._catalog_metrics.snapshot()
            return await self._result(catalog)

    async def _result(self, catalog: CatalogMetricSnapshot) -> OperationsMetrics:
        return OperationsMetrics(
            dossier_funnel=await self._repository.dossier_funnel(),
            overdue_reviews=await self._repository.overdue_reviews(datetime.now(UTC)),
            reviewer_workload=await self._repository.reviewer_workload(),
            payment_failures=await self._repository.payment_failures(),
            blockchain_failures=await self._repository.blockchain_failures(),
            public_catalog_cache_hit_ratio=catalog.cache_hit_ratio,
            public_catalog_cache_operations=catalog.cache_operations,
        )
