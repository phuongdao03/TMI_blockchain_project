from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_full_release_profile_contains_required_async_runtime_services() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "infrastructure" / "compose.production.yaml").read_text(
            encoding="utf-8"
        )
    )

    for name in ("clamav", "worker", "scheduler"):
        assert compose["services"][name]["profiles"] == ["full"]


def test_release_library_enables_full_profile_only_for_full_releases() -> None:
    release_library = (
        PROJECT_ROOT / "infrastructure" / "scripts" / "release-lib.sh"
    ).read_text(encoding="utf-8")

    expected_release_mode = (
        'release_mode="$(read_env_value "$PRODUCTION_ENV_FILE" "RELEASE_MODE")"'
    )

    assert expected_release_mode in release_library
    assert 'release_mode="${release_mode:-full}"' in release_library
    assert '[[ "$release_mode" == "full" ]]' in release_library
    assert 'compose_arguments+=(--profile full)' in release_library
