"""Add human wallet signing state without storing wallet secrets.

Revision ID: 0057_blockchain_human_signing
Revises: 0056_review_assessment_findings
Create Date: 2026-08-23
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0057_blockchain_human_signing"
down_revision: str | None = "0056_review_assessment_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "blockchain.sign"
ROLE = "BLOCKCHAIN_ADMIN"


def upgrade() -> None:
    with op.batch_alter_table("blockchain_transactions") as batch:
        batch.add_column(sa.Column("signer_user_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("signer_wallet_address", sa.CHAR(length=42), nullable=True)
        )
        batch.create_foreign_key(
            "fk_blockchain_transactions_signer_user",
            "users",
            ["signer_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "blockchain_wallet_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_address", sa.CHAR(length=42), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="ACTIVE"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(wallet_address) = 42", name="blockchain_wallet_link_address_length"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED')", name="blockchain_wallet_link_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "wallet_address", name="uq_blockchain_wallet_links_wallet_address"
        ),
    )
    op.create_index(
        "uq_blockchain_wallet_links_one_active",
        "blockchain_wallet_links",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_blockchain_wallet_links_user_active",
        "blockchain_wallet_links",
        ["user_id", "is_active"],
    )
    op.create_table(
        "blockchain_wallet_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_address", sa.CHAR(length=42), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("nonce_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(nonce_hash) = 64",
            name="blockchain_wallet_challenge_nonce_hash_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nonce_hash", name="uq_blockchain_wallet_challenges_nonce_hash"
        ),
    )
    op.create_index(
        "ix_blockchain_wallet_challenges_user_expires",
        "blockchain_wallet_challenges",
        ["user_id", "expires_at"],
    )
    op.create_table(
        "blockchain_transaction_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("signer_user_id", sa.Uuid(), nullable=False),
        sa.Column("expected_wallet_address", sa.CHAR(length=42), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.CHAR(length=42), nullable=False),
        sa.Column("proof_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("encoded_call_hash", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="PREPARED"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(proof_hash) = 64", name="blockchain_intent_proof_hash_length"
        ),
        sa.CheckConstraint(
            "length(encoded_call_hash) = 64",
            name="blockchain_intent_encoded_call_hash_length",
        ),
        sa.CheckConstraint("chain_id > 0", name="blockchain_intent_chain_id_positive"),
        sa.CheckConstraint(
            "status IN ('PREPARED', 'SUBMITTED', 'EXPIRED', 'CANCELLED')",
            name="blockchain_transaction_intent_status",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["blockchain_transactions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"], ["dossier_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["signer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_blockchain_transaction_intents_open",
        "blockchain_transaction_intents",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PREPARED'"),
        sqlite_where=sa.text("status = 'PREPARED'"),
    )
    op.create_index(
        "ix_blockchain_transaction_intents_status_expires",
        "blockchain_transaction_intents",
        ["status", "expires_at"],
    )
    _seed_permission()


def _seed_permission() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    roles = sa.table(
        "roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    mappings = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(permissions.insert().values(id=permission_id, code=PERMISSION))
    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.code == ROLE)
    ).scalar_one_or_none()
    if (
        role_id is not None
        and bind.execute(
            sa.select(mappings.c.role_id).where(
                mappings.c.role_id == role_id, mappings.c.permission_id == permission_id
            )
        ).first()
        is None
    ):
        bind.execute(
            mappings.insert().values(role_id=role_id, permission_id=permission_id)
        )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    mappings = sa.table("role_permissions", sa.column("permission_id", sa.Uuid()))
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is not None:
        bind.execute(mappings.delete().where(mappings.c.permission_id == permission_id))
        bind.execute(permissions.delete().where(permissions.c.id == permission_id))
    op.drop_index(
        "ix_blockchain_transaction_intents_status_expires",
        table_name="blockchain_transaction_intents",
    )
    op.drop_index(
        "uq_blockchain_transaction_intents_open",
        table_name="blockchain_transaction_intents",
    )
    op.drop_table("blockchain_transaction_intents")
    op.drop_index(
        "ix_blockchain_wallet_challenges_user_expires",
        table_name="blockchain_wallet_challenges",
    )
    op.drop_table("blockchain_wallet_challenges")
    op.drop_index(
        "ix_blockchain_wallet_links_user_active", table_name="blockchain_wallet_links"
    )
    op.drop_index(
        "uq_blockchain_wallet_links_one_active", table_name="blockchain_wallet_links"
    )
    op.drop_table("blockchain_wallet_links")
    with op.batch_alter_table("blockchain_transactions") as batch:
        batch.drop_constraint(
            "fk_blockchain_transactions_signer_user", type_="foreignkey"
        )
        batch.drop_column("signer_wallet_address")
        batch.drop_column("signer_user_id")
