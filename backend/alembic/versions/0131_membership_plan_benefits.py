"""Store tier descriptions and benefits in the membership catalog.

Revision ID: 0131_membership_plan_benefits
Revises: 0130_community_events
"""

import sqlalchemy as sa

from alembic import op

revision = "0131_membership_plan_benefits"
down_revision = "0130_community_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "membership_plans",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "membership_plans",
        sa.Column(
            "benefits",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "membership_plans",
        sa.Column("conditions", sa.Text(), nullable=False, server_default=""),
    )

    plans = sa.table(
        "membership_plans",
        sa.column("tier", sa.String(16)),
        sa.column("description", sa.Text()),
        sa.column("benefits", sa.JSON()),
        sa.column("conditions", sa.Text()),
    )
    defaults = {
        "SILVER": (
            "Mở rộng tri thức, hồ sơ chuyên môn và kết nối cộng đồng.",
            [
                "Toàn bộ quyền lợi cấp Đồng.",
                "Hồ sơ nâng cao và thư viện nội dung hội viên.",
                "4 chương trình Tinh Hoa Talk chuyên đề mỗi chu kỳ.",
                "Khung avatar Bạc và thông báo về chương trình phù hợp.",
            ],
            "Không bao gồm quyền vào phòng chat Đồng hành hoặc Tinh Hoa Circle.",
        ),
        "COMPANION": (
            "Đồng hành cùng những người muốn hợp tác và phát triển.",
            [
                "Toàn bộ quyền lợi cấp Đồng và Bạc.",
                "Phòng chat Đồng hành và khung avatar Vàng.",
                "6 chương trình Tinh Hoa Connect mỗi chu kỳ.",
                "Kết nối theo nhóm và đăng nhu cầu hợp tác.",
            ],
            (
                "Hoạt động kết nối tùy điều kiện từng chương trình; "
                "không bảo đảm có đối "
                "tác phù hợp."
            ),
        ),
        "PRESTIGE": (
            "Không gian chuyên sâu để kết nối và lan tỏa tinh hoa.",
            [
                "Toàn bộ quyền lợi các cấp Đồng, Bạc và Vàng.",
                "Phòng Tinh Hoa Circle và khung avatar Kim cương.",
                "Tối đa 2 buổi Circle và 1 buổi tư vấn 30 phút mỗi chu kỳ.",
                "Tối đa 2 đề xuất kết nối có điều phối mỗi chu kỳ.",
            ],
            (
                "Phải được xét duyệt trước khi thanh toán; quyền lợi "
                "tùy điều kiện công "
                "bố và chỗ trống."
            ),
        ),
    }
    bind = op.get_bind()
    for tier, (description, benefits, conditions) in defaults.items():
        bind.execute(
            plans.update()
            .where(plans.c.tier == tier)
            .values(
                description=description,
                benefits=benefits,
                conditions=conditions,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    plans = sa.table(
        "membership_plans",
        sa.column("description", sa.Text()),
        sa.column("benefits", sa.JSON()),
        sa.column("conditions", sa.Text()),
    )
    configured = bind.scalar(
        sa.select(sa.func.count())
        .select_from(plans)
        .where(
            sa.or_(
                plans.c.description != "",
                plans.c.conditions != "",
                plans.c.benefits != [],
            )
        )
    )
    if configured:
        raise RuntimeError(
            "Cannot drop configured membership benefits; export the plan catalog "
            "before rollback."
        )
    op.drop_column("membership_plans", "conditions")
    op.drop_column("membership_plans", "benefits")
    op.drop_column("membership_plans", "description")
