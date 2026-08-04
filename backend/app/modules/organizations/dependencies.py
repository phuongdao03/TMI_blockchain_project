from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.organizations.service import OrganizationService
from app.modules.users.security import SensitiveFieldCipher


async def get_organization_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[OrganizationService]:
    secret = settings.pii_encryption_key
    yield OrganizationService(
        session=session,
        cipher=SensitiveFieldCipher.from_base64(
            secret.get_secret_value() if secret is not None else ""
        ),
    )


OrganizationServiceDependency = Annotated[
    OrganizationService,
    Depends(get_organization_service),
]
