from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class UserStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class AccountType(StrEnum):
    PUBLIC_USER = "PUBLIC_USER"
    INDIVIDUAL_APPLICANT = "INDIVIDUAL_APPLICANT"
    ORGANIZATION_APPLICANT = "ORGANIZATION_APPLICANT"


class AuthProvider(StrEnum):
    GOOGLE = "GOOGLE"


USER_STATUS_TYPE = Enum(
    UserStatus,
    name="user_status",
    values_callable=lambda statuses: [status.value for status in statuses],
    validate_strings=True,
)
EMAIL_TYPE = CITEXT().with_variant(String(collation="NOCASE"), "sqlite")


class User(UtcTimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(EMAIL_TYPE, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[UserStatus] = mapped_column(
        USER_STATUS_TYPE,
        nullable=False,
        default=UserStatus.PENDING,
        server_default=UserStatus.PENDING.value,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    account_type: Mapped[AccountType | None] = mapped_column(
        Enum(
            AccountType,
            name="account_type",
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
        )
    )


class Role(UtcTimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class AuthIdentity(UtcTimestampMixin, Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        Index(
            "uq_auth_identities_provider_subject",
            "provider",
            "provider_subject",
            unique=True,
        ),
        Index(
            "uq_auth_identities_user_provider",
            "user_id",
            "provider",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[AuthProvider] = mapped_column(
        Enum(
            AuthProvider,
            name="auth_provider",
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Permission(UtcTimestampMixin, Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)


class RolePermission(UtcTimestampMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (Index("ix_role_permissions_permission_id", "permission_id"),)

    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserRole(UtcTimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_role_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class AuthSession(UtcTimestampMixin, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_id_expires_at", "user_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    device_name: Mapped[str | None] = mapped_column(String(255))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    user_agent: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("auth_sessions.id", ondelete="SET NULL"),
    )


class VerificationToken(UtcTimestampMixin, Base):
    __tablename__ = "verification_tokens"
    __table_args__ = (
        Index(
            "ix_verification_tokens_user_id_purpose",
            "user_id",
            "purpose",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
