"""Persistent account-owned login vouchers."""

from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision = "0145_login_vouchers"
down_revision = "0144_dossier_preparations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    campaigns = op.create_table(
        "voucher_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("amount_vnd", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount_vnd > 0", name="amount_positive"),
        sa.CheckConstraint("validity_days > 0", name="validity_positive"),
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="valid_period",
        ),
    )
    op.create_table(
        "voucher_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("amount_vnd", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "campaign_id", name="uq_voucher_claims_user_campaign"
        ),
    )
    op.create_index("ix_voucher_claims_user_id", "voucher_claims", ["user_id"])
    op.bulk_insert(
        campaigns,
        [
            {
                "id": UUID("50e981db-3cc9-478b-859e-315f582f5145"),
                "code": "EARLY_MEMBER_2026",
                "title": "Tinh Hoa Việt gửi tặng bạn 200.000đ!",
                "description": (
                    "Cảm ơn bạn đã đồng hành cùng Tinh Hoa Việt. "
                    "Nhận món quà tri ân và lưu vào tài khoản của bạn."
                ),
                "terms": (
                    "Ưu đãi dành cho phí hồ sơ đề cử, áp dụng một lần. "
                    "Không quy đổi thành tiền mặt. Chức năng áp dụng khi "
                    "thanh toán sẽ được thông báo sau."
                ),
                "image_path": "/images/promotions/golden-voucher.png",
                "amount_vnd": 200_000,
                "validity_days": 60,
                "active": True,
            }
        ],
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM voucher_claims")):
        raise RuntimeError("Preserve claimed vouchers before downgrade.")
    op.drop_index("ix_voucher_claims_user_id", table_name="voucher_claims")
    op.drop_table("voucher_claims")
    op.drop_table("voucher_campaigns")
