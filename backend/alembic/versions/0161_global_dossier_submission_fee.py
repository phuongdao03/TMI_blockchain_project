"""Allow a global dossier submission fee policy."""

import sqlalchemy as sa

from alembic import op

revision = "0161_global_dossier_submission_fee"
down_revision = "0160_dynamic_dossier_fees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fee_policies") as batch:
        batch.alter_column(
            "dossier_type_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
    op.create_index(
        "uq_fee_policy_global_version",
        "fee_policies",
        ["fee_type", "version_no"],
        unique=True,
        postgresql_where=sa.text("dossier_type_id IS NULL"),
        sqlite_where=sa.text("dossier_type_id IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    global_policy_count = int(
        bind.scalar(
            sa.text("SELECT count(*) FROM fee_policies WHERE dossier_type_id IS NULL")
        )
        or 0
    )
    if global_policy_count:
        raise RuntimeError(
            "Cannot downgrade while global fee policies exist; "
            "preserve fee policy history."
        )

    op.drop_index("uq_fee_policy_global_version", table_name="fee_policies")
    with op.batch_alter_table("fee_policies") as batch:
        batch.alter_column(
            "dossier_type_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
