from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_local_bootstrap_does_not_create_static_test_identities() -> None:
    bootstrap_scripts = (
        PROJECT_ROOT / "infrastructure/scripts/bootstrap-local.ps1",
        PROJECT_ROOT / "infrastructure/scripts/bootstrap-local.sh",
    )
    for script in bootstrap_scripts:
        content = script.read_text(encoding="utf-8")
        assert "app.scripts.seed_local" not in content
        assert "LocalOnly!23456" not in content
        assert "BLOCKCHAIN_SIGNER_PRIVATE_KEY" not in content


def test_runtime_runbook_does_not_publish_static_test_credentials() -> None:
    runbook = PROJECT_ROOT / "docs/runbooks/runtime-environment.md"
    content = runbook.read_text(encoding="utf-8")
    assert "LocalOnly!23456" not in content
    assert "applicant@example.com" not in content
    assert "reviewer@example.com" not in content
