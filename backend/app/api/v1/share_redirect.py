from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import RedirectResponse

from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.public.dependencies import enforce_public_engagement_rate_limit
from app.modules.public.publication_dependencies import PublicQrCodeServiceDependency

router = APIRouter(tags=["public-share"])
ShareTokenPath = Annotated[str, Path(min_length=43, max_length=128)]


@router.get(
    "/r/{token}",
    status_code=status.HTTP_302_FOUND,
    dependencies=[Depends(enforce_public_engagement_rate_limit)],
)
async def redirect_public_share_link(
    token: ShareTokenPath,
    request: Request,
    service: PublicQrCodeServiceDependency,
) -> RedirectResponse:
    settings = request.app.state.settings
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        raise EngagementUnavailableError()
    visitor_context = EngagementVisitorContext(secret=secret.get_secret_value())
    visitor = request.cookies.get(settings.engagement_visitor_cookie_name)
    issue_cookie = not visitor_context.is_valid(visitor)
    if issue_cookie:
        visitor = visitor_context.issue()
    assert visitor is not None
    slug = await service.resolve_redirect(token, visitor=visitor)
    response = RedirectResponse(
        url=f"/tai-san/{slug}",
        status_code=status.HTTP_302_FOUND,
        headers={"Referrer-Policy": "same-origin"},
    )
    if issue_cookie:
        response.set_cookie(
            key=settings.engagement_visitor_cookie_name,
            value=visitor,
            httponly=True,
            secure=settings.app_env != "local",
            samesite="lax",
            max_age=settings.engagement_view_dedupe_ttl_seconds,
            path="/",
        )
    return response
