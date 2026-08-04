from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class SearchSnapshotPeriod(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"


class SearchEvent(UtcTimestampMixin, Base):
    __tablename__ = "search_events"
    __table_args__ = (
        Index("ix_search_events_created_category", "created_at", "category_slug"),
        Index("ix_search_events_query_created", "query_hash", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_query: Mapped[str | None] = mapped_column(String(200))
    category_slug: Mapped[str | None] = mapped_column(String(180))
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_work_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("public_works.id", ondelete="SET NULL")
    )


class SearchTrendingSnapshot(Base):
    __tablename__ = "search_trending_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "period", "period_start", "query_hash", name="uq_search_trending_period"
        ),
        Index(
            "ix_search_trending_public",
            "period",
            "period_start",
            "is_suppressed",
            "search_count",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    display_query: Mapped[str] = mapped_column(String(200), nullable=False)
    search_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_suppressed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SearchSuppressedPhrase(UtcTimestampMixin, Base):
    __tablename__ = "search_suppressed_phrases"

    query_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    suppressed_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)


class SearchAnalyticsSnapshot(Base):
    __tablename__ = "search_analytics_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "period_start", "category_slug", name="uq_search_analytics_period_category"
        ),
        Index("ix_search_analytics_period", "period_start", "category_slug"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    category_slug: Mapped[str] = mapped_column(
        String(180), nullable=False, server_default=""
    )
    search_count: Mapped[int] = mapped_column(Integer, nullable=False)
    zero_result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_p95_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
