"""Create authentication, RBAC, session, and verification token tables.

Revision ID: 0002_auth_schema
Revises: 0001_baseline
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_auth_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_STATUSES = ("PENDING", "ACTIVE", "SUSPENDED", "DELETED")
POSTGRES_USER_STATUS = postgresql.ENUM(
    *USER_STATUSES,
    name="user_status",
    create_type=False,
)


def _timestamp_columns() -> tuple[sa.Column[sa.DateTime], ...]:
    return (
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
    )


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if is_postgresql:
        op.execute("CREATE EXTENSION IF NOT EXISTS citext")
        POSTGRES_USER_STATUS.create(bind, checkfirst=True)
        email_type: sa.types.TypeEngine[str] = postgresql.CITEXT()
        user_status_type: sa.types.TypeEngine[str] = POSTGRES_USER_STATUS
    else:
        email_type = sa.String(collation="NOCASE")
        user_status_type = sa.Enum(
            *USER_STATUSES,
            name="user_status",
            native_enum=False,
            create_constraint=True,
        )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", email_type, nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "status",
            user_status_type,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_role_permissions_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "role_id",
            "permission_id",
            name="pk_role_permissions",
        ),
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_user_roles_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_roles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "refresh_token_hash",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_id", sa.Uuid(), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["rotated_from_id"],
            ["auth_sessions.id"],
            name="fk_auth_sessions_rotated_from_id_auth_sessions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_auth_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint(
            "refresh_token_hash",
            name="uq_auth_sessions_refresh_token_hash",
        ),
    )
    op.create_index(
        "ix_auth_sessions_user_id_expires_at",
        "auth_sessions",
        ["user_id", "expires_at"],
    )
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_verification_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_tokens"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_verification_tokens_token_hash",
        ),
    )
    op.create_index(
        "ix_verification_tokens_user_id_purpose",
        "verification_tokens",
        ["user_id", "purpose"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("verification_tokens")
    op.drop_table("auth_sessions")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")

    if bind.dialect.name == "postgresql":
        POSTGRES_USER_STATUS.drop(bind, checkfirst=True)
        op.execute("DROP EXTENSION IF EXISTS citext")
