from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.council.service import CouncilService


async def get_council_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[CouncilService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    service = CouncilService(session=session, payload_cipher=cipher)
    try:
        yield service
    finally:
        await service.close()


CouncilServiceDependency = Annotated[
    CouncilService,
    Depends(get_council_service),
]
