from unittest.mock import MagicMock, patch
from db import create_ride_offer

import pytest

from db import (
    create_ride_request,
    get_or_create_user,
    get_user_by_clerk_id,
)


@pytest.fixture
def mock_database():
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value.__enter__.return_value = cursor
    cursor.lastrowid = 42

    with patch("db.get_db_connection", return_value=connection):
        yield connection, cursor


def test_create_ride_request_success(mock_database):
    connection, cursor = mock_database

    request_id = create_ride_request(
        passenger_id=1,
        origin="Edinburgh Waverley",
        destination="Edinburgh Napier University",
        origin_latitude=55.9521,
        origin_longitude=-3.1889,
        destination_latitude=55.9225,
        destination_longitude=-3.1722,
        travel_date="2026-11-15",
        departure_time="09:30",
        passenger_count=2,
        max_detour_minutes=15,
    )

    assert request_id == 42

    cursor.execute.assert_called_once()

    sql, values = cursor.execute.call_args.args

    assert "INSERT INTO ride_requests" in sql
    assert "origin_latitude" in sql
    assert "origin_longitude" in sql
    assert "destination_latitude" in sql
    assert "destination_longitude" in sql

    assert values == (
        1,
        "Edinburgh Waverley",
        55.9521,
        -3.1889,
        "Edinburgh Napier University",
        55.9225,
        -3.1722,
        "2026-11-15",
        "09:30",
        2,
        15,
    )

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()


def test_create_ride_request_rolls_back_on_failure(mock_database):
    connection, cursor = mock_database

    cursor.execute.side_effect = Exception("Simulated insert failure")

    with pytest.raises(Exception, match="Simulated insert failure"):
        create_ride_request(
            passenger_id=1,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude=55.9521,
            origin_longitude=-3.1889,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_create_ride_request_rejects_invalid_latitude(mock_database):
    connection, cursor = mock_database

    with pytest.raises(ValueError, match="Invalid origin latitude"):
        create_ride_request(
            passenger_id=1,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude=95,
            origin_longitude=-3.1889,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()
    connection.close.assert_not_called()
    cursor.execute.assert_not_called()


def test_create_ride_request_rejects_invalid_longitude(mock_database):
    connection, cursor = mock_database

    with pytest.raises(ValueError, match="Invalid origin longitude"):
        create_ride_request(
            passenger_id=1,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude=55.9521,
            origin_longitude=200,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()


def test_create_ride_request_rejects_non_numeric_coordinates(mock_database):
    connection, cursor = mock_database

    with pytest.raises(ValueError, match="Invalid origin latitude"):
        create_ride_request(
            passenger_id=1,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude="not-a-coordinate",
            origin_longitude=-3.1889,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()


def test_create_ride_request_rejects_infinite_coordinates(mock_database):
    connection, cursor = mock_database

    with pytest.raises(ValueError, match="Invalid origin latitude"):
        create_ride_request(
            passenger_id=1,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude=float("inf"),
            origin_longitude=-3.1889,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()


def test_get_or_create_user_success(mock_database):
    connection, cursor = mock_database

    expected_user = {
        "id": 42,
        "clerk_user_id": "user_test123",
        "display_name": "Test Student",
        "email": "student@example.com",
        "university": "Edinburgh Napier University",
        "verification_status": "pending",
        "account_status": "active",
    }

    cursor.fetchone.return_value = expected_user

    user = get_or_create_user(
        clerk_user_id="user_test123",
        email="STUDENT@example.com",
        display_name="Test Student",
        university="Edinburgh Napier University",
    )

    assert user == expected_user
    assert cursor.execute.call_count == 2

    insert_sql, insert_values = cursor.execute.call_args_list[0].args

    assert "INSERT INTO users" in insert_sql
    assert "ON DUPLICATE KEY UPDATE" in insert_sql

    assert insert_values == (
        "user_test123",
        "Test Student",
        "student@example.com",
        "Edinburgh Napier University",
    )

    select_sql, select_values = cursor.execute.call_args_list[1].args

    assert "SELECT" in select_sql
    assert "WHERE clerk_user_id = %s" in select_sql
    assert select_values == ("user_test123",)

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()


def test_get_or_create_user_returns_existing_user(mock_database):
    connection, cursor = mock_database

    existing_user = {
        "id": 12,
        "clerk_user_id": "user_existing123",
        "display_name": "Existing Student",
        "email": "existing@example.com",
        "university": "Edinburgh Napier University",
        "verification_status": "pending",
        "account_status": "active",
    }

    cursor.fetchone.return_value = existing_user

    user = get_or_create_user(
        clerk_user_id="user_existing123",
        email="existing@example.com",
        display_name="Existing Student",
        university="Edinburgh Napier University",
    )

    assert user["id"] == 12
    assert user["clerk_user_id"] == "user_existing123"
    assert cursor.execute.call_count == 2

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()


def test_get_or_create_user_rejects_invalid_clerk_id():
    with pytest.raises(ValueError, match="valid Clerk user ID"):
        get_or_create_user(
            clerk_user_id="invalid_id",
            email="student@example.com",
            display_name="Test Student",
            university="Edinburgh Napier University",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("email", "", "email address is required"),
        ("display_name", " ", "display name is required"),
        ("university", "", "university is required"),
    ],
)
def test_get_or_create_user_rejects_missing_profile_fields(
    field, value, message
):
    profile = {
        "clerk_user_id": "user_test123",
        "email": "student@example.com",
        "display_name": "Test Student",
        "university": "Edinburgh Napier University",
    }

    profile[field] = value

    with pytest.raises(ValueError, match=message):
        get_or_create_user(**profile)


def test_get_or_create_user_rolls_back_on_database_failure(mock_database):
    connection, cursor = mock_database

    cursor.execute.side_effect = Exception("Simulated database failure")

    with pytest.raises(Exception, match="Simulated database failure"):
        get_or_create_user(
            clerk_user_id="user_test123",
            email="student@example.com",
            display_name="Test Student",
            university="Edinburgh Napier University",
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_get_user_by_clerk_id_success(mock_database):
    connection, cursor = mock_database

    expected_user = {
        "id": 42,
        "clerk_user_id": "user_test123",
        "display_name": "Test Student",
        "email": "student@example.com",
        "university": "Edinburgh Napier University",
        "verification_status": "pending",
        "account_status": "active",
    }

    cursor.fetchone.return_value = expected_user

    user = get_user_by_clerk_id("user_test123")

    assert user == expected_user

    cursor.execute.assert_called_once()

    sql, values = cursor.execute.call_args.args

    assert "SELECT" in sql
    assert "FROM users" in sql
    assert "WHERE clerk_user_id = %s" in sql
    assert values == ("user_test123",)

    connection.close.assert_called_once()
    connection.commit.assert_not_called()


def test_get_user_by_clerk_id_returns_none_when_not_found(mock_database):
    connection, cursor = mock_database

    cursor.fetchone.return_value = None

    user = get_user_by_clerk_id("user_missing123")

    assert user is None

    cursor.execute.assert_called_once()

    sql, values = cursor.execute.call_args.args

    assert "FROM users" in sql
    assert "WHERE clerk_user_id = %s" in sql
    assert values == ("user_missing123",)

    connection.close.assert_called_once()


def test_get_user_by_clerk_id_rejects_invalid_clerk_id():
    with pytest.raises(ValueError, match="valid Clerk user ID"):
        get_user_by_clerk_id("invalid_id")


def test_get_user_by_clerk_id_closes_connection_on_failure(mock_database):
    connection, cursor = mock_database

    cursor.execute.side_effect = Exception("Simulated database failure")

    with pytest.raises(Exception, match="Simulated database failure"):
        get_user_by_clerk_id("user_test123")

    connection.close.assert_called_once()


def test_create_ride_offer_success(mock_database):
    connection, cursor = mock_database

    offer_id = create_ride_offer(
        driver_id=42,
        origin="Edinburgh Waverley",
        destination="Edinburgh Napier University",
        origin_latitude=55.9521,
        origin_longitude=-3.1889,
        destination_latitude=55.9225,
        destination_longitude=-3.1722,
        travel_date="2026-11-15",
        departure_time="09:30",
        available_seats=3,
        max_detour_minutes=15,
    )

    assert offer_id == 42

    cursor.execute.assert_called_once()

    sql, values = cursor.execute.call_args.args

    assert "INSERT INTO ride_offers" in sql
    assert "available_seats" in sql
    assert "max_detour_minutes" in sql

    assert values == (
        42,
        "Edinburgh Waverley",
        55.9521,
        -3.1889,
        "Edinburgh Napier University",
        55.9225,
        -3.1722,
        "2026-11-15",
        "09:30",
        3,
        15,
    )

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()


def test_create_ride_offer_rolls_back_on_failure(mock_database):
    connection, cursor = mock_database

    cursor.execute.side_effect = Exception("Simulated insert failure")

    with pytest.raises(Exception, match="Simulated insert failure"):
        create_ride_offer(
            driver_id=42,
            origin="Edinburgh Waverley",
            destination="Edinburgh Napier University",
            origin_latitude=55.9521,
            origin_longitude=-3.1889,
            destination_latitude=55.9225,
            destination_longitude=-3.1722,
            travel_date="2026-11-15",
            departure_time="09:30",
            available_seats=3,
            max_detour_minutes=15,
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("driver_id", 0, "valid driver ID"),
        ("available_seats", 0, "Available seats"),
        ("available_seats", 6, "Available seats"),
        ("max_detour_minutes", 7, "maximum detour"),
    ],
)
def test_create_ride_offer_rejects_invalid_values(
    mock_database, field, value, message
):
    arguments = {
        "driver_id": 42,
        "origin": "Edinburgh Waverley",
        "destination": "Edinburgh Napier University",
        "origin_latitude": 55.9521,
        "origin_longitude": -3.1889,
        "destination_latitude": 55.9225,
        "destination_longitude": -3.1722,
        "travel_date": "2026-11-15",
        "departure_time": "09:30",
        "available_seats": 3,
        "max_detour_minutes": 15,
    }

    arguments[field] = value

    with pytest.raises(ValueError, match=message):
        create_ride_offer(**arguments)

    connection, cursor = mock_database
    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()
    connection.close.assert_not_called()
