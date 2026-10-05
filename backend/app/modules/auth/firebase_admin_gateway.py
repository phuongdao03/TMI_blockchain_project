import asyncio
import importlib
import re
from typing import Any, Protocol
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

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
            app_name = "cns-admin-" + re.sub(
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

    async def unverified_password_email(self, id_token: str) -> str:
        """Resolve the email from a valid password identity, never client input."""
        try:
            claims = await asyncio.to_thread(
                self._auth.verify_id_token, id_token, app=self._app
            )
            if claims.get("firebase", {}).get("sign_in_provider") != "password":
                raise ValueError("Password sign-in is required.")
            uid = claims.get("uid")
            email = claims.get("email")
            if not isinstance(uid, str) or not isinstance(email, str):
                raise ValueError("Firebase identity is incomplete.")
            user = await asyncio.to_thread(self._auth.get_user, uid, app=self._app)
            if (
                user.uid != uid
                or not isinstance(user.email, str)
                or user.email.casefold() != email.casefold()
                or user.disabled
                or user.email_verified
            ):
                raise ValueError("Firebase identity cannot receive verification.")
            return email
        except Exception as exc:
            raise FirebaseAdminError(
                "Firebase verification identity is invalid."
            ) from exc

    async def branded_email_verification_link(
        self, email: str, *, app_base_url: str
    ) -> str:
        """Keep the Firebase one-time code but use the THV origin in the email."""
        try:
            continue_url = f"{app_base_url.rstrip('/')}/login"
            settings = self._auth.ActionCodeSettings(
                url=continue_url, handle_code_in_app=False
            )
            firebase_link = await asyncio.to_thread(
                self._auth.generate_email_verification_link,
                email,
                settings,
                app=self._app,
            )
            query = parse_qs(urlsplit(firebase_link).query)
            if (
                query.get("mode") != ["verifyEmail"]
                or len(query.get("oobCode", [])) != 1
            ):
                raise ValueError("Firebase verification link is invalid.")
            app_url = urlsplit(app_base_url)
            if app_url.scheme not in {"http", "https"} or not app_url.netloc:
                raise ValueError("Application URL is invalid.")
            return urlunsplit(
                (
                    app_url.scheme,
                    app_url.netloc,
                    "/auth/action",
                    urlencode({"mode": "verifyEmail", "oobCode": query["oobCode"][0]}),
                    "",
                )
            )
        except Exception as exc:
            raise FirebaseAdminError(
                "Firebase verification link is unavailable."
            ) from exc


__all__ = [
    "FirebaseAdminClient",
    "FirebaseAdminError",
    "FirebaseEmailVerificationClient",
    "FirebaseAdminGateway",
]
