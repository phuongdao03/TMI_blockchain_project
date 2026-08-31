from pathlib import Path


def test_payment_issue_permission_migration_is_additive() -> None:
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0065_payment_issue_permission.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision: str | None = "0064_admin_user_indexes"' in migration
    assert 'permissions.c.code == "payments.issue"' in migration
    assert "SUPER_ADMIN" not in migration
