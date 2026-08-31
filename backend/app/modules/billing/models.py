from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin
from app.modules.dossiers.models import DossierType


class PriceCatalogStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class FeeObligationStatus(StrEnum):
    OPEN = "OPEN"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    WAIVED = "WAIVED"
    CANCELLED = "CANCELLED"


class PriceCatalogVersion(UtcTimestampMixin, Base):
    __tablename__ = "price_catalog_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="effective_interval_valid",
        ),
        CheckConstraint(
            "status != 'PUBLISHED' OR published_at IS NOT NULL",
            name="published_has_timestamp",
        ),
        Index(
            "ix_price_catalog_versions_status_effective",
            "status",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    status: Mapped[PriceCatalogStatus] = mapped_column(
        Enum(
            PriceCatalogStatus,
            name="price_catalog_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=PriceCatalogStatus.DRAFT,
        server_default=PriceCatalogStatus.DRAFT.value,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )


class PriceCatalogEntry(Base):
    __tablename__ = "price_catalog_entries"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        UniqueConstraint(
            "catalog_version_id",
            "dossier_type_id",
            "service_code",
            name="uq_price_catalog_entry_scope",
        ),
        Index("ix_price_catalog_entries_dossier_type_id", "dossier_type_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    catalog_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(PriceCatalogVersion.id, ondelete="CASCADE"),
        nullable=False,
    )
    dossier_type_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierType.id, ondelete="RESTRICT"),
        nullable=False,
    )
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    tax_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="UNSPECIFIED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FeeObligation(UtcTimestampMixin, Base):
    __tablename__ = "fee_obligations"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        Index(
            "ix_fee_obligations_owner_status_due",
            "owner_user_id",
            "status",
            "due_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    price_catalog_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(PriceCatalogVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    price_catalog_entry_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(PriceCatalogEntry.id, ondelete="RESTRICT"),
        nullable=False,
    )
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    tax_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[FeeObligationStatus] = mapped_column(
        Enum(
            FeeObligationStatus,
            name="fee_obligation_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=FeeObligationStatus.OPEN,
        server_default=FeeObligationStatus.OPEN.value,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_snapshot_json: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
