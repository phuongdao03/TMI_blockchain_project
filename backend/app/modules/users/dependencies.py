from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.users.security import SensitiveFieldCipher
from app.modules.users.service import UserProfileService


async def get_user_profile_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[UserProfileService]:
    secret = settings.pii_encryption_key
    service = UserProfileService(
        session=session,
        cipher=SensitiveFieldCipher.from_base64(
            secret.get_secret_value() if secret is not None else ""
        ),
    )
    yield service


UserProfileServiceDependency = Annotated[
    UserProfileService,
    Depends(get_user_profile_service),
]
