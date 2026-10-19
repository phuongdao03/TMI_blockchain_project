"""Correct the seeded user-account guide to match available controls.

Revision ID: 0120_correct_admin_user_guide
Revises: 0119_business_guides
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape

import sqlalchemy as sa

from alembic import op

revision: str = "0120_correct_admin_user_guide"
down_revision: str | None = "0119_business_guides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TITLE = "Tra cứu và xử lý tài khoản người dùng"
_SUMMARY = "Tìm, lọc, tạm đình chỉ hoặc khôi phục đúng tài khoản."
_OLD_SUMMARY = "Đối chiếu đúng người và hồ sơ trước khi cập nhật hoặc khóa tài khoản."
_OLD_BODY = """
        <h2>Khi nào dùng?</h2><p>Dùng khi hỗ trợ một tài khoản hoặc cần
        kiểm tra người gửi hồ sơ. Chuẩn bị email hay mã hồ sơ để đối chiếu.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/users">Người dùng</a> và tìm theo email
        hoặc thông tin đã được cung cấp.</li>
        <li>Mở đúng tài khoản, đối chiếu người sở hữu và hồ sơ liên quan.
        Kiểm tra trạng thái, phiên bản và tài liệu trước khi xử lý.</li>
        <li>Nếu hồ sơ thiếu thông tin, gửi yêu cầu bổ sung để người nộp
        tự cập nhật. Nếu cần khóa tài khoản, ghi rõ căn cứ và lý do.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Kiểm tra lại trạng thái tài khoản và
        hồ sơ sau thao tác; đối chiếu thông báo gửi cho người dùng khi có.</p>
        <h2>Khi không tìm thấy tài khoản</h2><p>Kiểm tra lại email, mã hồ sơ
        và bộ lọc trước khi tạo hay sửa bất kỳ tài khoản nào.</p>
        """
_BODY = """
<h2>Khi nào dùng?</h2><p>Dùng khi cần đối chiếu một tài khoản hoặc xử lý
trạng thái truy cập. Nếu cần yêu cầu bổ sung hồ sơ, mở quy trình hồ sơ trong
khu vực Tiếp nhận hồ sơ; trang Người dùng không có thao tác này.</p>
<h2>Tra cứu</h2><ol>
<li>Mở <a href="/admin/users">Người dùng</a>. Tìm theo tên, email hoặc mã
người dùng; dùng bộ lọc Trạng thái và Sắp xếp khi danh sách dài.</li>
<li>Đối chiếu họ tên, email, trạng thái xác minh, vai trò, trạng thái tài
khoản và thời điểm đăng nhập gần nhất. Kiểm tra đúng người trước khi xử lý.</li>
</ol>
<h2>Tạm đình chỉ hoặc khôi phục</h2><ol>
<li>Nếu tài khoản đang Hoạt động, chọn <strong>Tạm đình chỉ</strong>; nếu đã
đình chỉ, chọn <strong>Khôi phục</strong>. Nút chỉ hiện khi tài khoản quản trị
có quyền xử lý trạng thái.</li>
<li>Đọc thông tin tài khoản trong hộp xác nhận, nhập lý do và xác nhận.
Sau khi đình chỉ, các phiên đăng nhập của tài khoản bị thu hồi.</li>
<li>Tìm lại tài khoản và kiểm tra nhãn trạng thái mới. Nếu trang báo lỗi,
tải lại dữ liệu trước khi thực hiện lại để tránh quyết định trên trạng thái
đã thay đổi.</li></ol>
<h2>Câu hỏi thường gặp</h2>
<h3>Vì sao không có nút đình chỉ?</h3><p>Tài khoản quản trị hiện tại có thể
không có quyền đó, hoặc tài khoản đích không ở trạng thái cho phép. Kiểm tra
quyền và trạng thái trước khi yêu cầu hỗ trợ.</p>
<h3>Không tìm thấy người dùng?</h3><p>Kiểm tra cách viết email, bỏ bộ lọc
trạng thái và thử lại với tên hoặc mã người dùng.</p>
"""


def _search(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE cms_guide_articles SET summary = :summary, body_html = :body, "
            "search_text = :search_text, search_summary = :search_summary, "
            "updated_at = :updated_at "
            "WHERE slug = 'admin-user-accounts' AND created_by IS NULL "
            "AND updated_by IS NULL AND version = 1"
        ),
        {
            "summary": _SUMMARY,
            "body": _BODY,
            "search_text": _search(f"{_TITLE} {_SUMMARY} administration {_BODY}"),
            "search_summary": _search(_SUMMARY),
            "updated_at": datetime.now(UTC),
        },
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE cms_guide_articles SET summary = :summary, body_html = :body, "
            "search_text = :search_text, search_summary = :search_summary, "
            "updated_at = :updated_at "
            "WHERE slug = 'admin-user-accounts' AND body_html = :current_body "
            "AND created_by IS NULL AND updated_by IS NULL AND version = 1"
        ),
        {
            "summary": _OLD_SUMMARY,
            "body": _OLD_BODY,
            "search_text": _search(
                f"{_TITLE} {_OLD_SUMMARY} administration {_OLD_BODY}"
            ),
            "search_summary": _search(_OLD_SUMMARY),
            "updated_at": datetime.now(UTC),
            "current_body": _BODY,
        },
    )
