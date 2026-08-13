"""Add exact document hash claims and adjudication.

Revision ID: 0052_document_hash_claims
Revises: 0051_private_media_encryption
Create Date: 2026-08-12
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0052_document_hash_claims"
down_revision: str | None = "0051_private_media_encryption"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_CODE = "document_claim.override"


def upgrade() -> None:
    op.create_table(
        "document_hash_anchors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(sha256) = 64",
            name="document_hash_anchor_sha256_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_hash_anchors"),
        sa.UniqueConstraint(
            "sha256",
            name="uq_document_hash_anchors_sha256",
        ),
    )
    op.create_table(
        "document_hash_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anchor_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("claimant_scope_type", sa.String(length=16), nullable=False),
        sa.Column("claimant_scope_id", sa.Uuid(), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "claimant_scope_type IN ('USER', 'ORGANIZATION')",
            name="document_hash_claim_scope_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["anchor_id"],
            ["document_hash_anchors.id"],
            name="fk_document_hash_claims_anchor_id_anchors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_document_hash_claims_media_asset_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_document_hash_claims_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name="fk_document_hash_claims_version_id_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_hash_claims"),
        sa.UniqueConstraint(
            "media_asset_id",
            name="uq_document_hash_claims_media_asset_id",
        ),
    )
    op.create_index(
        "ix_document_hash_claims_anchor_claimed_at",
        "document_hash_claims",
        ["anchor_id", "claimed_at"],
    )
    op.create_index(
        "ix_document_hash_claims_dossier_version_id",
        "document_hash_claims",
        ["dossier_version_id"],
    )
    op.create_table(
        "document_hash_adjudications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anchor_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("claimant_scope_type", sa.String(length=16), nullable=False),
        sa.Column("claimant_scope_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.String(length=32),
            nullable=False,
            server_default="ALLOW_REANCHOR",
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "claimant_scope_type IN ('USER', 'ORGANIZATION')",
            name="document_hash_adjudication_scope_type_valid",
        ),
        sa.CheckConstraint(
            "action = 'ALLOW_REANCHOR'",
            name="document_hash_adjudication_action_valid",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) >= 10",
            name="document_hash_adjudication_reason_length",
        ),
        sa.ForeignKeyConstraint(
            ["anchor_id"],
            ["document_hash_anchors.id"],
            name="fk_document_hash_adjudications_anchor_id_anchors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_document_hash_adjudications_media_asset_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_document_hash_adjudications_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_document_hash_adjudications_actor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_hash_adjudications"),
        sa.UniqueConstraint(
            "anchor_id",
            "media_asset_id",
            "dossier_id",
            name="uq_document_hash_adjudication_target",
        ),
    )
    op.create_index(
        "ix_document_hash_adjudications_dossier_created_at",
        "document_hash_adjudications",
        ["dossier_id", "created_at"],
    )
    _seed_permission()


def _seed_permission() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    mappings = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            permissions.insert().values(
                id=permission_id,
                code=PERMISSION_CODE,
            )
        )
    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.code == "SUPER_ADMIN")
    ).scalar_one_or_none()
    if role_id is not None:
        existing = bind.execute(
            sa.select(mappings.c.role_id).where(
                mappings.c.role_id == role_id,
                mappings.c.permission_id == permission_id,
            )
        ).first()
        if existing is None:
            bind.execute(
                mappings.insert().values(
                    role_id=role_id,
                    permission_id=permission_id,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    mappings = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar_one_or_none()
    if permission_id is not None:
        bind.execute(mappings.delete().where(mappings.c.permission_id == permission_id))
        bind.execute(permissions.delete().where(permissions.c.id == permission_id))
    op.drop_index(
        "ix_document_hash_adjudications_dossier_created_at",
        table_name="document_hash_adjudications",
    )
    op.drop_table("document_hash_adjudications")
    op.drop_index(
        "ix_document_hash_claims_dossier_version_id",
        table_name="document_hash_claims",
    )
    op.drop_index(
        "ix_document_hash_claims_anchor_claimed_at",
        table_name="document_hash_claims",
    )
    op.drop_table("document_hash_claims")
    op.drop_table("document_hash_anchors")
