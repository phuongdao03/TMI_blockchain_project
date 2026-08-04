from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
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
