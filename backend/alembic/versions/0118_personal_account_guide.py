"""Add shared personal profile and avatar instructions.

Revision ID: 0118_personal_account_guide
Revises: 0117_guide_role_plain_language
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0118_personal_account_guide"
down_revision: str | None = "0117_guide_role_plain_language"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SLUG = "personal-profile-settings"
_TITLE = "Cập nhật hồ sơ cá nhân và ảnh đại diện"
_SUMMARY = "Đổi tên hiển thị, thông tin liên hệ, ngôn ngữ, múi giờ và ảnh đại diện."
_BODY = """
<h2>Khi nào dùng?</h2>
<p>Đăng nhập để cập nhật thông tin cá nhân đang hiển thị trong tài khoản.
Tên hiển thị công khai được dùng cạnh bài viết và bình luận cộng đồng.
Thông tin công việc của nhân viên do quản trị viên cập nhật.</p>
<h2>Đổi tên hiển thị và thông tin liên hệ</h2>
<ol>
<li>Mở <a href="/account">Tài khoản</a>, chọn thẻ
<strong>Hồ sơ cá nhân</strong>.</li>
<li>Điền <strong>Họ và tên</strong> và
<strong>Tên hiển thị công khai</strong> theo cách bạn muốn người khác nhìn
thấy. Có thể cập nhật <strong>Số điện thoại</strong>; với số Việt Nam,
nhập số bắt đầu bằng 0.</li>
<li>Nếu cần, mở <strong>Ngôn ngữ và múi giờ</strong> để kiểm tra hai thông
tin này. Chọn <strong>Lưu hồ sơ</strong>.</li>
</ol>
<h2>Kiểm tra kết quả</h2>
<p>Trang báo <strong>Hồ sơ đã được cập nhật</strong>. Mở lại Tài khoản để
kiểm tra các trường đã lưu; tên hiển thị mới sẽ được dùng khi bạn tham gia
cộng đồng.</p>
<h2>Thay ảnh đại diện</h2>
<ol>
<li>Trong Hồ sơ cá nhân, mở mục <strong>Thay ảnh đại diện</strong> và chọn
<strong>Thêm tệp</strong>.</li>
<li>Chọn một ảnh JPG, PNG hoặc WEBP không quá 5 MB. Sau khi tên ảnh xuất hiện
trong danh sách, chọn <strong>Tải lên 1 tệp</strong>.</li>
<li>Chờ tải và kiểm tra hoàn tất. Trang tài khoản sẽ hiện
<strong>Ảnh đại diện đã được liên kết</strong>.</li>
</ol>
<h2>Nếu thao tác chưa thành công</h2>
<p>Với biểu mẫu cá nhân, đọc lỗi cạnh trường và sửa trước khi lưu lại.
Với ảnh, kiểm tra định dạng, dung lượng và kết nối; dùng nút
<strong>Thử lại 1 tệp</strong> nếu trình tải ảnh hiển thị lỗi.</p>
<h2>Câu hỏi thường gặp</h2>
<h3>Tôi có thể tự sửa phòng ban hoặc vị trí công việc không?</h3>
<p>Không. Nếu thông tin công việc chưa đúng, liên hệ quản trị viên nhân sự.
Bạn vẫn có thể tự sửa họ tên, tên hiển thị, số điện thoại và ảnh đại diện.</p>
<h3>Vì sao tôi chưa thấy ảnh mới?</h3>
<p>Kiểm tra thông báo tải ảnh đã hoàn tất, sau đó tải lại trang Tài khoản.
Nếu vẫn chưa hiện, thử tải lại ảnh hoặc liên hệ hỗ trợ.</p>
<h2>Hướng dẫn liên quan</h2>
<p>Nếu cần truy cập tài khoản, xem
<a href="/help/create-account-and-sign-in">Tạo tài khoản và đăng nhập</a>.</p>
"""


def _normalize(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


def upgrade() -> None:
    now = datetime.now(UTC)
    table = sa.table(
        "cms_guide_articles",
        sa.column("id", sa.Uuid()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("summary", sa.String()),
        sa.column("category", sa.String()),
        sa.column("audiences", sa.JSON()),
        sa.column("body_html", sa.Text()),
        sa.column("search_text", sa.Text()),
        sa.column("search_title", sa.Text()),
        sa.column("search_summary", sa.Text()),
        sa.column("sort_order", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": UUID("11111111-1111-4111-8111-000000000300"),
                "title": _TITLE,
                "slug": _SLUG,
                "summary": _SUMMARY,
                "category": "account",
                "audiences": ["VIEWER", "USER", "MODERATOR", "SUPER_ADMIN"],
                "body_html": _BODY,
                "search_text": _normalize(f"{_TITLE} {_SUMMARY} account {_BODY}"),
                "search_title": _normalize(_TITLE),
                "search_summary": _normalize(_SUMMARY),
                "sort_order": 22,
                "status": "PUBLISHED",
                "version": 1,
                "published_at": now,
                "created_by": None,
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM cms_guide_articles WHERE slug = :slug "
            "AND created_by IS NULL AND updated_by IS NULL AND version = 1"
        ).bindparams(slug=_SLUG)
    )
