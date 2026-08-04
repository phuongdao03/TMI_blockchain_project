from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import UUID

import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.qr_service import QrShareLinkService
from app.modules.public.detail_service import PublicWorkDetailService
from app.modules.public.models import PublicWorkVisibility


class PublicShareConfigurationError(ValueError):
    """Raised when the configured public origin is unsafe for a QR payload."""


class PublicQrRenderer(Protocol):
    def render(self, payload: str) -> bytes: ...


class QrCodePngRenderer:
    def render(self, payload: str) -> bytes:
        image = qrcode.make(payload)
        buffer = BytesIO()
        image.save(buffer)
        return buffer.getvalue()


@dataclass(frozen=True, slots=True)
class RenderedPublicQr:
    png: bytes
    payload: str


def canonical_public_work_url(
    public_base_url: str,
    slug: str,
    *,
    allow_local_http: bool,
) -> str:
    parsed = urlsplit(public_base_url)
    hostname = parsed.hostname
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    is_allowed_http = (
        parsed.scheme == "http" and allow_local_http and hostname in local_hosts
    )
    if (
        (parsed.scheme != "https" and not is_allowed_http)
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise PublicShareConfigurationError(
            "APP_BASE_URL must be an HTTPS origin (HTTP localhost is local-only)."
        )
    encoded_slug = quote(slug, safe="-._~")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"/tai-san/{encoded_slug}", "", "")
    )


class PublicQrCodeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        public_base_url: str,
        allow_local_http: bool,
        share_links: QrShareLinkService,
        renderer: PublicQrRenderer | None = None,
    ) -> None:
        self._detail = PublicWorkDetailService(session)
        self._public_base_url = public_base_url
        self._allow_local_http = allow_local_http
        self._renderer = renderer or QrCodePngRenderer()
        self._share_links = share_links

    async def render(self, slug: str) -> RenderedPublicQr | None:
        detail = await self._detail.get(slug)
        if detail is None or detail.visibility is not PublicWorkVisibility.PUBLIC:
            return None
        canonical = canonical_public_work_url(
            self._public_base_url,
            detail.canonical_slug,
            allow_local_http=self._allow_local_http,
        )
        parsed = urlsplit(canonical)
        token = await self._share_links.token_for_work(detail.id)
        payload = urlunsplit(
            (parsed.scheme, parsed.netloc, f"/r/{quote(token, safe='-._~')}", "", "")
        )
        return RenderedPublicQr(
            png=self._renderer.render(payload),
            payload=payload,
        )

    async def resolve_redirect(self, token: str, *, visitor: str) -> str:
        return await self._share_links.resolve_redirect(token, visitor=visitor)

    async def revoke(self, principal: AuthPrincipal, *, public_work_id: UUID) -> bool:
        return await self._share_links.revoke(
            principal,
            public_work_id=public_work_id,
        )
