
from unittest.mock import MagicMock, patch

import pytest
import requests

from services import geocoding
from services.geocoding import (
    GeocodingConfigurationError,
    GeocodingError,
    LocationNotFoundError,
    clear_geocoding_cache,
    geocode_address,
)


@pytest.fixture(autouse=True)
def reset_geocoding_state(monkeypatch):
    clear_geocoding_cache()

    monkeypatch.setenv(
        "NOMINATIM_USER_AGENT",
        "SmartRide/1.0 (contact: test@example.com)",
    )
    monkeypatch.setenv(
        "NOMINATIM_URL",
        "https://nominatim.openstreetmap.org/search",
    )

    with patch("services.geocoding._wait_for_rate_limit"):
        yield

    clear_geocoding_cache()


def mock_successful_response():
    response = MagicMock()

    response.json.return_value = [
        {
            "lat": "55.9521",
            "lon": "-3.1889",
            "display_name": "Edinburgh Waverley, Edinburgh, Scotland",
        }
    ]

    response.raise_for_status.return_value = None

    return response


def test_geocode_address_success():
    response = mock_successful_response()

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ) as mock_get:

        result = geocode_address("Edinburgh Waverley")

    assert result == {
        "latitude": 55.9521,
        "longitude": -3.1889,
        "display_name": (
            "Edinburgh Waverley, Edinburgh, Scotland"
        ),
    }

    mock_get.assert_called_once()

    args, kwargs = mock_get.call_args

    assert args[0] == (
        "https://nominatim.openstreetmap.org/search"
    )
    assert kwargs["params"]["q"] == "Edinburgh Waverley"
    assert kwargs["params"]["format"] == "jsonv2"
    assert kwargs["params"]["countrycodes"] == "gb"
    assert kwargs["headers"]["User-Agent"] == (
        "SmartRide/1.0 (contact: test@example.com)"
    )


def test_geocode_address_uses_cache():
    response = mock_successful_response()

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ) as mock_get:

        first_result = geocode_address("Edinburgh Waverley")
        second_result = geocode_address("Edinburgh Waverley")

    assert first_result == second_result
    mock_get.assert_called_once()


def test_geocode_address_cache_ignores_case_and_outer_spaces():
    response = mock_successful_response()

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ) as mock_get:

        first_result = geocode_address("Edinburgh Waverley")
        second_result = geocode_address(" edinburgh waverley ")

    assert first_result == second_result
    mock_get.assert_called_once()


@pytest.mark.parametrize(
    "address",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_geocode_address_rejects_invalid_address(address):
    with pytest.raises(ValueError, match="valid address"):
        geocode_address(address)


def test_geocode_address_rejects_address_over_255_characters():
    with pytest.raises(ValueError, match="255 characters"):
        geocode_address("A" * 256)


def test_geocode_address_requires_user_agent(monkeypatch):
    monkeypatch.delenv("NOMINATIM_USER_AGENT")

    with pytest.raises(
        GeocodingConfigurationError,
        match="NOMINATIM_USER_AGENT",
    ):
        geocode_address("Edinburgh Waverley")


def test_geocode_address_rejects_placeholder_user_agent(monkeypatch):
    monkeypatch.setenv(
        "NOMINATIM_USER_AGENT",
        "SmartRide/1.0 (contact: YOUR_REAL_CONTACT_EMAIL)",
    )

    with pytest.raises(
        GeocodingConfigurationError,
        match="real contact email",
    ):
        geocode_address("Edinburgh Waverley")


def test_geocode_address_handles_no_results():
    response = MagicMock()
    response.json.return_value = []
    response.raise_for_status.return_value = None

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ):
        with pytest.raises(LocationNotFoundError):
            geocode_address("Unknown fictional location")


def test_geocode_address_handles_network_failure():
    with patch(
        "services.geocoding.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(
            GeocodingError,
            match="Unable to contact",
        ):
            geocode_address("Edinburgh Waverley")


def test_geocode_address_handles_http_error():
    response = MagicMock()
    response.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("Service unavailable")
    )

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            GeocodingError,
            match="Unable to contact",
        ):
            geocode_address("Edinburgh Waverley")


def test_geocode_address_handles_invalid_json():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("Invalid JSON")

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            GeocodingError,
            match="invalid response",
        ):
            geocode_address("Edinburgh Waverley")


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        ("95", "-3.1889"),
        ("55.9521", "200"),
        ("nan", "-3.1889"),
        ("55.9521", "inf"),
        ("invalid", "-3.1889"),
    ],
)
def test_geocode_address_rejects_invalid_coordinates(
    latitude,
    longitude,
):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "lat": latitude,
            "lon": longitude,
            "display_name": "Test location",
        }
    ]

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            GeocodingError,
            match="invalid coordinates",
        ):
            geocode_address("Test location")


def test_geocode_address_handles_missing_display_name():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "lat": "55.9521",
            "lon": "-3.1889",
        }
    ]

    with patch(
        "services.geocoding.requests.get",
        return_value=response,
    ):
        with pytest.raises(
            GeocodingError,
            match="invalid coordinates",
        ):
            geocode_address("Test location")


def test_geocode_address_rejects_invalid_timeout():
    with pytest.raises(ValueError, match="positive number"):
        geocode_address("Edinburgh Waverley", timeout=0)


def test_geocode_address_rejects_invalid_country_code():
    with pytest.raises(ValueError, match="country code"):
        geocode_address(
            "Edinburgh Waverley",
            country_codes=" ",
        )
