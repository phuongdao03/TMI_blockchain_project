"""Add fail-closed media inspection state.

Revision ID: 0044_secure_media_inspection
Revises: 0043_staff_privileged_actions
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0044_secure_media_inspection"
down_revision: str | None = "0043_staff_privileged_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_MEDIA_STATUS = ("PENDING", "ACTIVE", "QUARANTINED", "DELETED")
NEW_MEDIA_STATUS = (*OLD_MEDIA_STATUS[:-1], "REJECTED", OLD_MEDIA_STATUS[-1])


def _status_check(values: tuple[str, ...]) -> str:
    serialized = ", ".join(f"'{value}'" for value in values)
    return f"status IN ({serialized})"


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint("media_status", type_="check")
        batch_op.create_check_constraint(
            "media_status",
            _status_check(NEW_MEDIA_STATUS),
        )
        batch_op.add_column(
            sa.Column(
                "inspection_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("inspection_reason_code", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_check_constraint(
            "inspection_attempts_non_negative",
            "inspection_attempts >= 0",
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE media_assets SET status = 'QUARANTINED' "
            "WHERE status = 'REJECTED'"
        )
    )
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint(
            "inspection_attempts_non_negative",
            type_="check",
        )
        batch_op.drop_constraint("media_status", type_="check")
        batch_op.create_check_constraint(
            "media_status",
            _status_check(OLD_MEDIA_STATUS),
        )
        batch_op.drop_column("inspected_at")
        batch_op.drop_column("inspection_reason_code")
        batch_op.drop_column("inspection_attempts")
