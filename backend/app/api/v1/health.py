from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.errors import ServiceNotReadyError
from app.core.health import HealthService
from app.core.schemas import (
    ErrorEnvelope,
    HealthData,
    ReadinessData,
    ResponseMeta,
    SuccessEnvelope,
)

router = APIRouter(tags=["health"])


def get_health_service(request: Request) -> HealthService:
    service: HealthService = request.app.state.health_service
    return service


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


@router.get("/health", response_model=SuccessEnvelope[HealthData])
async def health(request: Request) -> SuccessEnvelope[HealthData]:
    return SuccessEnvelope(
        data=HealthData(service="backend", status="ok"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/ready",
    response_model=SuccessEnvelope[ReadinessData],
    responses={
        503: {
            "description": "One or more dependencies are unavailable.",
            "model": ErrorEnvelope,
        }
    },
)
async def readiness(
    request: Request,
    health_service: HealthServiceDependency,
) -> SuccessEnvelope[ReadinessData]:
    dependencies = await health_service.check_readiness()
    if "down" in dependencies.values():
        raise ServiceNotReadyError(details={"dependencies": dependencies})

    return SuccessEnvelope(
        data=ReadinessData(dependencies=dependencies, status="ready"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
