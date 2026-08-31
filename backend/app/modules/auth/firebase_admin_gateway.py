import asyncio
import importlib
import re
from typing import Any, Protocol

from app.core.config import Settings


class FirebaseAdminError(RuntimeError):
    pass


class FirebaseAdminClient(Protocol):
    async def set_disabled(self, uid: str, *, disabled: bool) -> None: ...


class FirebaseEmailVerificationClient(Protocol):
    async def verify_email_for_identity(
        self, uid: str, *, expected_email: str
    ) -> bool: ...

    async def revoke_refresh_tokens(self, uid: str) -> None: ...


class FirebaseAdminGateway:
    """Administer Firebase Auth through Application Default Credentials."""

    def __init__(self, *, auth_module: Any, app: Any) -> None:
        self._auth = auth_module
        self._app = app

    @classmethod
    def create(cls, settings: Settings) -> "FirebaseAdminGateway":
        if not settings.firebase_project_id:
            raise FirebaseAdminError("Firebase project is not configured.")
        try:
            firebase_admin = importlib.import_module("firebase_admin")
            auth_module = importlib.import_module("firebase_admin.auth")
            app_name = "tmi-admin-" + re.sub(
                r"[^a-zA-Z0-9_-]", "-", settings.firebase_project_id
            )
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(
                    options={"projectId": settings.firebase_project_id},
                    name=app_name,
                )
        except Exception as exc:
            raise FirebaseAdminError("Firebase Admin SDK is unavailable.") from exc
        return cls(auth_module=auth_module, app=app)

    async def set_disabled(self, uid: str, *, disabled: bool) -> None:
        try:
            await asyncio.to_thread(
                self._auth.update_user,
                uid,
                disabled=disabled,
                app=self._app,
            )
        except Exception as exc:
            raise FirebaseAdminError("Firebase user update failed.") from exc

    async def verify_email_for_identity(self, uid: str, *, expected_email: str) -> bool:
        """Verify one enabled Firebase email only after an exact identity match."""
        try:
            user = await asyncio.to_thread(
                self._auth.get_user,
                uid,
                app=self._app,
            )
        except Exception as exc:
            raise FirebaseAdminError("Firebase identity lookup failed.") from exc

        actual_uid = getattr(user, "uid", None)
        actual_email = getattr(user, "email", None)
        if (
            actual_uid != uid
            or not isinstance(actual_email, str)
            or actual_email.strip().casefold() != expected_email.strip().casefold()
        ):
            raise FirebaseAdminError(
                "Firebase identity does not match the requested UID/email."
            )
        if bool(getattr(user, "disabled", False)):
            raise FirebaseAdminError("Firebase identity is disabled.")
        if bool(getattr(user, "email_verified", False)):
            return False

        try:
            await asyncio.to_thread(
                self._auth.update_user,
                uid,
                email_verified=True,
                app=self._app,
            )
        except Exception as exc:
            raise FirebaseAdminError(
                "Firebase email verification update failed."
            ) from exc
        return True

    async def revoke_refresh_tokens(self, uid: str) -> None:
        try:
            await asyncio.to_thread(
                self._auth.revoke_refresh_tokens,
                uid,
                app=self._app,
            )
        except Exception as exc:
            raise FirebaseAdminError(
                "Firebase refresh-token revocation failed."
            ) from exc


__all__ = [
    "FirebaseAdminClient",
    "FirebaseAdminError",
    "FirebaseEmailVerificationClient",
    "FirebaseAdminGateway",
]
