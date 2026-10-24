
from unittest.mock import patch

import app as app_module


def test_create_profile_rejects_unauthenticated_request():
    client = app_module.app.test_client()

    with patch(
        "app.get_authenticated_clerk_user_id",
        return_value=None,
    ):
        response = client.post(
            "/api/profile",
            json={"university": "Edinburgh Napier University"},
        )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Sign-in required."


def test_create_profile_rejects_missing_json_body():
    client = app_module.app.test_client()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_clerk_user_profile",
            return_value={
                "clerk_user_id": "user_test123",
                "email": "student@example.com",
                "display_name": "Test Student",
            },
        ),
    ):
        response = client.post("/api/profile")

    assert response.status_code == 400
    assert response.get_json()["error"] == "A JSON request body is required."


def test_create_profile_rejects_missing_university():
    client = app_module.app.test_client()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_clerk_user_profile",
            return_value={
                "clerk_user_id": "user_test123",
                "email": "student@example.com",
                "display_name": "Test Student",
            },
        ),
    ):
        response = client.post("/api/profile", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Please provide your university."


def test_create_profile_saves_verified_clerk_profile():
    client = app_module.app.test_client()

    clerk_profile = {
        "clerk_user_id": "user_test123",
        "email": "student@example.com",
        "display_name": "Test Student",
    }

    database_user = {
        "id": 42,
        **clerk_profile,
        "university": "Edinburgh Napier University",
        "verification_status": "pending",
        "account_status": "active",
    }

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_clerk_user_profile",
            return_value=clerk_profile,
        ),
        patch(
            "app.get_or_create_user",
            return_value=database_user,
        ) as mock_create,
    ):
        response = client.post(
            "/api/profile",
            json={"university": "Edinburgh Napier University"},
        )

    assert response.status_code == 200
    assert response.get_json()["profile"] == database_user

    mock_create.assert_called_once_with(
        clerk_user_id="user_test123",
        email="student@example.com",
        display_name="Test Student",
        university="Edinburgh Napier University",
    )


def test_create_profile_rejects_university_over_150_characters():
    client = app_module.app.test_client()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_clerk_user_profile",
            return_value={
                "clerk_user_id": "user_test123",
                "email": "student@example.com",
                "display_name": "Test Student",
            },
        ),
    ):
        response = client.post(
            "/api/profile",
            json={"university": "U" * 151},
        )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "University must be 150 characters or fewer."
    )


def test_create_profile_handles_database_failure():
    client = app_module.app.test_client()

    with (
        patch(
            "app.get_authenticated_clerk_user_id",
            return_value="user_test123",
        ),
        patch(
            "app.get_clerk_user_profile",
            return_value={
                "clerk_user_id": "user_test123",
                "email": "student@example.com",
                "display_name": "Test Student",
            },
        ),
        patch(
            "app.get_or_create_user",
            side_effect=RuntimeError("Database unavailable"),
        ),
    ):
        response = client.post(
            "/api/profile",
            json={"university": "Edinburgh Napier University"},
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == (
        "Unable to save your profile right now."
    )
