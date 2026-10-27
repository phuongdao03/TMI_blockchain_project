"""Account-scoped recovery before a dossier draft is created."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0144_dossier_preparations"
down_revision = "0143_submission_fee_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dossier_preparations",
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(none_as_null=True).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
        ),
        sa.Column("consumed_revision", sa.Integer()),
        sa.Column(
            "created_dossier_id",
            sa.Uuid(),
            sa.ForeignKey("dossiers.id", ondelete="SET NULL"),
        ),
        sa.Column("creation_fingerprint", sa.String(64)),
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
        sa.CheckConstraint("revision > 0", name="revision_positive"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM dossier_preparations WHERE payload_json IS NOT NULL"
        )
    ):
        raise RuntimeError(
            "Active dossier preparations must be preserved before downgrade."
        )
    op.drop_table("dossier_preparations")
