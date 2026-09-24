from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.modules.hr.location import (
    calculate_geodesic_distance_meters,
    is_accuracy_acceptable,
    is_within_radius,
    local_work_date_for,
)


def test_geodesic_distance_is_zero_for_the_same_location() -> None:
    distance = calculate_geodesic_distance_meters(
        latitude_a=Decimal("10.776900"),
        longitude_a=Decimal("106.700900"),
        latitude_b=Decimal("10.776900"),
        longitude_b=Decimal("106.700900"),
    )

    assert distance == Decimal("0")


def test_geodesic_distance_uses_the_haversine_earth_mean_radius() -> None:
    distance = calculate_geodesic_distance_meters(
        latitude_a=Decimal("0"),
        longitude_a=Decimal("0"),
        latitude_b=Decimal("0"),
        longitude_b=Decimal("1"),
    )

    assert float(distance) == pytest.approx(111_195, abs=1)


def test_geodesic_distance_rejects_coordinates_outside_the_geographic_range() -> None:
    with pytest.raises(ValueError, match="(?i)latitude"):
        calculate_geodesic_distance_meters(
            latitude_a=Decimal("90.001"),
            longitude_a=Decimal("0"),
            latitude_b=Decimal("0"),
            longitude_b=Decimal("0"),
        )


def test_radius_comparison_accepts_the_exact_policy_boundary() -> None:
    assert is_within_radius(distance_meters=Decimal("250.00"), radius_meters=250)
    assert not is_within_radius(distance_meters=Decimal("250.01"), radius_meters=250)


def test_accuracy_comparison_accepts_the_exact_policy_boundary() -> None:
    assert is_accuracy_acceptable(
        accuracy_meters=Decimal("40.00"), max_accuracy_meters=40
    )
    assert not is_accuracy_acceptable(
        accuracy_meters=Decimal("40.01"), max_accuracy_meters=40
    )


def test_local_work_date_uses_the_supplied_iana_timezone() -> None:
    occurred_at = datetime(2026, 9, 21, 0, 30, tzinfo=UTC)

    assert local_work_date_for(
        occurred_at=occurred_at, timezone="America/Los_Angeles"
    ) == date(2026, 9, 20)
    assert local_work_date_for(
        occurred_at=occurred_at, timezone="Asia/Ho_Chi_Minh"
    ) == date(2026, 9, 21)


def test_local_work_date_handles_a_dst_clock_change() -> None:
    before_change = datetime(2026, 3, 8, 6, 59, tzinfo=UTC)
    after_change = datetime(2026, 3, 8, 7, 0, tzinfo=UTC)

    assert local_work_date_for(
        occurred_at=before_change, timezone="America/New_York"
    ) == date(2026, 3, 8)
    assert local_work_date_for(
        occurred_at=after_change, timezone="America/New_York"
    ) == date(2026, 3, 8)


def test_local_work_date_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        local_work_date_for(
            occurred_at=datetime(2026, 9, 21, 0, 30), timezone="Asia/Ho_Chi_Minh"
        )


@pytest.mark.parametrize("timezone", ("Mars/Olympus_Mons", "../outside"))
def test_local_work_date_rejects_an_invalid_iana_timezone(timezone: str) -> None:
    with pytest.raises(ValueError, match="IANA"):
        local_work_date_for(
            occurred_at=datetime(2026, 9, 21, 0, 30, tzinfo=UTC),
            timezone=timezone,
        )
