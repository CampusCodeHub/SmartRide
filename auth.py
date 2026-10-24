
import os

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from dotenv import load_dotenv

load_dotenv()


def _get_allowed_origins():
    """Return the explicitly allowed frontend origins."""
    configured = os.getenv(
        "CLERK_AUTHORIZED_PARTIES",
        "http://127.0.0.1:5000,http://localhost:5000",
    )

    return [
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    ]


def authenticate_clerk_request(flask_request):
    """Verify a Clerk session token and return the SDK request state."""
    secret_key = os.getenv("CLERK_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("CLERK_SECRET_KEY is not configured.")

    options = AuthenticateRequestOptions(
        secret_key=secret_key,
        authorized_parties=_get_allowed_origins(),
    )

    with Clerk(bearer_auth=secret_key) as clerk:
        return clerk.authenticate_request(flask_request, options)


def get_authenticated_clerk_user_id(flask_request):
    """Return the verified Clerk user ID, or None if not signed in."""
    state = authenticate_clerk_request(flask_request)

    if not state.is_authenticated:
        return None

    payload = state.payload

    if not isinstance(payload, dict):
        return None

    user_id = payload.get("sub")

    if not isinstance(user_id, str) or not user_id.startswith("user_"):
        return None

    return user_id


def get_clerk_user_profile(clerk_user_id):
    """Retrieve trusted profile details from Clerk's Backend API."""
    if (
        not isinstance(clerk_user_id, str)
        or not clerk_user_id.startswith("user_")
    ):
        raise ValueError("A valid Clerk user ID is required.")

    secret_key = os.getenv("CLERK_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("CLERK_SECRET_KEY is not configured.")

    with Clerk(bearer_auth=secret_key) as clerk:
        user = clerk.users.get(user_id=clerk_user_id)

    def get_field(value, field):
        """Read a field from either a dictionary or an SDK object."""
        if isinstance(value, dict):
            return value.get(field)

        return getattr(value, field, None)

    email_addresses = get_field(user, "email_addresses") or []
    primary_email_id = get_field(user, "primary_email_address_id")

    primary_email = next(
        (
            item
            for item in email_addresses
            if get_field(item, "id") == primary_email_id
        ),
        None,
    )

    email = get_field(primary_email, "email_address")

    if not isinstance(email, str) or not email.strip():
        raise ValueError(
            "The Clerk account needs a primary email address."
        )

    first_name = get_field(user, "first_name") or ""
    last_name = get_field(user, "last_name") or ""

    display_name = f"{first_name} {last_name}".strip()

    if not display_name:
        display_name = email.strip().split("@")[0]

    return {
        "clerk_user_id": clerk_user_id,
        "email": email.strip().lower(),
        "display_name": display_name,
    }
