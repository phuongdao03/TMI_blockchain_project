"""Publish optional type-specific narratives without changing historic schemas."""

from copy import deepcopy
from uuid import UUID, uuid5

import sqlalchemy as sa

from alembic import op

revision = "0151_type_narrative_schemas"
down_revision = "0150_dossier_applicant_claims"
branch_labels = None
depends_on = None

NAMESPACE = UUID("3be263c8-02b4-438b-ab45-158a26cc5613")

# Frozen content: do not import the application's evolving catalog into a migration.
NARRATIVES = {
    "CULTURAL_WORK": (
        (
            "formation",
            "Bối cảnh hình thành tác phẩm",
            "Nêu thời gian, địa điểm, hoàn cảnh sáng tạo và nguồn đối chiếu nếu có.",
            "Ví dụ: ý tưởng hình thành năm nào, từ hoạt động hoặc trải nghiệm nào?",
        ),
        (
            "creative_contribution",
            "Đóng góp sáng tạo của tác phẩm",
            (
                "Mô tả phần đóng góp của tác giả; phân biệt nội dung tự tạo "
                "và nội dung kế thừa."
            ),
            "Ví dụ: cách thể hiện, cấu trúc hoặc nội dung do tác giả phát triển.",
        ),
        (
            "cultural_value",
            "Giá trị văn hóa và đối tượng tiếp nhận",
            "Giải thích giá trị mà tác phẩm hướng tới và nhóm người tiếp nhận cụ thể.",
            (
                "Ví dụ: tri thức, ký ức hoặc thực hành văn hóa được giới "
                "thiệu qua tác phẩm."
            ),
        ),
        (
            "recognition",
            "Quá trình công bố và ghi nhận",
            (
                "Liệt kê lần công bố hoặc ghi nhận đã có; nêu đơn vị, thời "
                "điểm và nguồn nếu biết."
            ),
            "Ví dụ: tên sự kiện giới thiệu, ngày công bố, bài viết hoặc hồ sơ lưu trữ.",
        ),
    ),
    "TRADEMARK": (
        (
            "development",
            "Lịch sử hình thành thương hiệu",
            (
                "Trình bày các mốc hình thành và phát triển, cùng chủ thể "
                "phụ trách từng giai đoạn."
            ),
            "Ví dụ: thời điểm bắt đầu sử dụng và những lần thay đổi nhận diện chính.",
        ),
        (
            "positioning",
            "Đặc điểm nhận diện và giá trị khác biệt",
            (
                "Mô tả dấu hiệu nhận diện và giá trị sử dụng; không coi tự "
                "khai là xác nhận quyền."
            ),
            (
                "Ví dụ: đặc điểm tên gọi, hình ảnh và cách người dùng nhận "
                "biết thương hiệu."
            ),
        ),
        (
            "market_presence",
            "Quá trình sử dụng và phạm vi hiện diện",
            (
                "Nêu hoạt động sử dụng thực tế theo thời gian, địa bàn hoặc "
                "kênh có thể đối chiếu."
            ),
            (
                "Ví dụ: nhóm sản phẩm, khu vực hoạt động và tài liệu ghi "
                "nhận việc sử dụng."
            ),
        ),
        (
            "recognition",
            "Ghi nhận và đóng góp của thương hiệu",
            (
                "Nêu ghi nhận hoặc đóng góp đã có, kèm thời điểm, chủ thể "
                "ghi nhận và giới hạn thông tin."
            ),
            "Ví dụ: chương trình tham gia, phản hồi có nguồn hoặc hoạt động cộng đồng.",
        ),
    ),
    "ARTWORK": (
        (
            "creation",
            "Quá trình sáng tác",
            (
                "Mô tả ý tưởng, các giai đoạn sáng tác và những người tham "
                "gia vào tác phẩm."
            ),
            (
                "Ví dụ: từ phác thảo, thử nghiệm đến bản hoàn thiện; mốc "
                "thời gian tương ứng."
            ),
        ),
        (
            "materials_technique",
            "Chất liệu và kỹ thuật thể hiện",
            (
                "Nêu chất liệu, công cụ và kỹ thuật có ý nghĩa đối với cách "
                "thể hiện tác phẩm."
            ),
            (
                "Ví dụ: chất liệu chính, kỹ thuật xử lý và đặc điểm của "
                "phiên bản được đề cử."
            ),
        ),
        (
            "originality",
            "Phần sáng tạo riêng và nội dung kế thừa",
            (
                "Chỉ rõ đóng góp riêng, nguồn cảm hứng và phần sử dụng từ "
                "nguồn khác nếu có."
            ),
            (
                "Ví dụ: phần bố cục do tác giả phát triển; nguồn tư liệu "
                "hoặc chất liệu tham khảo."
            ),
        ),
        (
            "presentation",
            "Trưng bày, biểu diễn và ghi nhận",
            (
                "Nêu lần trưng bày, biểu diễn, công bố hoặc ghi nhận; không "
                "suy diễn từ ảnh sự kiện."
            ),
            "Ví dụ: tên triển lãm, đơn vị tổ chức, thời gian và tài liệu dẫn chiếu.",
        ),
    ),
    "DOCUMENT": (
        (
            "provenance",
            "Nguồn gốc và hoàn cảnh lập tư liệu",
            (
                "Nêu người hoặc đơn vị lập tư liệu, hoàn cảnh hình thành và "
                "phần chưa xác định."
            ),
            "Ví dụ: tư liệu được lập trong hoạt động nào, vào khoảng thời gian nào?",
        ),
        (
            "custody",
            "Quá trình lưu giữ và chuyển giao",
            (
                "Mô tả các mốc lưu giữ, sao chép hoặc chuyển giao mà người "
                "nộp có thông tin."
            ),
            "Ví dụ: cá nhân, đơn vị từng lưu giữ; căn cứ tiếp nhận bản đang sử dụng.",
        ),
        (
            "historical_context",
            "Bối cảnh và nội dung phản ánh",
            (
                "Giới thiệu sự kiện, địa bàn hoặc chủ đề được phản ánh, phân "
                "biệt mô tả và nhận định."
            ),
            (
                "Ví dụ: chủ đề chính, giai đoạn được phản ánh và phạm vi nội "
                "dung còn thiếu."
            ),
        ),
        (
            "research_value",
            "Giá trị sử dụng và tình trạng tư liệu",
            (
                "Nêu giá trị tham khảo, mức độ đầy đủ, tình trạng bảo quản "
                "và giới hạn khi sử dụng."
            ),
            "Ví dụ: phần nội dung còn đọc được, bản gốc hay bản sao, nhu cầu bảo quản.",
        ),
    ),
    "CERTIFICATE": (
        (
            "recognition_basis",
            "Nội dung và căn cứ ghi nhận",
            (
                "Mô tả chính xác nội dung được ghi nhận, đối tượng nhận và "
                "điều kiện nếu biết."
            ),
            "Ví dụ: chứng nhận ghi nhận hoạt động nào, cho cá nhân hoặc tổ chức nào?",
        ),
        (
            "issuer_context",
            "Bối cảnh cấp và đơn vị ghi nhận",
            (
                "Nêu chương trình, đơn vị cấp và phạm vi ghi nhận; không suy "
                "rộng giá trị chứng nhận."
            ),
            "Ví dụ: tên chương trình, kỳ xét chọn và đầu mối công khai của đơn vị cấp.",
        ),
        (
            "achievement",
            "Quá trình đạt thành tích",
            (
                "Trình bày hoạt động hoặc kết quả dẫn đến việc được ghi "
                "nhận, có mốc thời gian."
            ),
            "Ví dụ: công việc đã thực hiện, sản phẩm hoặc kết quả tham gia xét chọn.",
        ),
        (
            "verification_context",
            "Thông tin phục vụ đối chiếu",
            (
                "Nêu nguồn hoặc cách có thể đối chiếu nội dung; ghi rõ phần "
                "chưa có nguồn xác nhận."
            ),
            "Ví dụ: số hiệu, danh sách công bố, đường dẫn nguồn hoặc đầu mối xác nhận.",
        ),
    ),
    "PERSON": (
        (
            "career",
            "Quá trình hoạt động và chuyên môn",
            "Tóm tắt các giai đoạn hoạt động liên quan trực tiếp đến nội dung đề cử.",
            "Ví dụ: lĩnh vực chuyên môn, vai trò và mốc thời gian của từng giai đoạn.",
        ),
        (
            "achievements",
            "Thành tựu tiêu biểu",
            "Nêu từng thành tựu, thời điểm, vai trò cá nhân và căn cứ ghi nhận nếu có.",
            (
                "Ví dụ: tên công trình hoặc kết quả; phần việc do cá nhân "
                "trực tiếp thực hiện."
            ),
        ),
        (
            "contribution",
            "Đóng góp cho chuyên môn và cộng đồng",
            (
                "Mô tả hoạt động, người thụ hưởng và đóng góp cụ thể; tránh "
                "chỉ liệt kê danh hiệu."
            ),
            "Ví dụ: hoạt động truyền dạy, hỗ trợ cộng đồng hoặc phát triển chuyên môn.",
        ),
        (
            "impact",
            "Thời gian và phạm vi ảnh hưởng",
            (
                "Giải thích phạm vi ảnh hưởng bằng thông tin có nguồn; nêu "
                "giới hạn của ước tính."
            ),
            (
                "Ví dụ: địa bàn, nhóm người thụ hưởng và giai đoạn có kết "
                "quả quan sát được."
            ),
        ),
    ),
    "ORGANIZATION": (
        (
            "history",
            "Quá trình hình thành và phát triển",
            "Nêu các mốc hình thành, thay đổi hoạt động và chủ thể kế thừa nếu có.",
            (
                "Ví dụ: năm bắt đầu hoạt động, các giai đoạn phát triển và "
                "thay đổi tên gọi."
            ),
        ),
        (
            "operations",
            "Hoạt động chuyên môn và thế mạnh",
            (
                "Mô tả hoạt động liên quan đến đề cử và cách tổ chức thực "
                "hiện trong thực tế."
            ),
            (
                "Ví dụ: lĩnh vực hoạt động, nhóm sản phẩm hoặc dịch vụ và "
                "đối tượng phục vụ."
            ),
        ),
        (
            "achievements",
            "Kết quả và thành tựu nổi bật",
            (
                "Liệt kê kết quả có thời gian, phạm vi và nguồn ghi nhận; "
                "phân biệt kết quả và kế hoạch."
            ),
            (
                "Ví dụ: dự án hoàn thành, kết quả áp dụng hoặc ghi nhận của "
                "đơn vị có tên cụ thể."
            ),
        ),
        (
            "contribution",
            "Đóng góp và trách nhiệm với cộng đồng",
            (
                "Nêu hoạt động, đối tác và người thụ hưởng, cùng căn cứ cho "
                "kết quả được khai báo."
            ),
            (
                "Ví dụ: chương trình cộng đồng, cách triển khai và kết quả "
                "trong từng giai đoạn."
            ),
        ),
    ),
    "PRODUCT": (
        (
            "development",
            "Quá trình phát triển và hoàn thiện",
            "Nêu nhu cầu xuất phát, giai đoạn phát triển và đơn vị hoặc nhóm tham gia.",
            "Ví dụ: từ bản thử nghiệm đến phiên bản được đề cử, kèm mốc hoàn thiện.",
        ),
        (
            "difference",
            "Chức năng và điểm khác biệt",
            (
                "Giải thích chức năng, khác biệt có thể đối chiếu và giới "
                "hạn của việc so sánh."
            ),
            "Ví dụ: vấn đề được giải quyết và điểm khác biệt so với cách làm hiện có.",
        ),
        (
            "application",
            "Thử nghiệm và phạm vi áp dụng",
            (
                "Nêu nơi, thời gian và điều kiện áp dụng; ghi rõ thử nghiệm "
                "hay sử dụng thực tế."
            ),
            "Ví dụ: địa điểm thử nghiệm, nhóm người dùng và điều kiện cần để vận hành.",
        ),
        (
            "results",
            "Kết quả và giá trị thực tế",
            (
                "Nêu kết quả đo hoặc quan sát, nguồn số liệu và đối tượng "
                "hưởng lợi; tránh số liệu ước đoán không ghi chú."
            ),
            "Ví dụ: chỉ tiêu trước và sau áp dụng, thời gian đo và tài liệu kết quả.",
        ),
    ),
    "CULTURAL_HERITAGE": (
        (
            "origin",
            "Nguồn gốc và lịch sử di sản",
            (
                "Trình bày tên gọi, truyền tích hoặc tư liệu lịch sử; phân "
                "biệt truyền khẩu và nguồn thành văn."
            ),
            (
                "Ví dụ: các tên gọi, mốc lịch sử và nguồn tư liệu hoặc người "
                "cung cấp thông tin."
            ),
        ),
        (
            "conservation",
            "Tình trạng bảo tồn và yếu tố tác động",
            (
                "Nêu tình trạng hiện tại, hoạt động bảo tồn đã thực hiện và "
                "các yếu tố có thể ảnh hưởng."
            ),
            (
                "Ví dụ: tình trạng không gian, hiện vật hoặc thực hành; khó "
                "khăn đang được ghi nhận."
            ),
        ),
        (
            "transmission",
            "Hoạt động thực hành và truyền dạy",
            (
                "Mô tả chủ thể thực hành, hình thức truyền dạy và sự tham "
                "gia của các thế hệ."
            ),
            (
                "Ví dụ: nhóm thực hành, lớp truyền dạy hoặc dịp sinh hoạt có "
                "thời gian cụ thể."
            ),
        ),
        (
            "community_value",
            "Giá trị và vai trò với cộng đồng",
            (
                "Giải thích vai trò của di sản đối với cộng đồng gắn bó; nêu "
                "tiếng nói và nguồn cộng đồng nếu có."
            ),
            (
                "Ví dụ: ý nghĩa trong sinh hoạt, tri thức được gìn giữ và "
                "người đang tham gia."
            ),
        ),
    ),
    "INITIATIVE": (
        (
            "problem",
            "Vấn đề và nhu cầu cần giải quyết",
            (
                "Mô tả vấn đề trước khi có sáng kiến, đối tượng bị ảnh hưởng "
                "và căn cứ xác định nhu cầu."
            ),
            "Ví dụ: khó khăn trong quy trình hiện có và nguồn ghi nhận khó khăn đó.",
        ),
        (
            "novelty",
            "Giải pháp và phần cải tiến",
            (
                "Giải thích cách giải quyết, phần cải tiến do nhóm phát "
                "triển và giới hạn của nhận định tính mới."
            ),
            "Ví dụ: bước xử lý được thay đổi và khác biệt so với phương án đã sử dụng.",
        ),
        (
            "implementation",
            "Quá trình triển khai và áp dụng",
            (
                "Nêu giai đoạn thực hiện, nơi áp dụng, người tham gia và "
                "điều kiện triển khai."
            ),
            "Ví dụ: thời điểm thử nghiệm, đơn vị áp dụng và điều chỉnh sau phản hồi.",
        ),
        (
            "impact",
            "Kết quả và khả năng nhân rộng",
            (
                "Nêu kết quả đã có, nguồn đối chiếu và điều kiện cần khi áp "
                "dụng ở nơi khác."
            ),
            "Ví dụ: thay đổi quan sát được, chi phí triển khai và giới hạn nhân rộng.",
        ),
    ),
    "INTELLECTUAL_ASSET": (
        (
            "development",
            "Quá trình hình thành tài sản số",
            (
                "Mô tả mục đích, người tham gia và các giai đoạn tạo lập tài "
                "sản được đề cử."
            ),
            (
                "Ví dụ: từ dữ liệu hoặc thiết kế ban đầu đến sản phẩm số "
                "đang được lưu giữ."
            ),
        ),
        (
            "versions",
            "Lịch sử phiên bản và thay đổi",
            (
                "Nêu các phiên bản đáng chú ý, thời điểm và nội dung thay "
                "đổi có thể đối chiếu."
            ),
            "Ví dụ: phiên bản phát hành, nhật ký thay đổi hoặc mốc lưu trữ nguồn.",
        ),
        (
            "original_contribution",
            "Phần đóng góp và nguồn sử dụng",
            (
                "Phân biệt phần tự phát triển, phần kế thừa và nguồn thành "
                "phần bên ngoài nếu có."
            ),
            "Ví dụ: mã nguồn, dữ liệu hoặc nội dung tham khảo và vai trò của từng bên.",
        ),
        (
            "applications",
            "Ứng dụng và giá trị sử dụng",
            "Mô tả nơi áp dụng, người sử dụng, kết quả và giới hạn của tài sản số.",
            "Ví dụ: mục đích sử dụng, nhóm người dùng và kết quả có nguồn ghi nhận.",
        ),
    ),
    "OTHER": (
        (
            "context",
            "Bối cảnh và đối tượng đề cử",
            "Giải thích đối tượng là gì và vì sao chưa phù hợp các nhóm hồ sơ hiện có.",
            "Ví dụ: bản chất đối tượng, chủ thể liên quan và phạm vi đề nghị xem xét.",
        ),
        (
            "value",
            "Giá trị và điểm nổi bật",
            (
                "Mô tả giá trị cụ thể mà người nộp đề nghị xem xét; phân "
                "biệt tự nhận định và ghi nhận có nguồn."
            ),
            "Ví dụ: điểm nổi bật, nhóm người hưởng lợi và căn cứ cho nhận định đó.",
        ),
        (
            "development",
            "Quá trình hình thành và phát triển",
            "Nêu các mốc hình thành, thay đổi và người hoặc đơn vị tham gia.",
            "Ví dụ: khi nào bắt đầu, các giai đoạn phát triển và tình trạng hiện tại.",
        ),
        (
            "recognition",
            "Thành tựu và nguồn đối chiếu",
            (
                "Nêu thành tựu hoặc ghi nhận nếu có; ghi rõ nội dung còn "
                "thiếu nguồn hoặc cần làm rõ."
            ),
            (
                "Ví dụ: tên hoạt động, thời gian, đơn vị ghi nhận và tài "
                "liệu có thể cung cấp."
            ),
        ),
    ),
}


def _tables() -> tuple[sa.TableClause, sa.TableClause]:
    types = sa.table(
        "dossier_types", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("dossier_type_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("schema_json", sa.JSON()),
    )
    return types, versions


def upgrade() -> None:
    types, versions = _tables()
    bind = op.get_bind()
    for type_id, code in bind.execute(
        sa.select(types.c.id, types.c.code).where(types.c.code.in_(tuple(NARRATIVES)))
    ):
        latest = bind.execute(
            sa.select(versions.c.version_no, versions.c.schema_json)
            .where(versions.c.dossier_type_id == type_id)
            .order_by(versions.c.version_no.desc())
            .limit(1)
        ).first()
        if latest is None:
            continue
        schema = deepcopy(latest.schema_json)
        if not isinstance(schema, dict) or not isinstance(
            schema.get("fields", []), list
        ):
            raise RuntimeError(
                "A built-in narrative template has an invalid field list."
            )
        fields = schema.setdefault("fields", [])
        existing_keys = {field["key"] for field in fields}
        for suffix, label, guidance, example in NARRATIVES[code]:
            key = f"narrative_{code.lower()}_{suffix}"
            if key not in existing_keys:
                fields.append(
                    {
                        "key": key,
                        "type": "textarea",
                        "label": label,
                        "required": False,
                        "maxLength": 5000,
                        "helpText": guidance,
                        "placeholder": example,
                    }
                )
        bind.execute(
            versions.insert().values(
                id=uuid5(NAMESPACE, str(type_id)),
                dossier_type_id=type_id,
                version_no=latest.version_no + 1,
                schema_json=schema,
            )
        )


def downgrade() -> None:
    types, versions = _tables()
    bind = op.get_bind()
    ids = {
        uuid5(NAMESPACE, str(value)) for value in bind.scalars(sa.select(types.c.id))
    }
    dossiers = sa.table("dossiers", sa.column("dossier_type_version_id", sa.Uuid()))
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(dossiers)
        .where(dossiers.c.dossier_type_version_id.in_(ids))
    ):
        raise RuntimeError("Narrative templates are in use by dossiers; roll forward.")
    preparations = sa.table(
        "dossier_preparations", sa.column("payload_json", sa.JSON())
    )
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(preparations)
        .where(
            sa.func.lower(
                sa.func.replace(
                    preparations.c.payload_json["dossierTypeVersionId"].as_string(),
                    "-",
                    "",
                )
            ).in_({identifier.hex for identifier in ids})
        )
    ):
        raise RuntimeError(
            "Narrative templates are in use by saved preparations; roll forward."
        )
    bind.execute(versions.delete().where(versions.c.id.in_(ids)))
