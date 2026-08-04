from uuid import UUID

from sqlalchemy import ForeignKey, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin
from app.modules.media.models import MediaAsset


class UserProfile(UtcTimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    avatar_media_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(MediaAsset.id, ondelete="SET NULL"),
    )
    locale: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="vi",
        server_default="vi",
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Asia/Ho_Chi_Minh",
        server_default="Asia/Ho_Chi_Minh",
    )
