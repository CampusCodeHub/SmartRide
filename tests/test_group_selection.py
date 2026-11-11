
import pytest

from services.group_selection import select_best_passenger_group


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


def make_request(request_id, passenger_count=1):
    return {
        "id": request_id,
        "passenger_count": passenger_count,
        "origin_latitude": 55.9400,
        "origin_longitude": -3.1830,
        "destination_latitude": 55.9300,
        "destination_longitude": -3.1770,
    }


def fake_router(coordinates):
    return 600 if len(coordinates) == 2 else 660


def make_duration_matrix(coordinates):
    """Create a predictable duration matrix for testing."""
    size = len(coordinates)

    return [
        [
            0.0 if row == column else 220.0
            for column in range(size)
        ]
        for row in range(size)
    ]


# ---------------------------------------------------------
# Existing group-selection tests
# ---------------------------------------------------------

def test_selects_group_with_most_passengers():
    requests = [
        make_request(101, 1),
        make_request(102, 2),
        make_request(103, 2),
    ]

    result = select_best_passenger_group(
        make_offer(),
        requests,
        route_duration_fn=fake_router,
    )

    assert result is not None
    assert result["passenger_count"] == 3
    assert set(result["request_ids"]) == {101, 102}


def test_prefers_lower_detour_when_passenger_count_is_equal():
    call_count = 0

    def variable_router(coordinates):
        nonlocal call_count
        call_count += 1

        if len(coordinates) == 2:
            return 600

        return 630 if call_count % 2 == 0 else 660

    result = select_best_passenger_group(
        make_offer(available_seats=2),
        [
            make_request(101, 1),
            make_request(102, 1),
        ],
        route_duration_fn=variable_router,
    )

    assert result is not None
    assert result["passenger_count"] == 2


def test_returns_none_when_no_group_fits():
    result = select_best_passenger_group(
        make_offer(available_seats=1),
        [
            make_request(101, 2),
            make_request(102, 2),
        ],
        route_duration_fn=fake_router,
    )

    assert result is None


def test_returns_none_for_empty_requests():
    result = select_best_passenger_group(
        make_offer(),
        [],
        route_duration_fn=fake_router,
    )

    assert result is None


def test_rejects_duplicate_request_ids():
    with pytest.raises(ValueError, match="invalid data"):
        select_best_passenger_group(
            make_offer(),
            [
                make_request(101),
                make_request(101),
            ],
            route_duration_fn=fake_router,
        )


def test_rejects_too_many_candidates():
    requests = [
        make_request(request_id)
        for request_id in range(101, 112)
    ]

    with pytest.raises(ValueError, match="up to 10"):
        select_best_passenger_group(
            make_offer(),
            requests,
            route_duration_fn=fake_router,
        )


def test_returns_selected_group_status():
    result = select_best_passenger_group(
        make_offer(),
        [make_request(101)],
        route_duration_fn=fake_router,
    )

    assert result["status"] == "selected_group"


def test_rejects_invalid_seat_capacity():
    with pytest.raises(ValueError, match="seat capacity"):
        select_best_passenger_group(
            make_offer(available_seats=0),
            [make_request(101)],
            route_duration_fn=fake_router,
        )


# ---------------------------------------------------------
# New shared duration matrix tests
# ---------------------------------------------------------

def test_uses_only_one_matrix_request_for_all_combinations():
    matrix_calls = []

    def fake_matrix(coordinates):
        matrix_calls.append(coordinates)
        return make_duration_matrix(coordinates)

    requests = [
        make_request(101, 1),
        make_request(102, 1),
        make_request(103, 1),
    ]

    result = select_best_passenger_group(
        make_offer(),
        requests,
        duration_matrix_fn=fake_matrix,
    )

    assert result is not None
    assert result["passenger_count"] == 3

    # All candidate combinations must reuse one matrix request.
    assert len(matrix_calls) == 1


def test_shared_matrix_removes_duplicate_coordinates():
    matrix_calls = []

    def fake_matrix(coordinates):
        matrix_calls.append(coordinates)
        return make_duration_matrix(coordinates)

    result = select_best_passenger_group(
        make_offer(),
        [
            make_request(101),
            make_request(102),
        ],
        duration_matrix_fn=fake_matrix,
    )

    assert result is not None
    assert len(matrix_calls) == 1

    # Driver and passenger coordinates are identical across
    # the two passenger requests, so only four unique locations
    # should be sent to the matrix provider.
    assert len(matrix_calls[0]) == 4


def test_shared_matrix_selects_feasible_group():
    def fake_matrix(coordinates):
        return make_duration_matrix(coordinates)

    result = select_best_passenger_group(
        make_offer(available_seats=2),
        [
            make_request(101),
            make_request(102),
        ],
        duration_matrix_fn=fake_matrix,
    )

    assert result is not None
    assert result["status"] == "selected_group"
    assert result["passenger_count"] == 2
    assert set(result["request_ids"]) == {101, 102}


def test_rejects_invalid_shared_matrix_dimensions():
    def fake_matrix(coordinates):
        return [[0.0, 100.0]]

    with pytest.raises(
        ValueError,
        match="Invalid driving duration matrix",
    ):
        select_best_passenger_group(
            make_offer(),
            [
                make_request(101),
                make_request(102),
            ],
            duration_matrix_fn=fake_matrix,
        )
