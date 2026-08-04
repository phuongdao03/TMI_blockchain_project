from app.core.errors import DomainError
from app.modules.voting.models import CampaignStatus
from app.modules.voting.types import EligibilityReason


class VotingCampaignForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_FORBIDDEN",
            message="Voting campaign access is forbidden.",
            status_code=403,
        )


class VotingCampaignNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_NOT_FOUND",
            message="Voting campaign was not found.",
            status_code=404,
        )


class VotingCampaignSlugConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_SLUG_CONFLICT",
            message="Voting campaign slug is already in use.",
            status_code=409,
        )


class VotingCampaignRulesLockedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_RULES_LOCKED",
            message="Only draft voting campaigns can be updated.",
            status_code=409,
        )


class VotingCampaignInvalidTransitionError(DomainError):
    def __init__(self, *, current: CampaignStatus, action: str) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_INVALID_TRANSITION",
            message="The voting campaign lifecycle transition is not allowed.",
            status_code=409,
            details={"currentStatus": current.value, "action": action},
        )


class VotingCampaignPreflightError(DomainError):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_PREFLIGHT_FAILED",
            message="The voting campaign did not pass lifecycle preflight checks.",
            status_code=409,
            details={"reasons": reasons},
        )


class VotingCampaignReasonRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_CAMPAIGN_REASON_REQUIRED",
            message="A reason is required for this campaign lifecycle action.",
            status_code=422,
        )


class VotingParticipantSetLockedError(DomainError):
    def __init__(self, *, current: CampaignStatus) -> None:
        super().__init__(
            code="VOTING_PARTICIPANT_SET_LOCKED",
            message="Campaign participants cannot be changed in this lifecycle state.",
            status_code=409,
            details={"currentStatus": current.value},
        )


class VotingParticipantWorkNotEligibleError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_PARTICIPANT_WORK_NOT_ELIGIBLE",
            message="Only published public works can participate in voting.",
            status_code=409,
        )


class VotingParticipantNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_PARTICIPANT_NOT_FOUND",
            message="Campaign participant was not found.",
            status_code=404,
        )


class VotingParticipantInvalidTransitionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTING_PARTICIPANT_INVALID_TRANSITION",
            message="The participant status transition is not allowed.",
            status_code=409,
        )


class VotingEligibilityDeniedError(DomainError):
    def __init__(self, reason: EligibilityReason) -> None:
        super().__init__(
            code=reason.value,
            message="The vote is not eligible under the campaign rules.",
            status_code=409,
            details={"reason": reason.value},
        )


class VotingIdempotencyConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="IDEMPOTENCY_CONFLICT",
            message="The idempotency key was already used for another vote payload.",
            status_code=409,
        )


class VotingVoteNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTE_NOT_FOUND",
            message="The vote was not found.",
            status_code=404,
        )


class VotingChangeNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTE_CHANGE_NOT_ALLOWED",
            message="This campaign does not allow vote changes.",
            status_code=409,
        )


class VotingRevokeNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VOTE_REVOKE_NOT_ALLOWED",
            message="This campaign does not allow vote revocation.",
            status_code=409,
        )
