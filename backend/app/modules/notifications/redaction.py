from collections.abc import Mapping

SAFE_NOTIFICATION_DATA_KEYS = frozenset(
    {
        "actionPath",
        "assignmentId",
        "assignment_id",
        "attendanceId",
        "certificateId",
        "certificate_id",
        "decision",
        "dossierId",
        "dossier_id",
        "invitationId",
        "leaveRequestId",
        "overtimeRequestId",
        "status",
    }
)


def redact_notification_data(data: Mapping[str, object]) -> dict[str, object]:
    """Return only primitive routing metadata; never pass dossier or GPS payloads."""

    safe_data: dict[str, object] = {}
    for key, value in data.items():
        if key not in SAFE_NOTIFICATION_DATA_KEYS:
            continue
        if key == "actionPath":
            if not isinstance(value, str) or (
                not value.startswith("/")
                or value.startswith("//")
                or "?" in value
                or "#" in value
            ):
                continue
        elif not isinstance(value, (str, int, bool)):
            continue
        safe_data[key] = value
    return safe_data
