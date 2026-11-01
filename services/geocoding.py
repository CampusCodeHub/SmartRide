
import math
import os
import threading
import time

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_TIMEOUT = 10

_cache = {}
_cache_lock = threading.Lock()

_rate_limit_lock = threading.Lock()
_last_request_time = 0.0


class GeocodingError(Exception):
    """Base exception for geocoding failures."""


class LocationNotFoundError(GeocodingError):
    """Raised when Nominatim cannot find the requested location."""


class GeocodingConfigurationError(GeocodingError):
    """Raised when geocoding configuration is missing."""


def _wait_for_rate_limit():
    """Ensure requests to the public service are at least one second apart."""
    global _last_request_time

    with _rate_limit_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        delay = max(0.0, 1.1 - elapsed)

        if delay:
            time.sleep(delay)

        _last_request_time = time.monotonic()


def _get_configuration():
    """Read the configurable Nominatim endpoint and application identity."""
    endpoint = os.getenv(
        "NOMINATIM_URL",
        "https://nominatim.openstreetmap.org/search",
    ).strip()

    user_agent = os.getenv("NOMINATIM_USER_AGENT", "").strip()

    if not endpoint:
        raise GeocodingConfigurationError(
            "NOMINATIM_URL is not configured."
        )

    if not user_agent or "YOUR_REAL_CONTACT_EMAIL" in user_agent:
        raise GeocodingConfigurationError(
            "Set NOMINATIM_USER_AGENT in your .env file using "
            "an identifying application name and real contact email."
        )

    return endpoint, user_agent


def geocode_address(address, country_codes="gb", timeout=DEFAULT_TIMEOUT):
    """
    Convert a user-entered address into geographic coordinates.

    Returns:
        {
            "latitude": float,
            "longitude": float,
            "display_name": str
        }

    Raises:
        ValueError: Invalid input.
        LocationNotFoundError: No matching location found.
        GeocodingConfigurationError: Missing configuration.
        GeocodingError: Network or response failure.
    """
    if not isinstance(address, str) or not address.strip():
        raise ValueError("A valid address is required.")

    if len(address.strip()) > 255:
        raise ValueError("Address must be 255 characters or fewer.")

    if not isinstance(country_codes, str) or not country_codes.strip():
        raise ValueError("A valid country code is required.")

    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        raise ValueError("Timeout must be a positive number.")

    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be a positive number.")

    clean_address = address.strip()
    clean_country_codes = country_codes.strip().lower()

    cache_key = (
        clean_address.casefold(),
        clean_country_codes,
    )

    with _cache_lock:
        cached_result = _cache.get(cache_key)

    if cached_result is not None:
        return cached_result.copy()

    endpoint, user_agent = _get_configuration()

    params = {
        "q": clean_address,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": clean_country_codes,
    }

    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-GB,en",
    }

    try:
        _wait_for_rate_limit()

        response = requests.get(
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )

        response.raise_for_status()
        results = response.json()

    except requests.exceptions.RequestException as error:
        raise GeocodingError(
            "Unable to contact the geocoding service."
        ) from error

    except (ValueError, TypeError) as error:
        raise GeocodingError(
            "The geocoding service returned an invalid response."
        ) from error

    if not isinstance(results, list):
        raise GeocodingError(
            "The geocoding service returned an unexpected response."
        )

    if not results:
        raise LocationNotFoundError(
            f"No location could be found for '{clean_address}'."
        )

    result = results[0]

    try:
        latitude = float(result["lat"])
        longitude = float(result["lon"])
        display_name = result["display_name"]

        if (
            not math.isfinite(latitude)
            or not -90 <= latitude <= 90
            or not math.isfinite(longitude)
            or not -180 <= longitude <= 180
            or not isinstance(display_name, str)
            or not display_name.strip()
        ):
            raise ValueError("Invalid location data.")

    except (KeyError, TypeError, ValueError) as error:
        raise GeocodingError(
            "The geocoding service returned invalid coordinates."
        ) from error

    location = {
        "latitude": latitude,
        "longitude": longitude,
        "display_name": display_name,
    }

    with _cache_lock:
        _cache[cache_key] = location.copy()

    return location


def clear_geocoding_cache():
    """Clear cached results, primarily for automated tests."""
    with _cache_lock:
        _cache.clear()
