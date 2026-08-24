"""Seed the versioned default dossier type catalog.

Revision ID: 0055_seed_default_dossier_types
Revises: 0054_dynamic_dossier_types
Create Date: 2026-08-23
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0055_seed_default_dossier_types"
down_revision: str | None = "0054_dynamic_dossier_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")


def _schema(description: str, fields: list[dict[str, object]]) -> dict[str, object]:
    return {"description": description, "fields": fields}


def _text(key: str, label: str, *, required: bool = True) -> dict[str, object]:
    return {"key": key, "type": "text", "label": label, "required": required}


def _catalog() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    definitions = (
        (
            "CULTURAL_WORK",
            "Tác phẩm văn hóa",
            _schema(
                "Xác lập nguồn gốc, tác giả và bối cảnh hình thành của tác phẩm "
                "văn hóa.",
                [
                    _text("rightsHolder", "Tác giả hoặc chủ sở hữu"),
                    {
                        "key": "workFormat",
                        "type": "select",
                        "label": "Loại hình tác phẩm",
                        "required": True,
                        "options": [
                            {"value": "VISUAL", "label": "Mỹ thuật / thiết kế"},
                            {"value": "PUBLICATION", "label": "Ấn phẩm"},
                            {"value": "DIGITAL", "label": "Nội dung số"},
                        ],
                    },
                ],
            ),
        ),
        (
            "TRADEMARK",
            "Nhãn hiệu và thương hiệu",
            _schema(
                "Lưu thông tin nhận diện, chủ sở hữu và phạm vi sử dụng thương hiệu.",
                [
                    _text("rightsHolder", "Chủ sở hữu nhãn hiệu"),
                    {
                        "key": "useScope",
                        "type": "textarea",
                        "label": "Phạm vi sử dụng",
                        "required": False,
                        "placeholder": "Lĩnh vực, thị trường hoặc kênh sử dụng.",
                    },
                ],
            ),
        ),
        (
            "ARTWORK",
            "Tác phẩm nghệ thuật",
            _schema(
                "Dành cho mỹ thuật, nhiếp ảnh, âm nhạc, sân khấu và các tác phẩm "
                "sáng tạo.",
                [
                    _text("creator", "Tác giả / nhóm tác giả"),
                    {
                        "key": "artForm",
                        "type": "select",
                        "label": "Loại hình",
                        "required": True,
                        "options": [
                            {"value": "VISUAL_ART", "label": "Mỹ thuật"},
                            {"value": "PHOTOGRAPHY", "label": "Nhiếp ảnh"},
                            {"value": "MUSIC", "label": "Âm nhạc"},
                        ],
                    },
                ],
            ),
        ),
        (
            "DOCUMENT",
            "Tài liệu và tư liệu",
            _schema(
                "Dành cho bản thảo, tư liệu nghiên cứu, hồ sơ lưu trữ và tài liệu số.",
                [
                    _text("custodian", "Đơn vị hoặc cá nhân lưu giữ"),
                    {
                        "key": "documentDate",
                        "type": "date",
                        "label": "Ngày lập tài liệu",
                        "required": False,
                    },
                ],
            ),
        ),
        (
            "CERTIFICATE",
            "Văn bằng, chứng nhận",
            _schema(
                "Ghi nhận văn bằng, giải thưởng, chứng nhận hoặc xác nhận chuyên môn.",
                [
                    _text("issuer", "Cơ quan / tổ chức cấp"),
                    {
                        "key": "issuedAt",
                        "type": "date",
                        "label": "Ngày cấp",
                        "required": True,
                    },
                ],
            ),
        ),
        (
            "PERSON",
            "Cá nhân tiêu biểu",
            _schema(
                "Hồ sơ giới thiệu một cá nhân, thành tựu và đóng góp đã được kiểm "
                "chứng.",
                [
                    _text("fullName", "Họ và tên"),
                    {
                        "key": "contribution",
                        "type": "textarea",
                        "label": "Đóng góp tiêu biểu",
                        "required": True,
                    },
                ],
            ),
        ),
        (
            "ORGANIZATION",
            "Tổ chức, doanh nghiệp",
            _schema(
                "Hồ sơ về tổ chức, doanh nghiệp, đơn vị cộng đồng hoặc sáng tạo.",
                [
                    _text("legalRepresentative", "Người đại diện"),
                    _text("registrationNumber", "Mã số đăng ký", required=False),
                ],
            ),
        ),
        (
            "PRODUCT",
            "Sản phẩm và giải pháp",
            _schema(
                "Dành cho sản phẩm, dịch vụ, giải pháp công nghệ hoặc mô hình có giá "
                "trị thực tiễn.",
                [
                    _text("provider", "Đơn vị phát triển"),
                    {
                        "key": "solutionArea",
                        "type": "select",
                        "label": "Lĩnh vực",
                        "required": True,
                        "options": [
                            {"value": "TECHNOLOGY", "label": "Công nghệ"},
                            {"value": "CULTURE", "label": "Văn hóa"},
                            {"value": "COMMUNITY", "label": "Cộng đồng"},
                        ],
                    },
                ],
            ),
        ),
        (
            "CULTURAL_HERITAGE",
            "Di sản văn hóa",
            _schema(
                "Ghi nhận di sản vật thể, phi vật thể, tri thức bản địa hoặc không "
                "gian văn hóa.",
                [
                    _text("heritageCommunity", "Cộng đồng / chủ thể thực hành"),
                    _text("location", "Địa điểm hoặc phạm vi phân bố", required=False),
                ],
            ),
        ),
        (
            "INITIATIVE",
            "Sáng kiến",
            _schema(
                "Dành cho ý tưởng, sáng kiến cải tiến hoặc đề án mang lại giá trị cộng "
                "đồng.",
                [
                    _text("proposer", "Tác giả sáng kiến"),
                    {
                        "key": "impact",
                        "type": "textarea",
                        "label": "Giá trị và tác động",
                        "required": True,
                    },
                ],
            ),
        ),
        (
            "INTELLECTUAL_ASSET",
            "Tài sản trí tuệ số",
            _schema(
                "Xác lập bằng chứng nguồn gốc cho tài sản số, dữ liệu, thiết kế và nội "
                "dung trực tuyến.",
                [
                    _text("rightsHolder", "Chủ sở hữu"),
                    {
                        "key": "assetFormat",
                        "type": "select",
                        "label": "Định dạng tài sản",
                        "required": True,
                        "options": [
                            {"value": "SOFTWARE", "label": "Phần mềm"},
                            {"value": "DATASET", "label": "Dữ liệu"},
                            {"value": "DIGITAL_CONTENT", "label": "Nội dung số"},
                        ],
                    },
                ],
            ),
        ),
        (
            "OTHER",
            "Loại hồ sơ khác",
            _schema(
                "Dùng khi hồ sơ chưa thuộc nhóm có sẵn; cán bộ sẽ hướng dẫn phân loại "
                "tiếp theo.",
                [
                    _text("applicantRole", "Người gửi hồ sơ"),
                    {
                        "key": "classificationNote",
                        "type": "textarea",
                        "label": "Đề xuất phân loại",
                        "required": True,
                    },
                ],
            ),
        ),
    )
    types: list[dict[str, object]] = []
    versions: list[dict[str, object]] = []
    for index, (code, name, schema) in enumerate(definitions, start=1):
        type_id = UUID(f"10000000-0000-4000-8000-{index:012d}")
        version_id = UUID(f"20000000-0000-4000-8000-{index:012d}")
        types.append(
            {
                "id": type_id,
                "category_id": CATEGORY_ID,
                "code": code,
                "name": name,
                "is_active": True,
            }
        )
        versions.append(
            {
                "id": version_id,
                "dossier_type_id": type_id,
                "version_no": 1,
                "schema_json": schema,
            }
        )
    return types, versions


def upgrade() -> None:
    dossier_types = sa.table(
        "dossier_types",
        sa.column("id", sa.Uuid()),
        sa.column("category_id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    dossier_type_versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("dossier_type_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("schema_json", sa.JSON()),
    )
    types, versions = _catalog()
    op.bulk_insert(dossier_types, types)
    op.bulk_insert(dossier_type_versions, versions)


def downgrade() -> None:
    type_ids = [row["id"] for row in _catalog()[0]]
    op.execute(
        sa.delete(
            sa.table("dossier_type_versions", sa.column("dossier_type_id", sa.Uuid()))
        ).where(sa.column("dossier_type_id", sa.Uuid()).in_(type_ids))
    )
    op.execute(
        sa.delete(sa.table("dossier_types", sa.column("id", sa.Uuid()))).where(
            sa.column("id", sa.Uuid()).in_(type_ids)
        )
    )
