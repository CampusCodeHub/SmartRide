
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from auth import get_clerk_user_profile


@patch("auth.Clerk")
def test_get_clerk_user_profile_returns_primary_email(
    mock_clerk, monkeypatch
):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_secret_key")

    mock_instance = MagicMock()
    mock_clerk.return_value.__enter__.return_value = mock_instance
    mock_instance.users.get.return_value = SimpleNamespace(
        email_addresses=[
            SimpleNamespace(
                id="email_primary",
                email_address="student@example.com",
            )
        ],
        primary_email_address_id="email_primary",
        first_name="Test",
        last_name="Student",
    )

    profile = get_clerk_user_profile("user_test123")

    assert profile == {
        "clerk_user_id": "user_test123",
        "email": "student@example.com",
        "display_name": "Test Student",
    }


def test_get_clerk_user_profile_rejects_invalid_user_id():
    with pytest.raises(ValueError, match="valid Clerk user ID"):
        get_clerk_user_profile("invalid_id")


def test_get_clerk_user_profile_requires_secret_key(monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
        get_clerk_user_profile("user_test123")


@patch("auth.Clerk")
def test_get_clerk_user_profile_rejects_missing_primary_email(
    mock_clerk, monkeypatch
):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_secret_key")

    mock_instance = MagicMock()
    mock_clerk.return_value.__enter__.return_value = mock_instance
    mock_instance.users.get.return_value = SimpleNamespace(
        email_addresses=[],
        primary_email_address_id=None,
        first_name="Test",
        last_name="Student",
    )

    with pytest.raises(ValueError, match="primary email address"):
        get_clerk_user_profile("user_test123")


@patch("auth.Clerk")
def test_get_clerk_user_profile_falls_back_to_email_username(
    mock_clerk, monkeypatch
):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_secret_key")

    mock_instance = MagicMock()
    mock_clerk.return_value.__enter__.return_value = mock_instance
    mock_instance.users.get.return_value = SimpleNamespace(
        email_addresses=[
            SimpleNamespace(
                id="email_primary",
                email_address="student@example.com",
            )
        ],
        primary_email_address_id="email_primary",
        first_name="",
        last_name="",
    )

    profile = get_clerk_user_profile("user_test123")

    assert profile["display_name"] == "student"
    assert profile["email"] == "student@example.com"
