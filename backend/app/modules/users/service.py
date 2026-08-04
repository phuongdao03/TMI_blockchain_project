import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import UserProfile
from app.modules.users.repository import UserProfileRepository
from app.modules.users.security import SensitiveFieldCipher

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProfileChanges:
    full_name: str | None = None
    phone: str | None = None
    avatar_media_id: UUID | None = None
    locale: str | None = None
    timezone: str | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ProfileView:
    user_id: UUID
    email: str
    full_name: str | None
    phone: str | None
    avatar_media_id: UUID | None
    locale: str
    timezone: str


class UserProfileService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        cipher: SensitiveFieldCipher,
    ) -> None:
        self._session = session
        self._repository = UserProfileRepository(session)
        self._cipher = cipher

    async def get_profile(self, *, user_id: UUID, email: str) -> ProfileView:
        async with self._session.begin():
            profile = await self._repository.get_profile(user_id)
            return self._view(user_id=user_id, email=email, profile=profile)

    async def update_profile(
        self,
        *,
        user_id: UUID,
        email: str,
        changes: ProfileChanges,
    ) -> ProfileView:
        async with self._session.begin():
            profile = await self._repository.get_profile(user_id, for_update=True)
            if profile is None:
                profile = UserProfile(user_id=user_id)
                self._repository.add_profile(profile)

            if "full_name" in changes.provided_fields:
                profile.full_name = changes.full_name
            if "phone" in changes.provided_fields:
                profile.phone_encrypted = (
                    self._cipher.encrypt(changes.phone)
                    if changes.phone is not None
                    else None
                )
            if "avatar_media_id" in changes.provided_fields:
                profile.avatar_media_id = changes.avatar_media_id
            if "locale" in changes.provided_fields and changes.locale is not None:
                profile.locale = changes.locale
            if "timezone" in changes.provided_fields and changes.timezone is not None:
                profile.timezone = changes.timezone

            await self._session.flush()
            view = self._view(user_id=user_id, email=email, profile=profile)

        logger.info(
            "security_audit",
            extra={
                "action": "user.profile.updated",
                "user_id": str(user_id),
                "changed_fields": sorted(changes.provided_fields),
            },
        )
        return view

    def _view(
        self,
        *,
        user_id: UUID,
        email: str,
        profile: UserProfile | None,
    ) -> ProfileView:
        return ProfileView(
            user_id=user_id,
            email=email,
            full_name=profile.full_name if profile is not None else None,
            phone=(
                self._cipher.decrypt(profile.phone_encrypted)
                if profile is not None and profile.phone_encrypted is not None
                else None
            ),
            avatar_media_id=(profile.avatar_media_id if profile is not None else None),
            locale=profile.locale if profile is not None else "vi",
            timezone=(profile.timezone if profile is not None else "Asia/Ho_Chi_Minh"),
        )

    async def close(self) -> None:
        await self._session.close()
