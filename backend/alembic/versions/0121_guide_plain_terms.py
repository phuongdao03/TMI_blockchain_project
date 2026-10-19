"""Remove payment provider branding from the seeded applicant guide.

Revision ID: 0121_guide_plain_terms
Revises: 0120_correct_admin_user_guide
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape

import sqlalchemy as sa

from alembic import op

revision: str = "0121_guide_plain_terms"
down_revision: str | None = "0120_correct_admin_user_guide"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SLUG = "dossier-payment-guide"
_OLD = "Thanh toán qua PayOS"
_NEW = "Tiếp tục thanh toán"


def _search(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


def _replace_text(before: str, after: str) -> None:
    connection = op.get_bind()
    row = connection.execute(
        sa.text(
            "SELECT title, summary, category, body_html FROM cms_guide_articles "
            "WHERE slug = :slug"
        ),
        {"slug": _SLUG},
    ).first()
    if row is None or before not in row.body_html:
        return
    body = row.body_html.replace(before, after)
    connection.execute(
        sa.text(
            "UPDATE cms_guide_articles SET body_html = :body, "
            "search_text = :search_text, updated_at = :updated_at "
            "WHERE slug = :slug AND body_html = :old_body"
        ),
        {
            "body": body,
            "search_text": _search(f"{row.title} {row.summary} {row.category} {body}"),
            "updated_at": datetime.now(UTC),
            "slug": _SLUG,
            "old_body": row.body_html,
        },
    )


def upgrade() -> None:
    _replace_text(_OLD, _NEW)


def downgrade() -> None:
    _replace_text(_NEW, _OLD)
