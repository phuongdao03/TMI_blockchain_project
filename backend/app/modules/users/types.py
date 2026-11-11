from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProfileChanges:
    full_name: str | None = None
    display_name: str | None = None
    phone: str | None = None
    avatar_media_id: UUID | None = None
    locale: str | None = None
    timezone: str | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class EmploymentView:
    employee_code: str
    department_name: str
    position: str
    employment_status: str
    join_date: date


@dataclass(frozen=True, slots=True)
class ProfileView:
    user_id: UUID
    email: str
    full_name: str | None
    display_name: str | None
    phone: str | None
    avatar_media_id: UUID | None
    avatar_url: str | None
    locale: str
    timezone: str
    employment: EmploymentView | None = None
