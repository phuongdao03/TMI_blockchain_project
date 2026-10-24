"""Complete the seeded membership catalog copy.

Revision ID: 0132_membership_catalog_content
Revises: 0131_membership_plan_benefits
"""

from collections.abc import Mapping

import sqlalchemy as sa

from alembic import op

revision = "0132_membership_catalog_content"
down_revision = "0131_membership_plan_benefits"
branch_labels = None
depends_on = None

PREVIOUS_COPY = {
    "SILVER": {
        "description": "Mở rộng tri thức, hồ sơ chuyên môn và kết nối cộng đồng.",
        "benefits": [
            "Toàn bộ quyền lợi cấp Đồng.",
            "Hồ sơ nâng cao và thư viện nội dung hội viên.",
            "4 chương trình Tinh Hoa Talk chuyên đề mỗi chu kỳ.",
            "Khung avatar Bạc và thông báo về chương trình phù hợp.",
        ],
        "conditions": (
            "Không bao gồm quyền vào phòng chat Đồng hành hoặc Tinh Hoa Circle."
        ),
    },
    "COMPANION": {
        "description": "Đồng hành cùng những người muốn hợp tác và phát triển.",
        "benefits": [
            "Toàn bộ quyền lợi cấp Đồng và Bạc.",
            "Phòng chat Đồng hành và khung avatar Vàng.",
            "6 chương trình Tinh Hoa Connect mỗi chu kỳ.",
            "Kết nối theo nhóm và đăng nhu cầu hợp tác.",
        ],
        "conditions": (
            "Hoạt động kết nối tùy điều kiện từng chương trình; "
            "không bảo đảm có đối tác phù hợp."
        ),
    },
    "PRESTIGE": {
        "description": "Không gian chuyên sâu để kết nối và lan tỏa tinh hoa.",
        "benefits": [
            "Toàn bộ quyền lợi các cấp Đồng, Bạc và Vàng.",
            "Phòng Tinh Hoa Circle và khung avatar Kim cương.",
            "Tối đa 2 buổi Circle và 1 buổi tư vấn 30 phút mỗi chu kỳ.",
            "Tối đa 2 đề xuất kết nối có điều phối mỗi chu kỳ.",
        ],
        "conditions": (
            "Phải được xét duyệt trước khi thanh toán; quyền lợi tùy điều kiện "
            "công bố và chỗ trống."
        ),
    },
}

COMPLETE_COPY = {
    "SILVER": {
        "description": (
            "Dành cho hội viên muốn phát triển hồ sơ chuyên môn và học hỏi qua "
            "các chương trình chuyên đề."
        ),
        "benefits": [
            "Huy hiệu cấp Bạc và khung avatar Bạc.",
            "Hồ sơ cá nhân nâng cao với thông tin chuyên môn và lĩnh vực hoạt động.",
            "Thêm liên kết chuyên môn, website hoặc sản phẩm theo quy định cộng đồng.",
            "Truy cập thư viện nội dung hội viên và xem lại nội dung được cấp quyền.",
            "Đăng ký 4 chương trình Tinh Hoa Talk chuyên đề trong mỗi chu kỳ 12 tháng.",
            "Nhận thông báo về chương trình hội viên và sự kiện phù hợp.",
        ],
        "conditions": (
            "Chương trình đăng ký theo lịch công bố và số chỗ còn. Không bao gồm "
            "phòng chat Đồng hành hoặc Tinh Hoa Circle."
        ),
    },
    "COMPANION": {
        "description": (
            "Dành cho hội viên muốn chủ động tìm cộng sự, chia sẻ nhu cầu và "
            "kết nối theo nhóm."
        ),
        "benefits": [
            "Huy hiệu cấp Vàng và khung avatar Vàng.",
            "Truy cập phòng chat Đồng hành dành cho hội viên Vàng và Kim cương.",
            "Đăng ký 6 chương trình Tinh Hoa Connect trong mỗi chu kỳ 12 tháng.",
            "Đăng nhu cầu hợp tác trong không gian kết nối theo quy định.",
            "Tìm kiếm hội viên đã công khai lĩnh vực hoạt động và tham gia kết nối "
            "theo nhóm.",
            "Đăng ký sớm chương trình phù hợp khi chính sách ưu tiên được công bố.",
            "Đăng ký workshop hội viên theo điều kiện của từng chương trình.",
        ],
        "conditions": (
            "Kết nối tùy sự đồng ý của các bên và điều kiện từng chương trình; "
            "không bảo đảm tìm được đối tác. Workshop có thể có điều kiện hoặc "
            "khoản phí riêng."
        ),
    },
    "PRESTIGE": {
        "description": (
            "Dành cho hội viên cần không gian kết nối chuyên sâu và hỗ trợ điều "
            "phối theo từng đề xuất."
        ),
        "benefits": [
            "Huy hiệu cấp Kim cương và khung avatar Kim cương.",
            "Truy cập phòng chat Tinh Hoa Circle.",
            "Tham gia tối đa 2 buổi Tinh Hoa Circle chuyên sâu trong mỗi chu kỳ "
            "12 tháng.",
            "Một buổi tư vấn hoặc định hướng 30 phút trong mỗi chu kỳ hội viên.",
            "Tối đa 2 đề xuất kết nối có điều phối trong mỗi chu kỳ hội viên.",
            "Gửi câu chuyện hội viên để Ban biên tập xem xét giới thiệu trong "
            "chuyên mục cộng đồng.",
            "Đề xuất kết nối chuyên sâu để Ban quản trị tiếp nhận và xử lý theo "
            "quy trình.",
            "Đăng ký chương trình giới hạn chỗ theo điều kiện được công bố.",
        ],
        "conditions": (
            "Cần được xét duyệt trước khi thanh toán. Mỗi kết nối chỉ diễn ra khi "
            "các bên đồng ý; nội dung giới thiệu phải qua tiêu chuẩn biên tập. "
            "Quyền lợi tùy lịch và số chỗ; không bảo đảm hợp tác, doanh thu hoặc "
            "gặp cá nhân cụ thể."
        ),
    },
}


def _apply_copy(
    source: Mapping[str, Mapping[str, object]],
    target: Mapping[str, Mapping[str, object]],
) -> None:
    plans = sa.table(
        "membership_plans",
        sa.column("id", sa.Uuid()),
        sa.column("tier", sa.String(16)),
        sa.column("active", sa.Boolean()),
        sa.column("description", sa.Text()),
        sa.column("benefits", sa.JSON()),
        sa.column("conditions", sa.Text()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            plans.c.id,
            plans.c.tier,
            plans.c.description,
            plans.c.benefits,
            plans.c.conditions,
        ).where(plans.c.active.is_(True))
    ).mappings()
    for row in rows:
        previous = source.get(row["tier"])
        replacement = target.get(row["tier"])
        if previous is None or replacement is None:
            continue
        changes = {
            field: replacement[field]
            for field in ("description", "benefits", "conditions")
            if row[field] == previous[field]
        }
        if changes:
            bind.execute(
                plans.update().where(plans.c.id == row["id"]).values(**changes)
            )


def upgrade() -> None:
    _apply_copy(PREVIOUS_COPY, COMPLETE_COPY)


def downgrade() -> None:
    _apply_copy(COMPLETE_COPY, PREVIOUS_COPY)
