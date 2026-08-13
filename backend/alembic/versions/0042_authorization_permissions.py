"""Seed production authorization permissions.

Revision ID: 0042_authorization_permissions
Revises: 0041_blockchain_receipt_proof
Create Date: 2026-08-10
"""

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0042_authorization_permissions"
down_revision: str | None = "0041_blockchain_receipt_proof"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "admin.staff.manage": ("SUPER_ADMIN",),
    "audit.read": ("SUPER_ADMIN",),
    "blockchain.manage": ("BLOCKCHAIN_ADMIN", "SUPER_ADMIN"),
    "certificate.read": ("APPLICANT", "ORG_MANAGER", "SUPER_ADMIN"),
    "cms.manage": ("CONTENT_ADMIN", "SUPER_ADMIN"),
    "council.manage": ("COUNCIL_SECRETARY", "SUPER_ADMIN"),
    "council.vote": ("COUNCIL_MEMBER",),
    "dossier.manage": ("APPLICANT", "ORG_MANAGER"),
    "engagement.qr.manage": ("CONTENT_ADMIN", "SUPER_ADMIN"),
    "operations.read": ("FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"),
    "payment.create": ("APPLICANT", "ORG_MANAGER"),
    "payment.manage": ("FINANCE_ADMIN", "SUPER_ADMIN"),
    "public_content.manage": ("CONTENT_ADMIN", "SUPER_ADMIN"),
    "ranking.manage": ("SUPER_ADMIN",),
    "review.assign": ("SUPER_ADMIN",),
    "review.submit": ("REVIEWER",),
    "search.analytics.read": ("CONTENT_ADMIN", "SUPER_ADMIN"),
}


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
    permission_codes = tuple(ROLE_PERMISSIONS)
    role_codes = tuple(
        sorted({role for allowed in ROLE_PERMISSIONS.values() for role in allowed})
    )
    existing_codes = set(bind.execute(sa.select(permissions.c.code)).scalars())
    missing = [
        {"id": uuid4(), "code": code}
        for code in permission_codes
        if code not in existing_codes
    ]
    if missing:
        bind.execute(permissions.insert(), missing)

    permission_ids: dict[str, UUID] = {
        cast(str, code): cast(UUID, permission_id)
        for code, permission_id in bind.execute(
            sa.select(permissions.c.code, permissions.c.id).where(
                permissions.c.code.in_(permission_codes)
            )
        ).all()
    }
    role_ids: dict[str, UUID] = {
        cast(str, code): cast(UUID, role_id)
        for code, role_id in bind.execute(
            sa.select(roles.c.code, roles.c.id).where(roles.c.code.in_(role_codes))
        ).all()
    }
    expected = {
        (role_ids[role_code], permission_ids[permission_code])
        for permission_code, allowed_roles in ROLE_PERMISSIONS.items()
        for role_code in allowed_roles
        if role_code in role_ids
    }
    existing = set(
        bind.execute(
            sa.select(mappings.c.role_id, mappings.c.permission_id).where(
                mappings.c.permission_id.in_(permission_ids.values())
            )
        ).all()
    )
    pending = [
        {"role_id": role_id, "permission_id": permission_id}
        for role_id, permission_id in expected - existing
    ]
    if pending:
        bind.execute(mappings.insert(), pending)


def downgrade() -> None:
    bind = op.get_bind()
    permissions, _, mappings = _tables()
    permission_codes = tuple(ROLE_PERMISSIONS)
    permission_ids = tuple(
        bind.execute(
            sa.select(permissions.c.id).where(permissions.c.code.in_(permission_codes))
        ).scalars()
    )
    if permission_ids:
        bind.execute(
            mappings.delete().where(mappings.c.permission_id.in_(permission_ids))
        )
    bind.execute(permissions.delete().where(permissions.c.code.in_(permission_codes)))
