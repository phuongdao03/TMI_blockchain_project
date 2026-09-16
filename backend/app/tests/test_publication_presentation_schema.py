import pytest
from pydantic import ValidationError

from app.modules.public.schemas import PublicVideoPresentationRequest


def test_video_poster_time_is_optional_and_can_select_a_later_frame() -> None:
    assert PublicVideoPresentationRequest().poster_time_ms is None
    assert (
        PublicVideoPresentationRequest.model_validate(
            {"posterTimeMs": 12500}
        ).poster_time_ms
        == 12500
    )


@pytest.mark.parametrize("value", [-1, 86400001, 12.5])
def test_invalid_poster_time_is_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        PublicVideoPresentationRequest.model_validate({"posterTimeMs": value})
