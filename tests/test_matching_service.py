
from datetime import date, time

from services import matching_service


def sample_offer():
    return {
        "id": 1,
        "driver_id": 10,
        "origin_latitude": 55.9500,
        "origin_longitude": -3.2000,
        "destination_latitude": 55.9000,
        "destination_longitude": -3.1000,
        "travel_date": date(2026, 11, 15),
        "departure_time": time(9, 0),
        "available_seats": 3,
        "max_detour_minutes": 10,
        "status": "open",
    }


def sample_request():
    return {
        "id": 20,
        "passenger_id": 25,
        "origin_latitude": 55.9400,
        "origin_longitude": -3.1800,
        "destination_latitude": 55.9100,
        "destination_longitude": -3.1200,
        "travel_date": date(2026, 11, 15),
        "departure_time": time(9, 10),
        "passenger_count": 1,
        "max_detour_minutes": 10,
        "status": "open",
    }


def test_returns_empty_when_offer_does_not_exist(monkeypatch):
    monkeypatch.setattr(
        matching_service,
        "get_ride_offer_for_matching",
        lambda offer_id, driver_id: None,
    )

    def unexpected_request_lookup(**kwargs):
        raise AssertionError("Requests should not be retrieved.")

    monkeypatch.setattr(
        matching_service,
        "get_open_ride_requests_for_matching",
        unexpected_request_lookup,
    )

    result = matching_service.find_matches_for_offer(1, 10)

    assert result == []


def test_retrieves_offer_and_requests(monkeypatch):
    offer = sample_offer()
    requests = [sample_request()]
    calls = {}

    def fake_get_offer(offer_id, driver_id):
        calls["offer"] = (offer_id, driver_id)
        return offer

    def fake_get_requests(travel_date, exclude_passenger_id):
        calls["requests"] = (travel_date, exclude_passenger_id)
        return requests

    monkeypatch.setattr(
        matching_service,
        "get_ride_offer_for_matching",
        fake_get_offer,
    )

    monkeypatch.setattr(
        matching_service,
        "get_open_ride_requests_for_matching",
        fake_get_requests,
    )

    result = matching_service.find_matches_for_offer(1, 10)

    assert calls["offer"] == (1, 10)
    assert calls["requests"] == (date(2026, 11, 15), 10)
    assert len(result) == 1
    assert result[0]["request_id"] == 20


def test_passes_matching_settings(monkeypatch):
    monkeypatch.setattr(
        matching_service,
        "get_ride_offer_for_matching",
        lambda offer_id, driver_id: sample_offer(),
    )

    monkeypatch.setattr(
        matching_service,
        "get_open_ride_requests_for_matching",
        lambda **kwargs: [sample_request()],
    )

    result = matching_service.find_matches_for_offer(
        1,
        10,
        pickup_radius_km=3.0,
        dropoff_radius_km=3.0,
        departure_window_minutes=30,
    )

    assert len(result) == 1


def test_returns_empty_when_no_requests_exist(monkeypatch):
    monkeypatch.setattr(
        matching_service,
        "get_ride_offer_for_matching",
        lambda offer_id, driver_id: sample_offer(),
    )

    monkeypatch.setattr(
        matching_service,
        "get_open_ride_requests_for_matching",
        lambda **kwargs: [],
    )

    result = matching_service.find_matches_for_offer(1, 10)

    assert result == []
