from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class BlockchainTransactionStatus(StrEnum):
    CREATED = "CREATED"
    SIGNING = "SIGNING"
    BROADCAST = "BROADCAST"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REPLACED = "REPLACED"


class BlockchainWalletLinkStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class BlockchainTransactionIntentStatus(StrEnum):
    PREPARED = "PREPARED"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CertificateStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CertificateVersionStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"
    ANCHOR_PENDING = "ANCHOR_PENDING"
    FAILED = "FAILED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class DocumentEvidenceStatus(StrEnum):
    QUEUED = "EVIDENCE_QUEUED"
    BROADCAST = "EVIDENCE_BROADCAST"
    CONFIRMED = "EVIDENCE_CONFIRMED"
    FAILED = "EVIDENCE_FAILED"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


BLOCKCHAIN_JSON = JSONB().with_variant(JSON(), "sqlite")


class Certificate(UtcTimestampMixin, Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            "current_version_no > 0",
            name="current_version_no_positive",
        ),
        CheckConstraint(
            "revocation_reason_hash IS NULL OR "
            "(length(revocation_reason_hash) = 64 "
            "AND revocation_reason_hash = lower(revocation_reason_hash))",
            name="certificate_revocation_reason_hash_format",
        ),
        Index("ix_certificates_dossier_status", "dossier_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    certificate_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CertificateStatus] = mapped_column(
        _enum(CertificateStatus, "certificate_status"),
        nullable=False,
        default=CertificateStatus.ACTIVE,
        server_default=CertificateStatus.ACTIVE.value,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason_hash: Mapped[str | None] = mapped_column(CHAR(64))
    revocation_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blockchain_transactions.id", ondelete="RESTRICT"),
    )
    public_token_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
        unique=True,
    )
    pdf_media_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
    )
    qr_payload: Mapped[str] = mapped_column(Text, nullable=False)


class DocumentBlockchainEvidence(UtcTimestampMixin, Base):
    __tablename__ = "document_blockchain_evidences"
    __table_args__ = (
        CheckConstraint(
            "length(evidence_key) = 64 AND length(commitment) = 64 "
            "AND length(submitter_reference) = 64",
            name="document_blockchain_evidence_hash_lengths",
        ),
        CheckConstraint(
            "(version_no = 1 AND predecessor_evidence_id IS NULL) OR "
            "(version_no > 1 AND predecessor_evidence_id IS NOT NULL)",
            name="document_blockchain_evidence_lineage",
        ),
        Index(
            "ix_document_blockchain_evidences_status_recorded_at",
            "status",
            "recorded_at",
        ),
        Index(
            "ix_document_blockchain_evidences_dossier_version_id",
            "dossier_id",
            "dossier_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_hash_claim_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("document_hash_claims.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
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
    evidence_key: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    commitment: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    submitter_reference: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_blockchain_evidences.id", ondelete="RESTRICT"),
        unique=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[DocumentEvidenceStatus] = mapped_column(
        _enum(DocumentEvidenceStatus, "document_blockchain_evidence_status"),
        nullable=False,
        default=DocumentEvidenceStatus.QUEUED,
        server_default=DocumentEvidenceStatus.QUEUED.value,
    )


class BlockchainTransaction(UtcTimestampMixin, Base):
    __tablename__ = "blockchain_transactions"
    __table_args__ = (
        CheckConstraint("chain_id > 0", name="chain_id_positive"),
        CheckConstraint(
            "confirmations >= 0",
            name="confirmations_non_negative",
        ),
        UniqueConstraint(
            "dossier_version_id",
            "network",
            "contract_address",
            "method",
            "payload_hash",
            name="uq_blockchain_transactions_idempotent_request",
        ),
        Index(
            "ix_blockchain_transactions_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
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
    certificate_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("certificates.id", ondelete="RESTRICT"),
    )
    document_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_blockchain_evidences.id", ondelete="RESTRICT"),
        unique=True,
    )
    signer_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    signer_wallet_address: Mapped[str | None] = mapped_column(CHAR(42))
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(CHAR(42), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(
        CHAR(66),
        unique=True,
    )
    nonce: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[BlockchainTransactionStatus] = mapped_column(
        _enum(BlockchainTransactionStatus, "blockchain_tx_status"),
        nullable=False,
        default=BlockchainTransactionStatus.CREATED,
        server_default=BlockchainTransactionStatus.CREATED.value,
    )
    confirmations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    receipt_block_number: Mapped[int | None] = mapped_column(BigInteger)
    receipt_block_hash: Mapped[str | None] = mapped_column(CHAR(66))
    receipt_event_name: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    broadcast_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockchainWalletLink(UtcTimestampMixin, Base):
    """A verified public wallet bound to a THV user, never a wallet secret."""

    __tablename__ = "blockchain_wallet_links"
    __table_args__ = (
        CheckConstraint(
            "length(wallet_address) = 42",
            name="blockchain_wallet_link_address_length",
        ),
        Index(
            "uq_blockchain_wallet_links_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
        Index(
            "ix_blockchain_wallet_links_user_active",
            "user_id",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    wallet_address: Mapped[str] = mapped_column(
        CHAR(42),
        nullable=False,
        unique=True,
    )
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[BlockchainWalletLinkStatus] = mapped_column(
        _enum(BlockchainWalletLinkStatus, "blockchain_wallet_link_status"),
        nullable=False,
        default=BlockchainWalletLinkStatus.ACTIVE,
        server_default=BlockchainWalletLinkStatus.ACTIVE.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockchainWalletChallenge(Base):
    __tablename__ = "blockchain_wallet_challenges"
    __table_args__ = (
        CheckConstraint(
            "length(nonce_hash) = 64",
            name="blockchain_wallet_challenge_nonce_hash_length",
        ),
        Index(
            "ix_blockchain_wallet_challenges_user_expires",
            "user_id",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    wallet_address: Mapped[str] = mapped_column(CHAR(42), nullable=False)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nonce_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BlockchainTransactionIntent(UtcTimestampMixin, Base):
    __tablename__ = "blockchain_transaction_intents"
    __table_args__ = (
        CheckConstraint(
            "length(proof_hash) = 64", name="blockchain_intent_proof_hash_length"
        ),
        CheckConstraint(
            "length(encoded_call_hash) = 64",
            name="blockchain_intent_encoded_call_hash_length",
        ),
        CheckConstraint("chain_id > 0", name="blockchain_intent_chain_id_positive"),
        Index(
            "uq_blockchain_transaction_intents_open",
            "transaction_id",
            unique=True,
            postgresql_where=text("status = 'PREPARED'"),
            sqlite_where=text("status = 'PREPARED'"),
        ),
        Index(
            "ix_blockchain_transaction_intents_status_expires",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blockchain_transactions.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    signer_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expected_wallet_address: Mapped[str] = mapped_column(CHAR(42), nullable=False)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(CHAR(42), nullable=False)
    proof_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    encoded_call_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[BlockchainTransactionIntentStatus] = mapped_column(
        _enum(
            BlockchainTransactionIntentStatus,
            "blockchain_transaction_intent_status",
        ),
        nullable=False,
        default=BlockchainTransactionIntentStatus.PREPARED,
        server_default=BlockchainTransactionIntentStatus.PREPARED.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CertificateVersion(Base):
    __tablename__ = "certificate_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        CheckConstraint(
            "(version_no = 1 AND predecessor_version_id IS NULL) OR "
            "(version_no > 1 AND predecessor_version_id IS NOT NULL "
            "AND length(trim(change_reason)) >= 20)",
            name="certificate_version_lineage",
        ),
        UniqueConstraint(
            "certificate_id",
            "version_no",
            name="uq_certificate_versions_certificate_id_version_no",
        ),
        UniqueConstraint(
            "public_token_hash",
            name="uq_certificate_versions_public_token_hash",
        ),
        Index(
            "uq_certificate_versions_active",
            "certificate_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_certificate_versions_open_request",
            "certificate_id",
            unique=True,
            sqlite_where=text(
                "status IN ('PENDING_APPROVAL', 'ANCHOR_PENDING', 'FAILED')"
            ),
            postgresql_where=text(
                "status IN ('PENDING_APPROVAL', 'ANCHOR_PENDING', 'FAILED')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    certificate_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("certificate_versions.id", ondelete="RESTRICT"),
    )
    dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        BLOCKCHAIN_JSON,
        nullable=False,
    )
    metadata_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    # A QR token identifies one issued version, never the mutable certificate
    # aggregate.  Values stay nullable for certificates issued before the
    # version-aware QR migration; new versions always receive both values.
    public_token_hash: Mapped[str | None] = mapped_column(
        CHAR(64),
    )
    qr_payload: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CertificateVersionStatus] = mapped_column(
        _enum(CertificateVersionStatus, "certificate_version_status"),
        nullable=False,
        default=CertificateVersionStatus.ACTIVE,
    )
    change_reason: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    pdf_media_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blockchain_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blockchain_transactions.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
