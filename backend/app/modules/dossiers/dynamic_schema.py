from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, datetime
from typing import Any, TypeGuard

from app.modules.dossiers.document_rules import (
    DOCUMENT_VISIBILITIES,
    DocumentRuleError,
    document_rules_from_schema,
)

SUPPORTED_FIELD_TYPES = {
    "text",
    "textarea",
    "number",
    "date",
    "datetime",
    "select",
    "multiselect",
    "radio",
    "checkbox",
    "currency",
    "email",
    "phone",
    "address",
    "person",
    "organization",
    "file",
}
CHOICE_FIELD_TYPES = {"select", "multiselect", "radio"}
EVIDENCE_VISIBILITIES = set(DOCUMENT_VISIBILITIES)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PUBLIC_FIELD_TYPES = {
    "text",
    "textarea",
    "number",
    "date",
    "datetime",
    "select",
    "multiselect",
    "radio",
    "checkbox",
    "currency",
}
PUBLIC_TEXT_MAX_LENGTH = 5_000
RUBRIC_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class DynamicSchemaError(ValueError):
    def __init__(
        self,
        path: str | None = None,
        message: str | None = None,
        *,
        errors: Sequence[Mapping[str, str]] | None = None,
    ) -> None:
        resolved = [dict(error) for error in errors or []]
        if not resolved:
            resolved = [
                {
                    "path": path or "schema",
                    "message": message or "Invalid dynamic schema.",
                }
            ]
        self.errors = resolved
        self.path = resolved[0]["path"]
        self.message = resolved[0]["message"]
        super().__init__(
            "; ".join(f"{error['path']}: {error['message']}" for error in self.errors)
        )


def _is_sequence(value: object) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _append_error(errors: list[dict[str, str]], path: str, message: str) -> None:
    errors.append({"path": path, "message": message})


def _validate_options(options: object, path: str, errors: list[dict[str, str]]) -> None:
    if not _is_sequence(options) or not options:
        _append_error(errors, path, "At least one option is required.")
        return

    values: set[str] = set()
    for index, option in enumerate(options):
        option_path = f"{path}.{index}"
        if isinstance(option, str):
            value = option.strip()
        elif isinstance(option, Mapping):
            raw_value = option.get("value")
            raw_label = option.get("label")
            value = raw_value.strip() if isinstance(raw_value, str) else ""
            if not isinstance(raw_label, str) or not raw_label.strip():
                _append_error(errors, f"{option_path}.label", "Label is required.")
        else:
            value = ""

        if not value:
            _append_error(errors, f"{option_path}.value", "Value is required.")
        elif value in values:
            _append_error(errors, f"{option_path}.value", "Value must be unique.")
        else:
            values.add(value)


def _validate_keyed_items(
    items: object,
    path: str,
    errors: list[dict[str, str]],
    *,
    visibility: bool = False,
) -> None:
    if items is None:
        return
    if not _is_sequence(items):
        _append_error(errors, path, "Must be a list.")
        return

    keys: set[str] = set()
    for index, item in enumerate(items):
        item_path = f"{path}.{index}"
        if not isinstance(item, Mapping):
            _append_error(errors, item_path, "Must be an object.")
            continue
        raw_key = item.get("key")
        key = raw_key.strip() if isinstance(raw_key, str) else ""
        if not key:
            _append_error(errors, f"{item_path}.key", "Key is required.")
        elif key in keys:
            _append_error(errors, f"{item_path}.key", "Key must be unique.")
        else:
            keys.add(key)

        label = item.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            _append_error(errors, f"{item_path}.label", "Label cannot be empty.")

        required = item.get("required")
        if required is not None and not isinstance(required, bool):
            _append_error(errors, f"{item_path}.required", "Must be a boolean.")

        if visibility:
            value = item.get("visibility")
            if value is not None and value not in EVIDENCE_VISIBILITIES:
                _append_error(
                    errors,
                    f"{item_path}.visibility",
                    "Unsupported visibility.",
                )


def _validate_review_rubric(rubric: object, errors: list[dict[str, str]]) -> None:
    if rubric is None:
        return
    path = "reviewRubric"
    if not isinstance(rubric, Mapping):
        _append_error(errors, path, "Must be an object.")
        return

    for key in ("version", "title"):
        value = rubric.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
            _append_error(
                errors,
                f"{path}.{key}",
                "Must be non-empty text up to 120 characters.",
            )

    assessment_method = rubric.get("assessmentMethod", "SCORED")
    if assessment_method not in {"SCORED", "VERDICT"}:
        _append_error(
            errors,
            f"{path}.assessmentMethod",
            "Must be SCORED or VERDICT.",
        )
    is_verdict = assessment_method == "VERDICT"

    gates = rubric.get("gates", [])
    _validate_keyed_items(gates, f"{path}.gates", errors)
    if _is_sequence(gates) and len(gates) > 10:
        _append_error(errors, f"{path}.gates", "At most 10 gates are allowed.")

    criteria = rubric.get("criteria")
    if not _is_sequence(criteria) or not 1 <= len(criteria) <= 10:
        _append_error(
            errors, f"{path}.criteria", "Between 1 and 10 criteria are required."
        )
    else:
        keys: set[str] = set()
        weight_total = 0
        for index, criterion in enumerate(criteria):
            item_path = f"{path}.criteria.{index}"
            if not isinstance(criterion, Mapping):
                _append_error(errors, item_path, "Must be an object.")
                continue
            raw_key = criterion.get("key")
            key = raw_key.strip() if isinstance(raw_key, str) else ""
            if not RUBRIC_KEY_PATTERN.fullmatch(key):
                _append_error(
                    errors, f"{item_path}.key", "Must be a lowercase stable key."
                )
            elif key in keys:
                _append_error(errors, f"{item_path}.key", "Key must be unique.")
            keys.add(key)
            for text_key in ("label", "description"):
                value = criterion.get(text_key)
                if not isinstance(value, str) or not value.strip():
                    _append_error(errors, f"{item_path}.{text_key}", "Is required.")
            if not is_verdict:
                weight = criterion.get("weight")
                if (
                    not isinstance(weight, int)
                    or isinstance(weight, bool)
                    or not 1 <= weight <= 100
                ):
                    _append_error(
                        errors,
                        f"{item_path}.weight",
                        "Must be an integer from 1 to 100.",
                    )
                else:
                    weight_total += weight
        if not is_verdict and weight_total != 100:
            _append_error(
                errors, f"{path}.criteria", "Criterion weights must total 100."
            )

    if is_verdict:
        if "thresholds" in rubric:
            _append_error(
                errors,
                f"{path}.thresholds",
                "Verdict rubrics must not define score thresholds.",
            )
        return

    thresholds = rubric.get("thresholds")
    if not isinstance(thresholds, Mapping):
        _append_error(errors, f"{path}.thresholds", "Must be an object.")
        return
    approve = thresholds.get("approveMin")
    reject = thresholds.get("rejectBelow")
    if not (
        isinstance(approve, int)
        and not isinstance(approve, bool)
        and isinstance(reject, int)
        and not isinstance(reject, bool)
        and 0 <= approve <= 100
        and 0 <= reject <= 100
        and reject < approve
    ):
        _append_error(
            errors,
            f"{path}.thresholds",
            "rejectBelow must be lower than approveMin and both must be 0–100.",
        )


def validate_dynamic_schema(schema: object) -> dict[str, Any]:
    if not isinstance(schema, Mapping):
        raise DynamicSchemaError("schema", "Must be an object.")

    errors: list[dict[str, str]] = []
    fields = schema.get("fields", [])
    if not _is_sequence(fields):
        _append_error(errors, "fields", "Must be a list.")
        fields = []

    keys: set[str] = set()
    for index, field in enumerate(fields):
        path = f"fields.{index}"
        if not isinstance(field, Mapping):
            _append_error(errors, path, "Must be an object.")
            continue

        raw_key = field.get("key")
        key = raw_key.strip() if isinstance(raw_key, str) else ""
        if not key:
            _append_error(errors, f"{path}.key", "Key is required.")
        elif key in keys:
            _append_error(errors, f"{path}.key", "Key must be unique.")
        else:
            keys.add(key)

        field_type = field.get("type")
        if field_type not in SUPPORTED_FIELD_TYPES:
            _append_error(errors, f"{path}.type", "Unsupported field type.")

        label = field.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            _append_error(errors, f"{path}.label", "Label cannot be empty.")

        required = field.get("required")
        if required is not None and not isinstance(required, bool):
            _append_error(errors, f"{path}.required", "Must be a boolean.")

        public_visibility = field.get("publicVisibility")
        if public_visibility is not None and not isinstance(public_visibility, bool):
            _append_error(errors, f"{path}.publicVisibility", "Must be a boolean.")
        elif public_visibility is True:
            if field_type not in PUBLIC_FIELD_TYPES:
                _append_error(
                    errors,
                    f"{path}.publicVisibility",
                    "This field type cannot be made public.",
                )
            if not isinstance(label, str) or not label.strip():
                _append_error(
                    errors,
                    f"{path}.label",
                    "A public field needs a label.",
                )
            if field_type in {"text", "textarea"}:
                maximum = field.get("maxLength")
                if (
                    not isinstance(maximum, int)
                    or isinstance(maximum, bool)
                    or not 1 <= maximum <= PUBLIC_TEXT_MAX_LENGTH
                ):
                    _append_error(
                        errors,
                        f"{path}.maxLength",
                        "A public text field needs a maxLength between 1 and "
                        f"{PUBLIC_TEXT_MAX_LENGTH}.",
                    )

        if field_type in CHOICE_FIELD_TYPES:
            _validate_options(field.get("options"), f"{path}.options", errors)

    requirements = schema.get("requirements")
    _validate_keyed_items(requirements, "requirements", errors)
    if _is_sequence(requirements):
        for index, requirement in enumerate(requirements):
            if not isinstance(requirement, Mapping):
                continue
            file_roles = requirement.get("fileRoles")
            path = f"requirements.{index}.fileRoles"
            if not _is_sequence(file_roles) or not file_roles:
                _append_error(errors, path, "At least one file role is required.")
                continue
            seen_roles: set[str] = set()
            for role_index, role in enumerate(file_roles):
                role_path = f"{path}.{role_index}"
                if not isinstance(role, str) or not role.strip():
                    _append_error(errors, role_path, "Must be a non-empty string.")
                    continue
                normalized_role = role.strip()
                if normalized_role in seen_roles:
                    _append_error(errors, role_path, "Duplicate file role.")
                seen_roles.add(normalized_role)

    _validate_keyed_items(schema.get("reviewChecklist"), "reviewChecklist", errors)
    _validate_review_rubric(schema.get("reviewRubric"), errors)

    try:
        document_rules_from_schema(schema)
    except DocumentRuleError as exc:
        _append_error(errors, "documentRules", str(exc))

    if errors:
        raise DynamicSchemaError(errors=errors)
    return deepcopy(dict(schema))


def _is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _option_values(field: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for option in field.get("options", []):
        if isinstance(option, str):
            values.add(option.strip())
        elif isinstance(option, Mapping) and isinstance(option.get("value"), str):
            values.add(option["value"].strip())
    return values


def _normalize_value(field: Mapping[str, Any], value: Any, path: str) -> Any:
    field_type = field["type"]
    normalized: Any
    if field_type in {"text", "textarea", "phone"}:
        if not isinstance(value, str):
            raise DynamicSchemaError(path, "Must be text.")
        normalized = value.strip()
    elif field_type == "email":
        if not isinstance(value, str) or not EMAIL_PATTERN.fullmatch(value.strip()):
            raise DynamicSchemaError(path, "Must be a valid email address.")
        normalized = value.strip().lower()
    elif field_type in {"number", "currency"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DynamicSchemaError(path, "Must be a number.")
        normalized = value
    elif field_type == "date":
        if not isinstance(value, str):
            raise DynamicSchemaError(path, "Must be a valid ISO date.")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise DynamicSchemaError(path, "Must be a valid ISO date.") from exc
        normalized = value
    elif field_type == "datetime":
        if not isinstance(value, str):
            raise DynamicSchemaError(path, "Must be a valid ISO datetime.")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise DynamicSchemaError(path, "Must be a valid ISO datetime.") from exc
        normalized = value
    elif field_type in {"select", "radio"}:
        if not isinstance(value, str) or value not in _option_values(field):
            raise DynamicSchemaError(path, "Must be one of the allowed options.")
        normalized = value
    elif field_type == "multiselect":
        allowed = _option_values(field)
        if not _is_sequence(value) or any(
            not isinstance(item, str) or item not in allowed for item in value
        ):
            raise DynamicSchemaError(path, "Contains an unsupported option.")
        normalized = list(value)
    elif field_type == "checkbox":
        if not isinstance(value, bool):
            raise DynamicSchemaError(path, "Must be a boolean.")
        normalized = value
    elif field_type in {"address", "person", "organization", "file"}:
        if not isinstance(value, Mapping):
            raise DynamicSchemaError(path, "Must be an object.")
        normalized = deepcopy(dict(value))
    else:
        normalized = deepcopy(value)

    if isinstance(normalized, str):
        minimum = field.get("minLength")
        maximum = field.get("maxLength")
        if isinstance(minimum, int) and len(normalized) < minimum:
            raise DynamicSchemaError(
                path, f"Must contain at least {minimum} characters."
            )
        if isinstance(maximum, int) and len(normalized) > maximum:
            raise DynamicSchemaError(
                path, f"Must contain at most {maximum} characters."
            )
    return normalized


def validate_and_normalize_form_data(
    schema: object, form_data: object
) -> dict[str, Any]:
    validated_schema = validate_dynamic_schema(schema)
    if not isinstance(form_data, Mapping):
        raise DynamicSchemaError("formData", "Must be an object.")

    fields = {
        field["key"]: field
        for field in validated_schema.get("fields", [])
        if isinstance(field, Mapping) and isinstance(field.get("key"), str)
    }
    errors: list[dict[str, str]] = []
    normalized: dict[str, Any] = {}

    for key in form_data:
        if key not in fields:
            _append_error(
                errors, str(key), "Field is not defined by this dossier type."
            )

    for key, field in fields.items():
        value = form_data.get(key)
        if _is_empty(value):
            if field.get("required"):
                _append_error(errors, key, "This field is required.")
            continue
        try:
            normalized[key] = _normalize_value(field, value, key)
        except DynamicSchemaError as exc:
            errors.extend(exc.errors)

    if errors:
        raise DynamicSchemaError(errors=errors)
    return normalized


def public_fields_from_schema(
    schema: object,
    form_data: object,
) -> list[dict[str, object]]:
    """Return only explicitly allowlisted, non-sensitive public form fields.

    The caller persists this projection in the immutable dossier snapshot.  A
    public response must use that snapshot projection and never inspect the
    mutable live dossier form data again.
    """

    validated_schema = validate_dynamic_schema(schema)
    normalized_data = validate_and_normalize_form_data(validated_schema, form_data)
    public_fields: list[dict[str, object]] = []
    for field in validated_schema.get("fields", []):
        if not isinstance(field, Mapping) or field.get("publicVisibility") is not True:
            continue
        field_type = field.get("type")
        key = field.get("key")
        label = field.get("label")
        if (
            field_type not in PUBLIC_FIELD_TYPES
            or not isinstance(key, str)
            or not isinstance(label, str)
            or not key
            or not label.strip()
            or key not in normalized_data
        ):
            continue
        value = normalized_data[key]
        if _is_empty(value):
            continue
        # The public field schema has already excluded object/PII field types.
        # Keep this final guard so a malformed stored schema fails closed.
        if isinstance(value, (str, int, float, bool)):
            safe_value: object = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            safe_value = list(value)
        else:
            continue
        public_fields.append(
            {
                "key": key,
                "label": label.strip(),
                "value": safe_value,
            }
        )
    return public_fields


def validate_schema_definition(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Compatibility entry point used by dossier-type authoring services."""

    return validate_dynamic_schema(schema)


def validate_form_data(
    schema: Mapping[str, Any], data: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate applicant data and return its canonical representation."""

    return validate_and_normalize_form_data(schema, data)
