# ruff: noqa: E501
"""Add type-specific rubric answers to reviews.

Revision ID: 0066_type_specific_review_rubric
Revises: 0065_payment_issue_permission
Create Date: 2026-08-30
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0066_type_specific_review_rubric"
down_revision: str | None = "0065_payment_issue_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TYPE_CODES = (
    "CULTURAL_WORK",
    "TRADEMARK",
    "ARTWORK",
    "DOCUMENT",
    "CERTIFICATE",
    "PERSON",
    "ORGANIZATION",
    "PRODUCT",
    "CULTURAL_HERITAGE",
    "INITIATIVE",
    "INTELLECTUAL_ASSET",
    "OTHER",
)

CRITERIA = {
    "ARTWORK": (
        ("originality", "Tính nguyên bản", 40),
        ("artistic_value", "Giá trị nghệ thuật", 35),
        ("craft", "Chất lượng thể hiện", 25),
    ),
    "DOCUMENT": (
        ("provenance", "Nguồn gốc tư liệu", 40),
        ("context", "Bối cảnh và đối chứng", 35),
        ("integrity", "Tính toàn vẹn", 25),
    ),
    "CERTIFICATE": (
        ("issuer", "Tính xác thực đơn vị cấp", 40),
        ("validity", "Hiệu lực", 35),
        ("scope", "Phạm vi chứng nhận", 25),
    ),
    "ORGANIZATION": (
        ("legal_status", "Tư cách pháp lý", 35),
        ("achievements", "Thành tựu kiểm chứng", 35),
        ("impact", "Tác động", 30),
    ),
    "PRODUCT": (
        ("evidence", "Bằng chứng vận hành", 35),
        ("quality", "Chất lượng giải pháp", 35),
        ("impact", "Hiệu quả thực tế", 30),
    ),
    "CULTURAL_HERITAGE": (
        ("provenance", "Nguồn gốc di sản", 35),
        ("community", "Chủ thể cộng đồng", 35),
        ("cultural_value", "Giá trị văn hóa", 30),
    ),
    "INITIATIVE": (
        ("novelty", "Tính mới", 35),
        ("feasibility", "Tính khả thi", 35),
        ("impact", "Tác động", 30),
    ),
    "TRADEMARK": (
        ("rights", "Quyền đối với nhãn hiệu", 40),
        ("use", "Bằng chứng sử dụng", 30),
        ("distinctiveness", "Khả năng phân biệt", 30),
    ),
    "INTELLECTUAL_ASSET": (
        ("rights", "Quyền tài sản trí tuệ", 40),
        ("originality", "Tính nguyên bản", 35),
        ("integrity", "Tính toàn vẹn số", 25),
    ),
    "PERSON": (
        ("identity", "Danh tính", 30),
        ("contribution", "Đóng góp kiểm chứng", 40),
        ("impact", "Tác động", 30),
    ),
    "CULTURAL_WORK": (
        ("provenance", "Nguồn gốc", 35),
        ("cultural_value", "Giá trị văn hóa", 40),
        ("quality", "Chất lượng thể hiện", 25),
    ),
    "OTHER": (
        ("evidence", "Chất lượng bằng chứng", 40),
        ("relevance", "Mức độ phù hợp", 30),
        ("impact", "Giá trị và tác động", 30),
    ),
}


def _rubric(code: str) -> dict[str, object]:
    return {
        "version": "2026.1",
        "title": f"Rubric chuyên biệt — {code}",
        "gates": [
            {
                "key": "eligibility",
                "label": "Đúng đối tượng và phạm vi tiếp nhận",
                "description": "Hồ sơ thuộc đúng loại và đáp ứng điều kiện tiếp nhận.",
                "required": True,
            },
            {
                "key": "rights_and_authority",
                "label": "Quyền nộp và thẩm quyền hợp lệ",
                "description": "Chủ thể có quyền sở hữu, sử dụng hoặc đại diện hợp lệ.",
                "required": True,
            },
            {
                "key": "evidence_integrity",
                "label": "Tính toàn vẹn của bằng chứng",
                "description": "Tài liệu không có dấu hiệu giả mạo hoặc mâu thuẫn trọng yếu.",
                "required": True,
            },
        ],
        "criteria": [
            {
                "key": key,
                "label": label,
                "description": f"Đánh giá {label.lower()} dựa trên bằng chứng đã khóa.",
                "weight": weight,
            }
            for key, label, weight in CRITERIA[code]
        ],
        "thresholds": {"approveMin": 75, "rejectBelow": 50},
    }


def _update_seeded_rubrics(*, remove: bool) -> None:
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("schema_json", sa.JSON()),
    )
    bind = op.get_bind()
    for index, code in enumerate(TYPE_CODES, start=1):
        version_id = UUID(f"20000000-0000-4000-8000-{index:012d}")
        schema = bind.scalar(
            sa.select(versions.c.schema_json).where(versions.c.id == version_id)
        )
        if not isinstance(schema, dict):
            continue
        updated = dict(schema)
        if remove:
            updated.pop("reviewRubric", None)
        else:
            updated["reviewRubric"] = _rubric(code)
        bind.execute(
            versions.update()
            .where(versions.c.id == version_id)
            .values(schema_json=updated)
        )


def upgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(sa.Column("rubric_version", sa.String(120), nullable=True))
        batch.add_column(
            sa.Column("specialist_score", sa.SmallInteger(), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "gate_answers",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.add_column(
            sa.Column(
                "specialist_answers",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.create_check_constraint(
            "specialist_score_range",
            "specialist_score IS NULL OR specialist_score BETWEEN 0 AND 100",
        )
    _update_seeded_rubrics(remove=False)


def downgrade() -> None:
    _update_seeded_rubrics(remove=True)
    with op.batch_alter_table("reviews") as batch:
        batch.drop_constraint("specialist_score_range", type_="check")
        batch.drop_column("specialist_answers")
        batch.drop_column("gate_answers")
        batch.drop_column("specialist_score")
        batch.drop_column("rubric_version")
