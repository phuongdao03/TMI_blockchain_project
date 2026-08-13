"""Add staff dual-control requests and non-destructive disablement.

Revision ID: 0043_staff_privileged_actions
Revises: 0042_authorization_permissions
Create Date: 2026-08-10
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0043_staff_privileged_actions"
down_revision: str | None = "0042_authorization_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPROVE_PERMISSION = "admin.staff.approve"


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "privileged_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum(
                "ROLE_CHANGE",
                "MFA_RECOVERY",
                name="privileged_action_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "EXPIRED",
                name="privileged_action_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("requested_role_code", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
            "approved_by_user_id IS NULL OR "
            "approved_by_user_id != requested_by_user_id",
            name="ck_privileged_actions_distinct_approver",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_privileged_actions_approved_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_privileged_actions_requested_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_privileged_actions_target_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_privileged_actions"),
    )
    op.create_index(
        "ix_privileged_actions_status_expires",
        "privileged_actions",
        ["status", "expires_at"],
    )
    op.create_index(
        "uq_privileged_actions_pending_target_type",
        "privileged_actions",
        ["target_user_id", "action_type"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
        sqlite_where=sa.text("status = 'PENDING'"),
    )
    _seed_approval_permission()


def _seed_approval_permission() -> None:
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
    permission_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == APPROVE_PERMISSION)
    )
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            permissions.insert(), {"id": permission_id, "code": APPROVE_PERMISSION}
        )
    role_id = bind.scalar(sa.select(roles.c.id).where(roles.c.code == "SUPER_ADMIN"))
    if role_id is not None:
        existing = bind.scalar(
            sa.select(mappings.c.role_id).where(
                mappings.c.role_id == role_id,
                mappings.c.permission_id == permission_id,
            )
        )
        if existing is None:
            bind.execute(
                mappings.insert(),
                {"role_id": role_id, "permission_id": permission_id},
            )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    mappings = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == APPROVE_PERMISSION)
    )
    if permission_id is not None:
        bind.execute(mappings.delete().where(mappings.c.permission_id == permission_id))
        bind.execute(permissions.delete().where(permissions.c.id == permission_id))
    op.drop_index(
        "uq_privileged_actions_pending_target_type",
        table_name="privileged_actions",
    )
    op.drop_index(
        "ix_privileged_actions_status_expires", table_name="privileged_actions"
    )
    op.drop_table("privileged_actions")
    op.drop_column("users", "disabled_at")
