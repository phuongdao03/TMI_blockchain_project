"""Render a legacy retained video frame without creating a provider copy."""

import asyncio
import subprocess
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from fastapi import HTTPException

_poster_slots = asyncio.Semaphore(2)
_posters: OrderedDict[str, tuple[float, bytes]] = OrderedDict()


def cached_poster(digest: str | None) -> bytes | None:
    if not digest or digest not in _posters:
        return None
    expires_at, content = _posters[digest]
    if expires_at <= monotonic():
        del _posters[digest]
        return None
    _posters.move_to_end(digest)
    return content


def retain_poster(digest: str | None, content: bytes) -> None:
    # Short-lived, bounded RAM only; no second Cloudinary asset or disk copy.
    if not digest or len(content) > 2 * 1024 * 1024:
        return
    _posters[digest] = (monotonic() + 300, content)
    _posters.move_to_end(digest)
    while len(_posters) > 16:
        _posters.popitem(last=False)


def _extract(content: bytes) -> bytes:
    # A seekable input also supports MP4s whose metadata follows the media data.
    # The directory is private and removed on success, failure and timeout.
    with TemporaryDirectory(prefix="tmi-poster-") as directory:
        source = Path(directory) / "source.video"
        source.write_bytes(content)
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-threads",
                "1",
                "-max_alloc",
                "67108864",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,matroska,webm,avi",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-vf",
                "scale=960:540:force_original_aspect_ratio=decrease",
                "-an",
                "-sn",
                "-dn",
                "-threads",
                "1",
                "-f",
                "image2pipe",
                "-c:v",
                "mjpeg",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=True,
        )
        if (
            not result.stdout.startswith(b"\xff\xd8")
            or len(result.stdout) > 2 * 1024 * 1024
        ):
            raise ValueError("Invalid poster output")
        return result.stdout


async def extract_video_poster(content: bytes) -> bytes:
    async with _poster_slots:
        try:
            task = asyncio.create_task(asyncio.to_thread(_extract, content))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # A disconnected request must not free a slot while its decoder
                # still runs. The subprocess timeout also bounds this wait.
                await asyncio.gather(task, return_exceptions=True)
                raise
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise HTTPException(
                status_code=503,
                detail="Ảnh bìa chưa sẵn sàng. Hãy thử lại hoặc chọn ảnh khác.",
            ) from error
