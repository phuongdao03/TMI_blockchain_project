from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from app.modules.auth.models import AccountType


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=12, max_length=128)]
    account_type: AccountType = Field(alias="accountType")


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Annotated[str, Field(min_length=32, max_length=256)]


class RegistrationAcceptedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class EmailVerifiedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["verified"]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]
    device_name: Annotated[
        str | None,
        Field(alias="deviceName", max_length=255),
    ] = None


class AuthUserData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    id: UUID
    email: EmailStr
    roles: tuple[str, ...]
    account_type: AccountType | None = Field(alias="accountType")


class LoginData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: AuthUserData


class OAuthStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    account_type: AccountType = Field(alias="accountType")
    next_path: Annotated[
        str | None,
        Field(alias="next", max_length=512),
    ] = None


class OAuthStartData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    authorization_url: str = Field(alias="authorizationUrl")


class OAuthLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    next_path: Annotated[
        str | None,
        Field(alias="next", max_length=512),
    ] = None


class AuthStatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["refreshed", "logged_out", "revoked"]


class AuthSessionData(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(name.split("_"))
        ),
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    id: UUID
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    token: Annotated[str, Field(min_length=32, max_length=256)]
    new_password: Annotated[
        SecretStr,
        Field(alias="newPassword", min_length=12, max_length=128),
    ]


class PasswordResetAcceptedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class PasswordResetData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["password_reset"]
