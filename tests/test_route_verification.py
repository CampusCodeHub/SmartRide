
import pytest

from services.route_verification import (
    RouteVerificationError,
    get_driving_duration_matrix,
)


def test_returns_valid_duration_matrix(monkeypatch):
    def fake_request(url):
        assert "/table/v1/driving/" in url
        assert "annotations=duration" in url

        return {
            "code": "Ok",
            "durations": [
                [0, 300, 600],
                [300, 0, 200],
                [600, 200, 0],
            ],
        }

    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        fake_request,
    )

    coordinates = [
        (55.9500, -3.1900),
        (55.9400, -3.1800),
        (55.9300, -3.1700),
    ]

    result = get_driving_duration_matrix(coordinates)

    assert result == [
        [0.0, 300.0, 600.0],
        [300.0, 0.0, 200.0],
        [600.0, 200.0, 0.0],
    ]


def test_rejects_invalid_coordinates():
    with pytest.raises(RouteVerificationError, match="invalid coordinates"):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
            (100, -3.1800),
        ])


def test_rejects_fewer_than_two_locations():
    with pytest.raises(RouteVerificationError, match="At least two"):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
        ])


def test_rejects_osrm_error_response(monkeypatch):
    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        lambda url: {"code": "NoTable"},
    )

    with pytest.raises(RouteVerificationError):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
            (55.9400, -3.1800),
        ])


def test_preserves_unreachable_routes_as_none(monkeypatch):
    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        lambda url: {
            "code": "Ok",
            "durations": [
                [0, None],
                [None, 0],
            ],
        },
    )

    result = get_driving_duration_matrix([
        (55.9500, -3.1900),
        (55.9400, -3.1800),
    ])

    assert result == [
        [0.0, None],
        [None, 0.0],
    ]


def test_rejects_incorrect_matrix_dimensions(monkeypatch):
    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        lambda url: {
            "code": "Ok",
            "durations": [
                [0, 300],
            ],
        },
    )

    with pytest.raises(RouteVerificationError, match="invalid duration matrix"):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
            (55.9400, -3.1800),
        ])


def test_rejects_invalid_duration_values(monkeypatch):
    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        lambda url: {
            "code": "Ok",
            "durations": [
                [0, -100],
                [100, 0],
            ],
        },
    )

    with pytest.raises(RouteVerificationError, match="invalid duration"):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
            (55.9400, -3.1800),
        ])


def test_rejects_nan_duration(monkeypatch):
    monkeypatch.setattr(
        "services.route_verification._request_osrm_json",
        lambda url: {
            "code": "Ok",
            "durations": [
                [0, float("nan")],
                [100, 0],
            ],
        },
    )

    with pytest.raises(RouteVerificationError, match="invalid duration"):
        get_driving_duration_matrix([
            (55.9500, -3.1900),
            (55.9400, -3.1800),
        ])
