def cloudinary_video_variant(
    url: str | None, *, transformation: str, extension: str
) -> str | None:
    """Build a variant from the public video source, not an MP4 derivative URL."""
    marker = "/video/upload/"
    if (
        not url
        or not url.startswith("https://res.cloudinary.com/")
        or marker not in url
    ):
        return None
    prefix, path = url.split(marker, 1)
    if path.startswith("c_limit,"):
        _, separator, path = path.partition("/")
        if not separator:
            return None
    base = path.rsplit(".", 1)[0]
    return f"{prefix}{marker}{transformation}/{base}.{extension}"
