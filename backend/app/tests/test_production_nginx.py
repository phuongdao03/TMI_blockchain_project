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
