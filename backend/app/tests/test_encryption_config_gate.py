import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def test_release_rejects_malformed_encryption_keys(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if os.name == "nt":
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.exists():
            bash = str(git_bash)
    if bash is None:
        pytest.skip("Bash is unavailable")

    project_root = Path(__file__).resolve().parents[3]
    release_lib = project_root / "infrastructure/scripts/release-lib.sh"
    env_file = tmp_path / ".env.production"
    command = 'source "$1"; require_encryption_key "$2" PII_ENCRYPTION_KEY'

    def validate(value: str) -> subprocess.CompletedProcess[str]:
        env_file.write_text(f"PII_ENCRYPTION_KEY={value}\n", encoding="utf-8")
        return subprocess.run(
            [bash, "-c", command, "bash", str(release_lib), str(env_file)],
            capture_output=True,
            text=True,
            check=False,
        )

    valid_key = base64.b64encode(bytes(range(32))).decode("ascii")
    assert validate(valid_key).returncode == 0
    assert validate("not-a-base64-key").returncode != 0
    assert validate(base64.b64encode(bytes(range(16))).decode("ascii")).returncode != 0
