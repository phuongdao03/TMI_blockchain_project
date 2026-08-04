from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class SearchHistoryPreference(UtcTimestampMixin, Base):
    __tablename__ = "search_history_preferences"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SearchHistoryEntry(UtcTimestampMixin, Base):
    __tablename__ = "search_history_entries"
    __table_args__ = (
        Index(
            "uq_search_history_entries_user_query_hash",
            "user_id",
            "query_hash",
            unique=True,
        ),
        Index(
            "ix_search_history_entries_user_searched",
            "user_id",
            "searched_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_query: Mapped[str] = mapped_column(String(200), nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
