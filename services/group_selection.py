
from itertools import combinations
from typing import Any, Callable

from services.group_optimisation import MAX_GROUP_REQUESTS
from services.group_route_optimiser import optimise_group_route
from services.route_verification import get_driving_duration_matrix


MAX_CANDIDATES = 10


def select_best_passenger_group(
    offer: dict[str, Any],
    requests: list[dict[str, Any]],
    *,
    route_duration_fn: Callable | None = None,
    duration_matrix_fn: Callable | None = None,
) -> dict[str, Any] | None:
    """
    Find the best feasible passenger group for a driver.

    Priorities:
    1. Maximise the number of passengers transported.
    2. Minimise additional driving time.
    3. Minimise total shared journey duration.

    A single driving duration matrix is reused across all candidate
    combinations to avoid repeated OSRM Table API requests.

    Returns the best group and its route, or None if no feasible
    combination exists.
    """

    if not isinstance(requests, list):
        raise ValueError("Passenger requests must be supplied as a list.")

    if not requests:
        return None

    if len(requests) > MAX_CANDIDATES:
        raise ValueError(
            f"Group selection supports up to {MAX_CANDIDATES} candidates."
        )

    try:
        available_seats = int(offer["available_seats"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Invalid driver seat capacity.") from None

    if available_seats < 1:
        raise ValueError("Invalid driver seat capacity.")

    # Validate each candidate before generating combinations.
    candidate_ids = set()

    for passenger in requests:
        try:
            request_id = passenger["id"]
            passenger_count = int(passenger["passenger_count"])

            if request_id is None or isinstance(request_id, bool):
                raise ValueError

            if request_id in candidate_ids:
                raise ValueError

            if passenger_count < 1:
                raise ValueError

            candidate_ids.add(request_id)

        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "A passenger candidate contains invalid data."
            ) from None

    # ---------------------------------------------------------
    # Shared duration matrix
    # ---------------------------------------------------------

    shared_matrix_provider = None

    if route_duration_fn is None:
        matrix_source = (
            duration_matrix_fn or get_driving_duration_matrix
        )

        cached_matrix = None
        coordinate_indexes = None

        def shared_matrix_provider(coordinates):
            """
            Retrieve the complete duration matrix once.

            Later calls receive only the relevant submatrix for
            their passenger combination.
            """
            nonlocal cached_matrix, coordinate_indexes

            if cached_matrix is None:
                origin = (
                    float(offer["origin_latitude"]),
                    float(offer["origin_longitude"]),
                )

                destination = (
                    float(offer["destination_latitude"]),
                    float(offer["destination_longitude"]),
                )

                all_coordinates = [origin, destination]

                for passenger in requests:
                    all_coordinates.extend([
                        (
                            float(passenger["origin_latitude"]),
                            float(passenger["origin_longitude"]),
                        ),
                        (
                            float(passenger["destination_latitude"]),
                            float(passenger["destination_longitude"]),
                        ),
                    ])

                # Remove duplicates while preserving coordinate order.
                unique_coordinates = list(
                    dict.fromkeys(all_coordinates)
                )

                coordinate_indexes = {
                    coordinate: index
                    for index, coordinate in enumerate(unique_coordinates)
                }

                # The only external matrix request for this selection.
                cached_matrix = matrix_source(unique_coordinates)

                expected_size = len(unique_coordinates)

                if (
                    not isinstance(cached_matrix, (list, tuple))
                    or len(cached_matrix) != expected_size
                    or any(
                        not isinstance(row, (list, tuple))
                        or len(row) != expected_size
                        for row in cached_matrix
                    )
                ):
                    raise ValueError(
                        "Invalid driving duration matrix."
                    )

            # Extract only the coordinates needed by this combination.
            try:
                indexes = [
                    coordinate_indexes[
                        (float(latitude), float(longitude))
                    ]
                    for latitude, longitude in coordinates
                ]
            except (KeyError, TypeError, ValueError):
                raise ValueError(
                    "Invalid coordinates in candidate group."
                ) from None

            return [
                [
                    cached_matrix[row][column]
                    for column in indexes
                ]
                for row in indexes
            ]

    # ---------------------------------------------------------
    # Evaluate candidate groups
    # ---------------------------------------------------------

    feasible_groups = []

    # Never evaluate groups larger than the optimiser supports.
    maximum_group_size = min(
        len(requests),
        MAX_GROUP_REQUESTS,
    )

    # Larger groups are considered first.
    for group_size in range(maximum_group_size, 0, -1):
        for group in combinations(requests, group_size):

            total_passengers = sum(
                int(passenger["passenger_count"])
                for passenger in group
            )

            if total_passengers > available_seats:
                continue

            # Reuse the shared matrix provider for every combination.
            routes = optimise_group_route(
                offer,
                list(group),
                route_duration_fn=route_duration_fn,
                duration_matrix_fn=shared_matrix_provider,
            )

            if not routes:
                continue

            best_route = routes[0]

            feasible_groups.append({
                "request_ids": best_route["request_ids"],
                "passenger_count": total_passengers,
                "group_size": group_size,
                "original_duration_minutes": (
                    best_route["original_duration_minutes"]
                ),
                "shared_duration_minutes": (
                    best_route["shared_duration_minutes"]
                ),
                "additional_travel_time_minutes": (
                    best_route["additional_travel_time_minutes"]
                ),
                "maximum_detour_minutes": (
                    best_route["maximum_detour_minutes"]
                ),
                "route_stops": best_route["route_stops"],
                "stop_sequence": best_route["stop_sequence"],
                "status": "selected_group",
            })

    if not feasible_groups:
        return None

    # Prefer more actual passengers, then less additional travel time.
    feasible_groups.sort(
        key=lambda group: (
            -group["passenger_count"],
            group["additional_travel_time_minutes"],
            group["shared_duration_minutes"],
            tuple(group["request_ids"]),
        )
    )

    return feasible_groups[0]
