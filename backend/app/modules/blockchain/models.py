from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
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


class CertificateStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


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
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    broadcast_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CertificateVersion(Base):
    __tablename__ = "certificate_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        UniqueConstraint(
            "certificate_id",
            "version_no",
            name="uq_certificate_versions_certificate_id_version_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    certificate_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
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
    blockchain_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blockchain_transactions.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
