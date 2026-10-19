"""Improve guide search ranking and enrich verified seed documentation.

Revision ID: 0114_guide_docs_search_and_faq
Revises: 0113_help_center_role_audit
"""

import re
import unicodedata
from collections.abc import Sequence
from html import unescape

import sqlalchemy as sa

from alembic import op

revision: str = "0114_guide_docs_search_and_faq"
down_revision: str | None = "0113_help_center_role_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PRECONDITIONS = {
    "explore-nominations": (
        "Không cần đăng nhập để xem nội dung đã công bố. Chuẩn bị tên tác phẩm "
        "hoặc tên chủ thể giúp việc tra cứu nhanh hơn."
    ),
    "create-account-and-sign-in": (
        "Cần có địa chỉ email bạn đang sử dụng và quyền truy cập hộp thư "
        "để xác minh tài khoản."
    ),
    "viewer-account-basics": (
        "Đăng nhập để xem thông báo, tài khoản và hoạt động gần đây của chính bạn."
    ),
    "create-and-submit-a-dossier": (
        "Đăng nhập bằng tài khoản đã mở chức năng gửi hồ sơ. Chuẩn bị thông tin "
        "và các tài liệu được biểu mẫu yêu cầu."
    ),
    "track-and-update-a-dossier": (
        "Cần có hồ sơ đã gửi. Dùng đúng tài khoản đã gửi hồ sơ để xem trạng thái "
        "và yêu cầu bổ sung."
    ),
    "review-an-assigned-dossier": (
        "Chỉ xử lý hồ sơ xuất hiện trong danh sách công việc được phân công "
        "cho tài khoản hiện tại."
    ),
    "attendance-and-employee-requests": (
        "Cần có hồ sơ nhân viên đã liên kết, quyền truy cập phù hợp và thiết bị "
        "được phép dùng vị trí khi chấm công."
    ),
    "verify-a-certificate": (
        "Cần mã bằng xác lập hoặc mã QR trên bản ghi cần đối chiếu."
    ),
    "admin-operations-start": (
        "Đăng nhập bằng tài khoản quản trị được cấp quyền cho công việc cần thực hiện."
    ),
    "common-account-and-guide-questions": (
        "Các trang thư viện và tra cứu công khai có thể mở mà không cần đăng nhập."
    ),
    "my-certificates": (
        "Cần có bằng đã phát hành gắn với tài khoản. Tệp PDF chỉ tải được "
        "khi hệ thống báo đã sẵn sàng."
    ),
}

_FAQS = {
    "explore-nominations": [
        (
            "Tôi có cần đăng nhập để xem đề cử đã công bố không?",
            "Không. Nội dung công khai có thể xem tại Thư viện đề cử. "
            "Thông tin chưa được công bố không xuất hiện trong danh sách công khai.",
        ),
        (
            "Vì sao không tìm thấy một nội dung?",
            "Kiểm tra lại từ khóa và bộ lọc. Danh sách công khai chỉ hiển thị "
            "nội dung đã được công bố.",
        ),
    ],
    "create-account-and-sign-in": [
        (
            "Tôi chưa nhận được email xác minh, cần làm gì?",
            "Kiểm tra địa chỉ email đã nhập và thư mục thư rác. Nếu trang đăng nhập "
            "còn hiển thị tùy chọn gửi lại email, hãy dùng tùy chọn đó.",
        ),
        (
            "Tôi quên mật khẩu ở đâu?",
            "Mở trang Đăng nhập, chọn chức năng quên mật khẩu nếu được hiển thị, "
            "rồi làm theo liên kết gửi tới email.",
        ),
    ],
    "viewer-account-basics": [
        (
            "Tôi xem thông báo và hoạt động tài khoản ở đâu?",
            "Mở Thông báo để xem cập nhật; mở Tài khoản để kiểm tra thông tin "
            "cá nhân; Hoạt động gần đây hiển thị lịch sử của tài khoản.",
        ),
        (
            "Vì sao tôi chưa thấy hướng dẫn tạo hồ sơ?",
            "Chức năng gửi hồ sơ chỉ xuất hiện sau khi hoàn tất bước chuyển tài khoản "
            "sang loại người gửi hồ sơ. Nếu chọn Để sau, tài khoản vẫn ở "
            "không gian tra cứu.",
        ),
    ],
    "create-and-submit-a-dossier": [
        (
            "Làm sao biết hồ sơ đã được gửi?",
            "Mở lại Hồ sơ của tôi và kiểm tra mã hồ sơ cùng trạng thái tiếp nhận "
            "sau khi gửi.",
        ),
        (
            "Tôi có thể sửa hồ sơ đã gửi không?",
            "Hồ sơ đã gửi ở chế độ chỉ đọc cho đến khi có yêu cầu bổ sung. "
            "Khi có yêu cầu, chỉ cập nhật phần được nêu.",
        ),
    ],
    "track-and-update-a-dossier": [
        (
            "Giao dịch hoàn tất nhưng trạng thái chưa đổi thì sao?",
            "Không thanh toán lần nữa. Ghi lại mã hồ sơ và mã giao dịch để bộ phận "
            "hỗ trợ đối chiếu.",
        ),
        (
            "Tôi nên cập nhật những phần nào?",
            "Chỉ bổ sung nội dung hoặc tài liệu được nêu trong yêu cầu đang mở "
            "của hồ sơ.",
        ),
    ],
    "review-an-assigned-dossier": [
        (
            "Vì sao hàng đợi của tôi đang trống?",
            "Hàng đợi chỉ hiển thị hồ sơ đã được phân công cho tài khoản. "
            "Liên hệ quản trị viên để kiểm tra việc phân công.",
        ),
        (
            "Gửi kết quả thẩm định có tự công bố hồ sơ không?",
            "Không. Kết quả được gửi để quản trị viên xem xét; thao tác này "
            "không tự quyết định việc duyệt hoặc công bố.",
        ),
    ],
    "attendance-and-employee-requests": [
        (
            "Vì sao tôi không thấy mục chấm công hoặc nghỉ phép?",
            "Các mục này cần hồ sơ nhân viên được liên kết với tài khoản và quyền "
            "phù hợp. Liên hệ quản trị viên nếu thông tin đã đúng mà mục vẫn "
            "chưa xuất hiện.",
        ),
        (
            "Trình duyệt không ghi nhận vị trí?",
            "Kiểm tra quyền vị trí của trình duyệt và thiết bị, sau đó thử lại "
            "tại điểm làm việc được cấu hình.",
        ),
    ],
    "verify-a-certificate": [
        (
            "Không tìm thấy bằng xác lập khi tra cứu?",
            "Kiểm tra lại mã hoặc quét lại mã QR. Nếu thông tin vẫn không khớp, "
            "liên hệ đơn vị phát hành để đối chiếu.",
        ),
        (
            "Kết quả xác minh chứng minh điều gì?",
            "Kết quả giúp đối chiếu dấu vân tay số và lịch sử ghi nhận; không thay thế "
            "kết luận pháp lý hoặc giấy tờ xác lập quyền sở hữu.",
        ),
    ],
    "admin-operations-start": [
        (
            "Bài hướng dẫn quản trị đã xuất bản có xuất hiện công khai ngay không?",
            "Chỉ bài đã xuất bản và được gắn phạm vi công khai mới xuất hiện "
            "trên trang Hướng dẫn công khai.",
        ),
        (
            "Tôi nên làm gì nếu một mục quản trị không xuất hiện?",
            "Kiểm tra tài khoản và quyền của công việc đó. Không dùng tài khoản khác "
            "để vượt qua giới hạn được cấp.",
        ),
    ],
    "common-account-and-guide-questions": [],
    "my-certificates": [
        (
            "Vì sao chưa tải được tệp PDF?",
            "Chỉ chọn Tải bằng xác lập PDF khi trạng thái cho biết tệp đã sẵn sàng. "
            "Nếu hệ thống đang chuẩn bị tệp, quay lại sau.",
        ),
        (
            "Lý do cập nhật cần dài bao nhiêu?",
            "Biểu mẫu yêu cầu ít nhất 20 ký tự và chỉ xuất hiện khi có thay đổi "
            "đã được xét duyệt.",
        ),
    ],
}


def _normalize(value: str) -> str:
    without_tags = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", without_tags)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(
        without_marks.replace("đ", "d").replace("Đ", "d").casefold().split()
    )


def _faq_html(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    questions = "".join(
        f"<h3>{question}</h3><p>{answer}</p>" for question, answer in items
    )
    return f"<h2>Câu hỏi thường gặp</h2>{questions}"


def upgrade() -> None:
    op.add_column(
        "cms_guide_articles",
        sa.Column("search_title", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "cms_guide_articles",
        sa.Column("search_summary", sa.Text(), nullable=False, server_default=""),
    )

    connection = op.get_bind()
    articles = sa.table(
        "cms_guide_articles",
        sa.column("id", sa.Uuid()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
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
    rows = tuple(
        connection.execute(
            sa.select(
                articles.c.id,
                articles.c.title,
                articles.c.slug,
                articles.c.summary,
                articles.c.category,
                articles.c.body_html,
                articles.c.version,
                articles.c.created_by,
                articles.c.updated_by,
            )
        ).mappings()
    )

    for row in rows:
        article = dict(row)
        slug = article["slug"]
        category = article["category"]
        body_html = article["body_html"]
        is_untouched_seed = (
            slug in _PRECONDITIONS
            and article["created_by"] is None
            and article["updated_by"] is None
            and article["version"] == 1
        )

        if is_untouched_seed:
            if slug == "common-account-and-guide-questions":
                category = "faq"
                body_html = (
                    "<h2>Câu hỏi thường gặp</h2>"
                    "<h3>Tôi có cần đăng nhập để tra cứu nội dung công khai không?</h3>"
                    "<p>Không. Bạn có thể mở Thư viện đề cử và trang Tra cứu "
                    "bằng xác lập để xem thông tin đã công bố.</p>"
                    "<h3>Tôi chưa nhận được email xác minh tài khoản thì sao?</h3>"
                    "<p>Kiểm tra địa chỉ email đã nhập và thư mục thư rác. Nếu trang "
                    "còn hiển thị lựa chọn gửi lại email, hãy dùng lựa chọn đó.</p>"
                    "<h3>Vì sao tôi không tìm thấy một nội dung trong thư viện?</h3>"
                    "<p>Thư viện công khai chỉ hiển thị nội dung đã công bố. "
                    "Kiểm tra từ khóa và bộ lọc rồi thử lại.</p>"
                    "<h3>Tôi tra cứu bằng xác lập ở đâu?</h3>"
                    "<p>Mở trang Tra cứu bằng xác lập, nhập mã hoặc dùng mã QR "
                    "được cung cấp rồi đối chiếu thông tin hiển thị.</p>"
                )
            else:
                condition = _PRECONDITIONS[slug]
                body_html = (
                    f"<h2>Điều kiện sử dụng</h2><p>{condition}</p>"
                    f"{body_html}{_faq_html(_FAQS[slug])}"
                )

        search_text = _normalize(
            f"{article['title']} {article['summary']} "
            f"{category.replace('-', ' ')} {body_html}"
        )
        connection.execute(
            articles.update()
            .where(articles.c.id == article["id"])
            .values(
                category=category,
                body_html=body_html,
                search_text=search_text,
                search_title=_normalize(article["title"]),
                search_summary=_normalize(article["summary"]),
            )
        )


def downgrade() -> None:
    op.drop_column("cms_guide_articles", "search_summary")
    op.drop_column("cms_guide_articles", "search_title")
