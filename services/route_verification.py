
import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


OSRM_BASE_URL = "https://router.project-osrm.org"
OSRM_TIMEOUT_SECONDS = 12


class RouteVerificationError(Exception):
    """Raised when a road route cannot be verified."""


def _valid_coordinate(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False

    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _request_osrm_json(url):
    """Send an OSRM request and return its decoded JSON response."""
    request = Request(
        url,
        headers={
            "User-Agent": "SmartRide/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=OSRM_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))

    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RouteVerificationError(
            "The road-routing service is temporarily unavailable."
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RouteVerificationError(
            "The road-routing service returned an invalid response."
        ) from error

    if not isinstance(data, dict):
        raise RouteVerificationError(
            "The road-routing service returned an invalid response."
        )

    return data


def _prepare_coordinate_path(coordinates):
    """Validate coordinates and prepare the OSRM coordinate path."""
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        raise RouteVerificationError(
            "At least two route locations are required."
        )

    for coordinate in coordinates:
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
            raise RouteVerificationError(
                "A route contains invalid coordinates."
            )

        latitude, longitude = coordinate

        if not _valid_coordinate(latitude, longitude):
            raise RouteVerificationError(
                "A route contains invalid coordinates."
            )

    return ";".join(
        f"{float(longitude)},{float(latitude)}"
        for latitude, longitude in coordinates
    )


def _get_driving_route_duration(coordinates):
    """
    Return OSRM's driving-route duration in seconds.

    Coordinates must be supplied as (latitude, longitude) pairs.
    """
    coordinate_path = _prepare_coordinate_path(coordinates)

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{quote(coordinate_path, safe=';,')}"
        "?overview=false&steps=false"
    )

    data = _request_osrm_json(url)

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteVerificationError(
            "A driving route could not be found for these locations."
        )

    duration = data["routes"][0].get("duration")

    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or duration < 0
    ):
        raise RouteVerificationError(
            "The road-routing service returned an invalid duration."
        )

    return float(duration)


def get_driving_duration_matrix(coordinates):
    """
    Retrieve driving durations between every pair of locations.

    Uses one OSRM Table API request.

    Coordinates must be supplied as (latitude, longitude) pairs.

    Returns:
        A square matrix of driving durations in seconds.
        None represents an unreachable route.
    """
    coordinate_path = _prepare_coordinate_path(coordinates)

    url = (
        f"{OSRM_BASE_URL}/table/v1/driving/"
        f"{quote(coordinate_path, safe=';,')}"
        "?annotations=duration"
    )

    data = _request_osrm_json(url)

    if data.get("code") != "Ok":
        raise RouteVerificationError(
            "Driving durations could not be retrieved."
        )

    durations = data.get("durations")
    expected_size = len(coordinates)

    if (
        not isinstance(durations, list)
        or len(durations) != expected_size
    ):
        raise RouteVerificationError(
            "The road-routing service returned an invalid duration matrix."
        )

    validated_matrix = []

    for row in durations:
        if not isinstance(row, list) or len(row) != expected_size:
            raise RouteVerificationError(
                "The road-routing service returned an invalid duration matrix."
            )

        validated_row = []

        for duration in row:
            if duration is None:
                validated_row.append(None)
                continue

            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration < 0
            ):
                raise RouteVerificationError(
                    "The road-routing service returned an invalid duration."
                )

            validated_row.append(float(duration))

        validated_matrix.append(validated_row)

    return validated_matrix


def verify_passenger_detour(offer, match):
    """
    Compare the driver's original route with the route including
    the passenger's pickup and drop-off.

    The driver's maximum detour allowance is authoritative.
    """
    driver_route = [
        (offer["origin_latitude"], offer["origin_longitude"]),
        (offer["destination_latitude"], offer["destination_longitude"]),
    ]

    shared_route = [
        (offer["origin_latitude"], offer["origin_longitude"]),
        (match["pickup_latitude"], match["pickup_longitude"]),
        (match["dropoff_latitude"], match["dropoff_longitude"]),
        (offer["destination_latitude"], offer["destination_longitude"]),
    ]

    maximum_detour = int(offer["max_detour_minutes"])

    original_seconds = _get_driving_route_duration(driver_route)
    shared_seconds = _get_driving_route_duration(shared_route)

    extra_seconds = max(0.0, shared_seconds - original_seconds)
    extra_minutes = extra_seconds / 60

    accepted = extra_seconds <= maximum_detour * 60

    return {
        "road_route_verified": True,
        "road_route_status": "accepted" if accepted else "rejected",
        "original_route_duration_minutes": round(original_seconds / 60, 2),
        "shared_route_duration_minutes": round(shared_seconds / 60, 2),
        "additional_travel_time_minutes": round(extra_minutes, 2),
        "maximum_detour_minutes": maximum_detour,
        "detour_within_limit": accepted,
        "requires_road_route_verification": False,
        "explanation": (
            f"The passenger adds approximately {extra_minutes:.1f} "
            f"minutes to the journey. This is within the driver's "
            f"{maximum_detour}-minute limit."
            if accepted
            else
            f"The passenger adds approximately {extra_minutes:.1f} "
            f"minutes, exceeding the driver's "
            f"{maximum_detour}-minute limit."
        ),
    }
