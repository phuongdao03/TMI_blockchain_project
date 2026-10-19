"""Keep applicant guides task focused and shorten the initiative author label.

Revision ID: 0122_plain_role_guides_and_author
Revises: 0121_guide_plain_terms
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0122_plain_role_guides_and_author"
down_revision: str | None = "0121_guide_plain_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GUIDE_REPLACEMENTS = {
    (
        'Sau khi nâng cấp, mở <a href="/help/create-and-submit-a-dossier">'
        "hướng dẫn tạo và gửi hồ sơ</a> để tiếp tục từng bước."
    ): (
        "Sau khi tài khoản được mở chức năng gửi hồ sơ, "
        "mục Hướng dẫn sử dụng sẽ hiển thị các bước phù hợp."
    ),
    (
        "Bộ phận tiếp nhận, người thẩm định và người quyết định xử lý theo\n"
        "        từng giai đoạn; người nộp không cần gửi lại khi chưa có yêu cầu."
    ): (
        "Hồ sơ được xử lý theo từng giai đoạn; "
        "bạn không cần gửi lại khi chưa có yêu cầu."
    ),
    "Bộ phận tiếp nhận xử lý tiếp.": "Hồ sơ được chuyển sang bước xử lý tiếp theo.",
    "Thanh toán qua PayOS": "Tiếp tục thanh toán",
}


def _search(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


def upgrade() -> None:
    connection = op.get_bind()
    dossier_versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("schema_json", sa.JSON()),
    )
    guides = connection.execute(
        sa.text(
            "SELECT id, title, summary, category, audiences, body_html "
            "FROM cms_guide_articles"
        )
    ).all()
    for guide in guides:
        audiences = guide.audiences
        if isinstance(audiences, str):
            import json

            audiences = json.loads(audiences)
        if not set(audiences).intersection({"PUBLIC", "VIEWER", "USER"}):
            continue
        body = guide.body_html
        for before, after in _GUIDE_REPLACEMENTS.items():
            body = body.replace(before, after)
        if body != guide.body_html:
            connection.execute(
                sa.text(
                    "UPDATE cms_guide_articles SET body_html = :body, "
                    "search_text = :search_text, updated_at = :updated_at "
                    "WHERE id = :id"
                ),
                {
                    "body": body,
                    "search_text": _search(
                        f"{guide.title} {guide.summary} {guide.category} {body}"
                    ),
                    "updated_at": datetime.now(UTC),
                    "id": guide.id,
                },
            )

    versions = connection.execute(
        sa.text(
            "SELECT v.id, v.schema_json FROM dossier_type_versions v "
            "JOIN dossier_types t ON t.id = v.dossier_type_id "
            "WHERE t.code = 'INITIATIVE'"
        )
    ).all()
    for version in versions:
        schema = version.schema_json
        if isinstance(schema, str):
            import json

            schema = json.loads(schema)
        fields = schema.get("fields", [])
        changed = False
        for field in fields:
            if (
                field.get("key") == "proposer"
                and field.get("label") == "Tác giả sáng kiến"
            ):
                field["label"] = "Tác giả"
                changed = True
        if changed:
            connection.execute(
                sa.update(dossier_versions)
                .where(dossier_versions.c.id == UUID(str(version.id)))
                .values(schema_json=schema)
            )


def downgrade() -> None:
    # Wording changes are intentionally retained; old content is not restored.
    pass
