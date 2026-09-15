import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.modules.public.video_poster import (
    _extract,
    cached_poster,
    extract_video_poster,
    retain_poster,
)


def test_poster_cache_expires_and_is_bounded() -> None:
    with patch("app.modules.public.video_poster.monotonic", return_value=100):
        for index in range(17):
            retain_poster(f"poster-{index}", b"jpeg")
        assert cached_poster("poster-0") is None
        assert cached_poster("poster-16") == b"jpeg"
    with patch("app.modules.public.video_poster.monotonic", return_value=401):
        assert cached_poster("poster-16") is None


def test_poster_uses_seekable_private_input_and_cleans_it() -> None:
    source: Path | None = None

    def render(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal source
        source = Path(command[command.index("-i") + 1])
        assert source.read_bytes() == b"retained video"
        assert command[command.index("-protocol_whitelist") + 1] == "file,pipe"
        assert kwargs["timeout"] == 30
        assert command[command.index("-frames:v") + 1] == "1"
        return subprocess.CompletedProcess(command, 0, b"\xff\xd8frame", b"")

    with patch("app.modules.public.video_poster.subprocess.run", side_effect=render):
        assert _extract(b"retained video") == b"\xff\xd8frame"
    assert source is not None and not source.exists()


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("ffmpeg", 30),
        ValueError("bad video"),
    ],
)
def test_poster_failure_is_an_explicit_retryable_error(failure: Exception) -> None:
    with patch("app.modules.public.video_poster._extract", side_effect=failure):
        with pytest.raises(HTTPException) as caught:
            asyncio.run(extract_video_poster(b"video"))
    assert caught.value.status_code == 503


def test_rejects_non_image_decoder_output() -> None:
    with patch(
        "app.modules.public.video_poster.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, b"not jpeg", b""),
    ):
        with pytest.raises(ValueError):
            _extract(b"video")
