from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency
from app.modules.cms.service import CmsService


async def get_cms_service(session: SessionDependency) -> AsyncIterator[CmsService]:
    yield CmsService(session=session, audit=AuditService(session))


CmsServiceDependency = Annotated[CmsService, Depends(get_cms_service)]
