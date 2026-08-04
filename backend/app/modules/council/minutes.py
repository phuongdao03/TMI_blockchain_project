from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from app.modules.council.models import (
    CouncilCase,
    CouncilCaseConflict,
    CouncilCaseDecision,
    CouncilSession,
    CouncilSessionMember,
    CouncilVote,
    CouncilVoteChoice,
)
from app.modules.council.types import CouncilCaseResultView


def group_votes(
    votes: tuple[CouncilVote, ...],
) -> dict[UUID, tuple[CouncilVote, ...]]:
    grouped: dict[UUID, list[CouncilVote]] = {}
    for vote in votes:
        grouped.setdefault(vote.case_id, []).append(vote)
    return {
        case_id: tuple(case_votes)
        for case_id, case_votes in grouped.items()
    }


def calculate_case_result(
    council_case: CouncilCase,
    votes: tuple[CouncilVote, ...],
    *,
    quorum_required: int,
) -> CouncilCaseResultView:
    counts = Counter(vote.choice for vote in votes)
    vote_counts = {
        choice: counts.get(choice, 0) for choice in CouncilVoteChoice
    }
    valid_count = len(votes)
    quorum_met = valid_count >= quorum_required
    decision: CouncilCaseDecision | None = None
    if quorum_met:
        for choice in (
            CouncilVoteChoice.APPROVE,
            CouncilVoteChoice.REJECT,
            CouncilVoteChoice.REQUEST_MORE_INFO,
        ):
            if vote_counts[choice] > valid_count / 2:
                decision = CouncilCaseDecision(choice.value)
                break
    return CouncilCaseResultView(
        case_id=council_case.id,
        dossier_id=council_case.dossier_id,
        dossier_version_id=council_case.dossier_version_id,
        decision=decision,
        quorum_met=quorum_met,
        valid_vote_count=valid_count,
        vote_counts=vote_counts,
    )


def build_minutes_payload(
    council_session: CouncilSession,
    *,
    members: tuple[CouncilSessionMember, ...],
    conflicts: tuple[CouncilCaseConflict, ...],
    votes: tuple[CouncilVote, ...],
    results: tuple[CouncilCaseResultView, ...],
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "session": {
            "id": str(council_session.id),
            "code": council_session.code,
            "title": council_session.title,
            "scheduledAt": _iso(council_session.scheduled_at),
            "openedAt": _iso(council_session.opened_at),
            "closedAt": _iso(council_session.closed_at),
            "quorumRequired": council_session.quorum_required,
        },
        "members": [
            {
                "memberUserId": str(item.member_user_id),
                "attendanceConfirmedAt": _iso(
                    item.attendance_confirmed_at
                ),
            }
            for item in members
        ],
        "conflicts": [
            {
                "caseId": str(item.case_id),
                "memberUserId": str(item.member_user_id),
                "hasConflict": item.has_conflict,
                "reason": item.reason,
                "declaredAt": _iso(item.declared_at),
            }
            for item in conflicts
        ],
        "votes": [
            {
                "caseId": str(item.case_id),
                "memberUserId": str(item.member_user_id),
                "choice": item.choice.value,
                "reason": item.reason,
                "votedAt": _iso(item.voted_at),
            }
            for item in votes
        ],
        "results": [
            {
                "caseId": str(item.case_id),
                "dossierId": str(item.dossier_id),
                "dossierVersionId": str(item.dossier_version_id),
                "decision": (
                    item.decision.value if item.decision is not None else None
                ),
                "quorumMet": item.quorum_met,
                "validVoteCount": item.valid_vote_count,
                "voteCounts": {
                    choice.value: item.vote_counts[choice]
                    for choice in CouncilVoteChoice
                },
            }
            for item in results
        ],
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )
    return normalized.isoformat()
