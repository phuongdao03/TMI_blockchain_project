from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.auth.models import User
from app.modules.dossiers.models import Dossier, DossierVersion


class CouncilSessionStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CouncilVoteChoice(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"


class CouncilCaseDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda values: [item.value for item in values],
        validate_strings=True,
    )


class CouncilSession(Base):
    __tablename__ = "council_sessions"
    __table_args__ = (
        CheckConstraint(
            "quorum_required > 0",
            name="quorum_required_positive",
        ),
        CheckConstraint(
            "minutes_hash IS NULL OR length(minutes_hash) = 64",
            name="minutes_hash_length",
        ),
        Index(
            "ix_council_sessions_status_scheduled_at",
            "status",
            "scheduled_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[CouncilSessionStatus] = mapped_column(
        _enum(CouncilSessionStatus, "council_session_status"),
        nullable=False,
        default=CouncilSessionStatus.DRAFT,
        server_default=CouncilSessionStatus.DRAFT.value,
    )
    quorum_required: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    minutes_hash: Mapped[str | None] = mapped_column(CHAR(64))


class CouncilCase(Base):
    __tablename__ = "council_cases"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "dossier_version_id",
            name="uq_council_cases_session_version",
        ),
        Index("ix_council_cases_dossier_id", "dossier_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(CouncilSession.id, ondelete="CASCADE"),
        nullable=False,
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(Dossier.id, ondelete="RESTRICT"),
        nullable=False,
    )
    dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[CouncilCaseDecision | None] = mapped_column(
        _enum(CouncilCaseDecision, "council_case_decision")
    )


class CouncilSessionMember(Base):
    __tablename__ = "council_session_members"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "member_user_id",
            name="uq_council_session_members_session_member",
        ),
        Index(
            "ix_council_session_members_member_session",
            "member_user_id",
            "session_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(CouncilSession.id, ondelete="CASCADE"),
        nullable=False,
    )
    member_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class CouncilCaseConflict(Base):
    __tablename__ = "council_case_conflicts"
    __table_args__ = (
        CheckConstraint(
            (
                "(has_conflict AND reason IS NOT NULL "
                "AND length(trim(reason)) > 0) "
                "OR (NOT has_conflict AND reason IS NULL)"
            ),
            name="council_conflict_reason_consistent",
        ),
        UniqueConstraint(
            "case_id",
            "member_user_id",
            name="uq_council_case_conflicts_case_member",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(CouncilCase.id, ondelete="CASCADE"),
        nullable=False,
    )
    member_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    has_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class CouncilVote(Base):
    __tablename__ = "council_votes"
    __table_args__ = (
        CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 2000",
            name="council_vote_reason_length",
        ),
        UniqueConstraint(
            "case_id",
            "member_user_id",
            name="uq_council_votes_case_member",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(CouncilCase.id, ondelete="CASCADE"),
        nullable=False,
    )
    member_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    choice: Mapped[CouncilVoteChoice] = mapped_column(
        _enum(CouncilVoteChoice, "council_vote_choice"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    voted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
