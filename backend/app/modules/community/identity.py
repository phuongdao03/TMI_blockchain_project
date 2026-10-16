from dataclasses import dataclass
from uuid import UUID

_MEMBER_DISPLAY_NAME = "Thành viên"
_ADMIN_DISPLAY_NAME = "Quản trị viên THV"


@dataclass(frozen=True, slots=True)
class PublicUserIdentity:
    display_name: str
    avatar_url: str | None
    role_label: str | None
    is_admin: bool


def public_user_identity(
    *,
    display_name: str | None,
    avatar_url: str | None,
    avatar_media_id: UUID | None,
    is_admin: bool,
    is_moderator: bool,
) -> PublicUserIdentity:
    if is_admin:
        return PublicUserIdentity(
            display_name=_ADMIN_DISPLAY_NAME,
            avatar_url=_avatar_url(avatar_media_id, avatar_url),
            role_label="Quản trị viên",
            is_admin=True,
        )
    return PublicUserIdentity(
        display_name=display_name or _MEMBER_DISPLAY_NAME,
        avatar_url=_avatar_url(avatar_media_id, avatar_url),
        role_label="Điều hành viên" if is_moderator else None,
        is_admin=False,
    )


def _avatar_url(media_id: UUID | None, fallback_url: str | None) -> str | None:
    if media_id is not None:
        return f"/api/v1/community/avatars/{media_id}"
    return fallback_url
