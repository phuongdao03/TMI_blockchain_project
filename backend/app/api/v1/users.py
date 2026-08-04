from typing import Any

from fastapi import APIRouter, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.users.dependencies import UserProfileServiceDependency
from app.modules.users.schemas import PatchUserProfileRequest, UserProfileData
from app.modules.users.service import ProfileChanges, ProfileView

router = APIRouter(prefix="/api/v1/users", tags=["users"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    422: {"description": "Request validation failed.", "model": ErrorEnvelope},
}


def _profile_data(view: ProfileView) -> UserProfileData:
    return UserProfileData(
        user_id=view.user_id,
        email=view.email,
        full_name=view.full_name,
        phone=view.phone,
        avatar_media_id=view.avatar_media_id,
        locale=view.locale,
        timezone=view.timezone,
    )


@router.get(
    "/me",
    response_model=SuccessEnvelope[UserProfileData],
    responses={401: PRIVATE_RESPONSES[401]},
)
async def get_me(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: UserProfileServiceDependency,
) -> SuccessEnvelope[UserProfileData]:
    profile = await service.get_profile(
        user_id=principal.user_id,
        email=principal.email,
    )
    return SuccessEnvelope(
        data=_profile_data(profile),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/me",
    response_model=SuccessEnvelope[UserProfileData],
    responses={
        401: PRIVATE_RESPONSES[401],
        403: {
            "description": "CSRF validation failed.",
            "model": ErrorEnvelope,
        },
        422: PRIVATE_RESPONSES[422],
    },
)
async def patch_me(
    payload: PatchUserProfileRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: UserProfileServiceDependency,
) -> SuccessEnvelope[UserProfileData]:
    fields = payload.model_fields_set
    profile = await service.update_profile(
        user_id=principal.user_id,
        email=principal.email,
        changes=ProfileChanges(
            full_name=payload.full_name,
            phone=payload.phone,
            avatar_media_id=payload.avatar_media_id,
            locale=payload.locale,
            timezone=payload.timezone,
            provided_fields=frozenset(fields),
        ),
    )
    return SuccessEnvelope(
        data=_profile_data(profile),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
