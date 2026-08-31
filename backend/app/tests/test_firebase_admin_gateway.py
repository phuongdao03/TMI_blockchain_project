import asyncio
from types import SimpleNamespace

import pytest

from app.modules.auth.firebase_admin_gateway import (
    FirebaseAdminError,
    FirebaseAdminGateway,
)


class _AuthModule:
    def __init__(self, user: object) -> None:
        self.user = user
        self.get_user_calls: list[tuple[str, object]] = []
        self.update_user_calls: list[tuple[str, dict[str, object]]] = []
        self.revoke_calls: list[tuple[str, object]] = []

    def get_user(self, uid: str, *, app: object) -> object:
        self.get_user_calls.append((uid, app))
        return self.user

    def update_user(self, uid: str, **kwargs: object) -> object:
        self.update_user_calls.append((uid, kwargs))
        return self.user

    def revoke_refresh_tokens(self, uid: str, *, app: object) -> object:
        self.revoke_calls.append((uid, app))
        return self.user


def test_verify_email_for_identity_updates_only_an_exact_enabled_match() -> None:
    async def scenario() -> None:
        app = object()
        auth = _AuthModule(
            SimpleNamespace(
                uid="firebase-test-super-admin",
                email="Super.Admin@Example.Test",
                email_verified=False,
                disabled=False,
            )
        )
        gateway = FirebaseAdminGateway(auth_module=auth, app=app)

        changed = await gateway.verify_email_for_identity(
            "firebase-test-super-admin",
            expected_email="super.admin@example.test",
        )

        assert changed is True
        assert auth.update_user_calls == [
            (
                "firebase-test-super-admin",
                {"email_verified": True, "app": app},
            )
        ]

    asyncio.run(scenario())


def test_verify_email_for_identity_rejects_a_mismatched_email_without_update() -> None:
    async def scenario() -> None:
        auth = _AuthModule(
            SimpleNamespace(
                uid="firebase-test-super-admin",
                email="another-admin@example.com",
                email_verified=False,
                disabled=False,
            )
        )
        gateway = FirebaseAdminGateway(auth_module=auth, app=object())

        with pytest.raises(FirebaseAdminError, match="does not match"):
            await gateway.verify_email_for_identity(
                "firebase-test-super-admin",
                expected_email="super.admin@example.test",
            )

        assert auth.update_user_calls == []

    asyncio.run(scenario())


def test_verify_email_for_identity_rejects_a_disabled_user_without_update() -> None:
    async def scenario() -> None:
        auth = _AuthModule(
            SimpleNamespace(
                uid="firebase-test-super-admin",
                email="super.admin@example.test",
                email_verified=False,
                disabled=True,
            )
        )
        gateway = FirebaseAdminGateway(auth_module=auth, app=object())

        with pytest.raises(FirebaseAdminError, match="disabled"):
            await gateway.verify_email_for_identity(
                "firebase-test-super-admin",
                expected_email="super.admin@example.test",
            )

        assert auth.update_user_calls == []

    asyncio.run(scenario())
