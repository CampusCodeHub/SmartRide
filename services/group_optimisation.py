
from itertools import count
from math import isfinite
from typing import Any


MAX_GROUP_REQUESTS = 4


class GroupOptimisationError(Exception):
    """Raised when group optimisation cannot be completed."""


def _validate_coordinate(latitude: Any, longitude: Any) -> tuple[float, float]:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Invalid passenger location coordinates.") from None

    if (
        not isfinite(lat)
        or not isfinite(lon)
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        raise ValueError("Invalid passenger location coordinates.")

    return lat, lon


def _prepare_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(requests, list):
        raise ValueError("Requests must be supplied as a list.")

    if not requests:
        return []

    if len(requests) > MAX_GROUP_REQUESTS:
        raise GroupOptimisationError(
            f"Group optimisation currently supports up to "
            f"{MAX_GROUP_REQUESTS} passenger requests."
        )

    prepared = []
    seen_ids = set()

    for request in requests:
        try:
            request_id = request["id"]
            passenger_count = int(request["passenger_count"])

            pickup_lat, pickup_lon = _validate_coordinate(
                request["origin_latitude"],
                request["origin_longitude"],
            )

            dropoff_lat, dropoff_lon = _validate_coordinate(
                request["destination_latitude"],
                request["destination_longitude"],
            )

        except ValueError as error:
            if "coordinates" in str(error).lower():
                raise

            raise ValueError(
                "A passenger request contains missing or invalid data."
            ) from None

        except (KeyError, TypeError):
            raise ValueError(
                "A passenger request contains missing or invalid data."
                ) from None

        if isinstance(request_id, bool) or request_id is None:
            raise ValueError("Every passenger request needs a valid ID.")

        if request_id in seen_ids:
            raise ValueError("Duplicate passenger request IDs are not allowed.")

        if passenger_count < 1:
            raise ValueError("Passenger count must be at least one.")

        seen_ids.add(request_id)

        prepared.append({
            "request_id": request_id,
            "passenger_count": passenger_count,
            "pickup": {
                "latitude": pickup_lat,
                "longitude": pickup_lon,
                "address": request.get("origin_address"),
            },
            "dropoff": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lon,
                "address": request.get("destination_address"),
            },
        })

    return prepared


def generate_feasible_stop_sequences(
    available_seats: int,
    requests: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """
    Generate every feasible pickup/drop-off ordering for a passenger group.

    A request's drop-off can only occur after its pickup.
    Passenger occupancy cannot exceed available seats.
    """
    if (
        isinstance(available_seats, bool)
        or not isinstance(available_seats, int)
        or available_seats < 1
    ):
        raise ValueError("Available seats must be a positive integer.")

    passengers = _prepare_requests(requests)

    if not passengers:
        return []

    total_passengers = sum(
        passenger["passenger_count"] for passenger in passengers
    )

    if total_passengers > available_seats:
        return []

    sequences = []

    # Track which passengers have been picked up and dropped off.
    picked_up = set()
    dropped_off = set()
    current_sequence = []

    def search(occupied_seats: int) -> None:
        if len(dropped_off) == len(passengers):
            sequences.append(list(current_sequence))
            return

        for passenger in passengers:
            request_id = passenger["request_id"]
            passenger_count = passenger["passenger_count"]

            # Option 1: Pick up this passenger.
            if (
                request_id not in picked_up
                and occupied_seats + passenger_count <= available_seats
            ):
                picked_up.add(request_id)

                current_sequence.append({
                    "request_id": request_id,
                    "action": "pickup",
                    "passenger_count": passenger_count,
                    "latitude": passenger["pickup"]["latitude"],
                    "longitude": passenger["pickup"]["longitude"],
                    "address": passenger["pickup"]["address"],
                })

                search(occupied_seats + passenger_count)

                current_sequence.pop()
                picked_up.remove(request_id)

            # Option 2: Drop off a passenger already onboard.
            if (
                request_id in picked_up
                and request_id not in dropped_off
            ):
                dropped_off.add(request_id)

                current_sequence.append({
                    "request_id": request_id,
                    "action": "dropoff",
                    "passenger_count": passenger_count,
                    "latitude": passenger["dropoff"]["latitude"],
                    "longitude": passenger["dropoff"]["longitude"],
                    "address": passenger["dropoff"]["address"],
                })

                search(occupied_seats - passenger_count)

                current_sequence.pop()
                dropped_off.remove(request_id)

    search(0)

    return sequences


def build_group_route(
    offer: dict[str, Any],
    stop_sequence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add the driver's origin and destination around passenger stops."""

    try:
        origin_lat, origin_lon = _validate_coordinate(
            offer["origin_latitude"],
            offer["origin_longitude"],
        )

        destination_lat, destination_lon = _validate_coordinate(
            offer["destination_latitude"],
            offer["destination_longitude"],
        )

    except (KeyError, TypeError, ValueError):
        raise ValueError("Driver journey coordinates are invalid.") from None

    route = [{
        "action": "driver_origin",
        "latitude": origin_lat,
        "longitude": origin_lon,
        "address": offer.get("origin_address"),
    }]

    route.extend(stop_sequence)

    route.append({
        "action": "driver_destination",
        "latitude": destination_lat,
        "longitude": destination_lon,
        "address": offer.get("destination_address"),
    })

    return route
