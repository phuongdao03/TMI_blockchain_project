"""Consolidate THV authorization into four product roles.

Revision ID: 0058_four_product_roles
Revises: 0057_blockchain_human_signing
Create Date: 2026-08-23
"""

import json
from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0058_four_product_roles"
down_revision: str | None = "0057_blockchain_human_signing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCT_ROLES = ("VIEWER", "USER", "MODERATOR", "SUPER_ADMIN")
USER_LEGACY_ROLES = frozenset({"APPLICANT", "ORG_MANAGER"})
# A moderator may assess assigned dossiers only.  Legacy operational roles are
# consolidated into MODERATOR for account continuity, never for permission
# inheritance: CMS, council, payment and blockchain administration remain
# SUPER_ADMIN responsibilities.
MODERATOR_PERMISSION_CODES = frozenset({"review.submit", "similarity.review"})
MODERATOR_LEGACY_ROLES = frozenset(
    {
        "REVIEWER",
        "COUNCIL_MEMBER",
        "COUNCIL_SECRETARY",
        "FINANCE_ADMIN",
        "CONTENT_ADMIN",
        "BLOCKCHAIN_ADMIN",
    }
)
ROLE_TARGETS = {
    **{role: "USER" for role in USER_LEGACY_ROLES},
    **{role: "MODERATOR" for role in MODERATOR_LEGACY_ROLES},
    "SUPER_ADMIN": "SUPER_ADMIN",
}
APPLICANT_ACCOUNT_TYPES = frozenset({"INDIVIDUAL_APPLICANT", "ORGANIZATION_APPLICANT"})


def _tables() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause, sa.TableClause]:
    return (
        sa.table(
            "users",
            sa.column("id", sa.Uuid()),
            sa.column("account_type", sa.String()),
        ),
        sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String())),
        sa.table(
            "user_roles",
            sa.column("user_id", sa.Uuid()),
            sa.column("role_id", sa.Uuid()),
        ),
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.Uuid()),
            sa.column("permission_id", sa.Uuid()),
        ),
    )


def _backup_tables() -> tuple[
    sa.TableClause,
    sa.TableClause,
    sa.TableClause,
    sa.TableClause,
    sa.TableClause,
    sa.TableClause,
]:
    return (
        sa.table(
            "role_consolidation_legacy_roles",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
        ),
        sa.table(
            "role_consolidation_legacy_user_roles",
            sa.column("user_id", sa.Uuid()),
            sa.column("role_code", sa.String()),
        ),
        sa.table(
            "role_consolidation_legacy_role_permissions",
            sa.column("role_code", sa.String()),
            sa.column("permission_code", sa.String()),
        ),
        sa.table(
            "role_consolidation_legacy_staff_invitations",
            sa.column("id", sa.Uuid()),
            sa.column("role_code", sa.String()),
        ),
        sa.table(
            "role_consolidation_legacy_privileged_actions",
            sa.column("id", sa.Uuid()),
            sa.column("requested_role_code", sa.String()),
        ),
        sa.table(
            "role_consolidation_legacy_voting_campaigns",
            sa.column("id", sa.Uuid()),
            sa.column("eligibility_rules", sa.JSON()),
        ),
    )


def _create_backups() -> None:
    op.create_table(
        "role_consolidation_legacy_roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
    )
    op.create_table(
        "role_consolidation_legacy_user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_code", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "role_code"),
    )
    op.create_table(
        "role_consolidation_legacy_role_permissions",
        sa.Column("role_code", sa.String(length=64), nullable=False),
        sa.Column("permission_code", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("role_code", "permission_code"),
    )
    op.create_table(
        "role_consolidation_legacy_staff_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("role_code", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "role_consolidation_legacy_privileged_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("requested_role_code", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "role_consolidation_legacy_voting_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("eligibility_rules", sa.JSON(), nullable=False),
    )


def _target_role(role_codes: set[str], account_type: str | None) -> str:
    if "SUPER_ADMIN" in role_codes:
        return "SUPER_ADMIN"
    if role_codes.intersection(MODERATOR_LEGACY_ROLES):
        return "MODERATOR"
    if role_codes.intersection(USER_LEGACY_ROLES) or (
        account_type in APPLICANT_ACCOUNT_TYPES
    ):
        return "USER"
    return "VIEWER"


def _remap_role_code(role_code: str | None) -> str | None:
    if role_code is None:
        return None
    fallback = role_code if role_code in PRODUCT_ROLES else "VIEWER"
    return ROLE_TARGETS.get(role_code, fallback)


def _remap_eligibility_rules(value: Any) -> dict[str, object] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    raw_roles = value.get("allowed_roles")
    if not isinstance(raw_roles, list):
        return dict(value)
    mapped_roles = list(
        dict.fromkeys(
            _remap_role_code(role)
            for role in raw_roles
            if isinstance(role, str) and _remap_role_code(role) is not None
        )
    )
    result = dict(value)
    result["allowed_roles"] = mapped_roles
    return result


def upgrade() -> None:
    bind = op.get_bind()
    users, roles, user_roles, role_permissions = _tables()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    _create_backups()
    (
        legacy_roles,
        legacy_user_roles,
        legacy_role_permissions,
        legacy_invitations,
        legacy_actions,
        legacy_campaigns,
    ) = _backup_tables()

    original_roles = list(bind.execute(sa.select(roles.c.id, roles.c.code)).mappings())
    original_assignments = list(
        bind.execute(
            sa.select(user_roles.c.user_id, roles.c.code.label("role_code")).join(
                roles, roles.c.id == user_roles.c.role_id
            )
        ).mappings()
    )
    original_permissions = list(
        bind.execute(
            sa.select(
                roles.c.code.label("role_code"),
                permissions.c.code.label("permission_code"),
            )
            .select_from(role_permissions)
            .join(roles, roles.c.id == role_permissions.c.role_id)
            .join(permissions, permissions.c.id == role_permissions.c.permission_id)
        ).mappings()
    )
    if original_roles:
        bind.execute(legacy_roles.insert(), [dict(row) for row in original_roles])
    if original_assignments:
        bind.execute(
            legacy_user_roles.insert(), [dict(row) for row in original_assignments]
        )
    if original_permissions:
        bind.execute(
            legacy_role_permissions.insert(),
            [dict(row) for row in original_permissions],
        )

    invitation_rows = list(
        bind.execute(sa.text("SELECT id, role_code FROM staff_invitations")).mappings()
    )
    action_rows = list(
        bind.execute(
            sa.text("SELECT id, requested_role_code FROM privileged_actions")
        ).mappings()
    )
    campaign_rows = list(
        bind.execute(
            sa.text("SELECT id, eligibility_rules FROM voting_campaigns")
        ).mappings()
    )
    if invitation_rows:
        bind.execute(
            legacy_invitations.insert(),
            [dict(row) for row in invitation_rows],
        )
    if action_rows:
        bind.execute(legacy_actions.insert(), [dict(row) for row in action_rows])
    if campaign_rows:
        bind.execute(legacy_campaigns.insert(), [dict(row) for row in campaign_rows])

    roles_by_user: defaultdict[UUID, set[str]] = defaultdict(set)
    for assignment in original_assignments:
        roles_by_user[assignment["user_id"]].add(str(assignment["role_code"]))
    all_users = list(
        bind.execute(sa.select(users.c.id, users.c.account_type)).mappings()
    )

    bind.execute(user_roles.delete())
    bind.execute(role_permissions.delete())
    bind.execute(roles.delete())

    product_role_ids = {code: uuid4() for code in PRODUCT_ROLES}
    bind.execute(
        roles.insert(),
        [{"id": role_id, "code": code} for code, role_id in product_role_ids.items()],
    )
    assignments = [
        {
            "user_id": row["id"],
            "role_id": product_role_ids[
                _target_role(
                    roles_by_user[row["id"]],
                    (
                        str(row["account_type"])
                        if row["account_type"] is not None
                        else None
                    ),
                )
            ],
        }
        for row in all_users
    ]
    if assignments:
        bind.execute(user_roles.insert(), assignments)

    permission_ids = {
        str(row["code"]): row["id"]
        for row in bind.execute(
            sa.select(permissions.c.id, permissions.c.code)
        ).mappings()
    }
    previous_permissions: defaultdict[str, set[str]] = defaultdict(set)
    for row in original_permissions:
        previous_permissions[str(row["role_code"])].add(str(row["permission_code"]))
    user_permissions = set().union(
        *(previous_permissions[role] for role in USER_LEGACY_ROLES)
    )
    product_permissions = {
        "VIEWER": set(),
        "USER": user_permissions,
        "MODERATOR": MODERATOR_PERMISSION_CODES,
        "SUPER_ADMIN": set(permission_ids),
    }
    mappings = [
        {"role_id": product_role_ids[role], "permission_id": permission_ids[code]}
        for role, codes in product_permissions.items()
        for code in codes
        if code in permission_ids
    ]
    if mappings:
        bind.execute(role_permissions.insert(), mappings)

    for row in invitation_rows:
        bind.execute(
            sa.text(
                "UPDATE staff_invitations SET role_code = :role_code WHERE id = :id"
            ),
            {"id": row["id"], "role_code": _remap_role_code(str(row["role_code"]))},
        )
    for row in action_rows:
        bind.execute(
            sa.text(
                "UPDATE privileged_actions SET requested_role_code = "
                ":role_code WHERE id = :id"
            ),
            {
                "id": row["id"],
                "role_code": _remap_role_code(
                    str(row["requested_role_code"])
                    if row["requested_role_code"] is not None
                    else None
                ),
            },
        )
    for row in campaign_rows:
        rules = _remap_eligibility_rules(row["eligibility_rules"])
        if rules is not None:
            bind.execute(
                sa.text(
                    "UPDATE voting_campaigns SET eligibility_rules = "
                    ":eligibility_rules WHERE id = :id"
                ),
                {"id": row["id"], "eligibility_rules": json.dumps(rules)},
            )


def downgrade() -> None:
    bind = op.get_bind()
    _, roles, user_roles, role_permissions = _tables()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    (
        legacy_roles,
        legacy_user_roles,
        legacy_role_permissions,
        legacy_invitations,
        legacy_actions,
        legacy_campaigns,
    ) = _backup_tables()

    role_rows = list(
        bind.execute(sa.select(legacy_roles.c.id, legacy_roles.c.code)).mappings()
    )
    assignment_rows = list(
        bind.execute(
            sa.select(legacy_user_roles.c.user_id, legacy_user_roles.c.role_code)
        ).mappings()
    )
    permission_rows = list(
        bind.execute(
            sa.select(
                legacy_role_permissions.c.role_code,
                legacy_role_permissions.c.permission_code,
            )
        ).mappings()
    )

    bind.execute(user_roles.delete())
    bind.execute(role_permissions.delete())
    bind.execute(roles.delete())
    if role_rows:
        bind.execute(roles.insert(), [dict(row) for row in role_rows])

    role_ids = {
        str(row["code"]): row["id"]
        for row in bind.execute(sa.select(roles.c.id, roles.c.code)).mappings()
    }
    restored_assignments = [
        {"user_id": row["user_id"], "role_id": role_ids[str(row["role_code"])]}
        for row in assignment_rows
        if str(row["role_code"]) in role_ids
    ]
    if restored_assignments:
        bind.execute(user_roles.insert(), restored_assignments)
    permission_ids = {
        str(row["code"]): row["id"]
        for row in bind.execute(
            sa.select(permissions.c.id, permissions.c.code)
        ).mappings()
    }
    restored_permissions = [
        {
            "role_id": role_ids[str(row["role_code"])],
            "permission_id": permission_ids[str(row["permission_code"])],
        }
        for row in permission_rows
        if str(row["role_code"]) in role_ids
        and str(row["permission_code"]) in permission_ids
    ]
    if restored_permissions:
        bind.execute(role_permissions.insert(), restored_permissions)

    invitation_rows = bind.execute(
        sa.select(legacy_invitations.c.id, legacy_invitations.c.role_code)
    ).mappings()
    for row in invitation_rows:
        bind.execute(
            sa.text(
                "UPDATE staff_invitations SET role_code = :role_code WHERE id = :id"
            ),
            dict(row),
        )
    for row in bind.execute(
        sa.select(legacy_actions.c.id, legacy_actions.c.requested_role_code)
    ).mappings():
        bind.execute(
            sa.text(
                "UPDATE privileged_actions SET requested_role_code = "
                ":requested_role_code WHERE id = :id"
            ),
            dict(row),
        )
    for row in bind.execute(
        sa.select(legacy_campaigns.c.id, legacy_campaigns.c.eligibility_rules)
    ).mappings():
        bind.execute(
            sa.text(
                "UPDATE voting_campaigns SET eligibility_rules = "
                ":eligibility_rules WHERE id = :id"
            ),
            {
                "id": row["id"],
                "eligibility_rules": json.dumps(row["eligibility_rules"]),
            },
        )

    op.drop_table("role_consolidation_legacy_voting_campaigns")
    op.drop_table("role_consolidation_legacy_privileged_actions")
    op.drop_table("role_consolidation_legacy_staff_invitations")
    op.drop_table("role_consolidation_legacy_role_permissions")
    op.drop_table("role_consolidation_legacy_user_roles")
    op.drop_table("role_consolidation_legacy_roles")
