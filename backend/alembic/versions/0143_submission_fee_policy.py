"""Keep legacy fees and enable explicit pre-review charging for new dossiers."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0143_submission_fee_policy"
down_revision = "0142_auth_session_idle_timeout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column(
            "submission_fee_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "dossiers",
        sa.Column(
            "submission_fee_snapshot",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )
    op.add_column(
        "dossiers",
        sa.Column("submission_fee_paid_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(
        sa.text("SELECT count(*) FROM dossiers WHERE submission_fee_required = true")
    ):
        raise RuntimeError(
            "Cannot remove submission fee policy while new-policy dossiers exist."
        )
    op.drop_column("dossiers", "submission_fee_paid_at")
    op.drop_column("dossiers", "submission_fee_snapshot")
    op.drop_column("dossiers", "submission_fee_required")
