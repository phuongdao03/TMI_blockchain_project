from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.council.models import (
    CouncilCaseDecision,
    CouncilSessionStatus,
    CouncilVoteChoice,
)


@dataclass(frozen=True, slots=True)
class CouncilSessionView:
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


@dataclass(frozen=True, slots=True)
class CouncilMemberView:
    id: UUID
    session_id: UUID
    member_user_id: UUID
    attendance_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class CouncilCaseView:
    id: UUID
    session_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int
    decision: CouncilCaseDecision | None


@dataclass(frozen=True, slots=True)
class CouncilConflictView:
    id: UUID
    case_id: UUID
    member_user_id: UUID
    has_conflict: bool
    reason: str | None
    declared_at: datetime


@dataclass(frozen=True, slots=True)
class CouncilVoteView:
    id: UUID
    case_id: UUID
    member_user_id: UUID
    choice: CouncilVoteChoice
    reason: str
    voted_at: datetime


@dataclass(frozen=True, slots=True)
class CouncilCaseResultView:
    case_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    decision: CouncilCaseDecision | None
    quorum_met: bool
    valid_vote_count: int
    vote_counts: Mapping[CouncilVoteChoice, int]


@dataclass(frozen=True, slots=True)
class CouncilMinutesView:
    session_id: UUID
    session_code: str
    closed_at: datetime
    quorum_required: int
    minutes_hash: str
    cases: tuple[CouncilCaseResultView, ...]


@dataclass(frozen=True, slots=True)
class CouncilSessionListItemView:
    session: CouncilSessionView
    my_attendance_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class CouncilSessionPage:
    items: tuple[CouncilSessionListItemView, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CouncilCaseDetailView:
    case: CouncilCaseView
    my_conflict: CouncilConflictView | None
    my_vote: CouncilVoteView | None
    result: CouncilCaseResultView | None


@dataclass(frozen=True, slots=True)
class CouncilSessionDetailView:
    session: CouncilSessionView
    my_attendance_confirmed_at: datetime | None
    cases: tuple[CouncilCaseDetailView, ...]
