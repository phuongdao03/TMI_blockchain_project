from pathlib import Path
from typing import TypedDict, cast

import yaml

from app.workers.celery_app import celery_app

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_SERVICES = {
    "anvil",
    "backend",
    "frontend",
    "nginx",
    "redis",
    "scheduler",
    "worker",
}


class ServiceConfig(TypedDict, total=False):
    depends_on: dict[str, dict[str, str]]
    environment: dict[str, str]
    entrypoint: list[str]
    healthcheck: dict[str, object]
    profiles: list[str]
    read_only: bool
    restart: str
    user: str
    volumes: list[str]


class ComposeConfig(TypedDict):
    services: dict[str, ServiceConfig]
    volumes: dict[str, object]


def load_compose() -> ComposeConfig:
    compose_path = PROJECT_ROOT / "compose.yaml"
    return cast(
        ComposeConfig,
        yaml.safe_load(compose_path.read_text(encoding="utf-8")),
    )


def test_compose_declares_required_local_services() -> None:
    compose = load_compose()
    services = compose["services"]

    assert set(services) == REQUIRED_SERVICES


def test_services_are_hardened_and_health_checked() -> None:
    services = load_compose()["services"]
    assert isinstance(services, dict)

    for name, service in services.items():
        assert service["restart"] == "unless-stopped", name
        assert service["user"] not in {"0", "0:0", "root"}, name
        assert "healthcheck" in service, name

    assert services["backend"]["read_only"] is True
    assert services["worker"]["read_only"] is True
    assert services["scheduler"]["read_only"] is True


def test_backend_waits_for_redis_and_anvil_health() -> None:
    backend = load_compose()["services"]["backend"]

    assert backend["depends_on"]["redis"]["condition"] == "service_healthy"
    assert backend["depends_on"]["anvil"]["condition"] == "service_healthy"
    assert backend["environment"]["REDIS_URL"] == "redis://redis:6379/0"
    assert backend["environment"]["ANVIL_RPC_URL"] == "http://anvil:8545"
    assert backend["environment"]["PII_ENCRYPTION_KEY"] == "${PII_ENCRYPTION_KEY:-}"


def test_anvil_command_bypasses_foundry_shell_entrypoint() -> None:
    anvil = load_compose()["services"]["anvil"]

    assert anvil["entrypoint"] == []


def test_only_redis_has_a_named_persistent_volume() -> None:
    compose = load_compose()

    assert set(compose["volumes"]) == {"redis_data"}
    redis_mounts = compose["services"]["redis"]["volumes"]
    assert redis_mounts == ["redis_data:/data"]


def test_frontend_stack_is_explicitly_deferred_to_profile() -> None:
    services = load_compose()["services"]

    assert services["frontend"]["profiles"] == ["frontend"]
    assert services["nginx"]["profiles"] == ["frontend"]


def test_environment_example_contains_placeholders_only() -> None:
    env_path = PROJECT_ROOT / ".env.example"
    entries = dict(
        line.split("=", maxsplit=1)
        for line in env_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )

    assert entries["APP_ENV"] == "local"
    assert entries["REDIS_URL"] == "redis://redis:6379/0"
    assert entries["ANVIL_RPC_URL"] == "http://anvil:8545"
    for secret_name in (
        "BLOCKCHAIN_SIGNER_PRIVATE_KEY",
        "CLOUDINARY_API_SECRET",
        "DATABASE_URL",
        "JWT_SECRET",
        "PAYMENT_WEBHOOK_SECRET",
        "PII_ENCRYPTION_KEY",
    ):
        assert entries[secret_name] == ""


def test_backend_image_runs_as_non_root() -> None:
    dockerfile = (PROJECT_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "USER 10001:10001" in dockerfile
    assert "python:3.12.8-slim-bookworm" in dockerfile


def test_celery_uses_redis_and_json_serialization() -> None:
    assert celery_app.conf.broker_url == "redis://redis:6379/0"
    assert celery_app.conf.result_backend == "redis://redis:6379/0"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.task_serializer == "json"
