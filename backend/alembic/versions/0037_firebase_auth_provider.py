"""Allow Firebase-backed Google identities.

Revision ID: 0037_firebase_auth_provider
Revises: 0036_dossier_content_claims
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037_firebase_auth_provider"
down_revision: str | None = "0036_dossier_content_claims"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_identities", recreate="always") as batch:
            batch.drop_constraint("auth_provider", type_="check")
            batch.create_check_constraint(
                "auth_provider", "provider IN ('GOOGLE', 'FIREBASE')"
            )
        return
    op.drop_constraint("auth_provider", "auth_identities", type_="check")
    op.create_check_constraint(
        "auth_provider",
        "auth_identities",
        "provider IN ('GOOGLE', 'FIREBASE')",
    )


def downgrade() -> None:
    bind = op.get_bind()
    firebase_count = bind.scalar(
        sa.text("SELECT count(*) FROM auth_identities WHERE provider = 'FIREBASE'")
    )
    if firebase_count:
        raise RuntimeError("Cannot downgrade while Firebase identities exist.")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_identities", recreate="always") as batch:
            batch.drop_constraint("auth_provider", type_="check")
            batch.create_check_constraint("auth_provider", "provider IN ('GOOGLE')")
        return
    op.drop_constraint("auth_provider", "auth_identities", type_="check")
    op.create_check_constraint(
        "auth_provider",
        "auth_identities",
        "provider IN ('GOOGLE')",
    )
