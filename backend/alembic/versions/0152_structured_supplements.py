"""Add supplement requests and immutable response/decision entries."""

import sqlalchemy as sa

from alembic import op

revision = "0152_structured_supplements"
down_revision = "0151_type_narrative_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplement_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "dossier_id",
            sa.Uuid(),
            sa.ForeignKey("dossiers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "requested_version_id",
            sa.Uuid(),
            sa.ForeignKey("dossier_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("criterion_key", sa.String(64), nullable=False),
        sa.Column("criterion_label", sa.String(255), nullable=False),
        sa.Column("claim_id", sa.Uuid()),
        sa.Column("requested_information", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ANSWERED', 'RESOLVED')", name="status_valid"
        ),
        sa.CheckConstraint("priority IN ('NORMAL', 'HIGH')", name="priority_valid"),
        sa.CheckConstraint("revision >= 0", name="revision_non_negative"),
    )
    op.create_index(
        "ix_supplement_requests_dossier_status",
        "supplement_requests",
        ["dossier_id", "status"],
    )
    op.create_table(
        "supplement_responses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "request_id",
            sa.Uuid(),
            sa.ForeignKey("supplement_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('RESPONSE', 'RESOLVE', 'REOPEN')", name="kind_valid"
        ),
        sa.UniqueConstraint(
            "request_id", "sequence_no", name="uq_supplement_response_sequence"
        ),
    )
    op.create_index(
        "ix_supplement_responses_request_created",
        "supplement_responses",
        ["request_id", "created_at"],
    )


def downgrade() -> None:
    for table_name in ("supplement_requests", "supplement_responses"):
        if op.get_bind().scalar(
            sa.select(sa.func.count()).select_from(sa.table(table_name))
        ):
            raise RuntimeError("Supplement history exists; retain it and roll forward.")
    op.drop_table("supplement_responses")
    op.drop_table("supplement_requests")
