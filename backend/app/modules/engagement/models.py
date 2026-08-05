from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class PublicWorkEngagementDaily(UtcTimestampMixin, Base):
    __tablename__ = "public_work_engagement_daily"
    __table_args__ = (
        CheckConstraint("unique_views >= 0", name="unique_views_non_negative"),
        CheckConstraint("share_events >= 0", name="share_events_non_negative"),
        CheckConstraint("qr_scans >= 0", name="qr_scans_non_negative"),
        CheckConstraint("report_requests >= 0", name="report_requests_non_negative"),
        Index(
            "ix_public_work_engagement_daily_date_work",
            "metric_date",
            "public_work_id",
        ),
    )

    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    unique_views: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    share_events: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    qr_scans: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    report_requests: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )


class EngagementAnalyticsSnapshot(Base):
    __tablename__ = "engagement_analytics_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "metric_date",
            name="uq_engagement_analytics_snapshots_metric_date",
        ),
        CheckConstraint(
            "unique_views >= 0",
            name="engagement_snapshot_unique_views_non_negative",
        ),
        CheckConstraint(
            "share_events >= 0",
            name="engagement_snapshot_share_events_non_negative",
        ),
        CheckConstraint(
            "qr_scans >= 0",
            name="engagement_snapshot_qr_scans_non_negative",
        ),
        CheckConstraint(
            "report_requests >= 0",
            name="engagement_snapshot_report_requests_non_negative",
        ),
        CheckConstraint(
            "favorite_events >= 0",
            name="engagement_snapshot_favorite_events_non_negative",
        ),
        Index("ix_engagement_analytics_snapshots_metric_date", "metric_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    unique_views: Mapped[int] = mapped_column(BigInteger, nullable=False)
    share_events: Mapped[int] = mapped_column(BigInteger, nullable=False)
    qr_scans: Mapped[int] = mapped_column(BigInteger, nullable=False)
    report_requests: Mapped[int] = mapped_column(BigInteger, nullable=False)
    favorite_events: Mapped[int] = mapped_column(BigInteger, nullable=False)


class EngagementVelocitySnapshot(Base):
    __tablename__ = "engagement_velocity_snapshots"
    __table_args__ = (
        CheckConstraint("window_end >= window_start", name="velocity_window_valid"),
        CheckConstraint(
            "candidate_count >= 0", name="velocity_candidate_count_non_negative"
        ),
        CheckConstraint("total_score >= 0", name="velocity_total_score_non_negative"),
        UniqueConstraint(
            "window_start",
            "window_end",
            name="uq_engagement_velocity_snapshots_window",
        ),
        Index("ix_engagement_velocity_snapshots_window_end", "window_end"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class EngagementVelocitySnapshotItem(Base):
    __tablename__ = "engagement_velocity_snapshot_items"
    __table_args__ = (
        CheckConstraint("rank > 0", name="velocity_rank_positive"),
        CheckConstraint("display_order > 0", name="velocity_display_order_positive"),
        CheckConstraint("score >= 0", name="velocity_score_non_negative"),
        UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_engagement_velocity_snapshot_items_display_order",
        ),
        Index(
            "ix_engagement_velocity_snapshot_items_snapshot_rank",
            "snapshot_id",
            "rank",
            "display_order",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("engagement_velocity_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class PublicWorkFavorite(Base):
    __tablename__ = "public_work_favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "public_work_id",
            name="user_work",
        ),
        Index(
            "ix_public_work_favorites_work_created",
            "public_work_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicWorkShareEvent(Base):
    __tablename__ = "public_work_share_events"
    __table_args__ = (
        Index(
            "ix_public_work_share_events_user_created",
            "user_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicShareLink(Base):
    __tablename__ = "public_share_links"
    __table_args__ = (
        Index("ix_public_share_links_work_created", "public_work_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
