from datetime import UTC, datetime
from typing import Annotated, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.voting.models import (
    CampaignStatus,
    CampaignType,
    CampaignWorkStatus,
    PeriodType,
    VoteStatus,
)
from app.modules.voting.types import EligibilityReason


class VotingEligibilityRulesData(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    organization_ids: list[UUID] = Field(default_factory=list, alias="organizationIds")
    allowed_roles: list[Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]] = (
        Field(default_factory=list, alias="allowedRoles")
    )

    @field_validator("organization_ids")
    @classmethod
    def unique_organization_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Eligibility values must be unique.")
        return value

    @field_validator("allowed_roles")
    @classmethod
    def unique_allowed_roles(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Eligibility values must be unique.")
        return value


class VotingCampaignRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[
        str,
        Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180),
    ]
    description: Annotated[str, Field(min_length=1, max_length=10_000)]
    campaign_type: CampaignType = Field(alias="campaignType")
    period_type: PeriodType = Field(alias="periodType")
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")
    max_votes_per_user: Annotated[int, Field(gt=0)] = Field(alias="maxVotesPerUser")
    max_votes_per_work_per_user: Annotated[int, Field(ge=1, le=1)] = Field(
        default=1,
        alias="maxVotesPerWorkPerUser",
    )
    allow_vote_change: bool = Field(default=False, alias="allowVoteChange")
    allow_vote_revoke: bool = Field(default=False, alias="allowVoteRevoke")
    require_verified_email: bool = Field(default=True, alias="requireVerifiedEmail")
    min_account_age_hours: Annotated[int, Field(ge=0)] = Field(
        default=0,
        alias="minAccountAgeHours",
    )
    eligibility_rules: VotingEligibilityRulesData = Field(
        default_factory=VotingEligibilityRulesData,
        alias="eligibilityRules",
    )

    @field_validator("name", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank.")
        return stripped

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Campaign timestamps must include a UTC offset.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone.") from exc
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> Self:
        if self.end_at <= self.start_at:
            raise ValueError("endAt must be later than startAt.")
        is_special = self.campaign_type is CampaignType.SPECIAL
        if is_special != (self.period_type is PeriodType.CUSTOM):
            raise ValueError("Campaign classification is inconsistent.")
        return self


class VotingCampaignData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    name: str
    slug: str
    description: str
    status: CampaignStatus
    campaign_type: CampaignType = Field(alias="campaignType")
    period_type: PeriodType = Field(alias="periodType")
    timezone: str
    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")
    max_votes_per_user: int = Field(alias="maxVotesPerUser")
    max_votes_per_work_per_user: int = Field(alias="maxVotesPerWorkPerUser")
    allow_vote_change: bool = Field(alias="allowVoteChange")
    allow_vote_revoke: bool = Field(alias="allowVoteRevoke")
    require_verified_email: bool = Field(alias="requireVerifiedEmail")
    min_account_age_hours: int = Field(alias="minAccountAgeHours")
    eligibility_rules: VotingEligibilityRulesData = Field(alias="eligibilityRules")
    rule_version: int = Field(alias="ruleVersion")
    created_by: UUID = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CampaignLifecycleReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Reason must not be blank.")
        return normalized


class CampaignParticipantRequest(CampaignLifecycleReasonRequest):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    work_id: UUID = Field(alias="workId")


class CampaignParticipantBulkRequest(CampaignLifecycleReasonRequest):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    work_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)] = Field(
        alias="workIds"
    )

    @field_validator("work_ids")
    @classmethod
    def unique_work_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("workIds must be unique.")
        return value


class CampaignParticipantData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    campaign_id: UUID = Field(alias="campaignId")
    work_id: UUID = Field(alias="workId")
    status: CampaignWorkStatus
    title: str
    slug: str
    approved_at: datetime | None = Field(alias="approvedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class VotingEligibilityData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    can_vote: bool = Field(alias="canVote")
    reasons: tuple[EligibilityReason, ...]
    remaining_quota: int = Field(alias="remainingQuota")
    rule_version: int = Field(alias="ruleVersion")
    server_time: datetime = Field(alias="serverTime")


class VoteMutationData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    vote_id: UUID = Field(alias="voteId")
    campaign_id: UUID = Field(alias="campaignId")
    work_id: UUID = Field(alias="workId")
    status: VoteStatus
    remaining_quota: int = Field(alias="remainingQuota")
    rule_version: int = Field(alias="ruleVersion")
    created_at: datetime = Field(alias="createdAt")
    previous_vote_id: UUID | None = Field(default=None, alias="previousVoteId")


class VoteChangeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    source_vote_id: UUID = Field(alias="sourceVoteId")
    target_work_id: UUID = Field(alias="targetWorkId")


class VoteHistoryData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    vote_id: UUID = Field(alias="voteId")
    campaign_id: UUID = Field(alias="campaignId")
    campaign_name: str = Field(alias="campaignName")
    campaign_slug: str = Field(alias="campaignSlug")
    work_id: UUID = Field(alias="workId")
    work_title: str = Field(alias="workTitle")
    work_slug: str = Field(alias="workSlug")
    status: VoteStatus
    created_at: datetime = Field(alias="createdAt")
    revoked_at: datetime | None = Field(alias="revokedAt")
    can_change: bool = Field(alias="canChange")
    can_revoke: bool = Field(alias="canRevoke")


class AdminVoteData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    vote_id: UUID = Field(alias="voteId")
    campaign_id: UUID = Field(alias="campaignId")
    campaign_name: str = Field(alias="campaignName")
    work_id: UUID = Field(alias="workId")
    work_title: str = Field(alias="workTitle")
    voter_reference: str = Field(alias="voterReference")
    status: VoteStatus
    source: str
    risk_score: str = Field(alias="riskScore")
    created_at: datetime = Field(alias="createdAt")
    revoked_at: datetime | None = Field(alias="revokedAt")


class PublicVotingCampaignData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    name: str
    slug: str
    description: str
    status: CampaignStatus
    timezone: str
    start_at: datetime = Field(alias="startAt")
    end_at: datetime = Field(alias="endAt")
    max_votes_per_user: int = Field(alias="maxVotesPerUser")
    allow_vote_change: bool = Field(alias="allowVoteChange")
    allow_vote_revoke: bool = Field(alias="allowVoteRevoke")
    rule_version: int = Field(alias="ruleVersion")
    server_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="serverTime"
    )


class PublicCampaignWorkData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    work_id: UUID = Field(alias="workId")
    title: str
    slug: str
    short_description: str = Field(alias="shortDescription")


class PublicVoteSummaryData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    work_id: UUID = Field(alias="workId")
    work_title: str = Field(alias="workTitle")
    work_slug: str = Field(alias="workSlug")
    effective_count: int = Field(alias="effectiveCount")
    refreshed_at: datetime = Field(alias="refreshedAt")
