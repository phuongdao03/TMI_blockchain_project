"""Branded verification mail for Firebase password accounts."""

from typing import Protocol

from app.core.errors import DomainError
from app.modules.auth.firebase_admin_gateway import FirebaseAdminError
from app.modules.auth.rate_limit import RegistrationRateLimiter
from app.modules.notifications.email import EmailGateway, EmailMessage, render_email


class VerificationIdentityGateway(Protocol):
    async def unverified_password_email(self, id_token: str) -> str: ...

    async def branded_email_verification_link(
        self, email: str, *, app_base_url: str
    ) -> str: ...


class FirebaseVerificationEmailService:
    def __init__(
        self,
        *,
        identity: VerificationIdentityGateway,
        email_gateway: EmailGateway,
        rate_limiter: RegistrationRateLimiter,
        app_base_url: str,
    ) -> None:
        self._identity = identity
        self._email_gateway = email_gateway
        self._rate_limiter = rate_limiter
        self._app_base_url = app_base_url

    async def send(self, *, id_token: str, client_ip: str) -> None:
        try:
            email = await self._identity.unverified_password_email(id_token)
        except FirebaseAdminError as exc:
            raise DomainError(
                code="EMAIL_VERIFICATION_IDENTITY_INVALID",
                message="Verification identity is invalid.",
                status_code=400,
            ) from exc
        await self._rate_limiter.check(email=email, client_ip=client_ip)
        try:
            action_url = await self._identity.branded_email_verification_link(
                email, app_base_url=self._app_base_url
            )
            text, html = render_email(
                title="Xác minh email của bạn",
                body=(
                    "Chào bạn, cảm ơn bạn đã tạo tài khoản Đề cử Tinh Hoa Việt. "
                    "Vui lòng xác minh địa chỉ email để hoàn tất đăng ký. "
                    "Nếu bạn không tạo tài khoản, hãy bỏ qua thư này."
                ),
                action_url=action_url,
                action_label="Xác minh email",
            )
            await self._email_gateway.send(
                EmailMessage(
                    to=email,
                    subject="Xác minh tài khoản Đề cử Tinh Hoa Việt",
                    text=text,
                    html=html,
                )
            )
        except Exception as exc:
            raise DomainError(
                code="EMAIL_VERIFICATION_UNAVAILABLE",
                message="Verification email service is unavailable.",
                status_code=503,
            ) from exc
