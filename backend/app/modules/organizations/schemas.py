from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class OrganizationSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CreateOrganizationRequest(OrganizationSchema):
    code: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{2,31}$")]
    legal_name: Annotated[str, Field(min_length=1, max_length=255)]
    display_name: Annotated[str, Field(min_length=1, max_length=255)]
    tax_code: Annotated[
        str | None,
        Field(pattern=r"^[A-Za-z0-9-]{3,32}$"),
    ] = None

    @field_validator("legal_name", "display_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        return value.strip()


class PatchOrganizationRequest(OrganizationSchema):
    legal_name: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    display_name: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    tax_code: Annotated[
        str | None,
        Field(pattern=r"^[A-Za-z0-9-]{3,32}$"),
    ] = None

    @model_validator(mode="after")
    def require_non_null_names(self) -> "PatchOrganizationRequest":
        for field_name in ("legal_name", "display_name"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self


class AddOrganizationMemberRequest(OrganizationSchema):
    email: EmailStr
    role_code: MembershipRole
    status: MembershipStatus = MembershipStatus.INVITED

    @field_validator("role_code")
    @classmethod
    def reject_owner_assignment(
        cls,
        value: MembershipRole,
    ) -> MembershipRole:
        if value is MembershipRole.OWNER:
            raise ValueError("OWNER can only be assigned during organization creation.")
        return value


class OrganizationData(OrganizationSchema):
    id: UUID
    code: str
    legal_name: str
    display_name: str
    tax_code: str | None
    status: OrganizationStatus
    owner_user_id: UUID
    current_role: MembershipRole
    can_manage_members: bool


class OrganizationMemberData(OrganizationSchema):
    user_id: UUID
    email: EmailStr
    role_code: MembershipRole
    status: MembershipStatus
    joined_at: datetime | None


class OrganizationActionData(OrganizationSchema):
    status: Literal["archived", "removed"]
