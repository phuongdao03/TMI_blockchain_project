from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_alert_policies_are_actionable_and_redact_sensitive_fields() -> None:
    document = yaml.safe_load(
        (ROOT / "infrastructure/monitoring/alert-policies.yaml").read_text(
            encoding="utf-8"
        )
    )

    denied = set(document["defaults"]["telemetry_redaction"]["deny_fields"])
    assert {"password", "token", "private_key", "authorization", "cookie"} <= denied
    for alert in document["alerts"]:
        assert alert["threshold"] >= 0
        assert alert["window"].endswith("m")
        assert alert["severity"] in {"page", "ticket"}
        assert alert["route"]
        assert alert["runbook"].startswith("docs/runbooks/")


def test_restore_runbook_contains_verifiable_drill_gates() -> None:
    runbook = (ROOT / "docs/runbooks/backup-and-restore.md").read_text(encoding="utf-8")
    normalized_runbook = " ".join(runbook.split())

    for gate in (
        "RPO",
        "RTO",
        "checksum",
        "canonical hashes",
        "Cloudinary",
        "chain ID",
        "public verification",
    ):
        assert gate in normalized_runbook


def test_delivery_yaml_files_parse_for_pipeline_dry_run() -> None:
    for relative_path in (
        ".github/workflows/delivery.yml",
        "infrastructure/compose.production.yaml",
        "infrastructure/monitoring/alert-policies.yaml",
    ):
        document = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
        assert isinstance(document, dict)
