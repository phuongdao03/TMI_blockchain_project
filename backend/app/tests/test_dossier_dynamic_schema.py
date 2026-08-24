from typing import Any

import pytest

from app.modules.dossiers.dynamic_schema import (
    DynamicSchemaError,
    public_fields_from_schema,
    validate_form_data,
    validate_schema_definition,
)


def test_schema_definition_accepts_supported_fields_and_checklists() -> None:
    schema = {
        "fields": [
            {
                "key": "artist_name",
                "label": "Tên tác giả",
                "type": "text",
                "required": True,
            },
            {
                "key": "category",
                "label": "Lĩnh vực",
                "type": "select",
                "required": True,
                "options": ["heritage", "innovation"],
            },
            {"key": "published_at", "label": "Ngày công bố", "type": "date"},
        ],
        "requirements": [
            {
                "key": "identity",
                "label": "Tài liệu xác minh chủ thể",
                "required": True,
                "fileRoles": ["IDENTITY", "EVIDENCE"],
            }
        ],
        "reviewChecklist": [
            {
                "key": "identity_match",
                "label": "Thông tin chủ thể nhất quán",
                "required": True,
            }
        ],
    }

    assert validate_schema_definition(schema) == schema


@pytest.mark.parametrize(
    ("schema", "error_path"),
    [
        (
            {"fields": [{"key": "title", "label": "A", "type": "unsupported"}]},
            "fields.0.type",
        ),
        (
            {
                "fields": [
                    {"key": "title", "label": "A", "type": "text"},
                    {"key": "title", "label": "B", "type": "text"},
                ]
            },
            "fields.1.key",
        ),
        (
            {"fields": [{"key": "kind", "label": "Loại", "type": "select"}]},
            "fields.0.options",
        ),
    ],
)
def test_schema_definition_returns_precise_errors(
    schema: dict[str, Any], error_path: str
) -> None:
    with pytest.raises(DynamicSchemaError) as exc_info:
        validate_schema_definition(schema)

    assert any(item["path"] == error_path for item in exc_info.value.errors)


def test_form_data_validation_normalizes_values() -> None:
    schema = {
        "fields": [
            {
                "key": "title",
                "label": "Tên nội dung",
                "type": "text",
                "required": True,
                "minLength": 3,
            },
            {"key": "budget", "label": "Ngân sách", "type": "currency", "min": 0},
            {
                "key": "themes",
                "label": "Chủ đề",
                "type": "multiselect",
                "options": ["culture", "technology", "community"],
            },
            {"key": "contact_email", "label": "Email", "type": "email"},
            {"key": "consent", "label": "Đồng ý", "type": "checkbox", "required": True},
        ]
    }

    result = validate_form_data(
        schema,
        {
            "title": "  Giá trị Việt  ",
            "budget": 2500000,
            "themes": ["culture", "community"],
            "contact_email": "hello@example.org",
            "consent": True,
        },
    )

    assert result["title"] == "Giá trị Việt"
    assert result["budget"] == 2500000


def test_form_data_validation_rejects_unknown_and_invalid_values() -> None:
    schema = {
        "fields": [
            {"key": "name", "label": "Tên", "type": "text", "required": True},
            {"key": "email", "label": "Email", "type": "email"},
            {"key": "published_at", "label": "Ngày công bố", "type": "date"},
        ]
    }

    with pytest.raises(DynamicSchemaError) as exc_info:
        validate_form_data(
            schema,
            {
                "name": "",
                "email": "not-an-email",
                "published_at": "31/12/2026",
                "internal": True,
            },
        )

    paths = {item["path"] for item in exc_info.value.errors}
    assert paths == {"name", "email", "published_at", "internal"}


def test_public_fields_require_an_explicit_safe_schema_flag() -> None:
    schema = {
        "fields": [
            {
                "key": "story",
                "label": "Câu chuyện tác phẩm",
                "type": "textarea",
                "maxLength": 2_000,
                "publicVisibility": True,
            },
            {
                "key": "genre",
                "label": "Thể loại",
                "type": "select",
                "options": ["heritage", "innovation"],
                "publicVisibility": True,
            },
            {
                "key": "owner_email",
                "label": "Email chủ sở hữu",
                "type": "email",
            },
        ]
    }

    assert validate_schema_definition(schema) == schema
    assert public_fields_from_schema(
        schema,
        {
            "story": "  Dấu ấn Việt được chuẩn bị để công bố.  ",
            "genre": "heritage",
            "owner_email": "private@example.test",
        },
    ) == [
        {
            "key": "story",
            "label": "Câu chuyện tác phẩm",
            "value": "Dấu ấn Việt được chuẩn bị để công bố.",
        },
        {
            "key": "genre",
            "label": "Thể loại",
            "value": "heritage",
        },
    ]


@pytest.mark.parametrize(
    ("field", "error_path"),
    [
        (
            {
                "key": "email",
                "label": "Email",
                "type": "email",
                "publicVisibility": True,
            },
            "fields.0.publicVisibility",
        ),
        (
            {
                "key": "story",
                "label": "Câu chuyện",
                "type": "textarea",
                "publicVisibility": True,
            },
            "fields.0.maxLength",
        ),
        (
            {
                "key": "story",
                "label": "Câu chuyện",
                "type": "textarea",
                "maxLength": 5_001,
                "publicVisibility": True,
            },
            "fields.0.maxLength",
        ),
    ],
)
def test_public_fields_reject_sensitive_or_unbounded_definitions(
    field: dict[str, object],
    error_path: str,
) -> None:
    with pytest.raises(DynamicSchemaError) as exc_info:
        validate_schema_definition({"fields": [field]})

    assert any(item["path"] == error_path for item in exc_info.value.errors)
