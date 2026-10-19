"""Add role-scoped help articles and anonymous feedback.

Revision ID: 0112_cms_guide_articles
Revises: 0111_public_profile_identity
"""

import html
import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0112_cms_guide_articles"
down_revision: str | None = "0111_public_profile_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalized_search_text(title: str, summary: str, body_html: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", body_html))
    plain = unicodedata.normalize("NFKD", f"{title} {summary} {plain}")
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return " ".join(plain.replace("đ", "d").replace("Đ", "d").casefold().split())


def upgrade() -> None:
    status_type = sa.Enum(
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED",
        name="cms_content_status",
        native_enum=False,
        create_constraint=True,
    )
    op.create_table(
        "cms_guide_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column(
            "audiences",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"PUBLIC\"]'"),
        ),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", status_type, nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_cms_guide_articles_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_cms_guide_articles_updated_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cms_guide_articles"),
        sa.UniqueConstraint("slug", name="uq_cms_guide_articles_slug"),
    )
    op.create_index(
        "ix_cms_guide_articles_status_order",
        "cms_guide_articles",
        ["status", "sort_order", "slug"],
    )
    op.create_index(
        "ix_cms_guide_articles_search_text", "cms_guide_articles", ["search_text"]
    )

    op.create_table(
        "cms_guide_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("client_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["cms_guide_articles.id"],
            name="fk_cms_guide_feedback_article_id_cms_guide_articles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cms_guide_feedback"),
        sa.UniqueConstraint(
            "article_id",
            "client_token_hash",
            name="uq_cms_guide_feedback_article_client",
        ),
    )
    op.create_index(
        "ix_cms_guide_feedback_article_created",
        "cms_guide_feedback",
        ["article_id", "created_at"],
    )

    now = datetime(2026, 10, 18, tzinfo=UTC)
    articles = [
        (
            UUID("11111111-1111-4111-8111-111111111101"),
            "Tìm và xem đề cử đã công bố",
            "explore-nominations",
            "Mở thư viện, tìm nội dung đã công bố và kiểm tra thông tin trên trang chi tiết.",  # noqa: E501
            "getting-started",
            ["PUBLIC"],
            """<h2>Mở thư viện đề cử</h2><p>Chọn <a href="/works">Thư viện đề cử</a> để xem những nội dung đã được công bố. Bạn không cần đăng nhập để đọc thông tin công khai.</p><h2>Tìm nội dung</h2><ol><li>Nhập tên tác phẩm hoặc từ khóa vào ô tìm kiếm.</li><li>Dùng danh mục để thu hẹp kết quả khi cần.</li><li>Mở một kết quả để xem nội dung và trạng thái hiển thị.</li></ol><blockquote>Hồ sơ thẩm định, thông tin liên hệ và giấy tờ cá nhân không được hiển thị trong thư viện công khai.</blockquote>""",  # noqa: E501
            10,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111102"),
            "Tạo tài khoản và đăng nhập an toàn",
            "create-account-and-sign-in",
            "Đăng ký bằng email đang sử dụng, xác minh địa chỉ và khôi phục quyền truy cập.",  # noqa: E501
            "account",
            ["PUBLIC"],
            """<h2>Đăng ký</h2><ol><li>Mở <a href="/register">Đăng ký</a> và điền thông tin được yêu cầu.</li><li>Mở email xác minh và làm theo liên kết trong thư.</li><li>Quay lại <a href="/login">Đăng nhập</a> bằng địa chỉ email đã xác minh.</li></ol><h2>Nếu quên mật khẩu</h2><p>Chọn mục quên mật khẩu trên trang đăng nhập và làm theo liên kết đặt lại được gửi tới email.</p><blockquote>Không chia sẻ mật khẩu, mã xác thực hoặc liên kết khôi phục với người khác.</blockquote>""",  # noqa: E501
            20,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111103"),
            "Tạo và gửi hồ sơ đề cử",
            "create-and-submit-a-dossier",
            "Chuẩn bị thông tin, tải tài liệu phù hợp, lưu bản nháp và gửi hồ sơ.",
            "dossiers",
            ["USER"],
            """<h2>Chuẩn bị hồ sơ</h2><ol><li>Mở <a href="/dossiers">Hồ sơ của tôi</a> rồi chọn tạo hồ sơ mới.</li><li>Chọn loại đề cử và điền thông tin chủ thể, tác phẩm theo biểu mẫu.</li><li>Tải các tài liệu được yêu cầu, kiểm tra tên tệp và nội dung trước khi gửi.</li><li>Lưu bản nháp nếu cần hoàn thiện sau; gửi hồ sơ khi các mục bắt buộc đã đầy đủ.</li></ol><h2>Sau khi gửi</h2><p>Mở lại hồ sơ của tôi để kiểm tra mã hồ sơ và trạng thái tiếp nhận. Hồ sơ đã gửi tạm thời ở chế độ chỉ đọc; cập nhật theo yêu cầu bổ sung nếu có.</p><blockquote>Chỉ tải lên tài liệu liên quan. Không gửi mật khẩu, mã xác thực hoặc thông tin thanh toán trong tệp hồ sơ.</blockquote>""",  # noqa: E501
            30,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111104"),
            "Theo dõi hồ sơ và gửi bổ sung",
            "track-and-update-a-dossier",
            "Kiểm tra thông báo, cập nhật đúng hồ sơ và theo dõi trạng thái mới.",
            "dossiers",
            ["USER"],
            """<h2>Kiểm tra yêu cầu</h2><ol><li>Mở <a href="/notifications">Thông báo</a> hoặc Hồ sơ của tôi.</li><li>Chọn đúng hồ sơ theo mã và đọc nội dung yêu cầu bổ sung.</li><li>Cập nhật phần được nêu, kiểm tra phiên bản tài liệu rồi gửi bổ sung.</li><li>Quay lại hồ sơ để xác nhận trạng thái mới.</li></ol><h2>Thanh toán khi được yêu cầu</h2><p>Đối chiếu mã hồ sơ và số tiền hiển thị trước khi thanh toán. Nếu giao dịch đã hoàn tất nhưng trạng thái chưa đổi, không thanh toán lần nữa; giữ lại mã giao dịch và liên hệ hỗ trợ.</p>""",  # noqa: E501
            40,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111105"),
            "Xử lý hồ sơ được phân công",
            "review-an-assigned-dossier",
            "Kiểm tra công việc được giao, ghi nhận căn cứ và gửi kết quả thẩm định.",
            "reviews",
            ["MODERATOR"],
            """<h2>Mở công việc được giao</h2><ol><li>Chọn <a href="/reviews">Hàng đợi thẩm định</a> hoặc Công việc được giao.</li><li>Mở hồ sơ đã được phân công cho tài khoản của bạn.</li><li>Đối chiếu mã hồ sơ, phiên bản tài liệu và hạn xử lý.</li><li>Đọc tài liệu, ghi nhận phát hiện và căn cứ; lưu bản nháp nếu chưa hoàn tất.</li><li>Kiểm tra nhận xét rồi gửi kết quả. Khai báo xung đột lợi ích trước khi tiếp tục nếu có.</li></ol><h2>Phạm vi quyết định</h2><p>Người đánh giá gửi kết quả cho quản trị viên xem xét. Việc gửi kết quả thẩm định không tự quyết định hồ sơ được duyệt hay công bố.</p><blockquote>Nếu danh sách trống, hãy liên hệ quản trị viên để kiểm tra việc phân công đúng tài khoản.</blockquote>""",  # noqa: E501
            50,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111106"),
            "Chấm công và gửi yêu cầu nhân sự",
            "attendance-and-employee-requests",
            "Dành cho tài khoản đã liên kết hồ sơ nhân viên và được cấp quyền sử dụng.",
            "employee-workflows",
            ["EMPLOYEE"],
            """<h2>Chấm công</h2><ol><li>Mở <a href="/attendance">Chấm công</a> trên thiết bị được phép dùng vị trí.</li><li>Kiểm tra điểm làm việc và lịch áp dụng trên tài khoản.</li><li>Bật quyền vị trí cho trình duyệt, ghi nhận giờ vào hoặc giờ ra và kiểm tra kết quả trong lịch sử.</li></ol><h2>Nghỉ phép và tăng ca</h2><p>Mở <a href="/leave">Nghỉ phép</a> hoặc <a href="/overtime">Tăng ca</a>, gửi yêu cầu theo biểu mẫu và theo dõi trạng thái trong tài khoản.</p><blockquote>Nếu chưa thấy mục nhân sự hoặc chưa thể chấm công, liên hệ quản trị viên để kiểm tra liên kết hồ sơ nhân viên, lịch và điểm làm việc.</blockquote>""",  # noqa: E501
            60,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111107"),
            "Tra cứu và kiểm tra bằng xác lập",
            "verify-a-certificate",
            "Dùng mã hoặc mã QR để đối chiếu thông tin công khai và trạng thái xác minh.",  # noqa: E501
            "verification",
            ["PUBLIC"],
            """<h2>Mở trang tra cứu</h2><ol><li>Mở <a href="/verify">Tra cứu bằng xác lập</a>.</li><li>Nhập mã bằng xác lập hoặc dùng mã QR được cung cấp.</li><li>Đối chiếu tên tác phẩm, chủ thể, thời điểm cấp và trạng thái hiện tại.</li><li>Nếu không tìm thấy, kiểm tra lại mã và liên hệ đơn vị phát hành khi dữ liệu không khớp.</li></ol><h2>Giới hạn của bằng xác lập</h2><p>Bản ghi xác minh dùng để đối chiếu dấu vân tay số và lịch sử ghi nhận. Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân; bằng xác lập không thay thế kết luận pháp lý hay giấy tờ quyền sở hữu.</p>""",  # noqa: E501
            70,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111108"),
            "Bắt đầu ca quản trị và xử lý công việc",
            "admin-operations-start",
            "Dành cho Super Admin: kiểm tra hàng đợi, xử lý theo phân quyền và lưu dấu vết.",  # noqa: E501
            "administration",
            ["SUPER_ADMIN"],
            """<h2>Kiểm tra tổng quan</h2><ol><li>Mở <a href="/admin/dashboard">Tổng quan quản trị</a> đầu ca.</li><li>Kiểm tra thông báo, hồ sơ chờ xử lý và cảnh báo vận hành.</li><li>Mở đúng mục quản trị từ menu để kiểm tra hồ sơ gốc và quyền thao tác.</li><li>Chuyển công việc cho người phụ trách khi nghiệp vụ nằm ngoài quyền của bạn.</li></ol><h2>Quản lý hướng dẫn</h2><p>Dùng <a href="/admin/guide/articles">Quản lý tài liệu hướng dẫn</a> để lưu nháp, xem trước, xuất bản hoặc lưu trữ bài hướng dẫn. Nội dung công khai chỉ xuất hiện sau khi xuất bản.</p><blockquote>Thao tác quản trị được ghi nhận trong nhật ký. Chỉ thực hiện thay đổi theo quyền được cấp và quy trình của đơn vị.</blockquote>""",  # noqa: E501
            80,
        ),
        (
            UUID("11111111-1111-4111-8111-111111111109"),
            "Câu hỏi thường gặp khi sử dụng hệ thống",
            "common-account-and-guide-questions",
            "Giải đáp ngắn về tài khoản, hồ sơ và quyền truy cập.",
            "faq",
            ["PUBLIC"],
            """<h2>Tôi không nhận được email xác minh</h2><p>Kiểm tra thư rác và địa chỉ email đã đăng ký. Sau đó quay lại trang đăng nhập để yêu cầu gửi lại email nếu tùy chọn đó đang hiển thị.</p><h2>Tôi không thấy hồ sơ được giao</h2><p>Chỉ hồ sơ đã phân công cho tài khoản của bạn mới xuất hiện trong hàng đợi. Liên hệ quản trị viên để xác nhận phân công.</p><h2>Tôi không thấy chức năng nhân sự</h2><p>Chấm công và yêu cầu nhân sự chỉ hiển thị cho tài khoản đã liên kết hồ sơ nhân viên và được cấp quyền phù hợp.</p><h2>Tôi đã thanh toán nhưng trạng thái chưa cập nhật</h2><p>Không thanh toán lần nữa. Giữ mã hồ sơ và mã giao dịch để bộ phận hỗ trợ đối chiếu.</p>""",  # noqa: E501
            90,
        ),
    ]
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
                "id": article_id,
                "title": title,
                "slug": slug,
                "summary": summary,
                "category": category,
                "audiences": audiences,
                "body_html": body_html,
                "search_text": _normalized_search_text(title, summary, body_html),
                "sort_order": sort_order,
                "status": "PUBLISHED",
                "version": 1,
                "published_at": now,
                "created_by": None,
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            }
            for (
                article_id,
                title,
                slug,
                summary,
                category,
                audiences,
                body_html,
                sort_order,
            ) in articles
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cms_guide_feedback_article_created", table_name="cms_guide_feedback"
    )
    op.drop_table("cms_guide_feedback")
    op.drop_index("ix_cms_guide_articles_search_text", table_name="cms_guide_articles")
    op.drop_index("ix_cms_guide_articles_status_order", table_name="cms_guide_articles")
    op.drop_table("cms_guide_articles")
