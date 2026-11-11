
import math
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create a TLS-secured connection to the SmartRide TiDB database."""
    required = (
        "TIDB_HOST",
        "TIDB_PORT",
        "TIDB_USER",
        "TIDB_PASSWORD",
        "TIDB_DATABASE",
    )

    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing database configuration: " + ", ".join(missing)
        )

    return pymysql.connect(
        host=os.environ["TIDB_HOST"],
        port=int(os.environ["TIDB_PORT"]),
        user=os.environ["TIDB_USER"],
        password=os.environ["TIDB_PASSWORD"],
        database=os.environ["TIDB_DATABASE"],
        connect_timeout=10,
        ssl={"ssl": True},
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_or_create_user(clerk_user_id, email, display_name, university):
    """Create a SmartRide user or return their existing database record."""
    if not clerk_user_id or not clerk_user_id.startswith("user_"):
        raise ValueError("A valid Clerk user ID is required.")

    if not email or not email.strip():
        raise ValueError("An email address is required.")

    if not display_name or not display_name.strip():
        raise ValueError("A display name is required.")

    if not university or not university.strip():
        raise ValueError("A university is required.")

    query = """
        INSERT INTO users (
            clerk_user_id,
            display_name,
            email,
            university
        )
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id)
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    clerk_user_id,
                    display_name.strip(),
                    email.strip().lower(),
                    university.strip(),
                ),
            )

            cursor.execute(
                """
                SELECT
                    id,
                    clerk_user_id,
                    display_name,
                    email,
                    university,
                    verification_status,
                    account_status,
                    created_at,
                    updated_at
                FROM users
                WHERE clerk_user_id = %s
                """,
                (clerk_user_id,),
            )
            user = cursor.fetchone()

        connection.commit()

        if user is None:
            raise RuntimeError("Unable to retrieve the SmartRide user.")

        return user

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _validate_coordinates(coordinates):
    """Validate geographic coordinates and return cleaned float values."""
    validated = {}

    for name, (value, minimum, maximum) in coordinates.items():
        try:
            coordinate = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {name.replace('_', ' ')}.")

        if (
            not math.isfinite(coordinate)
            or not minimum <= coordinate <= maximum
        ):
            raise ValueError(f"Invalid {name.replace('_', ' ')}.")

        validated[name] = coordinate

    return validated


def create_ride_request(
    passenger_id,
    origin,
    destination,
    origin_latitude,
    origin_longitude,
    destination_latitude,
    destination_longitude,
    travel_date,
    departure_time,
    passenger_count,
    max_detour_minutes,
):
    """Save a geographically complete ride request and return its ID."""
    coordinates = {
        "origin_latitude": (origin_latitude, -90, 90),
        "origin_longitude": (origin_longitude, -180, 180),
        "destination_latitude": (destination_latitude, -90, 90),
        "destination_longitude": (destination_longitude, -180, 180),
    }

    validated_coordinates = _validate_coordinates(coordinates)

    query = """
        INSERT INTO ride_requests (
            passenger_id,
            origin_address,
            origin_latitude,
            origin_longitude,
            destination_address,
            destination_latitude,
            destination_longitude,
            travel_date,
            departure_time,
            passenger_count,
            max_detour_minutes,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    passenger_id,
                    origin,
                    validated_coordinates["origin_latitude"],
                    validated_coordinates["origin_longitude"],
                    destination,
                    validated_coordinates["destination_latitude"],
                    validated_coordinates["destination_longitude"],
                    travel_date,
                    departure_time,
                    passenger_count,
                    max_detour_minutes,
                ),
            )

            request_id = cursor.lastrowid

        connection.commit()
        return request_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_ride_offer(
    driver_id,
    origin,
    destination,
    origin_latitude,
    origin_longitude,
    destination_latitude,
    destination_longitude,
    travel_date,
    departure_time,
    available_seats,
    max_detour_minutes,
):
    """Save a driver's ride offer and return its database ID."""

    if (
        isinstance(driver_id, bool)
        or not isinstance(driver_id, int)
        or driver_id <= 0
    ):
        raise ValueError("A valid driver ID is required.")

    if not isinstance(origin, str) or not origin.strip():
        raise ValueError("A starting location is required.")

    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("A destination is required.")

    origin = origin.strip()
    destination = destination.strip()

    if len(origin) > 255 or len(destination) > 255:
        raise ValueError("Locations must be 255 characters or fewer.")

    if (
        isinstance(available_seats, bool)
        or available_seats not in (1, 2, 3, 4, 5)
    ):
        raise ValueError("Available seats must be between 1 and 5.")

    if (
        isinstance(max_detour_minutes, bool)
        or max_detour_minutes not in (5, 10, 15, 20, 30)
    ):
        raise ValueError("Invalid maximum detour time.")

    coordinates = {
        "origin_latitude": (origin_latitude, -90, 90),
        "origin_longitude": (origin_longitude, -180, 180),
        "destination_latitude": (destination_latitude, -90, 90),
        "destination_longitude": (destination_longitude, -180, 180),
    }

    validated_coordinates = _validate_coordinates(coordinates)

    query = """
        INSERT INTO ride_offers (
            driver_id,
            origin_address,
            origin_latitude,
            origin_longitude,
            destination_address,
            destination_latitude,
            destination_longitude,
            travel_date,
            departure_time,
            available_seats,
            max_detour_minutes,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    driver_id,
                    origin,
                    validated_coordinates["origin_latitude"],
                    validated_coordinates["origin_longitude"],
                    destination,
                    validated_coordinates["destination_latitude"],
                    validated_coordinates["destination_longitude"],
                    travel_date,
                    departure_time,
                    available_seats,
                    max_detour_minutes,
                ),
            )

            offer_id = cursor.lastrowid

        connection.commit()
        return offer_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_user_by_clerk_id(clerk_user_id):
    """Retrieve an existing SmartRide user using their Clerk ID."""
    if not clerk_user_id or not clerk_user_id.startswith("user_"):
        raise ValueError("A valid Clerk user ID is required.")

    query = """
        SELECT
            id,
            clerk_user_id,
            display_name,
            email,
            university,
            verification_status,
            account_status,
            created_at,
            updated_at
        FROM users
        WHERE clerk_user_id = %s
        LIMIT 1
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (clerk_user_id,))
            user = cursor.fetchone()

        return user

    finally:
        connection.close()


def get_ride_offer_for_matching(offer_id, driver_id):
    """Retrieve an open ride offer belonging to a specific driver."""
    if (
        isinstance(offer_id, bool)
        or not isinstance(offer_id, int)
        or offer_id <= 0
    ):
        raise ValueError("A valid ride offer ID is required.")

    if (
        isinstance(driver_id, bool)
        or not isinstance(driver_id, int)
        or driver_id <= 0
    ):
        raise ValueError("A valid driver ID is required.")

    query = """
        SELECT
            id,
            driver_id,
            origin_address,
            origin_latitude,
            origin_longitude,
            destination_address,
            destination_latitude,
            destination_longitude,
            travel_date,
            departure_time,
            available_seats,
            max_detour_minutes,
            status
        FROM ride_offers
        WHERE id = %s
          AND driver_id = %s
          AND status = 'open'
        LIMIT 1
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (offer_id, driver_id))
            return cursor.fetchone()

    finally:
        connection.close()


def get_open_ride_requests_for_matching(
    travel_date,
    exclude_passenger_id=None,
):
    """Retrieve open passenger requests for a travel date."""
    query = """
        SELECT
            id,
            passenger_id,
            origin_address,
            origin_latitude,
            origin_longitude,
            destination_address,
            destination_latitude,
            destination_longitude,
            travel_date,
            departure_time,
            passenger_count,
            max_detour_minutes,
            status
        FROM ride_requests
        WHERE travel_date = %s
          AND status = 'open'
    """

    parameters = [travel_date]

    if exclude_passenger_id is not None:
        if (
            isinstance(exclude_passenger_id, bool)
            or not isinstance(exclude_passenger_id, int)
            or exclude_passenger_id <= 0
        ):
            raise ValueError("A valid passenger ID is required.")

        query += " AND passenger_id <> %s"
        parameters.append(exclude_passenger_id)

    query += " ORDER BY departure_time ASC, id ASC"

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            return cursor.fetchall()

    finally:
        connection.close()
