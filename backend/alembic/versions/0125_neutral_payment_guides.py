"""Use customer-facing names in payment help articles.

Revision ID: 0125_neutral_payment_guides
Revises: 0124_department_lead
"""

import re
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0125_neutral_payment_guides"
down_revision: str | None = "0124_department_lead"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, slug, title, summary, body_html, search_text, "
            "search_title, search_summary "
            "FROM cms_guide_articles WHERE title LIKE :provider "
            "OR summary LIKE :provider OR body_html LIKE :provider "
            "OR search_text LIKE :provider OR search_title LIKE :provider "
            "OR search_summary LIKE :provider OR body_html LIKE :old_label "
            "OR search_text LIKE :old_label OR search_title LIKE :old_label "
            "OR search_summary LIKE :old_label OR title LIKE :stack "
            "OR summary LIKE :stack OR body_html LIKE :stack "
            "OR search_text LIKE :stack OR search_title LIKE :stack "
            "OR search_summary LIKE :stack OR body_html LIKE :fingerprint "
            "OR search_text LIKE :fingerprint OR search_title LIKE :fingerprint "
            "OR search_summary LIKE :fingerprint OR body_html LIKE :review_flow "
            "OR search_text LIKE :review_flow OR search_title LIKE :review_flow "
            "OR search_summary LIKE :review_flow OR body_html LIKE :handoff "
            "OR search_text LIKE :handoff OR search_title LIKE :handoff "
            "OR search_summary LIKE :handoff"
        ),
        {
            "provider": "%PayOS%",
            "old_label": "%Tài chính%",
            "stack": "%Blockchain%",
            "fingerprint": "%dấu vân tay số%",
            "review_flow": "%quản trị viên%",
            "handoff": "%người phân công%",
        },
    ).all()
    for row in rows:
        hide_review_roles = row.slug in {
            "review-an-assigned-dossier",
            "moderator-work-allocations",
            "review-process-and-scorecard",
            "review-exceptions-faq",
        }

        def customer_copy(value: str, *, hide_roles: bool = hide_review_roles) -> str:
            if hide_roles:
                value = re.sub(
                    r"Người đánh giá gửi kết quả cho quản trị viên xem xét\.\s*Việc gửi kết quả thẩm định không tự quyết định hồ sơ được duyệt hay công bố\.",  # noqa: E501
                    "Sau khi gửi, kết quả thẩm định được ghi nhận. Việc gửi kết quả chưa đồng nghĩa hồ sơ đã được duyệt hoặc công bố.",  # noqa: E501
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"Kết quả được gửi để quản trị viên xem xét;\s*thao tác này không tự quyết định việc duyệt hoặc công bố\.",  # noqa: E501
                    "Kết quả đã được gửi; thao tác này chưa đồng nghĩa hồ sơ được duyệt hoặc công bố.",  # noqa: E501
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"quản trị viên xem kết quả để quyết định bước tiếp theo",
                    "trạng thái hồ sơ được cập nhật sau khi kết quả được tiếp nhận",
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"chờ quản trị viên xử lý",
                    "chờ trạng thái được cập nhật",
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"Quản trị viên chỉ định người và phiên bản hồ sơ;\s*hỏi người phân công nếu việc chưa xuất hiện",  # noqa: E501
                    "Chỉ hồ sơ được giao cho tài khoản của bạn mới xuất hiện; nếu vẫn chưa thấy, liên hệ bộ phận hỗ trợ",  # noqa: E501
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"Liên hệ quản trị viên để kiểm tra việc phân công\.?",
                    "Nếu vẫn chưa thấy, liên hệ bộ phận hỗ trợ.",
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"liên hệ quản trị viên để kiểm tra việc phân công đúng tài khoản",
                    "liên hệ bộ phận hỗ trợ để được hướng dẫn",
                    value,
                    flags=re.IGNORECASE,
                )
                value = re.sub(
                    r"liên hệ người phân công(?: để đối chiếu)?",
                    "liên hệ bộ phận hỗ trợ để được hướng dẫn",
                    value,
                    flags=re.IGNORECASE,
                )
            value = re.sub(
                r"Bản ghi xác minh dùng để đối chiếu dấu vân tay số và lịch sử ghi nhận\. Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân; bằng xác lập không thay thế kết luận pháp lý hay giấy tờ quyền sở hữu\.",  # noqa: E501
                "Bản xác lập giúp đối chiếu thông tin và lịch sử ghi nhận. Bản xác lập không thay thế kết luận pháp lý hay giấy tờ chứng minh quyền sở hữu.",  # noqa: E501
                value,
                flags=re.IGNORECASE,
            )
            value = re.sub(
                r"dấu vân tay số", "thông tin xác minh", value, flags=re.IGNORECASE
            )
            value = re.sub(
                r"Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân",
                "Bản xác lập không phải nơi lưu trữ hồ sơ gốc",
                value,
                flags=re.IGNORECASE,
            )
            value = re.sub(r"\bBlockchain\b", "hệ thống", value, flags=re.IGNORECASE)
            value = re.sub(
                r"Thanh toán qua PayOS",
                "Thanh toán trực tuyến",
                value,
                flags=re.IGNORECASE,
            )
            value = re.sub(r"PayOS", "đơn vị thanh toán", value, flags=re.IGNORECASE)
            value = re.sub(r"Tài chính", "Thu phí", value, flags=re.IGNORECASE)
            return value

        title = customer_copy(row.title)
        summary = customer_copy(row.summary)
        body = re.sub(
            r'(<a\b[^>]*\bhref\s*=\s*(["\'])/admin/payments(?:\?[^"\']*)?\2[^>]*>)[\s\S]*?(</a>)',
            r"\1Thu phí\3",
            row.body_html,
            flags=re.IGNORECASE,
        )
        body = customer_copy(body)
        search_text = customer_copy(row.search_text)
        search_title = customer_copy(row.search_title)
        search_summary = customer_copy(row.search_summary)
        if (
            title == row.title
            and summary == row.summary
            and body == row.body_html
            and search_text == row.search_text
            and search_title == row.search_title
            and search_summary == row.search_summary
        ):
            continue
        connection.execute(
            sa.text(
                "UPDATE cms_guide_articles SET title = :title, summary = :summary, "
                "body_html = :body, search_text = :search, "
                "search_title = :search_title, search_summary = :search_summary, "
                "updated_at = :updated_at WHERE id = :id"
            ),
            {
                "title": title,
                "summary": summary,
                "body": body,
                "search": search_text,
                "search_title": search_title,
                "search_summary": search_summary,
                "updated_at": datetime.now(UTC),
                "id": row.id,
            },
        )


def downgrade() -> None:
    # Keep published guide copy aligned with customer-facing labels.
    pass
