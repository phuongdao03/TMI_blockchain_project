"""Use plain language in the public certificate verification guide.

Revision ID: 0115_public_guide_plain_language
Revises: 0114_guide_docs_search_and_faq
"""

import re
import unicodedata
from collections.abc import Sequence
from html import unescape

import sqlalchemy as sa

from alembic import op

revision: str = "0115_public_guide_plain_language"
down_revision: str | None = "0114_guide_docs_search_and_faq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = (
    "<h2>Giới hạn của bằng xác lập</h2><p>Bản ghi xác minh dùng để đối chiếu "
    "dấu vân tay số và lịch sử ghi nhận. Blockchain không lưu ảnh, video, "
    "tệp gốc hoặc tài liệu cá nhân; bằng xác lập không thay thế kết luận "
    "pháp lý hay giấy tờ quyền sở hữu.</p>"
)
_NEW = (
    "<h2>Kết quả tra cứu cho biết điều gì?</h2><p>Kết quả giúp bạn đối chiếu "
    "thông tin và trạng thái của bằng xác lập với bản ghi đã công bố. "
    "Nếu thông tin không khớp, hãy liên hệ đơn vị phát hành để kiểm tra. "
    "Kết quả tra cứu không thay thế giấy tờ chứng minh quyền sở hữu "
    "hoặc kết luận của cơ quan có thẩm quyền.</p>"
)
_OLD_FAQ = (
    "Kết quả giúp đối chiếu dấu vân tay số và lịch sử ghi nhận; không thay thế "
    "kết luận pháp lý hoặc giấy tờ xác lập quyền sở hữu."
)
_NEW_FAQ = (
    "Kết quả cho biết thông tin và trạng thái của bằng xác lập đã công bố. "
    "Nếu cần xác nhận quyền sở hữu, hãy kiểm tra giấy tờ liên quan với "
    "đơn vị có thẩm quyền."
)


def _normalize(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


def upgrade() -> None:
    connection = op.get_bind()
    articles = sa.table(
        "cms_guide_articles",
        sa.column("slug", sa.String()),
        sa.column("title", sa.String()),
        sa.column("summary", sa.String()),
        sa.column("category", sa.String()),
        sa.column("body_html", sa.Text()),
        sa.column("search_text", sa.Text()),
        sa.column("version", sa.Integer()),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
    )
    row = (
        connection.execute(
            sa.select(articles).where(articles.c.slug == "verify-a-certificate")
        )
        .mappings()
        .first()
    )
    if not row or row["version"] != 1 or row["created_by"] or row["updated_by"]:
        return
    body = row["body_html"]
    if _OLD not in body:
        return
    body = body.replace(_OLD, _NEW).replace(_OLD_FAQ, _NEW_FAQ)
    search_text = _normalize(
        f"{row['title']} {row['summary']} {row['category'].replace('-', ' ')} {body}"
    )
    connection.execute(
        articles.update()
        .where(articles.c.slug == "verify-a-certificate")
        .values(body_html=body, search_text=search_text)
    )


def downgrade() -> None:
    pass
