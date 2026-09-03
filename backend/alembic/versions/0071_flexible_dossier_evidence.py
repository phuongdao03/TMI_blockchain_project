"""Create flexible evidence policies on active dossier type versions.

Revision ID: 0071_flexible_dossier_evidence
Revises: 0070_start_reviews_immediately
Create Date: 2026-09-02
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0071_flexible_dossier_evidence"
down_revision: str | None = "0070_start_reviews_immediately"
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
VERSION_IDS = {
    code: UUID(f"40000000-0000-4000-8000-{index:012d}")
    for index, code in enumerate(TYPE_CODES, start=1)
}

PDF = "application/pdf"
DOC = "application/msword"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLS = "application/vnd.ms-excel"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
IMAGES = ("image/jpeg", "image/png", "image/webp")
AUDIO = ("audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-wav")
VIDEO = ("video/mp4", "video/webm")
DOCUMENTS = (PDF, DOC, DOCX)

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
        ("evidence", "Chất lượng căn cứ", 40),
        ("relevance", "Mức độ phù hợp", 30),
        ("impact", "Giá trị và tác động", 30),
    ),
}


def _rule(
    key: str,
    label: str,
    mime_types: Sequence[str],
    *,
    max_bytes: int = 30 * 1024 * 1024,
    max_count: int = 20,
    visibility: str = "INTERNAL",
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "documentType": key,
        "required": False,
        "allowedMimeTypes": list(mime_types),
        "maxBytes": max_bytes,
        "maxCount": max_count,
        "defaultVisibility": visibility,
    }


def _rules(code: str) -> list[dict[str, object]]:
    primary_formats: dict[str, Sequence[str]] = {
        "ARTWORK": (*IMAGES, *AUDIO, *VIDEO, PDF),
        "CULTURAL_WORK": (*IMAGES, *AUDIO, *VIDEO, PDF),
        "CULTURAL_HERITAGE": (*IMAGES, *AUDIO, *VIDEO, PDF),
        "DOCUMENT": (*DOCUMENTS, *IMAGES),
        "CERTIFICATE": (PDF, *IMAGES),
        "TRADEMARK": (PDF, *IMAGES),
        "PERSON": (*IMAGES, *AUDIO, *VIDEO, *DOCUMENTS),
        "ORGANIZATION": (*DOCUMENTS, *IMAGES, *VIDEO),
        "PRODUCT": (*IMAGES, *VIDEO, *DOCUMENTS, XLS, XLSX),
        "INITIATIVE": (*DOCUMENTS, *IMAGES, *VIDEO, XLS, XLSX),
        "INTELLECTUAL_ASSET": (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO, "application/zip"),
        "OTHER": (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO, XLS, XLSX, "application/zip"),
    }
    public_primary = code in {
        "ARTWORK",
        "CULTURAL_WORK",
        "CULTURAL_HERITAGE",
        "PRODUCT",
        "TRADEMARK",
    }
    return [
        _rule(
            "PRIMARY",
            "Nội dung hoặc đối tượng chính",
            primary_formats[code],
            max_bytes=30 * 1024 * 1024,
            visibility="PUBLIC_PREVIEW" if public_primary else "INTERNAL",
        ),
        _rule(
            "PROVENANCE", "Thông tin nguồn gốc", (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO)
        ),
        _rule("RIGHTS", "Quyền sở hữu hoặc đại diện", (*DOCUMENTS, *IMAGES)),
        _rule(
            "ACHIEVEMENT",
            "Thành tích hoặc thông tin đối chứng",
            (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO, XLS, XLSX),
        ),
        _rule(
            "SUPPORTING",
            "Tài liệu bổ sung",
            (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO, XLS, XLSX, "application/zip"),
        ),
        _rule(
            "OTHER",
            "Tài liệu khác",
            (*DOCUMENTS, *IMAGES, *AUDIO, *VIDEO, XLS, XLSX, "application/zip"),
        ),
    ]


def _rubric(code: str) -> dict[str, object]:
    return {
        "version": "2026.2",
        "title": "Tiêu chí thẩm định theo loại hồ sơ",
        "gates": [
            {
                "key": "eligibility",
                "label": "Đúng đối tượng và phạm vi tiếp nhận",
                "description": "Hồ sơ thuộc đúng loại và phạm vi nền tảng tiếp nhận.",
                "required": True,
            },
            {
                "key": "rights_and_authority",
                "label": "Có căn cứ về quyền nộp hồ sơ",
                "description": (
                    "Thông tin và tài liệu đủ để đánh giá quyền nộp hoặc đại diện."
                ),
                "required": True,
            },
            {
                "key": "evidence_integrity",
                "label": "Tài liệu nhất quán và có thể kiểm tra",
                "description": (
                    "Không có mâu thuẫn trọng yếu hoặc dấu hiệu làm sai lệch."
                ),
                "required": True,
            },
        ],
        "criteria": [
            {
                "key": key,
                "label": label,
                "description": f"Đánh giá {label.lower()} từ nội dung hồ sơ đã khóa.",
                "weight": weight,
            }
            for key, label, weight in CRITERIA[code]
        ],
        "thresholds": {"approveMin": 75, "rejectBelow": 50},
    }


def _tables() -> tuple[sa.TableClause, sa.TableClause]:
    return (
        sa.table(
            "dossier_types", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
        ),
        sa.table(
            "dossier_type_versions",
            sa.column("id", sa.Uuid()),
            sa.column("dossier_type_id", sa.Uuid()),
            sa.column("version_no", sa.Integer()),
            sa.column("schema_json", sa.JSON()),
        ),
    )


def _schema(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("Dossier type schema is not an object.")
    return copy.deepcopy(value)


def upgrade() -> None:
    dossier_types, versions = _tables()
    bind = op.get_bind()
    inserts: list[dict[str, object]] = []
    for code in TYPE_CODES:
        type_id = bind.scalar(
            sa.select(dossier_types.c.id).where(dossier_types.c.code == code)
        )
        if type_id is None:
            continue
        latest = (
            bind.execute(
                sa.select(versions.c.version_no, versions.c.schema_json)
                .where(versions.c.dossier_type_id == type_id)
                .order_by(versions.c.version_no.desc())
                .limit(1)
            )
            .mappings()
            .one_or_none()
        )
        if latest is None or latest["version_no"] != 2:
            continue
        schema = _schema(latest["schema_json"])
        schema["documentRules"] = _rules(code)
        schema["reviewRubric"] = _rubric(code)
        inserts.append(
            {
                "id": VERSION_IDS[code],
                "dossier_type_id": type_id,
                "version_no": 3,
                "schema_json": schema,
            }
        )
    if inserts:
        op.bulk_insert(versions, inserts)


def downgrade() -> None:
    _, versions = _tables()
    op.execute(
        sa.delete(versions).where(versions.c.id.in_(tuple(VERSION_IDS.values())))
    )
