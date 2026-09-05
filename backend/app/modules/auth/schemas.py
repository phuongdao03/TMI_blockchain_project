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


INTERNAL_ACCOUNT_ROLES = ("MODERATOR",)
INTERNAL_MANAGED_ROLES = frozenset(INTERNAL_ACCOUNT_ROLES)
STAFF_ACCOUNT_STATUSES = ("ACTIVE", "SUSPENDED", "DISABLED")
StaffAccountRole = Literal["MODERATOR",]
StaffAccountStatus = Literal["ACTIVE", "SUSPENDED", "DISABLED"]
StaffInvitationStatus = Literal["PENDING", "ACCEPTED", "REVOKED", "EXPIRED"]


class StaffAccountUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    role: StaffAccountRole | None = None
    status: Literal["ACTIVE", "SUSPENDED", "DISABLED"] | None = None


class PrivilegedActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    action: Literal["ROLE_CHANGE"]
    requested_role: (
        Literal[
            "MODERATOR",
            "SUPER_ADMIN",
        ]
        | None
    ) = Field(default=None, alias="requestedRole")
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class PrivilegedActionData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    id: UUID
    target_user_id: UUID = Field(alias="targetUserId")
    action: Literal["ROLE_CHANGE", "MFA_RECOVERY"]
    status: Literal["PENDING", "APPROVED", "REJECTED", "EXPIRED"]
    requested_role: str | None = Field(default=None, alias="requestedRole")
    requested_by_user_id: UUID = Field(alias="requestedByUserId")
    approved_by_user_id: UUID | None = Field(default=None, alias="approvedByUserId")
    reason: str
    expires_at: datetime = Field(alias="expiresAt")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")


class StaffAccountData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    id: UUID
    email: EmailStr
    role: str
    status: StaffAccountStatus
    created_at: datetime | None = Field(default=None, alias="createdAt")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt")


class StaffPermissionReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    permissions: Annotated[list[str], Field(max_length=100)]
    expected_version: Annotated[int, Field(alias="expectedVersion", ge=0)]
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class StaffPermissionData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    user_id: UUID = Field(alias="userId")
    permissions: tuple[str, ...]
    version: int


class StaffInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    email: EmailStr
    role: StaffAccountRole
    organization_id: UUID | None = Field(default=None, alias="organizationId")


class StaffInvitationAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    invitation_token: Annotated[
        SecretStr,
        Field(alias="invitationToken", min_length=32, max_length=512),
    ]
    id_token: Annotated[
        str,
        Field(alias="idToken", min_length=100, max_length=16_384),
    ]


class StaffInvitationData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    id: UUID
    email: EmailStr
    role: str
    organization_id: UUID | None = Field(default=None, alias="organizationId")
    status: StaffInvitationStatus
    expires_at: datetime = Field(alias="expiresAt")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class StaffInvitationAcceptedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ACTIVE"]


class ApplicantUpgradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

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
    permissions: tuple[str, ...]
    account_type: AccountType | None = Field(alias="accountType")


class LoginData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: AuthUserData


class FirebaseExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id_token: Annotated[
        str,
        Field(alias="idToken", min_length=100, max_length=16_384),
    ]
    account_type: AccountType = Field(alias="accountType")
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
