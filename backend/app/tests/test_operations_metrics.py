import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.operations.service import OperationsService


class FixedMetricsRepository:
    async def dossier_funnel(self) -> dict[str, int]:
        return {"DRAFT": 4, "APPROVED": 2}

    async def overdue_reviews(self, now: object) -> int:
        del now
        return 3

    async def reviewer_workload(self) -> tuple[tuple[str, int], ...]:
        return (("reviewer-1", 5),)

    async def payment_failures(self) -> int:
        return 1

    async def blockchain_failures(self) -> int:
        return 2


def _principal(role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(), session_id=uuid4(), email="ops@tmigroup.vn", roles=(role,)
    )


def test_operations_metrics_are_server_aggregated_and_role_protected() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with AsyncSession(engine) as session:
            service = OperationsService(session, repository=FixedMetricsRepository())
            metrics = await service.metrics(_principal("SUPER_ADMIN"))
            assert metrics.dossier_funnel == {"DRAFT": 4, "APPROVED": 2}
            assert metrics.overdue_reviews == 3
            assert metrics.payment_failures == 1
            assert metrics.blockchain_failures == 2
            assert 0.0 <= metrics.public_catalog_cache_hit_ratio <= 1.0
            assert isinstance(metrics.public_catalog_cache_operations, dict)

            with pytest.raises(DomainError) as error:
                await service.metrics(_principal("APPLICANT"))
            assert error.value.code == "OPERATIONS_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())
