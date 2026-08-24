"""Restrict consolidated moderators to dossier review capabilities.

Revision ID: 0061_moderator_permissions
Revises: 0060_certificate_version_qr
Create Date: 2026-08-24
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0061_moderator_permissions"
down_revision: str | None = "0060_certificate_version_qr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Moderators can assess assigned dossiers and resolve similarity checks.  All
# operational, financial, publishing and blockchain capabilities are reserved
# for SUPER_ADMIN.
MODERATOR_PERMISSION_CODES = ("review.submit", "similarity.review")


def _tables() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause]:
    return (
        sa.table(
            "roles",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
        ),
        sa.table(
            "permissions",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
        ),
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.Uuid()),
            sa.column("permission_id", sa.Uuid()),
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    roles, permissions, role_permissions = _tables()
    moderator_id = bind.scalar(sa.select(roles.c.id).where(roles.c.code == "MODERATOR"))
    if moderator_id is None:
        return

    permission_ids: dict[str, UUID] = {
        str(code): permission_id
        for code, permission_id in bind.execute(
            sa.select(permissions.c.code, permissions.c.id).where(
                permissions.c.code.in_(MODERATOR_PERMISSION_CODES)
            )
        ).all()
    }
    bind.execute(
        role_permissions.delete().where(role_permissions.c.role_id == moderator_id)
    )
    mappings = [
        {"role_id": moderator_id, "permission_id": permission_ids[code]}
        for code in MODERATOR_PERMISSION_CODES
        if code in permission_ids
    ]
    if mappings:
        bind.execute(role_permissions.insert(), mappings)


def downgrade() -> None:
    # Do not silently restore the legacy union of privileged permissions.
    # Downgrading 0058 restores its preserved legacy authorization snapshot.
    return
