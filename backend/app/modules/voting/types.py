from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.modules.auth.models import UserStatus
from app.modules.voting.models import CampaignStatus


@dataclass(frozen=True, slots=True)
class EligibilitySnapshot:
    user_status: UserStatus
    email_verified_at: datetime | None
    account_created_at: datetime
    roles: tuple[str, ...]
    organization_ids: tuple[UUID, ...]
    campaign_status: CampaignStatus
    start_at: datetime
    end_at: datetime
    require_verified_email: bool
    min_account_age_hours: int
    allowed_roles: tuple[str, ...]
    allowed_organization_ids: tuple[UUID, ...]
    participant_eligible: bool | None
    effective_vote_count: int
    already_voted: bool
    max_votes_per_user: int
    rule_version: int


class EligibilityReason(StrEnum):
    USER_NOT_ACTIVE = "USER_NOT_ACTIVE"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    ACCOUNT_TOO_NEW = "ACCOUNT_TOO_NEW"
    CAMPAIGN_PAUSED = "CAMPAIGN_PAUSED"
    CAMPAIGN_NOT_ACTIVE = "CAMPAIGN_NOT_ACTIVE"
    CAMPAIGN_NOT_STARTED = "CAMPAIGN_NOT_STARTED"
    CAMPAIGN_ENDED = "CAMPAIGN_ENDED"
    ROLE_NOT_ELIGIBLE = "ROLE_NOT_ELIGIBLE"
    ORGANIZATION_NOT_ELIGIBLE = "ORGANIZATION_NOT_ELIGIBLE"
    WORK_NOT_ELIGIBLE = "WORK_NOT_ELIGIBLE"
    VOTE_LIMIT_REACHED = "VOTE_LIMIT_REACHED"
    ALREADY_VOTED = "ALREADY_VOTED"


class EligibilityAction(StrEnum):
    CREATE = "CREATE"
    CHANGE = "CHANGE"
    REVOKE = "REVOKE"
