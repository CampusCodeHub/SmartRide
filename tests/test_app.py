import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


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
            "travel_date": "2026-10-24",
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
            "travel_date": "2026-10-24",
            "departure_time": "12:43",
            "max_detour": "5",
            "passengers": "10",
        },
    )

    assert response.status_code == 400
    assert b"Please select a valid passenger count." in response.data