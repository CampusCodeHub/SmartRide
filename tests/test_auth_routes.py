
from unittest.mock import patch

import app as app_module


def test_current_user_rejects_unauthenticated_request():
    client = app_module.app.test_client()

    with patch(
        "app.get_authenticated_clerk_user_id",
        return_value=None,
    ):
        response = client.get("/api/me")

    assert response.status_code == 401
    assert response.get_json()["authenticated"] is False


def test_current_user_returns_verified_clerk_id():
    client = app_module.app.test_client()

    with patch(
        "app.get_authenticated_clerk_user_id",
        return_value="user_test123",
    ):
        response = client.get("/api/me")

    assert response.status_code == 200
    assert response.get_json() == {
        "authenticated": True,
        "clerk_user_id": "user_test123",
    }


def test_current_user_handles_verification_failure():
    client = app_module.app.test_client()

    with patch(
        "app.get_authenticated_clerk_user_id",
        side_effect=RuntimeError("Verification failed"),
    ):
        response = client.get("/api/me")

    assert response.status_code == 401
    assert response.get_json()["authenticated"] is False
