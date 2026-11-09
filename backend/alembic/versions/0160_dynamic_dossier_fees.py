"""Add dynamic, versioned dossier fee policies and snapshots."""

from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0160_dynamic_dossier_fees"
down_revision = "0159_media_upload_sessions"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "billing.fees.read",
    "billing.fees.policies.create",
    "billing.fees.policies.approve",
    "billing.fees.policies.cancel",
    "billing.fees.obligations.manage",
    "billing.fees.waivers.request",
    "billing.fees.waivers.approve",
)


def upgrade() -> None:
    with op.batch_alter_table("dossiers") as batch:
        batch.add_column(
            sa.Column(
                "submission_fee_policy_mode",
                sa.String(length=16),
                nullable=False,
                server_default="LEGACY",
            )
        )
        batch.create_check_constraint(
            "ck_dossiers_submission_fee_policy_mode",
            "submission_fee_policy_mode IN ('LEGACY', 'DYNAMIC')",
        )
        batch.add_column(
            sa.Column(
                "submission_fee_waived_at", sa.DateTime(timezone=True), nullable=True
            )
        )

    op.create_table(
        "fee_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fee_type", sa.String(length=64), nullable=False),
        sa.Column("dossier_type_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="VND"
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="DRAFT"
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("version_no > 0", name="version_no_positive"),
        sa.CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        sa.CheckConstraint("currency = 'VND'", name="currency_vnd"),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="effective_interval_valid"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SCHEDULED', 'ACTIVE', 'EXPIRED', 'CANCELLED')",
            name="fee_policy_status",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CANCELLED') OR approved_at IS NOT NULL",
            name="approved_policy_has_timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_type_id"], ["dossier_types.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fee_type", "dossier_type_id", "version_no", name="uq_fee_policy_version"
        ),
    )
    op.create_index(
        "ix_fee_policies_scope_effective",
        "fee_policies",
        ["fee_type", "dossier_type_id", "status", "starts_at", "ends_at"],
    )
    op.create_table(
        "fee_policy_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column(
            "before_json",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "after_json",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["fee_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fee_policy_events_policy_created",
        "fee_policy_events",
        ["policy_id", "created_at"],
    )
    op.create_table(
        "fee_waivers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("fee_type", sa.String(length=64), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="VND"
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="REQUESTED"
        ),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'REDEEMED', 'EXPIRED')",
            name="fee_waiver_status",
        ),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dossier_id", "fee_type", name="uq_fee_waiver_scope"),
    )
    op.create_index(
        "ix_fee_waivers_status_expires", "fee_waivers", ["status", "expires_at"]
    )

    with op.batch_alter_table("fee_obligations") as batch:
        batch.drop_constraint("uq_fee_obligations_dossier_id", type_="unique")
        batch.drop_constraint("amount_minor_positive", type_="check")
        batch.create_check_constraint("amount_minor_non_negative", "amount_minor >= 0")
        batch.alter_column(
            "price_catalog_version_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch.alter_column(
            "price_catalog_entry_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch.add_column(sa.Column("fee_type", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("fee_policy_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("fee_policy_version_no", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column("gross_amount_minor", sa.BigInteger(), nullable=True)
        )
        batch.add_column(
            sa.Column("waiver_amount_minor", sa.BigInteger(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_fee_obligations_fee_policy_id_fee_policies",
            "fee_policies",
            ["fee_policy_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "uq_fee_obligations_dossier_fee_type",
        "fee_obligations",
        ["dossier_id", "fee_type"],
        unique=True,
        postgresql_where=sa.text("fee_type IS NOT NULL"),
        sqlite_where=sa.text("fee_type IS NOT NULL"),
    )
    op.create_index(
        "uq_fee_obligations_legacy_dossier_id",
        "fee_obligations",
        ["dossier_id"],
        unique=True,
        postgresql_where=sa.text("fee_type IS NULL"),
        sqlite_where=sa.text("fee_type IS NULL"),
    )

    permission_table = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(128))
    )
    existing = set(
        op.get_bind().scalars(
            sa.select(permission_table.c.code).where(
                permission_table.c.code.in_(PERMISSIONS)
            )
        )
    )
    additions = [
        {"id": uuid5(NAMESPACE_URL, f"cns-permission:{code}"), "code": code}
        for code in PERMISSIONS
        if code not in existing
    ]
    if additions:
        op.bulk_insert(permission_table, additions)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(
        sa.text("SELECT count(*) FROM fee_obligations WHERE fee_policy_id IS NOT NULL")
    ):
        raise RuntimeError(
            "Fee policy obligations exist; roll forward to preserve snapshots."
        )
    if bind.scalar(sa.text("SELECT count(*) FROM fee_policies")):
        raise RuntimeError("Fee policy history exists; roll forward to preserve it.")
    if bind.scalar(sa.text("SELECT count(*) FROM fee_waivers")):
        raise RuntimeError("Fee waiver history exists; roll forward to preserve it.")
    if bind.scalar(
        sa.text(
            "SELECT count(*) FROM dossiers WHERE submission_fee_policy_mode = 'DYNAMIC'"
        )
    ):
        raise RuntimeError(
            "Dynamic fee dossiers exist; roll forward to preserve policy mode."
        )
    if bind.scalar(
        sa.text(
            "SELECT count(*) FROM (SELECT dossier_id FROM fee_obligations "
            "GROUP BY dossier_id HAVING count(*) > 1) duplicate_dossiers"
        )
    ):
        raise RuntimeError(
            "Multiple fee obligations exist for a dossier; roll forward."
        )

    permission_table = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(128))
    )
    for table_name, column_name in (
        ("role_permissions", "permission_id"),
        ("user_permissions", "permission_id"),
    ):
        reference_table = sa.table(table_name, sa.column(column_name, sa.Uuid()))
        assigned = bind.scalar(
            sa.select(sa.func.count())
            .select_from(
                reference_table.join(
                    permission_table,
                    reference_table.c[column_name] == permission_table.c.id,
                )
            )
            .where(permission_table.c.code.in_(PERMISSIONS))
        )
        if assigned:
            raise RuntimeError(
                "Fee permissions are assigned; remove assignments and roll forward."
            )
    bind.execute(
        permission_table.delete().where(permission_table.c.code.in_(PERMISSIONS))
    )

    op.drop_index("uq_fee_obligations_legacy_dossier_id", table_name="fee_obligations")
    op.drop_index("uq_fee_obligations_dossier_fee_type", table_name="fee_obligations")
    with op.batch_alter_table("fee_obligations") as batch:
        batch.drop_constraint(
            "fk_fee_obligations_fee_policy_id_fee_policies", type_="foreignkey"
        )
        batch.drop_column("waiver_amount_minor")
        batch.drop_column("gross_amount_minor")
        batch.drop_column("fee_policy_version_no")
        batch.drop_column("fee_policy_id")
        batch.drop_column("fee_type")
        batch.drop_constraint("amount_minor_non_negative", type_="check")
        batch.create_check_constraint("amount_minor_positive", "amount_minor > 0")
        batch.alter_column(
            "price_catalog_version_id", existing_type=sa.Uuid(), nullable=False
        )
        batch.alter_column(
            "price_catalog_entry_id", existing_type=sa.Uuid(), nullable=False
        )
        batch.create_unique_constraint("uq_fee_obligations_dossier_id", ["dossier_id"])

    op.drop_index("ix_fee_waivers_status_expires", table_name="fee_waivers")
    op.drop_table("fee_waivers")
    op.drop_index("ix_fee_policy_events_policy_created", table_name="fee_policy_events")
    op.drop_table("fee_policy_events")
    op.drop_index("ix_fee_policies_scope_effective", table_name="fee_policies")
    op.drop_table("fee_policies")
    with op.batch_alter_table("dossiers") as batch:
        batch.drop_constraint("ck_dossiers_submission_fee_policy_mode", type_="check")
        batch.drop_column("submission_fee_policy_mode")
        batch.drop_column("submission_fee_waived_at")
