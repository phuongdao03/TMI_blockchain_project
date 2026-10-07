from app.modules.public.cloudinary_variants import cloudinary_video_variant


def test_hls_and_poster_use_original_public_video_path() -> None:
    mp4 = (
        "https://res.cloudinary.com/demo/video/upload/"
        "c_limit,w_1280,h_720,q_auto:good,vc_auto,f_mp4/"
        "v123/public/video.mp4"
    )
    assert (
        cloudinary_video_variant(
            mp4, transformation="sp_auto:maxres_720p/f_m3u8", extension="m3u8"
        )
        == "https://res.cloudinary.com/demo/video/upload/sp_auto:maxres_720p/f_m3u8/v123/public/video.m3u8"
    )
    assert (
        cloudinary_video_variant(
            mp4, transformation="so_auto,q_auto,f_webp", extension="webp"
        )
        == "https://res.cloudinary.com/demo/video/upload/so_auto,q_auto,f_webp/v123/public/video.webp"
    )


def test_local_media_proxy_has_no_cloudinary_variants() -> None:
    assert (
        cloudinary_video_variant(
            "/api/v1/public/works/a/media/b",
            transformation="sp_auto:maxres_720p",
            extension="m3u8",
        )
        is None
    )
