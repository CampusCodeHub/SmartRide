
from datetime import date, datetime, time, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Iterable


EARTH_RADIUS_KM = 6371.0088


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat_a, lon_a, lat_b, lon_b = map(
        radians,
        (
            float(latitude_a),
            float(longitude_a),
            float(latitude_b),
            float(longitude_b),
        ),
    )

    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a

    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1, value)))


def _coordinate(record: dict[str, Any], name: str) -> float:
    try:
        value = float(record[name])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Invalid {name}.") from None

    if "latitude" in name:
        valid = -90 <= value <= 90
    else:
        valid = -180 <= value <= 180

    if not valid:
        raise ValueError(f"Invalid {name}.")

    return value


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return date.fromisoformat(value)

    raise ValueError("Invalid travel date.")


def _minutes_since_midnight(value: Any) -> int:
    if isinstance(value, datetime):
        value = value.time()

    if isinstance(value, time):
        return value.hour * 60 + value.minute

    # PyMySQL can return SQL TIME values as timedelta objects.
    if isinstance(value, timedelta):
        total_seconds = value.total_seconds()

        if not 0 <= total_seconds < 86400:
            raise ValueError("Invalid departure time.")

        return int(total_seconds // 60)

    if isinstance(value, str):
        parsed = time.fromisoformat(value)
        return parsed.hour * 60 + parsed.minute

    raise ValueError("Invalid departure time.")


def _point_to_segment_km(
    point_lat: float,
    point_lon: float,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> tuple[float, float]:
    reference_lat = radians((start_lat + end_lat + point_lat) / 3)

    def project(lat: float, lon: float) -> tuple[float, float]:
        x = EARTH_RADIUS_KM * radians(lon) * cos(reference_lat)
        y = EARTH_RADIUS_KM * radians(lat)
        return x, y

    sx, sy = project(start_lat, start_lon)
    ex, ey = project(end_lat, end_lon)
    px, py = project(point_lat, point_lon)

    dx, dy = ex - sx, ey - sy
    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return haversine_km(
            point_lat, point_lon, start_lat, start_lon
        ), 0.0

    fraction = ((px - sx) * dx + (py - sy) * dy) / length_squared
    fraction = max(0.0, min(1.0, fraction))

    closest_x = sx + fraction * dx
    closest_y = sy + fraction * dy

    distance = sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

    return distance, fraction


def evaluate_ride_offer(
    offer: dict[str, Any],
    requests: Iterable[dict[str, Any]],
    *,
    pickup_radius_km: float = 2.0,
    dropoff_radius_km: float = 2.0,
    departure_window_minutes: int = 60,
) -> list[dict[str, Any]]:

    if pickup_radius_km <= 0 or dropoff_radius_km <= 0:
        raise ValueError("Screening radii must be positive.")

    if departure_window_minutes < 0:
        raise ValueError("Departure window cannot be negative.")

    if str(offer.get("status", "")).lower() != "open":
        return []

    driver_date = _as_date(offer["travel_date"])
    driver_departure = _minutes_since_midnight(offer["departure_time"])

    seats = int(offer["available_seats"])

    if seats < 1:
        return []

    start_lat = _coordinate(offer, "origin_latitude")
    start_lon = _coordinate(offer, "origin_longitude")
    end_lat = _coordinate(offer, "destination_latitude")
    end_lon = _coordinate(offer, "destination_longitude")

    matches = []

    for request in requests:
        if str(request.get("status", "")).lower() != "open":
            continue

        try:
            if _as_date(request["travel_date"]) != driver_date:
                continue

            passenger_count = int(request["passenger_count"])

            if passenger_count < 1 or passenger_count > seats:
                continue

            passenger_departure = _minutes_since_midnight(
                request["departure_time"]
            )

            time_difference = abs(
                passenger_departure - driver_departure
            )

            if time_difference > departure_window_minutes:
                continue

            # Passenger pickup and drop-off coordinates
            pickup_lat = _coordinate(request, "origin_latitude")
            pickup_lon = _coordinate(request, "origin_longitude")
            dropoff_lat = _coordinate(request, "destination_latitude")
            dropoff_lon = _coordinate(request, "destination_longitude")

            # Calculate approximate pickup distance
            pickup_distance, pickup_position = _point_to_segment_km(
                pickup_lat,
                pickup_lon,
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )

            # Calculate approximate drop-off distance
            dropoff_distance, dropoff_position = _point_to_segment_km(
                dropoff_lat,
                dropoff_lon,
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )

            if pickup_distance > pickup_radius_km:
                continue

            if dropoff_distance > dropoff_radius_km:
                continue

            # Drop-off must occur after pickup along the route
            if dropoff_position <= pickup_position:
                continue

            score = (
                pickup_distance
                + dropoff_distance
                + (time_difference / max(1, departure_window_minutes))
            )

            matches.append({
                "request_id": request["id"],
                "passenger_id": request.get("passenger_id"),
                "passenger_count": passenger_count,

                # Passenger pickup information
                "pickup_address": request.get("origin_address"),
                "pickup_latitude": pickup_lat,
                "pickup_longitude": pickup_lon,

                # Passenger drop-off information
                "dropoff_address": request.get("destination_address"),
                "dropoff_latitude": dropoff_lat,
                "dropoff_longitude": dropoff_lon,

                # Existing matching calculations
                "pickup_distance_km": round(pickup_distance, 3),
                "dropoff_distance_km": round(dropoff_distance, 3),
                "departure_difference_minutes": time_difference,
                "route_pickup_position": round(pickup_position, 4),
                "route_dropoff_position": round(dropoff_position, 4),
                "screening_score": round(score, 4),

                "status": "potential_match",
                "requires_road_route_verification": True,

                "explanation": (
                    "Request is compatible by date, seats, time and "
                    "approximate route position. Road detour requires "
                    "verification."
                ),
            })

        except (KeyError, TypeError, ValueError):
            continue

    return sorted(
        matches,
        key=lambda item: (
            item["screening_score"],
            item["departure_difference_minutes"],
            item["request_id"],
        ),
    )
