from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
)


@dataclass(frozen=True, slots=True)
class CreateOrganization:
    code: str
    legal_name: str
    display_name: str
    tax_code: str | None = None


@dataclass(frozen=True, slots=True)
class OrganizationChanges:
    legal_name: str | None = None
    display_name: str | None = None
    tax_code: str | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class UpsertMember:
    email: str
    role_code: MembershipRole
    status: MembershipStatus


@dataclass(frozen=True, slots=True)
class OrganizationView:
    id: UUID
    code: str
    legal_name: str
    display_name: str
    tax_code: str | None
    status: OrganizationStatus
    owner_user_id: UUID
    current_role: MembershipRole
    can_manage_members: bool


@dataclass(frozen=True, slots=True)
class MemberView:
    user_id: UUID
    email: str
    role_code: MembershipRole
    status: MembershipStatus
    joined_at: datetime | None


@dataclass(frozen=True, slots=True)
class Page[ItemT]:
    items: tuple[ItemT, ...]
    total: int
