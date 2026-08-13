from typing import Annotated

from fastapi import Depends

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency


def get_audit_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AuditService:
    return AuditService(session, settings=settings)


AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
