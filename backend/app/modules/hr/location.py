"""Pure, server-side location and time primitives for attendance decisions.

This module deliberately has no database, HTTP or logging dependency.  The
attendance service owns policy resolution and evidence persistence; these
functions only provide deterministic measurements and timezone conversions from
already-validated data.
"""

from datetime import date, datetime
from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

EARTH_MEAN_RADIUS_METERS = Decimal("6371008.8")


def calculate_geodesic_distance_meters(
    *,
    latitude_a: Decimal,
    longitude_a: Decimal,
    latitude_b: Decimal,
    longitude_b: Decimal,
) -> Decimal:
    """Return the Haversine distance between two geographic positions in metres."""
    _validate_latitude(latitude_a)
    _validate_latitude(latitude_b)
    _validate_longitude(longitude_a)
    _validate_longitude(longitude_b)

    latitude_a_radians = radians(float(latitude_a))
    latitude_b_radians = radians(float(latitude_b))
    latitude_delta = latitude_b_radians - latitude_a_radians
    longitude_delta = radians(float(longitude_b - longitude_a))

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_a_radians)
        * cos(latitude_b_radians)
        * sin(longitude_delta / 2) ** 2
    )
    clamped_haversine = min(1.0, max(0.0, haversine))
    central_angle = 2 * atan2(sqrt(clamped_haversine), sqrt(1 - clamped_haversine))
    return Decimal(str(float(EARTH_MEAN_RADIUS_METERS) * central_angle))


def is_within_radius(*, distance_meters: Decimal, radius_meters: int) -> bool:
    """Return whether a non-negative calculated distance is within a policy radius."""
    _validate_positive_or_zero(distance_meters, field_name="Distance")
    if radius_meters <= 0:
        raise ValueError("Radius must be greater than zero.")
    return distance_meters <= Decimal(radius_meters)


def is_accuracy_acceptable(
    *, accuracy_meters: Decimal, max_accuracy_meters: int
) -> bool:
    """Return whether a reported positive GPS accuracy satisfies the policy limit."""
    _validate_positive(accuracy_meters, field_name="Accuracy")
    if max_accuracy_meters <= 0:
        raise ValueError("Maximum accuracy must be greater than zero.")
    return accuracy_meters <= Decimal(max_accuracy_meters)


def local_work_date_for(*, occurred_at: datetime, timezone: str) -> date:
    """Convert a server event time to the supplied effective IANA workday."""
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise ValueError("Event time must be timezone-aware.")
    try:
        effective_timezone = ZoneInfo(timezone.strip())
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("Timezone must be a valid IANA timezone.") from error
    return occurred_at.astimezone(effective_timezone).date()


def _validate_latitude(value: Decimal) -> None:
    if not value.is_finite() or not Decimal("-90") <= value <= Decimal("90"):
        raise ValueError("Latitude must be between -90 and 90 degrees.")


def _validate_longitude(value: Decimal) -> None:
    if not value.is_finite() or not Decimal("-180") <= value <= Decimal("180"):
        raise ValueError("Longitude must be between -180 and 180 degrees.")


def _validate_positive_or_zero(value: Decimal, *, field_name: str) -> None:
    if not value.is_finite() or value < 0:
        raise ValueError(f"{field_name} must be zero or greater.")


def _validate_positive(value: Decimal, *, field_name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
