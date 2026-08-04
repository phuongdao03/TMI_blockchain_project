from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.council.models import (
    CouncilCaseDecision,
    CouncilSessionStatus,
    CouncilVoteChoice,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class CouncilSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CreateCouncilSessionRequest(CouncilSchema):
    code: Annotated[str, Field(min_length=3, max_length=64)]
    title: Annotated[str, Field(min_length=1, max_length=255)]
    scheduled_at: datetime
    quorum_required: Annotated[int, Field(ge=1, le=50)]
    member_user_ids: Annotated[list[UUID], Field(min_length=1, max_length=50)]

    @field_validator("member_user_ids")
    @classmethod
    def unique_members(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Council member IDs must be unique.")
        return value


class AddCouncilCaseRequest(CouncilSchema):
    dossier_id: UUID


class CouncilConflictRequest(CouncilSchema):
    has_conflict: bool
    reason: Annotated[str | None, Field(max_length=2_000)] = None


class CouncilVoteRequest(CouncilSchema):
    choice: CouncilVoteChoice
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]


class CouncilSessionData(CouncilSchema):
    id: UUID
    code: str
    title: str
    scheduled_at: datetime
    status: CouncilSessionStatus
    quorum_required: int
    opened_at: datetime | None
    closed_at: datetime | None
    minutes_hash: str | None
    member_count: int
    attendance_count: int


class CouncilMemberData(CouncilSchema):
    id: UUID
    session_id: UUID
    member_user_id: UUID
    attendance_confirmed_at: datetime | None


class CouncilCaseData(CouncilSchema):
    id: UUID
    session_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int
    decision: CouncilCaseDecision | None


class CouncilConflictData(CouncilSchema):
    id: UUID
    case_id: UUID
    member_user_id: UUID
    has_conflict: bool
    reason: str | None
    declared_at: datetime


class CouncilVoteData(CouncilSchema):
    id: UUID
    case_id: UUID
    member_user_id: UUID
    choice: CouncilVoteChoice
    reason: str
    voted_at: datetime


class CouncilCaseResultData(CouncilSchema):
    case_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    decision: CouncilCaseDecision | None
    quorum_met: bool
    valid_vote_count: int
    vote_counts: dict[CouncilVoteChoice, int]


class CouncilSessionListItemData(CouncilSchema):
    session: CouncilSessionData
    my_attendance_confirmed_at: datetime | None


class CouncilCaseDetailData(CouncilSchema):
    case: CouncilCaseData
    my_conflict: CouncilConflictData | None
    my_vote: CouncilVoteData | None
    result: CouncilCaseResultData | None


class CouncilSessionDetailData(CouncilSchema):
    session: CouncilSessionData
    my_attendance_confirmed_at: datetime | None
    cases: list[CouncilCaseDetailData]


class CouncilMinutesData(CouncilSchema):
    session_id: UUID
    session_code: str
    closed_at: datetime
    quorum_required: int
    minutes_hash: str
    cases: list[CouncilCaseResultData]
