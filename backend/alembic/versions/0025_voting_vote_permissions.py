"""Seed redacted vote operations permission.

Revision ID: 0025_voting_vote_permissions
Revises: 0024_vote_aggregates
Create Date: 2026-08-03
"""

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0025_voting_vote_permissions"
down_revision: str | None = "0024_vote_aggregates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_CODE = "voting.vote.read"
ADMIN_ROLE_CODES = ("CONTENT_ADMIN", "SUPER_ADMIN")


def _tables() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause]:
    return (
        sa.table(
            "permissions",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
        ),
        sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String())),
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.Uuid()),
            sa.column("permission_id", sa.Uuid()),
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    permissions, roles, mappings = _tables()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar_one_or_none()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            permissions.insert().values(id=permission_id, code=PERMISSION_CODE)
        )
    role_ids = tuple(
        bind.execute(
            sa.select(roles.c.id).where(roles.c.code.in_(ADMIN_ROLE_CODES))
        ).scalars()
    )
    existing = set(
        bind.execute(
            sa.select(mappings.c.role_id).where(
                mappings.c.permission_id == permission_id,
                mappings.c.role_id.in_(role_ids),
            )
        ).scalars()
    )
    pending = [
        {"role_id": role_id, "permission_id": cast(UUID, permission_id)}
        for role_id in role_ids
        if role_id not in existing
    ]
    if pending:
        bind.execute(mappings.insert(), pending)


def downgrade() -> None:
    bind = op.get_bind()
    permissions, _, mappings = _tables()
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar_one_or_none()
    if permission_id is not None:
        bind.execute(mappings.delete().where(mappings.c.permission_id == permission_id))
    bind.execute(permissions.delete().where(permissions.c.code == PERMISSION_CODE))
