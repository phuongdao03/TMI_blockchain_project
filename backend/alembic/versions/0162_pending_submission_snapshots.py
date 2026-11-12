"""Allow version snapshots to remain unsubmitted while fees are pending."""

import sqlalchemy as sa

from alembic import op

revision = "0162_pending_submission_snapshots"
down_revision = "0161_global_dossier_submission_fee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dossier_versions") as batch:
        batch.alter_column(
            "submitted_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    pending_count = int(
        bind.scalar(
            sa.text("SELECT count(*) FROM dossier_versions WHERE submitted_at IS NULL")
        )
        or 0
    )
    if pending_count:
        raise RuntimeError("Cannot downgrade while pending submission snapshots exist.")
    with op.batch_alter_table("dossier_versions") as batch:
        batch.alter_column(
            "submitted_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
