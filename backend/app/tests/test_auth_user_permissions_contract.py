from uuid import uuid4

from app.modules.auth.schemas import AuthUserData


def test_auth_user_contract_exposes_effective_permissions() -> None:
    data = AuthUserData(
        id=uuid4(),
        email="admin@example.com",
        roles=("SUPER_ADMIN",),
        permissions=("users.read", "users.suspend"),
        accountType=None,
    )

    assert data.model_dump(mode="json", by_alias=True)["permissions"] == [
        "users.read",
        "users.suspend",
    ]
