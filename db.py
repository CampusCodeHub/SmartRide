
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
            user_id = cursor.lastrowid

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


def create_ride_request(
    passenger_id,
    origin,
    destination,
    travel_date,
    departure_time,
    passenger_count,
    max_detour_minutes,
):
    """Save a ride request and return its generated database ID."""
    query = """
        INSERT INTO ride_requests (
            passenger_id,
            origin_address,
            destination_address,
            travel_date,
            departure_time,
            passenger_count,
            max_detour_minutes,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    passenger_id,
                    origin,
                    destination,
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
