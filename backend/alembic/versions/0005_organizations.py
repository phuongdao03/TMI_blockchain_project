"""Create organizations and scoped memberships.

Revision ID: 0005_organizations
Revises: 0004_user_profiles
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_organizations"
down_revision: str | None = "0004_user_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORGANIZATION_STATUS = ("ACTIVE", "ARCHIVED")
MEMBERSHIP_ROLE = ("OWNER", "ORG_MANAGER", "MEMBER")
MEMBERSHIP_STATUS = ("INVITED", "ACTIVE")


def _timestamps() -> tuple[sa.Column[sa.DateTime], ...]:
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
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("tax_code_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *ORGANIZATION_STATUS,
                name="organization_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_organizations_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("code", name="uq_organizations_code"),
    )
    op.create_table(
        "organization_members",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role_code",
            sa.Enum(
                *MEMBERSHIP_ROLE,
                name="membership_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                *MEMBERSHIP_STATUS,
                name="membership_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_members_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_organization_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "user_id",
            name="pk_organization_members",
        ),
    )
    op.create_index(
        "ix_organization_members_user_id",
        "organization_members",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("organization_members")
    op.drop_table("organizations")
