from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.blockchain import router as blockchain_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.cms import router as cms_router
from app.api.v1.content_reports import router as content_reports_router
from app.api.v1.council import router as council_router
from app.api.v1.dossiers import router as dossiers_router
from app.api.v1.engagement import router as engagement_router
from app.api.v1.health import router as health_router
from app.api.v1.media import router as media_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.operations import router as operations_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.payments import router as payments_router
from app.api.v1.public import router as public_router
from app.api.v1.public_works_admin import router as public_works_admin_router
from app.api.v1.ranking_admin import router as ranking_admin_router
from app.api.v1.ranking_admin_publish import router as ranking_admin_publish_router
from app.api.v1.ranking_public import router as ranking_public_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.search import router as search_router
from app.api.v1.search_discovery import router as search_discovery_router
from app.api.v1.search_history import router as search_history_router
from app.api.v1.share_redirect import router as share_redirect_router
from app.api.v1.users import router as users_router
from app.api.v1.voting import router as voting_router
from app.api.v1.voting_admin import router as voting_admin_router
from app.api.v1.voting_me import router as voting_me_router
from app.api.v1.voting_public import router as voting_public_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.health import HealthService
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.probes import AnvilProbe, RedisProbe


def _build_health_service(settings: Settings) -> HealthService:
    return HealthService(
        {
            "anvil": AnvilProbe(
                url=settings.anvil_rpc_url,
                timeout_seconds=settings.readiness_timeout_seconds,
            ),
            "redis": RedisProbe(
                url=settings.redis_url,
                timeout_seconds=settings.readiness_timeout_seconds,
            ),
        }
    )


def create_application(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()

    # Source: https://fastapi.tiangolo.com/advanced/events/#lifespan
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        active_health_service = health_service or _build_health_service(
            resolved_settings
        )
        application.state.health_service = active_health_service
        try:
            yield
        finally:
            await active_health_service.close()

    configure_logging(
        service=resolved_settings.service_name,
        environment=resolved_settings.app_env,
        level=resolved_settings.log_level,
    )

    app = FastAPI(
        title="TMI Blockchain Certificate Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "Idempotency-Key",
            "X-CSRF-Token",
            "X-Request-ID",
        ],
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        production=resolved_settings.app_env == "production",
    )
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(blockchain_router)
    app.include_router(council_router)
    app.include_router(cms_router)
    app.include_router(certificates_router)
    app.include_router(content_reports_router)
    app.include_router(dossiers_router)
    app.include_router(engagement_router)
    app.include_router(media_router)
    app.include_router(organizations_router)
    app.include_router(notifications_router)
    app.include_router(operations_router)
    app.include_router(payments_router)
    app.include_router(public_router)
    app.include_router(public_works_admin_router)
    app.include_router(ranking_public_router)
    app.include_router(ranking_admin_router)
    app.include_router(ranking_admin_publish_router)
    app.include_router(reviews_router)
    app.include_router(search_router)
    app.include_router(search_history_router)
    app.include_router(share_redirect_router)
    app.include_router(search_discovery_router)
    app.include_router(users_router)
    app.include_router(voting_admin_router)
    app.include_router(voting_router)
    app.include_router(voting_me_router)
    app.include_router(voting_public_router)
    return app


app = create_application()
