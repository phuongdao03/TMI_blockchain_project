"""Add a responsible employee to each department.

Revision ID: 0124_department_lead
Revises: 0123_rename_fee_guides
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0124_department_lead"
down_revision: str | None = "0123_rename_fee_guides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("departments") as batch:
        batch.add_column(sa.Column("manager_employee_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_departments_manager_employee_id_employees",
            "employees",
            ["manager_employee_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("departments") as batch:
        batch.drop_constraint(
            "fk_departments_manager_employee_id_employees",
            type_="foreignkey",
        )
        batch.drop_column("manager_employee_id")
