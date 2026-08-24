from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_production_nginx_allows_firebase_google_auth() -> None:
    config_paths = (
        PROJECT_ROOT / "infrastructure" / "nginx" / "production.conf.template",
        PROJECT_ROOT
        / "infrastructure"
        / "nginx"
        / "decu.tinhhoaviet.org.vn.conf.example",
    )

    for config_path in config_paths:
        config = config_path.read_text(encoding="utf-8")
        assert "script-src 'self' 'unsafe-inline' https://apis.google.com" in config
        assert "frame-src 'self' https://*.firebaseapp.com" in config


def test_document_verification_accepts_its_bounded_binary_body_only() -> None:
    config_paths = (
        PROJECT_ROOT / "infrastructure" / "nginx" / "production.conf.template",
        PROJECT_ROOT
        / "infrastructure"
        / "nginx"
        / "decu.tinhhoaviet.org.vn.conf.example",
    )

    verification_location = "location ~ ^/api/v1/media/[0-9a-fA-F-]+/verifications$"
    for config_path in config_paths:
        config = config_path.read_text(encoding="utf-8")
        assert "client_max_body_size 1m;" in config
        assert verification_location in config
        location_start = config.index(verification_location)
        location_end = config.index("\n    }", location_start)
        assert "client_max_body_size 25m;" in config[location_start:location_end]
