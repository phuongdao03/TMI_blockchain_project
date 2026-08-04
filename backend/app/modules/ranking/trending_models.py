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


class TrendingSnapshot(Base):
    __tablename__ = "trending_snapshots"
    __table_args__ = (
        CheckConstraint("window_end > window_start", name="window_valid"),
        CheckConstraint(
            "length(source_digest) = 64",
            name="source_digest_length",
        ),
        CheckConstraint(
            "length(result_digest) = 64",
            name="result_digest_length",
        ),
        CheckConstraint("candidate_count >= 0", name="candidate_count_non_negative"),
        CheckConstraint("total_score >= 0", name="total_score_non_negative"),
        UniqueConstraint(
            "window_start",
            "window_end",
            name="uq_trending_snapshots_window",
        ),
        Index(
            "ix_trending_snapshots_window_end",
            "window_end",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TrendingSnapshotItem(Base):
    __tablename__ = "trending_snapshot_items"
    __table_args__ = (
        CheckConstraint("rank > 0", name="rank_positive"),
        CheckConstraint("display_order > 0", name="display_order_positive"),
        CheckConstraint("score >= 0", name="score_non_negative"),
        UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_trending_snapshot_items_display_order",
        ),
        Index(
            "ix_trending_snapshot_items_snapshot_rank",
            "snapshot_id",
            "rank",
            "display_order",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("trending_snapshots.id", ondelete="CASCADE"),
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
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(BigInteger, nullable=False)
