"""Add immutable certificate version lifecycle metadata.

Revision ID: 0047_certificate_version_lifecycle
Revises: 0046_similarity_review_cases
Create Date: 2026-08-11
"""

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0047_certificate_version_lifecycle"
down_revision: str | None = "0046_similarity_review_cases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION_STATUSES = (
    "PENDING_APPROVAL",
    "REJECTED",
    "ANCHOR_PENDING",
    "FAILED",
    "ACTIVE",
    "SUPERSEDED",
    "REVOKED",
)
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "certificate.version.request": ("APPLICANT", "ORG_MANAGER"),
    "certificate.version.decide": ("SUPER_ADMIN",),
}


def _authorization_tables() -> tuple[
    sa.TableClause,
    sa.TableClause,
    sa.TableClause,
]:
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


def _seed_permissions() -> None:
    bind = op.get_bind()
    permissions, roles, mappings = _authorization_tables()
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


def upgrade() -> None:
    with op.batch_alter_table("certificate_versions") as batch_op:
        batch_op.add_column(
            sa.Column("predecessor_version_id", sa.Uuid(), nullable=True)
        )
        batch_op.add_column(sa.Column("status", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("change_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("requested_by", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("decided_by", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("pdf_media_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_certificate_versions_predecessor",
            "certificate_versions",
            ["predecessor_version_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_certificate_versions_requested_by_users",
            "users",
            ["requested_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_certificate_versions_decided_by_users",
            "users",
            ["decided_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_certificate_versions_pdf_media",
            "media_assets",
            ["pdf_media_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Preserve the currently published version. Older rows remain immutable history.
    op.execute(
        sa.text(
            "UPDATE certificate_versions AS cv SET "
            "status = CASE WHEN cv.version_no = ("
            "SELECT c.current_version_no FROM certificates AS c "
            "WHERE c.id = cv.certificate_id"
            ") THEN 'ACTIVE' ELSE 'SUPERSEDED' END, "
            "pdf_media_id = CASE WHEN cv.version_no = ("
            "SELECT c.current_version_no FROM certificates AS c "
            "WHERE c.id = cv.certificate_id"
            ") THEN (SELECT c.pdf_media_id FROM certificates AS c "
            "WHERE c.id = cv.certificate_id) ELSE NULL END, "
            "predecessor_version_id = CASE WHEN cv.version_no > 1 THEN ("
            "SELECT previous.id FROM certificate_versions AS previous "
            "WHERE previous.certificate_id = cv.certificate_id "
            "AND previous.version_no = cv.version_no - 1"
            ") ELSE NULL END, "
            "change_reason = CASE WHEN cv.version_no > 1 "
            "THEN 'Imported from the existing certificate history.' "
            "ELSE NULL END"
        )
    )

    with op.batch_alter_table("certificate_versions") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=24),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "certificate_version_status",
            "status IN ("
            + ", ".join(f"'{status}'" for status in VERSION_STATUSES)
            + ")",
        )
        batch_op.create_check_constraint(
            "certificate_version_lineage",
            "(version_no = 1 AND predecessor_version_id IS NULL) OR "
            "(version_no > 1 AND predecessor_version_id IS NOT NULL "
            "AND length(trim(change_reason)) >= 20)",
        )

    op.create_index(
        "uq_certificate_versions_active",
        "certificate_versions",
        ["certificate_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ACTIVE'"),
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_certificate_versions_open_request",
        "certificate_versions",
        ["certificate_id"],
        unique=True,
        sqlite_where=sa.text(
            "status IN ('PENDING_APPROVAL', 'ANCHOR_PENDING', 'FAILED')"
        ),
        postgresql_where=sa.text(
            "status IN ('PENDING_APPROVAL', 'ANCHOR_PENDING', 'FAILED')"
        ),
    )

    with op.batch_alter_table("certificates") as batch_op:
        batch_op.add_column(
            sa.Column("revocation_reason_hash", sa.CHAR(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("revocation_transaction_id", sa.Uuid(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_certificates_revocation_transaction",
            "blockchain_transactions",
            ["revocation_transaction_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "certificate_revocation_reason_hash_format",
            "revocation_reason_hash IS NULL OR "
            "(length(revocation_reason_hash) = 64 "
            "AND revocation_reason_hash = lower(revocation_reason_hash))",
        )

    _seed_permissions()


def downgrade() -> None:
    bind = op.get_bind()
    permissions, _, mappings = _authorization_tables()
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

    with op.batch_alter_table("certificates") as batch_op:
        batch_op.drop_constraint(
            "certificate_revocation_reason_hash_format",
            type_="check",
        )
        batch_op.drop_constraint(
            "fk_certificates_revocation_transaction",
            type_="foreignkey",
        )
        batch_op.drop_column("revocation_transaction_id")
        batch_op.drop_column("revocation_reason_hash")

    op.drop_index(
        "uq_certificate_versions_open_request",
        table_name="certificate_versions",
    )
    op.drop_index(
        "uq_certificate_versions_active",
        table_name="certificate_versions",
    )
    with op.batch_alter_table("certificate_versions") as batch_op:
        batch_op.drop_constraint("certificate_version_lineage", type_="check")
        batch_op.drop_constraint("certificate_version_status", type_="check")
        batch_op.drop_constraint(
            "fk_certificate_versions_pdf_media",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_certificate_versions_decided_by_users",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_certificate_versions_requested_by_users",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_certificate_versions_predecessor",
            type_="foreignkey",
        )
        batch_op.drop_column("revoked_at")
        batch_op.drop_column("pdf_media_id")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("decided_at")
        batch_op.drop_column("decided_by")
        batch_op.drop_column("requested_at")
        batch_op.drop_column("requested_by")
        batch_op.drop_column("change_reason")
        batch_op.drop_column("status")
        batch_op.drop_column("predecessor_version_id")
