"""Store editorial image cover crop without altering retained source assets."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0078_editorial_covers"
down_revision: str | None = "0077_publication_presentation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("public_work_media") as batch:
        for name, default in [
            ("cover_x", "50"),
            ("cover_y", "50"),
            ("cover_zoom", "100"),
        ]:
            batch.add_column(
                sa.Column(name, sa.Integer(), nullable=False, server_default=default)
            )
        batch.create_check_constraint(
            "cover_crop_supported",
            "cover_x BETWEEN 0 AND 100 AND cover_y BETWEEN 0 AND 100 "
            "AND cover_zoom BETWEEN 100 AND 300",
        )


def downgrade() -> None:
    with op.batch_alter_table("public_work_media") as batch:
        batch.drop_constraint("cover_crop_supported", type_="check")
        for name in ["cover_zoom", "cover_y", "cover_x"]:
            batch.drop_column(name)
