from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin
from app.modules.auth.models import User
from app.modules.organizations.models import Organization


class DossierStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PRECHECK = "PRECHECK"
    NEEDS_SUPPLEMENT = "NEEDS_SUPPLEMENT"
    UNDER_REVIEW = "UNDER_REVIEW"
    COUNCIL_REVIEW = "COUNCIL_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    ANCHOR_PENDING = "ANCHOR_PENDING"
    ANCHORED = "ANCHORED"
    CERTIFICATE_ISSUED = "CERTIFICATE_ISSUED"
    PUBLISHED = "PUBLISHED"
    REVOKED = "REVOKED"
    CANCELLED = "CANCELLED"


class DossierVisibility(StrEnum):
    PRIVATE = "PRIVATE"
    UNLISTED = "UNLISTED"
    PUBLIC = "PUBLIC"


class DocumentClaimantScope(StrEnum):
    USER = "USER"
    ORGANIZATION = "ORGANIZATION"


class DocumentHashAdjudicationAction(StrEnum):
    ALLOW_REANCHOR = "ALLOW_REANCHOR"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="display_order_non_negative",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    slug: Mapped[str | None] = mapped_column(String(160), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )


class Dossier(UtcTimestampMixin, Base):
    __tablename__ = "dossiers"
    __table_args__ = (
        CheckConstraint(
            "current_version_no >= 0",
            name="current_version_no_non_negative",
        ),
        Index(
            "ix_dossiers_owner_status_created_at",
            "owner_user_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_dossiers_organization_status",
            "organization_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(Organization.id, ondelete="RESTRICT"),
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(280), unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    _status: Mapped[DossierStatus] = mapped_column(
        "status",
        _enum(DossierStatus, "dossier_status"),
        nullable=False,
        default=DossierStatus.DRAFT,
        server_default=DossierStatus.DRAFT.value,
    )
    visibility: Mapped[DossierVisibility] = mapped_column(
        _enum(DossierVisibility, "visibility"),
        nullable=False,
        default=DossierVisibility.PRIVATE,
        server_default=DossierVisibility.PRIVATE.value,
    )
    current_version_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @hybrid_property
    def status(self) -> DossierStatus:
        return self._status

    def _set_status_from_workflow(self, target: DossierStatus) -> None:
        self._status = target


SNAPSHOT_TYPE = JSONB().with_variant(JSON(), "sqlite")


class DossierVersion(Base):
    __tablename__ = "dossier_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        UniqueConstraint(
            "dossier_id",
            "version_no",
            name="uq_dossier_versions_dossier_id_version_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(
        SNAPSHOT_TYPE,
        nullable=False,
    )
    canonical_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    submitted_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DossierContentClaim(Base):
    """Immutable exact-content claim used to prevent duplicate submissions."""

    __tablename__ = "dossier_content_claims"
    __table_args__ = (
        UniqueConstraint(
            "content_fingerprint",
            name="uq_dossier_content_claims_fingerprint",
        ),
        Index(
            "ix_dossier_content_claims_dossier_id",
            "dossier_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentHashAnchor(Base):
    __tablename__ = "document_hash_anchors"
    __table_args__ = (
        CheckConstraint(
            "length(sha256) = 64",
            name="document_hash_anchor_sha256_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentHashClaim(Base):
    __tablename__ = "document_hash_claims"
    __table_args__ = (
        Index(
            "ix_document_hash_claims_anchor_claimed_at",
            "anchor_id",
            "claimed_at",
        ),
        Index(
            "ix_document_hash_claims_dossier_version_id",
            "dossier_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    anchor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DocumentHashAnchor.id, ondelete="RESTRICT"),
        nullable=False,
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(Dossier.id, ondelete="RESTRICT"),
        nullable=False,
    )
    dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    claimant_scope_type: Mapped[DocumentClaimantScope] = mapped_column(
        _enum(DocumentClaimantScope, "document_claimant_scope"),
        nullable=False,
    )
    claimant_scope_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentHashAdjudication(Base):
    __tablename__ = "document_hash_adjudications"
    __table_args__ = (
        CheckConstraint(
            "length(trim(reason)) >= 10",
            name="document_hash_adjudication_reason_length",
        ),
        UniqueConstraint(
            "anchor_id",
            "media_asset_id",
            "dossier_id",
            name="uq_document_hash_adjudication_target",
        ),
        Index(
            "ix_document_hash_adjudications_dossier_created_at",
            "dossier_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    anchor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DocumentHashAnchor.id, ondelete="RESTRICT"),
        nullable=False,
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(Dossier.id, ondelete="RESTRICT"),
        nullable=False,
    )
    claimant_scope_type: Mapped[DocumentClaimantScope] = mapped_column(
        _enum(DocumentClaimantScope, "document_adjudication_scope"),
        nullable=False,
    )
    claimant_scope_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[DocumentHashAdjudicationAction] = mapped_column(
        _enum(DocumentHashAdjudicationAction, "document_adjudication_action"),
        nullable=False,
        default=DocumentHashAdjudicationAction.ALLOW_REANCHOR,
        server_default=DocumentHashAdjudicationAction.ALLOW_REANCHOR.value,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DossierStatusHistory(Base):
    __tablename__ = "dossier_status_history"
    __table_args__ = (
        Index(
            "ix_dossier_status_history_dossier_created_at",
            "dossier_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[DossierStatus] = mapped_column(
        _enum(DossierStatus, "dossier_status_history_from"),
        nullable=False,
    )
    to_status: Mapped[DossierStatus] = mapped_column(
        _enum(DossierStatus, "dossier_status_history_to"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    reason_code: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DossierEvidence(Base):
    __tablename__ = "dossier_evidences"
    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="display_order_non_negative",
        ),
        Index(
            "ix_dossier_evidences_dossier_version_order",
            "dossier_id",
            "dossier_version_id",
            "display_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="CASCADE"),
        nullable=False,
    )
    dossier_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
