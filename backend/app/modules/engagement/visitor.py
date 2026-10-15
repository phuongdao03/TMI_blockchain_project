import hashlib
import hmac
import secrets

from fastapi import Request, Response

from app.modules.engagement.errors import EngagementUnavailableError


class EngagementVisitorContext:
    def __init__(self, *, secret: str) -> None:
        self._secret = secret.encode()

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        return f"{token}.{self._signature(token)}"

    def is_valid(self, value: str | None) -> bool:
        if value is None:
            return False
        token, separator, signature = value.partition(".")
        return (
            bool(separator)
            and len(token) == 43
            and hmac.compare_digest(signature, self._signature(token))
        )

    def digest(self, value: str) -> str:
        return hmac.new(
            self._secret,
            value.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _signature(self, token: str) -> str:
        return hmac.new(
            self._secret,
            token.encode(),
            hashlib.sha256,
        ).hexdigest()


def get_or_issue_engagement_visitor(request: Request, response: Response) -> str:
    settings = request.app.state.settings
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        raise EngagementUnavailableError()
    visitor_context = EngagementVisitorContext(secret=secret.get_secret_value())
    cookie_visitor = request.cookies.get(settings.engagement_visitor_cookie_name)
    if visitor_context.is_valid(cookie_visitor):
        assert cookie_visitor is not None
        return cookie_visitor
    visitor = visitor_context.issue()
    response.set_cookie(
        key=settings.engagement_visitor_cookie_name,
        value=visitor,
        httponly=True,
        secure=settings.app_env != "local",
        samesite="lax",
        max_age=settings.engagement_view_dedupe_ttl_seconds,
        path="/",
    )
    return visitor
