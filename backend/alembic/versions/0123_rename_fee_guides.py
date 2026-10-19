"""Use the Thu phí label in existing administration guides.

Revision ID: 0123_rename_fee_guides
Revises: 0122_plain_role_guides_and_author
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0123_rename_fee_guides"
down_revision: str | None = "0122_plain_role_guides_and_author"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, body_html, search_text FROM cms_guide_articles "
            "WHERE body_html LIKE :term"
        ),
        {"term": "%Tài chính%"},
    ).all()
    for row in rows:
        body = row.body_html.replace(
            '<a href="/admin/payments">Tài chính</a>',
            '<a href="/admin/payments">Thu phí</a>',
        )
        if body == row.body_html:
            continue
        connection.execute(
            sa.text(
                "UPDATE cms_guide_articles SET body_html = :body, "
                "search_text = :search, updated_at = :updated_at WHERE id = :id"
            ),
            {
                "body": body,
                "search": row.search_text.replace("Tài chính", "Thu phí"),
                "updated_at": datetime.now(UTC),
                "id": row.id,
            },
        )


def downgrade() -> None:
    # Keep published wording aligned with the navigation label.
    pass
