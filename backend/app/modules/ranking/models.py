from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"
    __table_args__ = (
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint(
            "campaign_rule_version > 0",
            name="rule_version_positive",
        ),
        CheckConstraint(
            "length(source_digest) = 64",
            name="source_digest_length",
        ),
        CheckConstraint(
            "length(result_digest) = 64",
            name="result_digest_length",
        ),
        CheckConstraint(
            "candidate_count >= 0",
            name="candidate_count_non_negative",
        ),
        CheckConstraint(
            "total_valid_votes >= 0",
            name="total_votes_non_negative",
        ),
        UniqueConstraint(
            "campaign_id",
            "version",
            name="uq_ranking_snapshots_campaign_version",
        ),
        Index(
            "ix_ranking_snapshots_campaign_created",
            "campaign_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("voting_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_valid_votes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class RankingSnapshotItem(Base):
    __tablename__ = "ranking_snapshot_items"
    __table_args__ = (
        CheckConstraint("rank > 0", name="rank_positive"),
        CheckConstraint("category_rank > 0", name="category_rank_positive"),
        CheckConstraint(
            "display_order > 0",
            name="display_order_positive",
        ),
        CheckConstraint("score >= 0", name="score_non_negative"),
        CheckConstraint(
            "effective_vote_count >= 0",
            name="vote_count_non_negative",
        ),
        UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_ranking_snapshot_items_snapshot_display_order",
        ),
        Index(
            "ix_ranking_snapshot_items_snapshot_rank",
            "snapshot_id",
            "rank",
            "display_order",
        ),
        Index(
            "ix_ranking_snapshot_items_category_rank",
            "snapshot_id",
            "category_id",
            "category_rank",
            "display_order",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("ranking_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    category_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(BigInteger, nullable=False)
    effective_vote_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
