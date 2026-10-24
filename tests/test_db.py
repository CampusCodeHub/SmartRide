
from unittest.mock import MagicMock, patch

import pytest

from db import create_ride_request, get_or_create_user


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
        travel_date="2026-11-15",
        departure_time="09:30",
        passenger_count=2,
        max_detour_minutes=15,
    )

    assert request_id == 42

    cursor.execute.assert_called_once()
    sql, values = cursor.execute.call_args.args

    assert "INSERT INTO ride_requests" in sql
    assert values == (
        1,
        "Edinburgh Waverley",
        "Edinburgh Napier University",
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
            travel_date="2026-11-15",
            departure_time="09:30",
            passenger_count=2,
            max_detour_minutes=15,
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


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
