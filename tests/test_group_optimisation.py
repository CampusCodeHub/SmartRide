
import pytest

from services.group_optimisation import (
    GroupOptimisationError,
    build_group_route,
    generate_feasible_stop_sequences,
)


def make_offer(**overrides):
    offer = {
        "origin_latitude": 55.9500,
        "origin_longitude": -3.1900,
        "destination_latitude": 55.9200,
        "destination_longitude": -3.1700,
        "origin_address": "Edinburgh Waverley",
        "destination_address": "Edinburgh Napier University",
        "available_seats": 4,
    }
    offer.update(overrides)
    return offer


def make_request(request_id=101, **overrides):
    request = {
        "id": request_id,
        "passenger_count": 1,
        "origin_latitude": 55.9400,
        "origin_longitude": -3.1830,
        "destination_latitude": 55.9300,
        "destination_longitude": -3.1770,
        "origin_address": "Pickup location",
        "destination_address": "Drop-off location",
    }
    request.update(overrides)
    return request


def test_generates_one_sequence_for_one_passenger():
    sequences = generate_feasible_stop_sequences(
        2,
        [make_request()],
    )

    assert len(sequences) == 1

    assert [stop["action"] for stop in sequences[0]] == [
        "pickup",
        "dropoff",
    ]


def test_generates_all_valid_sequences_for_two_passengers():
    sequences = generate_feasible_stop_sequences(
        2,
        [
            make_request(101),
            make_request(102),
        ],
    )

    # Four stops with each pickup before its own drop-off.
    assert len(sequences) == 6


def test_every_passenger_is_picked_up_before_dropoff():
    sequences = generate_feasible_stop_sequences(
        3,
        [
            make_request(101),
            make_request(102),
        ],
    )

    for sequence in sequences:
        for request_id in (101, 102):
            pickup_index = next(
                index
                for index, stop in enumerate(sequence)
                if stop["request_id"] == request_id
                and stop["action"] == "pickup"
            )

            dropoff_index = next(
                index
                for index, stop in enumerate(sequence)
                if stop["request_id"] == request_id
                and stop["action"] == "dropoff"
            )

            assert pickup_index < dropoff_index


def test_never_exceeds_available_seats():
    sequences = generate_feasible_stop_sequences(
        2,
        [
            make_request(101, passenger_count=2),
            make_request(102, passenger_count=1),
        ],
    )

    for sequence in sequences:
        occupied = 0

        for stop in sequence:
            if stop["action"] == "pickup":
                occupied += stop["passenger_count"]
            else:
                occupied -= stop["passenger_count"]

            assert 0 <= occupied <= 2

        assert occupied == 0


def test_rejects_group_exceeding_available_seats():
    sequences = generate_feasible_stop_sequences(
        2,
        [
            make_request(101, passenger_count=2),
            make_request(102, passenger_count=1),
        ],
    )

    assert sequences == []


def test_returns_empty_for_no_requests():
    assert generate_feasible_stop_sequences(3, []) == []


def test_rejects_duplicate_request_ids():
    with pytest.raises(ValueError, match="Duplicate"):
        generate_feasible_stop_sequences(
            3,
            [
                make_request(101),
                make_request(101),
            ],
        )


def test_rejects_invalid_coordinates():
    with pytest.raises(ValueError, match="coordinates"):
        generate_feasible_stop_sequences(
            3,
            [
                make_request(101, origin_latitude=200),
            ],
        )


def test_rejects_more_than_supported_requests():
    requests = [
        make_request(request_id)
        for request_id in range(101, 106)
    ]

    with pytest.raises(GroupOptimisationError, match="up to 4"):
        generate_feasible_stop_sequences(5, requests)


def test_builds_route_with_driver_origin_and_destination():
    offer = make_offer()

    sequence = generate_feasible_stop_sequences(
        2,
        [make_request()],
    )[0]

    route = build_group_route(offer, sequence)

    assert route[0]["action"] == "driver_origin"
    assert route[-1]["action"] == "driver_destination"

    assert route[0]["latitude"] == offer["origin_latitude"]
    assert route[-1]["latitude"] == offer["destination_latitude"]

    assert len(route) == 4
