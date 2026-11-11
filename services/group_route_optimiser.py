
from math import isfinite
from typing import Any, Callable

from services.group_optimisation import (
    build_group_route,
    generate_feasible_stop_sequences,
)
from services.route_verification import get_driving_duration_matrix


def optimise_group_route(
    offer: dict[str, Any],
    requests: list[dict[str, Any]],
    *,
    route_duration_fn: Callable | None = None,
    duration_matrix_fn: Callable | None = None,
) -> list[dict[str, Any]]:
    """
    Evaluate feasible passenger group sequences using driving durations.

    A route must satisfy:
    1. The driver's maximum additional travel time.
    2. Every passenger's individual maximum additional travel time.

    Production uses an OSRM Table API duration matrix.

    route_duration_fn preserves compatibility with existing tests
    and callers that inject a route-duration function.

    duration_matrix_fn allows matrix calculations to be tested
    without network access.
    """

    if not requests:
        return []

    # ---------------------------------------------------------
    # Validate driver settings
    # ---------------------------------------------------------

    try:
        maximum_detour = float(offer["max_detour_minutes"])
        available_seats = int(offer["available_seats"])

        if (
            not isfinite(maximum_detour)
            or maximum_detour < 0
            or available_seats < 1
        ):
            raise ValueError

    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "Invalid driver capacity or detour allowance."
        ) from None

    # ---------------------------------------------------------
    # Validate passenger detour settings
    # ---------------------------------------------------------

    passenger_detour_limits = {}

    for request in requests:
        try:
            request_id = request["id"]

            # Backward-compatible fallback for older requests.
            passenger_limit = float(
                request.get("max_detour_minutes", maximum_detour)
            )

            if (
                not isfinite(passenger_limit)
                or passenger_limit < 0
            ):
                raise ValueError

            passenger_detour_limits[request_id] = passenger_limit

        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "A passenger has an invalid detour allowance."
            ) from None

    # ---------------------------------------------------------
    # Generate feasible pickup/drop-off sequences
    # ---------------------------------------------------------

    sequences = generate_feasible_stop_sequences(
        available_seats,
        requests,
    )

    if not sequences:
        return []

    origin = (
        float(offer["origin_latitude"]),
        float(offer["origin_longitude"]),
    )

    destination = (
        float(offer["destination_latitude"]),
        float(offer["destination_longitude"]),
    )

    feasible_routes = []

    # ---------------------------------------------------------
    # Prepare route duration calculation
    # ---------------------------------------------------------

    if route_duration_fn is not None:

        # Backward-compatible route function.
        original_duration_seconds = route_duration_fn([
            origin,
            destination,
        ])

        if (
            original_duration_seconds is None
            or original_duration_seconds <= 0
        ):
            raise ValueError(
                "Original journey duration must be positive."
            )

        def calculate_route_duration(coordinates):
            return route_duration_fn(coordinates)

    else:

        if duration_matrix_fn is None:
            duration_matrix_fn = get_driving_duration_matrix

        # Collect every location used by the driver and passengers.
        all_coordinates = [origin, destination]

        for request in requests:
            all_coordinates.extend([
                (
                    float(request["origin_latitude"]),
                    float(request["origin_longitude"]),
                ),
                (
                    float(request["destination_latitude"]),
                    float(request["destination_longitude"]),
                ),
            ])

        # Remove duplicates while preserving coordinate order.
        unique_coordinates = list(dict.fromkeys(all_coordinates))

        coordinate_indexes = {
            coordinate: index
            for index, coordinate in enumerate(unique_coordinates)
        }

        # Request the driving duration matrix.
        duration_matrix = duration_matrix_fn(unique_coordinates)

        expected_size = len(unique_coordinates)

        if (
            not isinstance(duration_matrix, (list, tuple))
            or len(duration_matrix) != expected_size
        ):
            raise ValueError("Invalid driving duration matrix.")

        for row in duration_matrix:
            if (
                not isinstance(row, (list, tuple))
                or len(row) != expected_size
            ):
                raise ValueError("Invalid driving duration matrix.")

        origin_index = coordinate_indexes[origin]
        destination_index = coordinate_indexes[destination]

        original_duration_seconds = duration_matrix[
            origin_index
        ][destination_index]

        if (
            original_duration_seconds is None
            or original_duration_seconds <= 0
        ):
            raise ValueError(
                "Original journey duration must be positive."
            )

        def calculate_route_duration(coordinates):
            """Calculate journey duration using matrix entries."""

            total_seconds = 0.0

            for index in range(len(coordinates) - 1):
                start = coordinates[index]
                end = coordinates[index + 1]

                start_index = coordinate_indexes[start]
                end_index = coordinate_indexes[end]

                leg_duration = duration_matrix[
                    start_index
                ][end_index]

                # None represents an unreachable road route.
                if leg_duration is None:
                    return None

                leg_duration = float(leg_duration)

                if (
                    not isfinite(leg_duration)
                    or leg_duration < 0
                ):
                    return None

                total_seconds += leg_duration

            return total_seconds

    # ---------------------------------------------------------
    # Evaluate each possible group route
    # ---------------------------------------------------------

    for sequence in sequences:

        complete_route = build_group_route(
            offer,
            sequence,
        )

        coordinates = [
            (
                float(stop["latitude"]),
                float(stop["longitude"]),
            )
            for stop in complete_route
        ]

        # Calculate the driver's complete shared journey.
        shared_duration_seconds = calculate_route_duration(
            coordinates
        )

        if shared_duration_seconds is None:
            continue

        # Check the driver's maximum detour.
        additional_seconds = max(
            0.0,
            shared_duration_seconds - original_duration_seconds,
        )

        additional_minutes = additional_seconds / 60

        if additional_minutes > maximum_detour:
            continue

        # -----------------------------------------------------
        # Check each passenger's individual journey
        # -----------------------------------------------------

        passenger_detours = []
        passenger_limits_satisfied = True

        for request in requests:

            request_id = request["id"]

            pickup_index = next(
                (
                    index
                    for index, stop in enumerate(complete_route)
                    if (
                        stop.get("request_id") == request_id
                        and stop.get("action") == "pickup"
                    )
                ),
                None,
            )

            dropoff_index = next(
                (
                    index
                    for index, stop in enumerate(complete_route)
                    if (
                        stop.get("request_id") == request_id
                        and stop.get("action") == "dropoff"
                    )
                ),
                None,
            )

            if (
                pickup_index is None
                or dropoff_index is None
                or pickup_index >= dropoff_index
            ):
                passenger_limits_satisfied = False
                break

            passenger_origin = (
                float(request["origin_latitude"]),
                float(request["origin_longitude"]),
            )

            passenger_destination = (
                float(request["destination_latitude"]),
                float(request["destination_longitude"]),
            )

            # Passenger's original journey.
            original_passenger_duration = calculate_route_duration([
                passenger_origin,
                passenger_destination,
            ])

            if (
                original_passenger_duration is None
                or original_passenger_duration <= 0
            ):
                passenger_limits_satisfied = False
                break

            # Only calculate the route between this passenger's
            # own pickup and drop-off positions.
            passenger_shared_coordinates = coordinates[
                pickup_index:dropoff_index + 1
            ]

            shared_passenger_duration = calculate_route_duration(
                passenger_shared_coordinates
            )

            if shared_passenger_duration is None:
                passenger_limits_satisfied = False
                break

            passenger_additional_seconds = max(
                0.0,
                shared_passenger_duration
                - original_passenger_duration,
            )

            passenger_additional_minutes = (
                passenger_additional_seconds / 60
            )

            passenger_maximum_detour = (
                passenger_detour_limits[request_id]
            )

            # Reject the complete group route if even one
            # passenger exceeds their individual detour limit.
            if (
                passenger_additional_minutes
                > passenger_maximum_detour
            ):
                passenger_limits_satisfied = False
                break

            passenger_detours.append({
                "request_id": request_id,
                "original_duration_minutes": round(
                    original_passenger_duration / 60,
                    2,
                ),
                "shared_duration_minutes": round(
                    shared_passenger_duration / 60,
                    2,
                ),
                "additional_travel_time_minutes": round(
                    passenger_additional_minutes,
                    2,
                ),
                "maximum_detour_minutes": (
                    passenger_maximum_detour
                ),
                "detour_within_limit": True,
            })

        if not passenger_limits_satisfied:
            continue

        # -----------------------------------------------------
        # Build feasible group result
        # -----------------------------------------------------

        request_ids = list(dict.fromkeys(
            stop["request_id"]
            for stop in sequence
        ))

        total_passengers = sum(
            request["passenger_count"]
            for request in requests
            if request["id"] in request_ids
        )

        feasible_routes.append({
            "request_ids": request_ids,
            "passenger_count": total_passengers,

            "original_duration_minutes": round(
                original_duration_seconds / 60,
                2,
            ),

            "shared_duration_minutes": round(
                shared_duration_seconds / 60,
                2,
            ),

            "additional_travel_time_minutes": round(
                additional_minutes,
                2,
            ),

            "maximum_detour_minutes": maximum_detour,
            "detour_within_limit": True,

            "passenger_detours": passenger_detours,
            "passenger_detours_within_limits": True,

            "route_stops": complete_route,
            "stop_sequence": sequence,
            "status": "feasible_group",
        })

    # ---------------------------------------------------------
    # Rank feasible routes
    # ---------------------------------------------------------

    return sorted(
        feasible_routes,
        key=lambda route: (
            route["additional_travel_time_minutes"],
            route["shared_duration_minutes"],
            tuple(route["request_ids"]),
        ),
    )
