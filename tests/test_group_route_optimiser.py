
import pytest

from services.group_route_optimiser import optimise_group_route


def make_offer(**overrides):
    offer = {
        "origin_latitude": 55.9500,
        "origin_longitude": -3.1900,
        "destination_latitude": 55.9200,
        "destination_longitude": -3.1700,
        "available_seats": 3,
        "max_detour_minutes": 10,
    }
    offer.update(overrides)
    return offer


def make_request(request_id, **overrides):
    request = {
        "id": request_id,
        "passenger_count": 1,
        "origin_latitude": 55.9400,
        "origin_longitude": -3.1830,
        "destination_latitude": 55.9300,
        "destination_longitude": -3.1770,
    }
    request.update(overrides)
    return request


# ---------------------------------------------------------
# Existing route-duration tests
# ---------------------------------------------------------

def test_finds_feasible_group_route():
    def fake_router(coordinates):
        return 600 if len(coordinates) == 2 else 660

    results = optimise_group_route(
        make_offer(),
        [make_request(101)],
        route_duration_fn=fake_router,
    )

    assert len(results) == 1
    assert results[0]["request_ids"] == [101]
    assert results[0]["passenger_count"] == 1
    assert results[0]["additional_travel_time_minutes"] == 1.0


def test_rejects_route_exceeding_detour_limit():
    def fake_router(coordinates):
        return 600 if len(coordinates) == 2 else 1300

    results = optimise_group_route(
        make_offer(max_detour_minutes=10),
        [make_request(101)],
        route_duration_fn=fake_router,
    )

    assert results == []


def test_ranks_shorter_detour_first():
    route_calls = 0

    def fake_router(coordinates):
        nonlocal route_calls
        route_calls += 1

        if len(coordinates) == 2:
            return 600

        return 660 + (route_calls * 30)

    results = optimise_group_route(
        make_offer(),
        [
            make_request(101),
            make_request(102),
        ],
        route_duration_fn=fake_router,
    )

    assert len(results) > 1

    durations = [
        route["additional_travel_time_minutes"]
        for route in results
    ]

    assert durations == sorted(durations)


def test_returns_empty_when_group_exceeds_capacity():
    results = optimise_group_route(
        make_offer(available_seats=1),
        [
            make_request(101),
            make_request(102),
        ],
        route_duration_fn=lambda coordinates: 600,
    )

    assert results == []


def test_returns_empty_without_requests():
    results = optimise_group_route(
        make_offer(),
        [],
        route_duration_fn=lambda coordinates: 600,
    )

    assert results == []


def test_calculates_original_and_shared_durations():
    def fake_router(coordinates):
        return 600 if len(coordinates) == 2 else 720

    results = optimise_group_route(
        make_offer(),
        [make_request(101)],
        route_duration_fn=fake_router,
    )

    assert results[0]["original_duration_minutes"] == 10.0
    assert results[0]["shared_duration_minutes"] == 12.0
    assert results[0]["additional_travel_time_minutes"] == 2.0


# ---------------------------------------------------------
# Matrix-based optimisation tests
# ---------------------------------------------------------

def make_duration_matrix(coordinates):
    """Create a predictable matrix for testing."""
    size = len(coordinates)

    return [
        [
            0.0 if row == column else 220.0
            for column in range(size)
        ]
        for row in range(size)
    ]


def test_uses_only_one_matrix_request_for_multiple_sequences():
    matrix_calls = []

    def fake_matrix(coordinates):
        matrix_calls.append(coordinates)
        return make_duration_matrix(coordinates)

    results = optimise_group_route(
        make_offer(),
        [
            make_request(101),
            make_request(102),
        ],
        duration_matrix_fn=fake_matrix,
    )

    assert len(matrix_calls) == 1
    assert len(matrix_calls[0]) == 4
    assert len(results) > 1


def test_calculates_shared_duration_from_matrix_legs():
    def fake_matrix(coordinates):
        size = len(coordinates)

        matrix = [
            [
                0.0 if row == column else 240.0
                for column in range(size)
            ]
            for row in range(size)
        ]

        # Coordinate order:
        # 0 = driver origin
        # 1 = driver destination
        # 2 = passenger pickup
        # 3 = passenger drop-off

        matrix[0][1] = 600.0
        matrix[0][2] = 240.0
        matrix[2][3] = 240.0
        matrix[3][1] = 240.0

        return matrix

    results = optimise_group_route(
        make_offer(),
        [make_request(101)],
        duration_matrix_fn=fake_matrix,
    )

    assert len(results) == 1
    assert results[0]["original_duration_minutes"] == 10.0
    assert results[0]["shared_duration_minutes"] == 12.0
    assert results[0]["additional_travel_time_minutes"] == 2.0


def test_rejects_unreachable_route_legs():
    def fake_matrix(coordinates):
        matrix = make_duration_matrix(coordinates)

        # Make the first pickup leg unreachable.
        matrix[0][2] = None

        return matrix

    results = optimise_group_route(
        make_offer(),
        [make_request(101)],
        duration_matrix_fn=fake_matrix,
    )

    assert results == []


def test_rejects_invalid_duration_matrix_dimensions():
    def fake_matrix(coordinates):
        return [[0.0, 100.0]]

    with pytest.raises(ValueError, match="Invalid driving duration matrix"):
        optimise_group_route(
            make_offer(),
            [make_request(101)],
            duration_matrix_fn=fake_matrix,
        )


# ---------------------------------------------------------
# Individual passenger detour tests
# ---------------------------------------------------------

def make_passenger_detour_router(offer):
    """
    Simulate predictable journey durations.

    Driver's original journey: 10 minutes.
    Driver's shared journey: 10 minutes.
    Passenger's original journey: 5 minutes.
    Passenger's journey with another passenger's stop inserted:
    7 minutes.
    """

    driver_origin = (
        offer["origin_latitude"],
        offer["origin_longitude"],
    )

    driver_destination = (
        offer["destination_latitude"],
        offer["destination_longitude"],
    )

    def fake_router(coordinates):

        # Driver's original journey.
        if (
            coordinates[0] == driver_origin
            and coordinates[-1] == driver_destination
            and len(coordinates) == 2
        ):
            return 600

        # Driver's complete shared journey.
        if (
            coordinates[0] == driver_origin
            and coordinates[-1] == driver_destination
        ):
            return 600

        # Passenger's original journey.
        if len(coordinates) == 2:
            return 300

        # Passenger's shared journey with intermediate stops.
        return 420

    return fake_router


def test_passenger_detour_within_individual_limit():
    offer = make_offer()

    result = optimise_group_route(
        offer,
        [
            make_request(
                101,
                max_detour_minutes=5,
            )
        ],
        route_duration_fn=make_passenger_detour_router(offer),
    )

    assert len(result) == 1

    passenger = result[0]["passenger_detours"][0]

    assert passenger["request_id"] == 101
    assert passenger["original_duration_minutes"] == 5.0
    assert passenger["shared_duration_minutes"] == 5.0
    assert passenger["additional_travel_time_minutes"] == 0.0
    assert passenger["maximum_detour_minutes"] == 5.0
    assert passenger["detour_within_limit"] is True


def test_rejects_sequences_exceeding_individual_passenger_limit():
    offer = make_offer()

    requests = [
        make_request(101, max_detour_minutes=0),
        make_request(102, max_detour_minutes=0),
    ]

    results = optimise_group_route(
        offer,
        requests,
        route_duration_fn=make_passenger_detour_router(offer),
    )

    assert results

    # Any route that inserts another passenger's stop between
    # this passenger's pickup and drop-off would add two minutes.
    # Such routes must not appear in the feasible results.
    for route in results:
        assert route["passenger_detours_within_limits"] is True

        for passenger in route["passenger_detours"]:
            assert passenger["additional_travel_time_minutes"] <= (
                passenger["maximum_detour_minutes"]
            )


def test_supports_different_detour_limits_for_passengers():
    offer = make_offer()

    requests = [
        make_request(101, max_detour_minutes=0),
        make_request(102, max_detour_minutes=2),
    ]

    results = optimise_group_route(
        offer,
        requests,
        route_duration_fn=make_passenger_detour_router(offer),
    )

    assert results

    for route in results:
        passenger_limits = {
            passenger["request_id"]: passenger["maximum_detour_minutes"]
            for passenger in route["passenger_detours"]
        }

        assert passenger_limits[101] == 0.0
        assert passenger_limits[102] == 2.0

        for passenger in route["passenger_detours"]:
            assert passenger["detour_within_limit"] is True
            assert passenger["additional_travel_time_minutes"] <= (
                passenger["maximum_detour_minutes"]
            )


@pytest.mark.parametrize(
    "detour_value",
    [-1, "invalid", float("inf"), float("nan")],
)
def test_rejects_invalid_passenger_detour_limits(detour_value):
    with pytest.raises(
        ValueError,
        match="invalid detour allowance",
    ):
        optimise_group_route(
            make_offer(),
            [
                make_request(
                    101,
                    max_detour_minutes=detour_value,
                )
            ],
            route_duration_fn=lambda coordinates: 600,
        )
