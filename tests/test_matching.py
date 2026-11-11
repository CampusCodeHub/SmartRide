from datetime import date, timedelta

import pytest

from services.matching import evaluate_ride_offer, haversine_km


def make_offer(**overrides):
    record = {
        "id": 10,
        "driver_id": 7,
        "origin_latitude": 55.9500,
        "origin_longitude": -3.1900,
        "destination_latitude": 55.9200,
        "destination_longitude": -3.1700,
        "travel_date": date.today() + timedelta(days=2),
        "departure_time": "09:00:00",
        "available_seats": 3,
        "max_detour_minutes": 15,
        "status": "open",
    }
    record.update(overrides)
    return record


def make_request(**overrides):
    record = {
        "id": 101,
        "passenger_id": 22,
        "origin_latitude": 55.9400,
        "origin_longitude": -3.1830,
        "destination_latitude": 55.9300,
        "destination_longitude": -3.1770,
        "travel_date": date.today() + timedelta(days=2),
        "departure_time": "09:10:00",
        "passenger_count": 2,
        "max_detour_minutes": 10,
        "status": "open",
    }
    record.update(overrides)
    return record


def test_haversine_distance_is_zero_for_same_point():
    assert haversine_km(55.95, -3.19, 55.95, -3.19) == pytest.approx(0)


def test_haversine_distance_is_symmetric():
    forward = haversine_km(55.95, -3.19, 55.92, -3.17)
    reverse = haversine_km(55.92, -3.17, 55.95, -3.19)
    assert forward == pytest.approx(reverse)


def test_finds_compatible_request():
    matches = evaluate_ride_offer(make_offer(), [make_request()])

    assert len(matches) == 1
    assert matches[0]["request_id"] == 101
    assert matches[0]["status"] == "potential_match"
    assert matches[0]["requires_road_route_verification"] is True


def test_rejects_request_on_different_date():
    request = make_request(travel_date=date.today() + timedelta(days=3))
    assert evaluate_ride_offer(make_offer(), [request]) == []


def test_rejects_request_with_insufficient_seats():
    request = make_request(passenger_count=4)
    assert evaluate_ride_offer(make_offer(), [request]) == []


def test_rejects_request_outside_departure_window():
    request = make_request(departure_time="11:00:00")
    assert evaluate_ride_offer(make_offer(), [request]) == []


def test_rejects_closed_offer():
    assert evaluate_ride_offer(
        make_offer(status="closed"),
        [make_request()],
    ) == []


def test_rejects_closed_request():
    assert evaluate_ride_offer(
        make_offer(),
        [make_request(status="cancelled")],
    ) == []


def test_rejects_pickup_far_from_route():
    request = make_request(origin_latitude=56.10, origin_longitude=-3.19)
    assert evaluate_ride_offer(make_offer(), [request]) == []


def test_rejects_dropoff_before_pickup():
    request = make_request(
        origin_latitude=55.9250,
        origin_longitude=-3.1750,
        destination_latitude=55.9450,
        destination_longitude=-3.1850,
    )
    assert evaluate_ride_offer(make_offer(), [request]) == []


def test_ranks_closer_match_ahead_of_less_close_match():
    closer = make_request(id=201)
    less_close = make_request(
        id=202,
        origin_latitude=55.9390,
        origin_longitude=-3.1820,
        destination_latitude=55.9290,
        destination_longitude=-3.1760,
        departure_time="09:25:00",
    )

    matches = evaluate_ride_offer(make_offer(), [less_close, closer])

    assert len(matches) == 2
    assert matches[0]["request_id"] == 201


def test_skips_malformed_request_without_failing_other_matches():
    malformed = {"id": 999, "status": "open"}
    matches = evaluate_ride_offer(
        make_offer(),
        [malformed, make_request()],
    )
    assert [item["request_id"] for item in matches] == [101]


def test_rejects_non_positive_screening_radius():
    with pytest.raises(ValueError, match="radii must be positive"):
        evaluate_ride_offer(
            make_offer(),
            [make_request()],
            pickup_radius_km=0,
        )
