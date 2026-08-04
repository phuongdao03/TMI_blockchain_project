from enum import StrEnum


class VoteEventType(StrEnum):
    CREATED = "VOTE_CREATED"
    REVOKED_FOR_CHANGE = "VOTE_REVOKED_FOR_CHANGE"
    CREATED_BY_CHANGE = "VOTE_CREATED_BY_CHANGE"
    REVOKED = "VOTE_REVOKED"


class VoteOutboxEventType(StrEnum):
    CREATED = "voting.vote.created"
    CHANGED = "voting.vote.changed"
    REVOKED = "voting.vote.revoked"


VOTE_RESULT_EVENTS = (
    VoteEventType.CREATED.value,
    VoteEventType.CREATED_BY_CHANGE.value,
    VoteEventType.REVOKED.value,
)
