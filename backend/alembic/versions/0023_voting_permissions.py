"""Seed fine-grained voting campaign permissions.

Revision ID: 0023_voting_permissions
Revises: 0022_voting_foundation
Create Date: 2026-08-03
"""

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0023_voting_permissions"
down_revision: str | None = "0022_voting_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_CODES = ("voting.campaign.read", "voting.campaign.manage")
ADMIN_ROLE_CODES = ("CONTENT_ADMIN", "SUPER_ADMIN")


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
    existing = set(bind.execute(sa.select(permissions.c.code)).scalars())
    missing_permissions = [
        {"id": uuid4(), "code": code}
        for code in PERMISSION_CODES
        if code not in existing
    ]
    if missing_permissions:
        bind.execute(permissions.insert(), missing_permissions)
    permission_rows: dict[str, UUID] = {
        cast(str, row[0]): cast(UUID, row[1])
        for row in bind.execute(
            sa.select(permissions.c.code, permissions.c.id).where(
                permissions.c.code.in_(PERMISSION_CODES)
            )
        ).all()
    }
    role_rows: dict[str, UUID] = {
        cast(str, row[0]): cast(UUID, row[1])
        for row in bind.execute(
            sa.select(roles.c.code, roles.c.id).where(
                roles.c.code.in_(ADMIN_ROLE_CODES)
            )
        ).all()
    }
    existing_mappings = set(
        bind.execute(
            sa.select(mappings.c.role_id, mappings.c.permission_id).where(
                mappings.c.role_id.in_(role_rows.values()),
                mappings.c.permission_id.in_(permission_rows.values()),
            )
        ).all()
    )
    pending = [
        {"role_id": role_id, "permission_id": permission_id}
        for role_id in role_rows.values()
        for permission_id in permission_rows.values()
        if (role_id, permission_id) not in existing_mappings
    ]
    if pending:
        bind.execute(mappings.insert(), pending)


def downgrade() -> None:
    bind = op.get_bind()
    permissions, _, mappings = _tables()
    permission_ids = tuple(
        bind.execute(
            sa.select(permissions.c.id).where(permissions.c.code.in_(PERMISSION_CODES))
        ).scalars()
    )
    if permission_ids:
        bind.execute(
            mappings.delete().where(mappings.c.permission_id.in_(permission_ids))
        )
    bind.execute(permissions.delete().where(permissions.c.code.in_(PERMISSION_CODES)))
