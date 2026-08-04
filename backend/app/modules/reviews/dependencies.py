from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.reviews.precheck_service import PrecheckService
from app.modules.reviews.service import ReviewService


async def get_precheck_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PrecheckService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    service = PrecheckService(session=session, payload_cipher=cipher)
    try:
        yield service
    finally:
        await service.close()


PrecheckServiceDependency = Annotated[
    PrecheckService,
    Depends(get_precheck_service),
]


async def get_review_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[ReviewService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    service = ReviewService(session=session, payload_cipher=cipher)
    try:
        yield service
    finally:
        await service.close()


ReviewServiceDependency = Annotated[
    ReviewService,
    Depends(get_review_service),
]
