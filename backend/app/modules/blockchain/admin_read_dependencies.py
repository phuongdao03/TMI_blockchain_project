from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency
from app.modules.blockchain.admin_read_service import BlockchainAdminReadService


def get_blockchain_admin_read_service(
    session: SessionDependency,
) -> BlockchainAdminReadService:
    return BlockchainAdminReadService(session)


BlockchainAdminReadServiceDependency = Annotated[
    BlockchainAdminReadService,
    Depends(get_blockchain_admin_read_service),
]
