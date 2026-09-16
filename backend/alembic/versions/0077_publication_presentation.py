"""Persist video cover time and certificate listing preference."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0077_publication_presentation"
down_revision: str | None = "0076_large_video_evidence_limit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("public_work_media") as batch:
        batch.add_column(sa.Column("poster_time_ms", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            "poster_time_supported",
            "poster_time_ms IS NULL OR "
            "(poster_time_ms >= 0 AND poster_time_ms <= 86400000)",
        )
    with op.batch_alter_table("public_works") as batch:
        batch.add_column(
            sa.Column(
                "show_certificate",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("public_works") as batch:
        batch.drop_column("show_certificate")
    with op.batch_alter_table("public_work_media") as batch:
        batch.drop_constraint("poster_time_supported", type_="check")
        batch.drop_column("poster_time_ms")
