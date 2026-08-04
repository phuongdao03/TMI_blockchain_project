from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class OrganizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MembershipRole(StrEnum):
    OWNER = "OWNER"
    ORG_MANAGER = "ORG_MANAGER"
    MEMBER = "MEMBER"


class MembershipStatus(StrEnum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


class Organization(UtcTimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_code_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[OrganizationStatus] = mapped_column(
        _enum(OrganizationStatus, "organization_status"),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
        server_default=OrganizationStatus.ACTIVE.value,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationMember(UtcTimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (Index("ix_organization_members_user_id", "user_id"),)

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_code: Mapped[MembershipRole] = mapped_column(
        _enum(MembershipRole, "membership_role"),
        nullable=False,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        _enum(MembershipStatus, "membership_status"),
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
