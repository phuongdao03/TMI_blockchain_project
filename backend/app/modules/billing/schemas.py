from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.billing.models import FeePolicyStatus, FeeWaiverStatus


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class BillingSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CreateFeePolicyRequest(BillingSchema):
    fee_type: Annotated[str, Field(min_length=2, max_length=64)]
    dossier_type_id: UUID | None = None
    amount_minor: Annotated[int, Field(gt=0, le=10**12)]
    starts_at: datetime
    ends_at: datetime | None = None
    display_name: Annotated[str | None, Field(max_length=255)] = None
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @field_validator("fee_type", "reason", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ApplySubmissionFeeRequest(BillingSchema):
    amount_minor: Annotated[int, Field(gt=0, le=10**12)]


class CancelFeePolicyRequest(BillingSchema):
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ApproveFeePolicyRequest(BillingSchema):
    confirm_activation: bool = False


class FeePolicyData(BillingSchema):
    id: UUID
    fee_type: str
    dossier_type_id: UUID | None
    version_no: int
    amount_minor: int
    currency: str
    display_name: str
    reason: str
    starts_at: datetime
    ends_at: datetime | None
    status: FeePolicyStatus
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None


class RequestFeeWaiverRequest(BillingSchema):
    dossier_id: UUID
    fee_type: Annotated[str, Field(min_length=2, max_length=64)]
    amount_minor: Annotated[int, Field(gt=0, le=10**12)]
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @field_validator("fee_type", "reason", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class GrantFeeWaiverRequest(BillingSchema):
    dossier_id: UUID
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class DecideFeeWaiverRequest(BillingSchema):
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class FeeWaiverData(BillingSchema):
    id: UUID
    dossier_id: UUID
    fee_type: str
    amount_minor: int
    currency: str
    reason: str
    status: FeeWaiverStatus
    requested_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    redeemed_at: datetime | None
    expires_at: datetime


class FeeObligationData(BillingSchema):
    id: UUID
    dossier_id: UUID
    owner_user_id: UUID
    price_catalog_version_id: UUID | None
    price_catalog_entry_id: UUID | None
    service_code: str
    description: str
    amount_minor: int
    currency: str
    tax_mode: str
    status: str
    due_at: datetime
    paid_at: datetime | None
    fee_type: str | None = None
    fee_policy_id: UUID | None = None
    fee_policy_version_no: int | None = None
    gross_amount_minor: int | None = None
    waiver_amount_minor: int | None = None
