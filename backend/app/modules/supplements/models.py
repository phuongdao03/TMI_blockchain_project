from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SupplementRequest(Base):
    __tablename__ = "supplement_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'ANSWERED', 'RESOLVED')", name="status_valid"
        ),
        CheckConstraint("priority IN ('NORMAL', 'HIGH')", name="priority_valid"),
        CheckConstraint("revision >= 0", name="revision_non_negative"),
        Index("ix_supplement_requests_dossier_status", "dossier_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False
    )
    requested_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dossier_versions.id", ondelete="RESTRICT"), nullable=False
    )
    criterion_key: Mapped[str] = mapped_column(String(64), nullable=False)
    criterion_label: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_id: Mapped[UUID | None] = mapped_column(Uuid)
    requested_information: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    responses: Mapped[list["SupplementResponse"]] = relationship(
        lazy="selectin", order_by="SupplementResponse.sequence_no"
    )


class SupplementResponse(Base):
    __tablename__ = "supplement_responses"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "sequence_no", name="uq_supplement_response_sequence"
        ),
        CheckConstraint("kind IN ('RESPONSE', 'RESOLVE', 'REOPEN')", name="kind_valid"),
        Index("ix_supplement_responses_request_created", "request_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("supplement_requests.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="RESPONSE")
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
