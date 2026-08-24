import pytest

from app.modules.dossiers.document_rules import (
    DocumentRuleError,
    document_rules_from_schema,
    validate_attachment_against_rules,
    validate_required_document_rules,
)
from app.modules.dossiers.dynamic_schema import (
    DynamicSchemaError,
    validate_dynamic_schema,
)


def _schema() -> dict[str, object]:
    return {
        "fields": [],
        "documentRules": [
            {
                "key": "ARTWORK_IMAGE",
                "label": "Ảnh tác phẩm",
                "documentType": "ARTWORK_IMAGE",
                "required": True,
                "allowedMimeTypes": ["image/jpeg", "image/png", "image/webp"],
                "maxBytes": 20 * 1024 * 1024,
                "maxCount": 5,
                "defaultVisibility": "PUBLIC_PREVIEW",
            },
            {
                "key": "OWNERSHIP_PROOF",
                "label": "Chứng minh quyền sở hữu",
                "documentType": "OWNERSHIP_PROOF",
                "required": True,
                "allowedMimeTypes": ["application/pdf"],
                "maxBytes": 30 * 1024 * 1024,
                "maxCount": 2,
                "defaultVisibility": "INTERNAL",
            },
        ],
    }


def test_document_rules_parse_and_apply_server_owned_visibility() -> None:
    rules = document_rules_from_schema(_schema())

    selection = validate_attachment_against_rules(
        rules,
        evidence_type="ARTWORK_IMAGE",
        evidence_role="ARTWORK_IMAGE",
        mime_type="image/png",
        byte_size=1024,
        existing=(),
    )

    assert selection is not None
    assert selection.document_type == "ARTWORK_IMAGE"
    assert selection.default_visibility == "PUBLIC_PREVIEW"


def test_document_rules_reject_wrong_mime_and_count() -> None:
    rules = document_rules_from_schema(_schema())

    with pytest.raises(DocumentRuleError, match="not allowed"):
        validate_attachment_against_rules(
            rules,
            evidence_type="ARTWORK_IMAGE",
            evidence_role="ARTWORK_IMAGE",
            mime_type="application/pdf",
            byte_size=1024,
            existing=(),
        )

    with pytest.raises(DocumentRuleError, match="maximum"):
        validate_attachment_against_rules(
            rules,
            evidence_type="OWNERSHIP_PROOF",
            evidence_role="OWNERSHIP_PROOF",
            mime_type="application/pdf",
            byte_size=1024,
            existing=(("OWNERSHIP_PROOF", "OWNERSHIP_PROOF"),) * 2,
        )


def test_document_rules_require_all_mandatory_roles_at_submission() -> None:
    rules = document_rules_from_schema(_schema())

    with pytest.raises(DocumentRuleError, match="required"):
        validate_required_document_rules(
            rules,
            evidences=(("ARTWORK_IMAGE", "ARTWORK_IMAGE"),),
        )


@pytest.mark.parametrize(
    "visibility",
    ("EXPOSE_EVERYTHING", "REVIEWER_ONLY", "ADMIN_ONLY"),
)
def test_document_rules_reject_unknown_or_unsupported_visibility(
    visibility: str,
) -> None:
    invalid = _schema()
    invalid["documentRules"] = [
        {
            **_schema()["documentRules"][0],  # type: ignore[index]
            "defaultVisibility": visibility,
        }
    ]

    with pytest.raises(DocumentRuleError, match="visibility"):
        document_rules_from_schema(invalid)


def test_dynamic_schema_rejects_invalid_document_rules_before_publication() -> None:
    invalid = _schema()
    invalid["documentRules"] = [
        {
            **_schema()["documentRules"][0],  # type: ignore[index]
            "maxCount": 0,
        }
    ]

    with pytest.raises(DynamicSchemaError, match="maxCount"):
        validate_dynamic_schema(invalid)
