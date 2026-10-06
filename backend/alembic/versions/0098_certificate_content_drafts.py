"""Review certificate content before the first metadata hash is frozen.

Revision ID: 0098_certificate_content_drafts
Revises: 0097_seed_public_work_categories
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0098_certificate_content_drafts"
down_revision: str | None = "0097_seed_public_work_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certificate_content_drafts",
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column(
            "content_json", JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("dossier_id"),
    )

    # Dossiers approved before this release must pass the same review gate.
    bind = op.get_bind()
    dossiers = sa.table(
        "dossiers",
        sa.column("id", sa.Uuid()),
        sa.column("status", sa.String()),
        sa.column("current_version_no", sa.Integer()),
    )
    versions = sa.table(
        "dossier_versions",
        sa.column("dossier_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("snapshot_json", JSONB().with_variant(sa.JSON(), "sqlite")),
    )
    certificates = sa.table("certificates", sa.column("dossier_id", sa.Uuid()))
    drafts = sa.table(
        "certificate_content_drafts",
        sa.column("dossier_id", sa.Uuid()),
        sa.column("content_json", JSONB().with_variant(sa.JSON(), "sqlite")),
    )
    rows = bind.execute(
        sa.select(dossiers.c.id, versions.c.snapshot_json)
        .join(
            versions,
            sa.and_(
                versions.c.dossier_id == dossiers.c.id,
                versions.c.version_no == dossiers.c.current_version_no,
            ),
        )
        .outerjoin(certificates, certificates.c.dossier_id == dossiers.c.id)
        .where(
            dossiers.c.status.in_(("APPROVED", "PAYMENT_PENDING", "PAID")),
            certificates.c.dossier_id.is_(None),
        )
    )
    for dossier_id, snapshot in rows:
        dossier = snapshot.get("dossier", {}) if isinstance(snapshot, dict) else {}
        dossier = dossier if isinstance(dossier, dict) else {}
        category = dossier.get("category", {})
        category = category if isinstance(category, dict) else {}
        bind.execute(
            sa.insert(drafts).values(
                dossier_id=dossier_id,
                content_json={
                    "title": str(dossier.get("title") or "Chưa đặt tên")[:255],
                    "summary": str(dossier.get("summary") or "")[:5000],
                    "subject": "",
                    "category": str(category.get("name") or "Chưa phân loại")[:255],
                },
            )
        )


def downgrade() -> None:
    op.drop_table("certificate_content_drafts")
