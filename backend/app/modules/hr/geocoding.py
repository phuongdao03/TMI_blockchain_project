"""Bounded, admin-only address lookup; never return the Stadia credential."""

import math

import httpx

from app.core.errors import DomainError

STADIA_SEARCH_URL = "https://api.stadiamaps.com/geocoding/v1/search"


async def search_worksite_addresses(
    query: str, api_key: str
) -> list[dict[str, object]]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                STADIA_SEARCH_URL,
                params={"text": query, "size": 5},
                headers={"Authorization": f"Stadia-Auth {api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise DomainError(
            code="HR_GEOCODING_UNAVAILABLE",
            message="Address search is temporarily unavailable.",
            status_code=502,
        ) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise DomainError(
            code="HR_GEOCODING_UNAVAILABLE",
            message="Address search returned an invalid response.",
            status_code=502,
        )

    results: list[dict[str, object]] = []
    for feature in payload["features"][:5]:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if not isinstance(geometry, dict) or not isinstance(properties, dict):
            continue
        coordinates = geometry.get("coordinates")
        label = properties.get("label")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) < 2
            or not isinstance(label, str)
            or not label.strip()
        ):
            continue
        lng, lat = coordinates[:2]
        if (
            isinstance(lat, (int, float))
            and not isinstance(lat, bool)
            and isinstance(lng, (int, float))
            and not isinstance(lng, bool)
            and math.isfinite(lat)
            and math.isfinite(lng)
            and -90 <= lat <= 90
            and -180 <= lng <= 180
        ):
            results.append({"label": label[:240], "latitude": lat, "longitude": lng})
    return results
