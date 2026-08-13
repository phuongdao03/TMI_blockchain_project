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

    async def job_status_counts(self) -> dict[str, int]:
        return {"QUEUED": 2, "DEAD_LETTERED": 1}

    async def oldest_queued_at(self):  # type: ignore[no-untyped-def]
        return None

    async def job_retry_failures(self) -> int:
        return 4

    async def dead_lettered_jobs_by_task(self) -> dict[str, int]:
        return {"blockchain.broadcast": 1}


def _principal(role: str, *permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="ops@tmigroup.vn",
        roles=(role,),
        permissions=permissions,
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
            assert metrics.job_status_counts == {"QUEUED": 2, "DEAD_LETTERED": 1}
            assert metrics.job_retry_failures == 4
            assert 0.0 <= metrics.public_catalog_cache_hit_ratio <= 1.0
            assert isinstance(metrics.public_catalog_cache_operations, dict)
            await service.metrics(_principal("AUDITOR", "operations.read"))

            with pytest.raises(DomainError) as error:
                await service.metrics(_principal("APPLICANT"))
            assert error.value.code == "OPERATIONS_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())
