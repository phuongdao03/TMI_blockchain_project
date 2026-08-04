from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency
from app.modules.dossiers.service import DossierService


async def get_dossier_service(
    session: SessionDependency,
) -> AsyncIterator[DossierService]:
    yield DossierService(session=session)


DossierServiceDependency = Annotated[
    DossierService,
    Depends(get_dossier_service),
]
