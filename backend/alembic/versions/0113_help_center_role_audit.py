"""Add Viewer guidance and normalize seeded guide categories.

Revision ID: 0113_help_center_role_audit
Revises: 0112_cms_guide_articles
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0113_help_center_role_audit"
down_revision: str | None = "0112_cms_guide_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE cms_guide_articles SET category = 'review-workflows' "
            "WHERE slug = 'review-an-assigned-dossier' "
            "AND created_by IS NULL AND version = 1"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE cms_guide_articles SET category = 'account' "
            "WHERE slug = 'common-account-and-guide-questions' "
            "AND created_by IS NULL AND version = 1"
        )
    )

    now = datetime.now(UTC)
    articles = sa.table(
        "cms_guide_articles",
        sa.column("id", sa.Uuid()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("summary", sa.String()),
        sa.column("category", sa.String()),
        sa.column("audiences", sa.JSON()),
        sa.column("body_html", sa.Text()),
        sa.column("search_text", sa.Text()),
        sa.column("sort_order", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    title = "Hướng dẫn dành cho Người tra cứu"
    summary = (
        "Tra cứu nội dung công khai, dùng tiện ích cá nhân và bắt đầu hồ sơ "
        "khi cần gửi đề cử."
    )
    body_html = (
        "<h2>Mở không gian tra cứu</h2><ol>"
        "<li>Đăng nhập bằng tài khoản Người tra cứu rồi mở "
        '<a href="/workspace">Tổng quan</a>.</li>'
        '<li>Chọn <a href="/works">Thư viện đề cử</a> để tìm tên tác phẩm '
        "hoặc chủ thể, lọc danh mục và mở kết quả đã công bố.</li>"
        '<li>Chọn <a href="/verify">Tra cứu bằng xác lập</a>, nhập mã '
        "hoặc quét QR được cung cấp rồi đối chiếu thông tin hiển thị.</li>"
        "</ol><h2>Dùng tiện ích cá nhân</h2><ol>"
        '<li>Mở <a href="/notifications">Thông báo</a> để xem cập nhật '
        "gửi tới tài khoản.</li>"
        '<li>Mở <a href="/account">Tài khoản</a> để kiểm tra thông tin '
        "cá nhân và cài đặt đang được cung cấp.</li>"
        '<li>Mở <a href="/activity">Hoạt động gần đây</a> để xem lịch sử '
        "hoạt động của tài khoản.</li>"
        "</ol><h2>Bắt đầu gửi hồ sơ</h2><ol>"
        "<li>Trên Tổng quan, chọn <strong>Gửi tác phẩm hoặc hồ sơ</strong>.</li>"
        "<li>Chọn <strong>Cá nhân</strong> hoặc "
        "<strong>Doanh nghiệp hoặc tổ chức</strong>, rồi chọn "
        "<strong>Tiếp tục</strong>.</li>"
        "<li>Hoàn thiện thông tin liên hệ trong "
        '<a href="/account">Tài khoản</a>. Sau khi nâng cấp, mở '
        '<a href="/help/create-and-submit-a-dossier">hướng dẫn tạo và gửi '
        "hồ sơ</a> để tiếp tục từng bước.</li>"
        "</ol><blockquote>Nếu bạn chọn <strong>Để sau</strong>, tài khoản vẫn "
        "ở quyền Người tra cứu và chưa thể tạo hồ sơ. Hướng dẫn hồ sơ chỉ mở "
        "sau khi tài khoản chuyển sang vai trò USER.</blockquote>"
    )
    search_text = (
        "huong dan danh cho nguoi tra cuu dung khong gian tra cuu thu vien de cu "
        "cong cu ca nhan gui tac pham ho so ca nhan doanh nghiep to chuc tiep tuc "
        "viewer tong quan thong bao tai khoan hoat dong gan day"
    )
    op.bulk_insert(
        articles,
        [
            {
                "id": UUID("11111111-1111-4111-8111-11111111110a"),
                "title": title,
                "slug": "viewer-account-basics",
                "summary": summary,
                "category": "getting-started",
                "audiences": ["VIEWER"],
                "body_html": body_html,
                "search_text": search_text,
                "sort_order": 25,
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

    certificate_title = "Xem và cập nhật bằng xác lập của tôi"
    certificate_summary = (
        "Tìm bằng đã phát hành, tải PDF, theo dõi phiên bản và gửi yêu cầu "
        "cập nhật khi đủ điều kiện."
    )
    certificate_body = (
        "<h2>Mở danh sách bằng đã phát hành</h2><ol>"
        '<li>Mở <a href="/certificates">Bằng xác lập của tôi</a>.</li>'
        "<li>Thẻ bằng hiển thị mã, tên tài sản, danh mục, phiên bản và trạng thái.</li>"
        "<li>Nếu danh sách trống, bằng sẽ xuất hiện sau khi hồ sơ hoàn tất lệ phí "
        'và được phát hành. Chọn <a href="/dossiers">Theo dõi hồ sơ của tôi</a> '
        "để xem hồ sơ liên quan.</li></ol>"
        "<h2>Xem và tải tệp</h2><ol>"
        "<li>Chọn <strong>Xem và tải bằng</strong> với bằng đang có hiệu lực; "
        "chọn <strong>Xem lịch sử</strong> với bằng đã hết hiệu lực hoặc bị "
        "thu hồi.</li>"
        "<li>Trong trang chi tiết, chọn "
        "<strong>Tải bằng xác lập PDF</strong> khi PDF đã sẵn sàng. "
        "Nếu đang chuẩn bị, quay lại sau.</li>"
        "<li>Dùng lịch sử bằng để đối chiếu các phiên bản cũ. Mã QR và nút "
        "<strong>Mở trang tra cứu</strong> dẫn tới thông tin kiểm tra công "
        "khai.</li></ol>"
        "<h2>Gửi yêu cầu cập nhật</h2><ol>"
        "<li>Chỉ gửi khi hồ sơ có thông tin mới đã được xét duyệt và biểu mẫu "
        "<strong>Cập nhật bằng xác lập</strong> xuất hiện.</li>"
        "<li>Nhập lý do cập nhật dài ít nhất 20 ký tự vào ô "
        "<strong>Lý do cập nhật</strong>.</li>"
        "<li>Chọn <strong>Gửi yêu cầu cập nhật</strong> rồi theo dõi trạng thái "
        "yêu cầu "
        "đang mở trên cùng trang.</li></ol>"
        "<blockquote>Yêu cầu cập nhật không tự sửa bằng ngay lập tức. "
        "Nếu chưa có thay đổi "
        "được duyệt, màn hình sẽ báo chưa có thay đổi cần cập nhật.</blockquote>"
    )
    op.bulk_insert(
        articles,
        [
            {
                "id": UUID("11111111-1111-4111-8111-11111111110b"),
                "title": certificate_title,
                "slug": "my-certificates",
                "summary": certificate_summary,
                "category": "certificates",
                "audiences": ["USER"],
                "body_html": certificate_body,
                "search_text": (
                    "xem cap nhat tai pdf bang xac lap cua toi da phat hanh "
                    "ma tai san danh muc phien ban trang thai lich su qr "
                    "yeu cau cap nhat ly do"
                ),
                "sort_order": 75,
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
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM cms_guide_articles WHERE slug = 'viewer-account-basics' "
            "AND created_by IS NULL AND version = 1"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM cms_guide_articles WHERE slug = 'my-certificates' "
            "AND created_by IS NULL AND version = 1"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE cms_guide_articles SET category = 'reviews' "
            "WHERE slug = 'review-an-assigned-dossier' "
            "AND created_by IS NULL AND version = 1"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE cms_guide_articles SET category = 'faq' "
            "WHERE slug = 'common-account-and-guide-questions' "
            "AND created_by IS NULL AND version = 1"
        )
    )
