from typing import Annotated

from fastapi import Depends

from app.modules.affiliate.service import AffiliateService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency


def get_affiliate_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AffiliateService:
    return AffiliateService(
        session,
        affiliate_enabled=settings.affiliate_enabled,
        direct_commission_enabled=settings.affiliate_direct_commission_enabled,
    )


AffiliateServiceDependency = Annotated[
    AffiliateService,
    Depends(get_affiliate_service),
]
