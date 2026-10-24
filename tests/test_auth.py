
from unittest.mock import MagicMock, patch

import pytest
import auth
from clerk_backend_api.security.types import AuthStatus, RequestState


def test_authentication_requires_secret_key(monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
        auth.authenticate_clerk_request(MagicMock())


@patch("auth.Clerk")
def test_authentication_uses_clerk_sdk(mock_clerk, monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_secret_key")

    mock_instance = MagicMock()
    mock_clerk.return_value.__enter__.return_value = mock_instance

    fake_request = MagicMock()
    expected_state = MagicMock()
    mock_instance.authenticate_request.return_value = expected_state

    result = auth.authenticate_clerk_request(fake_request)

    assert result is expected_state
    mock_clerk.assert_called_once_with(bearer_auth="test_secret_key")
    mock_instance.authenticate_request.assert_called_once()

    options = mock_instance.authenticate_request.call_args.args[1]
    assert options.secret_key == "test_secret_key"
    assert "http://127.0.0.1:5000" in options.authorized_parties
    assert "http://localhost:5000" in options.authorized_parties


def test_request_state_identifies_authenticated_session():
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        token="verified-session-token",
        payload={"sub": "user_test123"},
    )

    assert state.is_authenticated is True
    assert state.payload["sub"] == "user_test123"


def test_request_state_identifies_unauthenticated_session():
    state = RequestState(status=AuthStatus.SIGNED_OUT)

    assert state.is_authenticated is False


@patch("auth.authenticate_clerk_request")
def test_get_authenticated_user_id_returns_verified_id(mock_authenticate):
    mock_authenticate.return_value = RequestState(
        status=AuthStatus.SIGNED_IN,
        token="verified-session-token",
        payload={"sub": "user_test123"},
    )

    result = auth.get_authenticated_clerk_user_id(MagicMock())

    assert result == "user_test123"


@patch("auth.authenticate_clerk_request")
def test_get_authenticated_user_id_rejects_signed_out_state(
    mock_authenticate,
):
    mock_authenticate.return_value = RequestState(
        status=AuthStatus.SIGNED_OUT
    )

    result = auth.get_authenticated_clerk_user_id(MagicMock())

    assert result is None


@patch("auth.authenticate_clerk_request")
def test_get_authenticated_user_id_rejects_missing_subject(
    mock_authenticate,
):
    mock_authenticate.return_value = RequestState(
        status=AuthStatus.SIGNED_IN,
        token="verified-session-token",
        payload={},
    )

    result = auth.get_authenticated_clerk_user_id(MagicMock())

    assert result is None
