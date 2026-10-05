import asyncio

import pytest

from app.core.errors import DomainError
from app.modules.auth.firebase_verification_email import (
    FirebaseVerificationEmailService,
)


def test_verification_mail_is_branded_and_sent_to_verified_identity() -> None:
    async def scenario() -> None:
        messages = []

        class Identity:
            async def unverified_password_email(self, id_token: str) -> str:
                assert id_token == "valid-token"
                return "member@example.com"

            async def branded_email_verification_link(
                self, email: str, *, app_base_url: str
            ) -> str:
                assert email == "member@example.com"
                assert app_base_url == "https://decu.tinhhoaviet.org.vn"
                return "https://decu.tinhhoaviet.org.vn/auth/action?mode=verifyEmail&oobCode=abc"

        class Mail:
            async def send(self, message):
                messages.append(message)
                return "message-1"

        class Limit:
            async def check(self, *, email: str, client_ip: str) -> None:
                assert (email, client_ip) == ("member@example.com", "127.0.0.1")

        service = FirebaseVerificationEmailService(
            identity=Identity(),
            email_gateway=Mail(),
            rate_limiter=Limit(),
            app_base_url="https://decu.tinhhoaviet.org.vn",
        )
        await service.send(id_token="valid-token", client_ip="127.0.0.1")

        assert len(messages) == 1
        assert messages[0].to == "member@example.com"
        assert "Đề cử Tinh Hoa Việt" in messages[0].subject
        assert "Xác minh email</a>" in messages[0].html
        assert "tmi-blockchain" not in messages[0].html
        assert "decu.tinhhoaviet.org.vn/auth/action" in messages[0].html

    asyncio.run(scenario())


def test_mail_failure_reports_unavailable_instead_of_success() -> None:
    async def scenario() -> None:
        class Identity:
            async def unverified_password_email(self, id_token: str) -> str:
                return "member@example.com"

            async def branded_email_verification_link(
                self, email: str, *, app_base_url: str
            ) -> str:
                return "https://decu.tinhhoaviet.org.vn/auth/action?mode=verifyEmail&oobCode=abc"

        class Mail:
            async def send(self, message):
                raise OSError("SMTP unavailable")

        class Limit:
            async def check(self, *, email: str, client_ip: str) -> None:
                pass

        service = FirebaseVerificationEmailService(
            identity=Identity(),
            email_gateway=Mail(),
            rate_limiter=Limit(),
            app_base_url="https://decu.tinhhoaviet.org.vn",
        )
        with pytest.raises(DomainError) as exc_info:
            await service.send(id_token="valid-token", client_ip="127.0.0.1")
        assert exc_info.value.code == "EMAIL_VERIFICATION_UNAVAILABLE"
        assert exc_info.value.status_code == 503

    asyncio.run(scenario())
