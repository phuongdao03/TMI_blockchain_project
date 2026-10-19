"""Remove internal role codes from user guide copy.

Revision ID: 0117_guide_role_plain_language
Revises: 0116_role_workflow_guides
"""

import re
import unicodedata
from collections.abc import Sequence
from html import unescape

import sqlalchemy as sa

from alembic import op

revision: str = "0117_guide_role_plain_language"
down_revision: str | None = "0116_role_workflow_guides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = "sau khi tài khoản chuyển sang vai trò USER."
_NEW = "sau khi tài khoản được chuyển sang loại có thể gửi hồ sơ."


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
        sa.column("search_title", sa.Text()),
        sa.column("search_summary", sa.Text()),
        sa.column("version", sa.Integer()),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
    )
    row = (
        connection.execute(
            sa.select(articles).where(articles.c.slug == "viewer-account-basics")
        )
        .mappings()
        .first()
    )
    if row and row["version"] == 1 and not row["created_by"] and not row["updated_by"]:
        body = row["body_html"]
        if _OLD in body:
            body = body.replace(_OLD, _NEW)
            search_text = _normalize(
                f"{row['title']} {row['summary']} "
                f"{row['category'].replace('-', ' ')} {body}"
            )
            connection.execute(
                articles.update()
                .where(articles.c.slug == "viewer-account-basics")
                .values(body_html=body, search_text=search_text)
            )

    employee = (
        connection.execute(
            sa.select(articles).where(
                articles.c.slug == "attendance-and-employee-requests"
            )
        )
        .mappings()
        .first()
    )
    if not employee or employee["version"] != 1:
        return
    if employee["created_by"] or employee["updated_by"]:
        return
    title = "Chọn hướng dẫn chấm công và yêu cầu nhân sự"
    summary = "Mở đúng hướng dẫn cho chấm công, nghỉ phép hoặc tăng ca."
    body = (
        "<h2>Chọn công việc cần thực hiện</h2><ul>"
        '<li><a href="/help/employee-attendance">Chấm công vào và ra</a>: '
        "kiểm tra điểm làm việc, ghi nhận giờ và xem lịch sử.</li>"
        '<li><a href="/help/employee-leave-request">Gửi và theo dõi đơn nghỉ</a>: '
        "nhập khoảng ngày, loại nghỉ và theo dõi kết quả duyệt.</li>"
        '<li><a href="/help/employee-overtime-request">Đăng ký và theo dõi '
        "tăng ca</a>: gửi thời gian dự kiến và lý do.</li></ul>"
        "<p>Nếu không thấy các mục nhân sự, liên hệ quản trị viên để kiểm tra "
        "hồ sơ nhân viên liên kết với tài khoản.</p>"
    )
    connection.execute(
        articles.update()
        .where(articles.c.slug == "attendance-and-employee-requests")
        .values(
            title=title,
            summary=summary,
            body_html=body,
            search_title=_normalize(title),
            search_summary=_normalize(summary),
            search_text=_normalize(
                f"{title} {summary} {employee['category'].replace('-', ' ')} {body}"
            ),
        )
    )


def downgrade() -> None:
    pass
