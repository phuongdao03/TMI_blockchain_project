from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html import escape
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.blockchain import router as blockchain_router
from app.api.v1.certificate_revocations import router as certificate_revocations_router
from app.api.v1.certificate_version_requests import (
    router as certificate_version_requests_router,
)
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
from app.api.v1.staff_accounts import router as staff_accounts_router
from app.api.v1.staff_invitations import router as staff_invitations_router
from app.api.v1.users import router as users_router
from app.api.v1.voting import router as voting_router
from app.api.v1.voting_admin import router as voting_admin_router
from app.api.v1.voting_me import router as voting_me_router
from app.api.v1.voting_public import router as voting_public_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.core.health import DependencyProbe, HealthService
from app.core.logging import configure_logging
from app.core.middleware import (
    PreviewModeMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.probes import AnvilProbe, RedisProbe


def _build_health_service(settings: Settings) -> HealthService:
    probes: dict[str, DependencyProbe] = {
        "redis": RedisProbe(
            url=settings.redis_url,
            timeout_seconds=settings.readiness_timeout_seconds,
        )
    }
    if settings.business_workflows_enabled:
        probes["anvil"] = AnvilProbe(
            url=settings.anvil_rpc_url,
            timeout_seconds=settings.readiness_timeout_seconds,
        )

    return HealthService(probes)


def _render_api_docs(schema: dict[str, Any]) -> str:
    """Render a CDN-free API index so /docs still works in restricted networks."""
    rows: list[str] = []
    for path, operations in sorted(schema.get("paths", {}).items()):
        for method, operation in sorted(operations.items()):
            if method not in {"get", "post", "put", "patch", "delete", "options"}:
                continue
            tags = operation.get("tags") or ["other"]
            summary = operation.get("summary") or operation.get("operationId") or ""
            rows.append(
                "<tr>"
                f"<td><span class='method method-{escape(method)}'>"
                f"{escape(method.upper())}</span></td>"
                f"<td><code>{escape(path)}</code></td>"
                f"<td>{escape(str(tags[0]))}</td>"
                f"<td>{escape(str(summary))}</td>"
                "</tr>"
            )
    title = escape(str(schema.get("info", {}).get("title", "API")))
    version = escape(str(schema.get("info", {}).get("version", "")))
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · API docs</title>
<style>
:root {{
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}}
body {{ margin: 0; background: #0c0d10; color: #e8e9ed; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 48px 24px 72px; }}
.eyebrow {{
  color: #f2bd7c; letter-spacing: .16em; text-transform: uppercase;
  font-size: 12px; font-weight: 700;
}}
h1 {{ margin: 12px 0 8px; font-size: clamp(28px, 5vw, 48px); letter-spacing: -.04em; }}
p {{ color: #a9adb8; max-width: 700px; line-height: 1.6; }}
.links {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 28px 0; }}
a {{
  color: #f5c898; text-decoration: none; border: 1px solid #363942;
  padding: 10px 14px; border-radius: 10px;
}}
a:hover {{ border-color:#f5c898; }}
 .table-wrap {{
  overflow: auto; border: 1px solid #292c34; border-radius: 16px;
  background: #121419;
}}
table {{ width: 100%; border-collapse: collapse; min-width: 760px; }}
th, td {{
  padding: 14px 16px; border-bottom: 1px solid #292c34;
  text-align: left; vertical-align: top;
}}
th {{
  color: #8e94a3; font-size: 12px; letter-spacing: .1em;
  text-transform: uppercase;
}}
tr:last-child td {{ border-bottom: 0; }}
code {{ color: #d9dde7; font-family: ui-monospace, SFMono-Regular, monospace; }}
.method {{
  display: inline-block; min-width: 54px; padding: 4px 7px;
  border-radius: 6px; font-size: 11px; font-weight: 800; text-align: center;
}}
.method-get {{ background: #163a2b; color: #78e3a7; }}
.method-post {{ background: #3b2f16; color: #f6c66f; }}
.method-put, .method-patch {{ background: #202b45; color: #91b7ff; }}
.method-delete {{ background: #411f27; color: #ff9eae; }}
footer {{ margin-top: 18px; color: #6e7380; font-size: 13px; }}
</style>
</head>
<body><main>
<div class="eyebrow">TMI Certificate · API reference</div>
<h1>{title}</h1>
<p>Danh sách endpoint được hiển thị trực tiếp từ OpenAPI schema.
Trang này không phụ thuộc JavaScript hoặc CDN bên ngoài.</p>
<div class="links">
  <a href="/openapi.json">Tải OpenAPI JSON</a><a href="/redoc">Mở ReDoc</a>
</div>
<div class="table-wrap"><table><thead><tr>
<th>Method</th><th>Endpoint</th><th>Nhóm</th><th>Mô tả</th>
</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<footer>{len(rows)} endpoint · version {version}</footer>
</main></body></html>"""


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
        title="Đề cử Tinh Hoa Việt API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=(
            None if resolved_settings.app_env == "production" else "/openapi.json"
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    if resolved_settings.app_env != "production":

        @app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
        async def api_docs() -> HTMLResponse:
            return HTMLResponse(_render_api_docs(app.openapi()))

        @app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
        async def api_redoc_redirect() -> HTMLResponse:
            return HTMLResponse(
                '<!doctype html><meta http-equiv="refresh" content="0; url=/docs">'
                '<a href="/docs">Open API docs</a>'
            )

    if resolved_settings.release_mode == "preview":
        app.add_middleware(PreviewModeMiddleware)
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
    app.include_router(certificate_version_requests_router)
    app.include_router(certificate_revocations_router)
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
    app.include_router(staff_accounts_router)
    app.include_router(staff_invitations_router)
    app.include_router(search_discovery_router)
    app.include_router(users_router)
    app.include_router(voting_admin_router)
    app.include_router(voting_router)
    app.include_router(voting_me_router)
    app.include_router(voting_public_router)
    return app


app = create_application()
