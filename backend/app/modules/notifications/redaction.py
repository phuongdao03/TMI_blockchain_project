import re
from collections.abc import Mapping

_COMMUNITY_POST_PATH = re.compile(
    r"/community/posts/(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+"
)
_COMMUNITY_COMMENT_FRAGMENT = re.compile(
    r"comment-[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}"
)

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
            if not isinstance(value, str):
                continue
            path, separator, fragment = value.partition("#")
            is_comment_target = (
                _COMMUNITY_POST_PATH.fullmatch(path) is not None
                and _COMMUNITY_COMMENT_FRAGMENT.fullmatch(fragment) is not None
            )
            if (
                not value.startswith("/")
                or value.startswith("//")
                or "?" in value
                or (
                    separator
                    and fragment != "community-comments-title"
                    and not is_comment_target
                )
            ):
                continue
        elif not isinstance(value, (str, int, bool)):
            continue
        safe_data[key] = value
    return safe_data
