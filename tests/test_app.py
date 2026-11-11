
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from html import unescape


import pytest

from app import app
from services.geocoding import (
    GeocodingError,
    LocationNotFoundError,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def valid_journey_data():
    return {
        "origin": "Edinburgh Waverley",
        "destination": "Edinburgh Napier University",
        "travel_date": (
            date.today() + timedelta(days=1)
        ).isoformat(),
        "departure_time": "09:30",
        "max_detour": "15",
        "passengers": "2",
    }


def mock_authenticated_user():
    return {
        "id": 42,
        "clerk_user_id": "user_test123",
        "display_name": "Test Student",
        "email": "student@example.com",
        "university": "Edinburgh Napier University",
        "verification_status": "pending",
        "account_status": "active",
    }


def mock_geocoding_results():
    return [
        {
            "latitude": 55.9521,
            "longitude": -3.1889,
            "display_name": "Edinburgh Waverley, Edinburgh",
        },
        {
            "latitude": 55.9225,
            "longitude": -3.1722,
            "display_name": "Edinburgh Napier University, Edinburgh",
        },
    ]


def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"SmartRide" in response.data


def test_find_ride_page_loads(client):
    response = client.get("/find-ride")

    assert response.status_code == 200
    assert b"Your journey details" in response.data


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "SmartRide",
        "status": "healthy",
    }


def test_edit_journey_preserves_values(client):
    response = client.get(
        "/find-ride",
        query_string={
            "origin": "Edinburgh Waverley",
            "destination": "Arthur's Seat",
            "travel_date": "2026-10-24",
            "departure_time": "12:43",
            "max_detour": "5",
            "passengers": "4",
            "edit": "1",
        },
    )

    assert response.status_code == 200
    assert b'value="Edinburgh Waverley"' in response.data
    assert b'value="Arthur&#39;s Seat"' in response.data
    assert b'value="12:43"' in response.data
    assert b'value="2026-10-24"' in response.data


def test_find_ride_rejects_missing_locations(client):
    response = client.get(
        "/find-ride",
        query_string={
            "origin": "",
            "destination": "",
            "travel_date": (
                date.today() + timedelta(days=1)
            ).isoformat(),
            "departure_time": "12:43",
            "max_detour": "5",
            "passengers": "4",
        },
    )

    assert response.status_code == 400
    assert b"Starting location and destination are required." in response.data


def test_find_ride_rejects_past_date(client):
    response = client.get(
        "/find-ride",
        query_string={
            "origin": "Edinburgh Waverley",
            "destination": "Arthur's Seat",
            "travel_date": "2020-01-01",
            "departure_time": "12:43",
            "max_detour": "5",
            "passengers": "4",
        },
    )

    assert response.status_code == 400
    assert b"Travel date cannot be in the past." in response.data


def test_find_ride_rejects_invalid_passenger_count(client):
    response = client.get(
        "/find-ride",
        query_string={
            "origin": "Edinburgh Waverley",
            "destination": "Arthur's Seat",
            "travel_date": (
                date.today() + timedelta(days=1)
            ).isoformat(),
            "departure_time": "12:43",
            "max_detour": "5",
            "passengers": "10",
        },
    )

    assert response.status_code == 400
    assert b"Please select a valid passenger count." in response.data


def test_db_health_endpoint_success(client):
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {"database_name": "test"}

    with patch("app.get_db_connection", return_value=mock_connection):
        response = client.get("/db-health")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "SmartRide",
        "database_status": "connected",
        "database": "test",
    }

    mock_cursor.execute.assert_called_once_with(
        "SELECT DATABASE() AS database_name"
    )
    mock_connection.close.assert_called_once()


def test_db_health_endpoint_failure(client):
    with patch(
        "app.get_db_connection",
        side_effect=Exception("Simulated database failure"),
    ):
        response = client.get("/db-health")

    assert response.status_code == 503
    assert response.get_json() == {
        "application": "SmartRide",
        "database_status": "unavailable",
    }


def test_find_ride_post_requires_sign_in(client):
    with patch(
        "app.get_authenticated_clerk_user_id",
        return_value=None,
    ) as mock_auth:
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 401
    assert b"Please sign in before submitting a journey." in response.data
    mock_auth.assert_called_once()


def test_find_ride_post_rejects_authentication_failure(client):
    with patch(
        "app.get_authenticated_clerk_user_id",
        side_effect=Exception("Authentication failure"),
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 401
    assert b"Unable to verify your account" in response.data


def test_find_ride_post_requires_existing_profile(client):
    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=None,
        ),
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 403
    assert b"complete your SmartRide profile" in response.data


def test_find_ride_post_rejects_inactive_account(client):
    inactive_user = mock_authenticated_user()
    inactive_user["account_status"] = "suspended"

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=inactive_user,
        ),
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 403
    assert b"account is not currently active" in response.data


def test_find_ride_post_saves_authenticated_journey(client):
    user = mock_authenticated_user()
    locations = mock_geocoding_results()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=locations,
        ) as mock_geocode,
        patch(
            "app.create_ride_request",
            return_value=101,
        ) as mock_create,
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 201
    assert b"Journey saved!" in response.data
    assert b"Request #101 saved successfully." in response.data

    assert mock_geocode.call_count == 2

    mock_create.assert_called_once_with(
        passenger_id=42,
        origin="Edinburgh Waverley",
        destination="Edinburgh Napier University",
        origin_latitude=55.9521,
        origin_longitude=-3.1889,
        destination_latitude=55.9225,
        destination_longitude=-3.1722,
        travel_date=(
            date.today() + timedelta(days=1)
        ).isoformat(),
        departure_time="09:30",
        passenger_count=2,
        max_detour_minutes=15,
    )


def test_find_ride_post_handles_unknown_location(client):
    user = mock_authenticated_user()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=LocationNotFoundError("Not found"),
        ),
        patch("app.create_ride_request") as mock_create,
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 400
    response_text = unescape(response.get_data(as_text=True)).lower()
    assert "couldn't find one of those locations" in response_text
    mock_create.assert_not_called()


def test_find_ride_post_handles_geocoding_service_failure(client):
    user = mock_authenticated_user()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=GeocodingError("Service unavailable"),
        ),
        patch("app.create_ride_request") as mock_create,
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 503
    assert b"temporarily unavailable" in response.data
    mock_create.assert_not_called()


def test_find_ride_post_handles_database_failure(client):
    user = mock_authenticated_user()
    locations = mock_geocoding_results()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=locations,
        ),
        patch(
            "app.create_ride_request",
            side_effect=Exception("Database failure"),
        ),
    ):
        response = client.post(
            "/find-ride",
            data=valid_journey_data(),
        )

    assert response.status_code == 500
    response_text = unescape(response.get_data(as_text=True)).lower()
    assert "couldn't save your journey" in response_text


def test_find_ride_post_rejects_invalid_data_before_authentication(client):
    journey = valid_journey_data()
    journey["passengers"] = "10"

    with patch("app.get_authenticated_clerk_user_id") as mock_auth:
        response = client.post(
            "/find-ride",
            data=journey,
        )

    assert response.status_code == 400
    assert b"Please select a valid passenger count." in response.data
    mock_auth.assert_not_called()


# ---------------------------------------------------------------------------
# Driver ride-offer route tests
# ---------------------------------------------------------------------------

def valid_ride_offer_data():
    return {
        "origin": "Edinburgh Waverley",
        "destination": "Edinburgh Napier University",
        "travel_date": (
            date.today() + timedelta(days=1)
        ).isoformat(),
        "departure_time": "09:30",
        "available_seats": "3",
        "max_detour": "15",
    }


def test_offer_ride_page_loads(client):
    response = client.get("/offer-ride")

    assert response.status_code == 200
    assert b"Create a ride offer" in response.data
    assert b"Publish ride offer" in response.data


def test_offer_ride_post_requires_sign_in(client):
    with patch(
        "app.get_authenticated_clerk_user_id",
        return_value=None,
    ) as mock_auth:
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 401
    mock_auth.assert_called_once()


def test_offer_ride_post_rejects_authentication_failure(client):
    with patch(
        "app.get_authenticated_clerk_user_id",
        side_effect=Exception("Authentication failure"),
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 401


def test_offer_ride_post_requires_existing_profile(client):
    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=None,
        ),
        patch("app.geocode_address") as mock_geocode,
        patch("app.create_ride_offer") as mock_create,
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 403
    mock_geocode.assert_not_called()
    mock_create.assert_not_called()


def test_offer_ride_post_rejects_inactive_account(client):
    inactive_user = mock_authenticated_user()
    inactive_user["account_status"] = "suspended"

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=inactive_user,
        ),
        patch("app.geocode_address") as mock_geocode,
        patch("app.create_ride_offer") as mock_create,
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 403
    mock_geocode.assert_not_called()
    mock_create.assert_not_called()


def test_offer_ride_post_allows_pending_verification(client):
    user = mock_authenticated_user()
    assert user["verification_status"] == "pending"

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=mock_geocoding_results(),
        ),
        patch(
            "app.create_ride_offer",
            return_value=202,
        ) as mock_create,
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 201
    assert b"Ride offer confirmed!" in response.data
    assert b"Ride offer #202 saved successfully." in response.data

    mock_create.assert_called_once_with(
        driver_id=42,
        origin="Edinburgh Waverley",
        destination="Edinburgh Napier University",
        origin_latitude=55.9521,
        origin_longitude=-3.1889,
        destination_latitude=55.9225,
        destination_longitude=-3.1722,
        travel_date=(
            date.today() + timedelta(days=1)
        ).isoformat(),
        departure_time="09:30",
        available_seats=3,
        max_detour_minutes=15,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("origin", ""),
        ("destination", ""),
        ("travel_date", "2020-01-01"),
        ("travel_date", "not-a-date"),
        ("departure_time", "25:90"),
        ("available_seats", "0"),
        ("available_seats", "6"),
        ("max_detour", "7"),
    ],
)
def test_offer_ride_post_rejects_invalid_data_before_authentication(
    client,
    field,
    value,
):
    offer = valid_ride_offer_data()
    offer[field] = value

    with patch("app.get_authenticated_clerk_user_id") as mock_auth:
        response = client.post(
            "/offer-ride",
            data=offer,
        )

    assert response.status_code == 400
    mock_auth.assert_not_called()


def test_offer_ride_post_handles_unknown_location(client):
    user = mock_authenticated_user()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=LocationNotFoundError("Not found"),
        ),
        patch("app.create_ride_offer") as mock_create,
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 400
    mock_create.assert_not_called()


def test_offer_ride_post_handles_geocoding_service_failure(client):
    user = mock_authenticated_user()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=GeocodingError("Service unavailable"),
        ),
        patch("app.create_ride_offer") as mock_create,
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 503
    mock_create.assert_not_called()


def test_offer_ride_post_handles_database_failure(client):
    user = mock_authenticated_user()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_user_by_clerk_id",
            return_value=user,
        ),
        patch(
            "app.geocode_address",
            side_effect=mock_geocoding_results(),
        ),
        patch(
            "app.create_ride_offer",
            side_effect=Exception("Database failure"),
        ),
    ):
        response = client.post(
            "/offer-ride",
            data=valid_ride_offer_data(),
        )

    assert response.status_code == 500
