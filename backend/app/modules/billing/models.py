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
    text,
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


class FeePolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class FeeWaiverStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"


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


class FeePolicy(UtcTimestampMixin, Base):
    __tablename__ = "fee_policies"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("currency = 'VND'", name="currency_vnd"),
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="effective_interval_valid"
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'CANCELLED') OR approved_at IS NOT NULL",
            name="approved_policy_has_timestamp",
        ),
        UniqueConstraint(
            "fee_type", "dossier_type_id", "version_no", name="uq_fee_policy_version"
        ),
        Index(
            "ix_fee_policies_scope_effective",
            "fee_type",
            "dossier_type_id",
            "status",
            "starts_at",
            "ends_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    fee_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dossier_type_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(DossierType.id, ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="VND"
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[FeePolicyStatus] = mapped_column(
        Enum(
            FeePolicyStatus,
            name="fee_policy_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=FeePolicyStatus.DRAFT,
        server_default=FeePolicyStatus.DRAFT.value,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FeePolicyEvent(Base):
    __tablename__ = "fee_policy_events"
    __table_args__ = (
        Index("ix_fee_policy_events_policy_created", "policy_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(FeePolicy.id, ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    before_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    after_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FeeWaiver(UtcTimestampMixin, Base):
    __tablename__ = "fee_waivers"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        UniqueConstraint("dossier_id", "fee_type", name="uq_fee_waiver_scope"),
        Index("ix_fee_waivers_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False
    )
    fee_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="VND"
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[FeeWaiverStatus] = mapped_column(
        Enum(
            FeeWaiverStatus,
            name="fee_waiver_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=FeeWaiverStatus.REQUESTED,
        server_default=FeeWaiverStatus.REQUESTED.value,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FeeObligation(UtcTimestampMixin, Base):
    __tablename__ = "fee_obligations"
    __table_args__ = (
        CheckConstraint("length(currency) = 3", name="currency_length"),
        Index(
            "ix_fee_obligations_owner_status_due",
            "owner_user_id",
            "status",
            "due_at",
        ),
        Index(
            "uq_fee_obligations_dossier_fee_type",
            "dossier_id",
            "fee_type",
            unique=True,
            postgresql_where=text("fee_type IS NOT NULL"),
            sqlite_where=text("fee_type IS NOT NULL"),
        ),
        Index(
            "uq_fee_obligations_legacy_dossier_id",
            "dossier_id",
            unique=True,
            postgresql_where=text("fee_type IS NULL"),
            sqlite_where=text("fee_type IS NULL"),
        ),
        CheckConstraint("amount_minor >= 0", name="amount_minor_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    price_catalog_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(PriceCatalogVersion.id, ondelete="RESTRICT"),
        nullable=True,
    )
    price_catalog_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(PriceCatalogEntry.id, ondelete="RESTRICT"),
        nullable=True,
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
    fee_type: Mapped[str | None] = mapped_column(String(64))
    fee_policy_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey(FeePolicy.id, ondelete="RESTRICT")
    )
    fee_policy_version_no: Mapped[int | None] = mapped_column(Integer)
    gross_amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    waiver_amount_minor: Mapped[int | None] = mapped_column(BigInteger)
