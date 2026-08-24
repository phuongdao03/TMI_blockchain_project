"""Bind certificate QR verification tokens to immutable versions.

Revision ID: 0060_certificate_version_qr
Revises: 0059_document_rule_visibility
Create Date: 2026-08-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0060_certificate_version_qr"
down_revision: str | None = "0059_document_rule_visibility"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable fields preserve compatibility for rejected/legacy records.  New
    # issuance and correction code always writes both values before a version
    # can become publicly verifiable.
    with op.batch_alter_table("certificate_versions") as batch:
        batch.add_column(sa.Column("public_token_hash", sa.CHAR(length=64)))
        batch.add_column(sa.Column("qr_payload", sa.Text()))
        batch.create_unique_constraint(
            "uq_certificate_versions_public_token_hash",
            ["public_token_hash"],
        )

    # Preserve current QR links from the pre-version-aware model.  Historical
    # legacy versions had never been assigned distinct tokens, so they remain
    # unlinked rather than being mapped unsafely to the current content.
    certificate_versions = sa.table(
        "certificate_versions",
        sa.column("id", sa.Uuid()),
        sa.column("certificate_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("public_token_hash", sa.CHAR(length=64)),
        sa.column("qr_payload", sa.Text()),
    )
    certificates = sa.table(
        "certificates",
        sa.column("id", sa.Uuid()),
        sa.column("current_version_no", sa.Integer()),
        sa.column("public_token_hash", sa.CHAR(length=64)),
        sa.column("qr_payload", sa.Text()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            certificate_versions.c.id,
            certificates.c.public_token_hash,
            certificates.c.qr_payload,
        )
        .join(
            certificates,
            certificates.c.id == certificate_versions.c.certificate_id,
        )
        .where(
            certificate_versions.c.version_no
            == certificates.c.current_version_no
        )
    ).mappings()
    for row in rows:
        bind.execute(
            sa.update(certificate_versions)
            .where(certificate_versions.c.id == row["id"])
            .values(
                public_token_hash=row["public_token_hash"],
                qr_payload=row["qr_payload"],
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("certificate_versions") as batch:
        batch.drop_constraint(
            "uq_certificate_versions_public_token_hash",
            type_="unique",
        )
        batch.drop_column("qr_payload")
        batch.drop_column("public_token_hash")
