import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response

from app.api.v1.hr import AddressSearchRequest, search_attendance_worksite_address
from app.core.config import Settings
from app.core.errors import DomainError
from app.modules.hr import geocoding


def test_geocoding_returns_only_bounded_labels_and_coordinates(monkeypatch):
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/geocoding/v1/search"
        assert request.url.params["size"] == "5"
        assert request.headers["Authorization"] == "Stadia-Auth server-secret"
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [106.7, 10.72]},
                        "properties": {"label": "Văn phòng", "private": "not returned"},
                    },
                    {
                        "geometry": {"coordinates": [999, 10.72]},
                        "properties": {"label": "Invalid"},
                    },
                ]
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        geocoding.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    results = asyncio.run(
        geocoding.search_worksite_addresses("Văn phòng", "server-secret")
    )
    assert results == [{"label": "Văn phòng", "latitude": 10.72, "longitude": 106.7}]


def test_geocoding_hides_upstream_error_and_key(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        geocoding.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(401)), **kwargs
        ),
    )
    with pytest.raises(DomainError) as caught:
        asyncio.run(geocoding.search_worksite_addresses("Văn phòng", "server-secret"))
    assert caught.value.code == "HR_GEOCODING_UNAVAILABLE"
    assert "server-secret" not in caught.value.message


def test_address_search_rejects_non_admin_before_using_provider():
    with pytest.raises(DomainError) as caught:
        asyncio.run(
            search_attendance_worksite_address(
                request=SimpleNamespace(state=SimpleNamespace(request_id="test")),
                response=Response(),
                input_data=AddressSearchRequest(q="Văn phòng"),
                principal=SimpleNamespace(roles=("USER",)),
                settings=Settings(stadia_maps_api_key="server-secret"),
            )
        )
    assert caught.value.status_code == 403
