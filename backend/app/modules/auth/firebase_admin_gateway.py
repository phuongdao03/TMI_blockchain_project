import asyncio
import importlib
import re
from typing import Any, Protocol

from app.core.config import Settings


class FirebaseAdminError(RuntimeError):
    pass


class FirebaseAdminClient(Protocol):
    async def set_disabled(self, uid: str, *, disabled: bool) -> None: ...


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


__all__ = [
    "FirebaseAdminClient",
    "FirebaseAdminError",
    "FirebaseAdminGateway",
]
