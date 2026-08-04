from typing import cast

from sqlalchemy import Table, UniqueConstraint

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
)


def test_blockchain_and_certificate_models_follow_status_catalog() -> None:
    assert tuple(BlockchainTransactionStatus) == (
        BlockchainTransactionStatus.CREATED,
        BlockchainTransactionStatus.SIGNING,
        BlockchainTransactionStatus.BROADCAST,
        BlockchainTransactionStatus.CONFIRMED,
        BlockchainTransactionStatus.FAILED,
        BlockchainTransactionStatus.REPLACED,
    )
    assert tuple(CertificateStatus) == (
        CertificateStatus.ACTIVE,
        CertificateStatus.EXPIRED,
        CertificateStatus.REVOKED,
    )
    assert BlockchainTransaction.__tablename__ == "blockchain_transactions"
    assert Certificate.__tablename__ == "certificates"
    assert any(
        isinstance(constraint, UniqueConstraint)
        and constraint.name == "uq_certificate_versions_certificate_id_version_no"
        for constraint in cast(Table, CertificateVersion.__table__).constraints
    )
