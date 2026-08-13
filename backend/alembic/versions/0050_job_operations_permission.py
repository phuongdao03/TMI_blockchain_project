"""Add privileged durable job management permission.

Revision ID: 0050_job_operations_permission
Revises: 0049_durable_jobs
Create Date: 2026-08-11
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0050_job_operations_permission"
down_revision: str | None = "0049_durable_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "operations.jobs.manage"
ROLE = "SUPER_ADMIN"


def _tables() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause]:
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
    return permissions, roles, mappings


def upgrade() -> None:
    bind = op.get_bind()
    permissions, roles, mappings = _tables()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            permissions.insert(),
            {"id": permission_id, "code": PERMISSION},
        )
    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.code == ROLE)
    ).scalar_one_or_none()
    if role_id is None:
        return
    exists = bind.execute(
        sa.select(mappings.c.role_id).where(
            mappings.c.role_id == role_id,
            mappings.c.permission_id == permission_id,
        )
    ).first()
    if exists is None:
        bind.execute(
            mappings.insert(),
            {"role_id": role_id, "permission_id": permission_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    permissions, _, mappings = _tables()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    ).scalar_one_or_none()
    if permission_id is None:
        return
    bind.execute(mappings.delete().where(mappings.c.permission_id == permission_id))
    bind.execute(permissions.delete().where(permissions.c.id == permission_id))
