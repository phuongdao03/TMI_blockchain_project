"""Deprecated CertificateRegistry signing dependency.

Kept temporarily as a rollback reference. Active API routes no longer import
this module and this provider always fails closed.
"""

from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.blockchain.errors import BlockchainLegacyFlowDeprecatedError
from app.modules.blockchain.human_signing_service import HumanSigningService


async def get_human_signing_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> HumanSigningService:
    del session, settings
    raise BlockchainLegacyFlowDeprecatedError()


HumanSigningServiceDependency = Annotated[
    HumanSigningService,
    Depends(get_human_signing_service),
]
