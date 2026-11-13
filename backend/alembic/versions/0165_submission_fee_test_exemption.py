"""Add a narrow test-only submission fee exemption to existing users."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0165_submission_fee_test_exemption"
down_revision = "0164_affiliate_short_codes_and_two_levels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "submission_fee_test_exemption",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "submission_fee_test_exemption_changed_at", sa.DateTime(timezone=True)
            )
        )
        batch.add_column(
            sa.Column("submission_fee_test_exemption_changed_by_user_id", sa.Uuid())
        )
        batch.create_foreign_key(
            "fk_users_submission_fee_test_exemption_actor",
            "users",
            ["submission_fee_test_exemption_changed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint(
            "fk_users_submission_fee_test_exemption_actor", type_="foreignkey"
        )
        batch.drop_column("submission_fee_test_exemption_changed_by_user_id")
        batch.drop_column("submission_fee_test_exemption_changed_at")
        batch.drop_column("submission_fee_test_exemption")
