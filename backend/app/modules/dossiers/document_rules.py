"""Server-owned document requirements for dynamic dossier types.

The dynamic dossier schema describes which evidence is accepted for a type of
dossier.  This module deliberately contains no database or HTTP concerns so
the same constraints are applied when a document is attached and again before
the dossier is submitted.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeGuard

DOCUMENT_VISIBILITIES = frozenset(
    {
        "PRIVATE",
        "INTERNAL",
        "PUBLIC_PREVIEW",
        "PUBLIC",
    }
)
_MIME_TYPE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$"
)
_MAX_DOCUMENT_BYTES = 300 * 1024 * 1024
_MAX_DOCUMENT_COUNT = 100


class DocumentRuleError(ValueError):
    """Raised when a dynamic document rule or attachment is invalid."""


@dataclass(frozen=True, slots=True)
class DocumentRule:
    key: str
    label: str
    document_type: str
    required: bool
    allowed_mime_types: frozenset[str]
    max_bytes: int
    max_count: int
    default_visibility: str


def _is_sequence(value: object) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _normalise_code(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentRuleError(f"{field} is required.")
    return value.strip().upper()


def _normalise_mime_types(value: object, *, path: str) -> frozenset[str]:
    if not _is_sequence(value) or not value:
        raise DocumentRuleError(f"{path} must contain at least one MIME type.")

    normalized: set[str] = set()
    for index, raw_mime_type in enumerate(value):
        if not isinstance(raw_mime_type, str):
            raise DocumentRuleError(f"{path}.{index} must be a MIME type.")
        mime_type = raw_mime_type.strip().lower()
        if not _MIME_TYPE_PATTERN.fullmatch(mime_type):
            raise DocumentRuleError(f"{path}.{index} must be a valid MIME type.")
        normalized.add(mime_type)
    return frozenset(normalized)


def _positive_int(value: object, *, path: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DocumentRuleError(f"{path} must be a positive integer.")
    if value > maximum:
        raise DocumentRuleError(f"{path} exceeds the supported maximum.")
    return value


def document_rules_from_schema(schema: object) -> tuple[DocumentRule, ...]:
    """Parse the optional ``documentRules`` portion of a dossier schema.

    Missing rules preserve compatibility with older dossier types.  When rules
    exist, all authorization decisions are derived from them rather than from
    a visibility value supplied by the browser.
    """

    if not isinstance(schema, Mapping):
        raise DocumentRuleError("schema must be an object.")

    raw_rules = schema.get("documentRules")
    if raw_rules is None:
        return ()
    if not _is_sequence(raw_rules):
        raise DocumentRuleError("documentRules must be a list.")

    rules: list[DocumentRule] = []
    seen_keys: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        path = f"documentRules.{index}"
        if not isinstance(raw_rule, Mapping):
            raise DocumentRuleError(f"{path} must be an object.")

        key = _normalise_code(raw_rule.get("key"), field=f"{path}.key")
        if key in seen_keys:
            raise DocumentRuleError(f"{path}.key must be unique.")
        seen_keys.add(key)

        raw_label = raw_rule.get("label", key)
        if not isinstance(raw_label, str) or not raw_label.strip():
            raise DocumentRuleError(f"{path}.label is required.")

        raw_required = raw_rule.get("required", False)
        if not isinstance(raw_required, bool):
            raise DocumentRuleError(f"{path}.required must be a boolean.")

        visibility = raw_rule.get("defaultVisibility", "PRIVATE")
        if (
            not isinstance(visibility, str)
            or visibility.strip().upper() not in DOCUMENT_VISIBILITIES
        ):
            raise DocumentRuleError(
                f"{path}.defaultVisibility is an unsupported visibility."
            )

        rules.append(
            DocumentRule(
                key=key,
                label=raw_label.strip(),
                document_type=_normalise_code(
                    raw_rule.get("documentType", key),
                    field=f"{path}.documentType",
                ),
                required=raw_required,
                allowed_mime_types=_normalise_mime_types(
                    raw_rule.get("allowedMimeTypes"),
                    path=f"{path}.allowedMimeTypes",
                ),
                max_bytes=_positive_int(
                    raw_rule.get("maxBytes"),
                    path=f"{path}.maxBytes",
                    maximum=_MAX_DOCUMENT_BYTES,
                ),
                max_count=_positive_int(
                    raw_rule.get("maxCount", 1),
                    path=f"{path}.maxCount",
                    maximum=_MAX_DOCUMENT_COUNT,
                ),
                default_visibility=visibility.strip().upper(),
            )
        )
    return tuple(rules)


def _existing_codes(entry: object) -> tuple[str | None, str | None]:
    if isinstance(entry, Mapping):
        role = entry.get("evidence_role", entry.get("evidenceRole"))
        document_type = entry.get("evidence_type", entry.get("evidenceType"))
    elif isinstance(entry, tuple) and len(entry) >= 2:
        role, document_type = entry[0], entry[1]
    else:
        role = getattr(entry, "evidence_role", None)
        document_type = getattr(entry, "evidence_type", None)

    normalized_role = (
        role.strip().upper() if isinstance(role, str) and role.strip() else None
    )
    normalized_type = (
        document_type.strip().upper()
        if isinstance(document_type, str) and document_type.strip()
        else None
    )
    return normalized_role, normalized_type


def _matches_rule(rule: DocumentRule, entry: object) -> bool:
    role, document_type = _existing_codes(entry)
    return role == rule.key or (role is None and document_type == rule.document_type)


def _select_rule(
    rules: Sequence[DocumentRule],
    *,
    evidence_type: str,
    evidence_role: str | None,
) -> DocumentRule:
    normalized_type = _normalise_code(evidence_type, field="evidence_type")
    normalized_role = (
        _normalise_code(evidence_role, field="evidence_role")
        if evidence_role is not None and evidence_role.strip()
        else None
    )

    if normalized_role is not None:
        matched = next((rule for rule in rules if rule.key == normalized_role), None)
        if matched is None:
            raise DocumentRuleError(
                "The selected evidence role is not allowed for this dossier."
            )
        if matched.document_type != normalized_type:
            raise DocumentRuleError(
                "The selected evidence role does not match its document type."
            )
        return matched

    candidates = [rule for rule in rules if rule.document_type == normalized_type]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise DocumentRuleError(
            "The selected document type is not allowed for this dossier."
        )
    raise DocumentRuleError("An evidence role is required for this document type.")


def validate_attachment_against_rules(
    rules: Sequence[DocumentRule],
    *,
    evidence_type: str,
    evidence_role: str | None,
    mime_type: str,
    byte_size: int,
    existing: Sequence[object],
) -> DocumentRule | None:
    """Validate one attachment and return its server-owned document rule."""

    if not rules:
        return None

    rule = _select_rule(
        rules,
        evidence_type=evidence_type,
        evidence_role=evidence_role,
    )
    normalized_mime_type = (
        mime_type.strip().lower() if isinstance(mime_type, str) else ""
    )
    if normalized_mime_type not in rule.allowed_mime_types:
        raise DocumentRuleError(
            f"{normalized_mime_type or 'This file type'} is not allowed for "
            f"{rule.label}."
        )
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 1:
        raise DocumentRuleError("The document size is invalid.")
    if byte_size > rule.max_bytes:
        raise DocumentRuleError(
            f"The document exceeds the maximum size for {rule.label}."
        )

    current_count = sum(1 for entry in existing if _matches_rule(rule, entry))
    if current_count >= rule.max_count:
        raise DocumentRuleError(
            f"The maximum number of files for {rule.label} has been reached."
        )
    return rule


def validate_required_document_rules(
    rules: Sequence[DocumentRule],
    *,
    evidences: Sequence[object],
) -> None:
    """Ensure all required rules are present before a dossier is submitted."""

    for rule in rules:
        count = sum(1 for evidence in evidences if _matches_rule(rule, evidence))
        if rule.required and count == 0:
            raise DocumentRuleError(f"{rule.label} is required before submission.")
        if count > rule.max_count:
            raise DocumentRuleError(
                f"The maximum number of files for {rule.label} was exceeded."
            )
