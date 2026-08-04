"""Add OAuth identities and public viewer account intent.

Revision ID: 0019_oauth_identities
Revises: 0018_search_foundation
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_oauth_identities"
down_revision: str | None = "0018_search_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCOUNT_TYPE_CONSTRAINT = "users_account_type_valid"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint(
            ACCOUNT_TYPE_CONSTRAINT,
            "users",
            type_="check",
        )
        op.create_check_constraint(
            ACCOUNT_TYPE_CONSTRAINT,
            "users",
            "account_type IS NULL OR account_type IN "
            "('PUBLIC_USER', 'INDIVIDUAL_APPLICANT', "
            "'ORGANIZATION_APPLICANT')",
        )

    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=True,
        )
    if bind.dialect.name == "sqlite":
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_nocase "
            "ON users(email COLLATE NOCASE)"
        )

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("provider IN ('GOOGLE')", name="auth_provider"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_auth_identities_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_identities"),
    )
    op.create_index(
        "uq_auth_identities_provider_subject",
        "auth_identities",
        ["provider", "provider_subject"],
        unique=True,
    )
    op.create_index(
        "uq_auth_identities_user_provider",
        "auth_identities",
        ["user_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    incompatible_users = bind.scalar(
        sa.text(
            "SELECT count(*) FROM users "
            "WHERE password_hash IS NULL OR account_type = 'PUBLIC_USER'"
        )
    )
    if incompatible_users:
        raise RuntimeError(
            "Cannot downgrade OAuth identities while provider-only or "
            "PUBLIC_USER accounts exist."
        )

    op.drop_index(
        "uq_auth_identities_user_provider",
        table_name="auth_identities",
    )
    op.drop_index(
        "uq_auth_identities_provider_subject",
        table_name="auth_identities",
    )
    op.drop_table("auth_identities")
    if bind.dialect.name == "sqlite":
        op.drop_index("ux_users_email_nocase", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=False,
        )
    if bind.dialect.name == "sqlite":
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_nocase "
            "ON users(email COLLATE NOCASE)"
        )
    if bind.dialect.name != "sqlite":
        op.drop_constraint(
            ACCOUNT_TYPE_CONSTRAINT,
            "users",
            type_="check",
        )
        op.create_check_constraint(
            ACCOUNT_TYPE_CONSTRAINT,
            "users",
            "account_type IS NULL OR account_type IN "
            "('INDIVIDUAL_APPLICANT', 'ORGANIZATION_APPLICANT')",
        )
