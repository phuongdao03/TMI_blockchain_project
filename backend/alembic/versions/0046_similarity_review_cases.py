"""Add private near-duplicate similarity review cases.

Revision ID: 0046_similarity_review_cases
Revises: 0045_trusted_media_provenance
Create Date: 2026-08-10
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0046_similarity_review_cases"
down_revision: str | None = "0045_trusted_media_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "similarity.review"


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("perceptual_hash", sa.CHAR(length=16), nullable=True),
    )
    op.create_table(
        "similarity_review_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "left_dossier_version_id",
            sa.Uuid(),
            sa.ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "right_dossier_version_id",
            sa.Uuid(),
            sa.ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("signal_type", sa.String(length=16), nullable=False),
        sa.Column("text_score", sa.Float(), nullable=True),
        sa.Column("image_distance", sa.SmallInteger(), nullable=True),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "assigned_reviewer_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "assigned_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("disposition", sa.String(length=16), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "left_dossier_version_id != right_dossier_version_id",
            name="similarity_distinct_versions",
        ),
        sa.CheckConstraint(
            "signal_type IN ('TEXT', 'IMAGE')",
            name="similarity_signal_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ASSIGNED', 'RESOLVED')",
            name="similarity_case_status",
        ),
        sa.CheckConstraint(
            "disposition IS NULL OR "
            "disposition IN ('DISTINCT', 'RELATED', 'SAME_WORK')",
            name="similarity_disposition",
        ),
        sa.CheckConstraint(
            "(signal_type = 'TEXT' AND text_score BETWEEN 0 AND 1 "
            "AND image_distance IS NULL) OR "
            "(signal_type = 'IMAGE' AND image_distance BETWEEN 0 AND 64 "
            "AND text_score IS NULL)",
            name="similarity_signal_value",
        ),
        sa.CheckConstraint(
            "(status = 'OPEN' AND assigned_reviewer_user_id IS NULL "
            "AND assigned_by IS NULL AND assigned_at IS NULL) OR "
            "(status = 'ASSIGNED' AND assigned_reviewer_user_id IS NOT NULL "
            "AND assigned_by IS NOT NULL AND assigned_at IS NOT NULL) OR "
            "(status = 'RESOLVED' AND assigned_reviewer_user_id IS NOT NULL "
            "AND disposition IS NOT NULL AND length(trim(resolution_reason)) >= 20 "
            "AND resolved_at IS NOT NULL)",
            name="similarity_case_lifecycle",
        ),
        sa.UniqueConstraint(
            "left_dossier_version_id",
            "right_dossier_version_id",
            "signal_type",
            "policy_version",
            name="uq_similarity_case_pair_signal_policy",
        ),
    )
    op.create_index(
        "ix_similarity_cases_reviewer_status_created",
        "similarity_review_cases",
        ["assigned_reviewer_user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_similarity_cases_status_created",
        "similarity_review_cases",
        ["status", "created_at"],
    )

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
    bind = op.get_bind()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            permissions.insert().values(id=permission_id, code=PERMISSION)
        )
    reviewer_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.code == "REVIEWER")
    ).scalar_one_or_none()
    if reviewer_id is not None:
        bind.execute(
            mappings.insert().values(
                role_id=reviewer_id,
                permission_id=permission_id,
            )
        )


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    mappings = sa.table(
        "role_permissions",
        sa.column("permission_id", sa.Uuid()),
    )
    bind = op.get_bind()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is not None:
        bind.execute(
            mappings.delete().where(mappings.c.permission_id == permission_id)
        )
        bind.execute(permissions.delete().where(permissions.c.id == permission_id))
    op.drop_index(
        "ix_similarity_cases_status_created",
        table_name="similarity_review_cases",
    )
    op.drop_index(
        "ix_similarity_cases_reviewer_status_created",
        table_name="similarity_review_cases",
    )
    op.drop_table("similarity_review_cases")
    op.drop_column("media_assets", "perceptual_hash")
