
from db import (
    get_ride_offer_for_matching,
    get_open_ride_requests_for_matching,
)

from services.matching import evaluate_ride_offer
from services.group_selection import select_best_passenger_group
from services.group_optimisation import GroupOptimisationError
from services.route_verification import (
    RouteVerificationError,
    verify_passenger_detour,
)


MAX_GROUP_CANDIDATES = 10


def _retrieve_and_screen_matches(
    offer_id,
    driver_id,
    pickup_radius_km,
    dropoff_radius_km,
    departure_window_minutes,
):
    """Retrieve the offer and screen compatible passenger requests."""

    offer = get_ride_offer_for_matching(offer_id, driver_id)

    if offer is None:
        return None, [], []

    requests = get_open_ride_requests_for_matching(
        travel_date=offer["travel_date"],
        exclude_passenger_id=driver_id,
    )

    matches = evaluate_ride_offer(
        offer,
        requests,
        pickup_radius_km=pickup_radius_km,
        dropoff_radius_km=dropoff_radius_km,
        departure_window_minutes=departure_window_minutes,
    )

    return offer, requests, matches


def _verify_individual_matches(offer, matches):
    """Verify each potential passenger's individual road detour."""

    for match in matches:
        try:
            verification = verify_passenger_detour(offer, match)
            match.update(verification)

            if verification["detour_within_limit"]:
                match["status"] = "road_verified_match"
            else:
                match["status"] = "rejected_detour"

        except (
            RouteVerificationError,
            KeyError,
            TypeError,
            ValueError,
        ):
            match.update({
                "road_route_verified": False,
                "road_route_status": "unavailable",
                "detour_within_limit": None,
                "requires_road_route_verification": True,
                "status": "verification_pending",
                "explanation": (
                    "The initial journey screening passed, but road "
                    "detour verification is temporarily unavailable. "
                    "Please try again."
                ),
            })

    return matches


def _prepare_group_candidates(matches, requests):
    """Convert verified matches into the group optimiser's format."""

    requests_by_id = {
        passenger["id"]: passenger
        for passenger in requests
    }

    verified_matches = [
        match
        for match in matches
        if match.get("road_route_status") == "accepted"
    ]

    # Only the strongest screening candidates are considered.
    verified_matches = verified_matches[:MAX_GROUP_CANDIDATES]

    candidates = []

    for match in verified_matches:
        original_request = requests_by_id.get(match["request_id"])

        if original_request is None:
            continue

        candidates.append({
            "id": match["request_id"],
            "passenger_id": match.get("passenger_id"),
            "passenger_count": match["passenger_count"],

            "origin_address": match.get("pickup_address"),
            "origin_latitude": match["pickup_latitude"],
            "origin_longitude": match["pickup_longitude"],

            "destination_address": match.get("dropoff_address"),
            "destination_latitude": match["dropoff_latitude"],
            "destination_longitude": match["dropoff_longitude"],

            "max_detour_minutes": original_request[
                "max_detour_minutes"
            ],
        })

    return candidates


def find_matches_for_offer(
    offer_id,
    driver_id,
    pickup_radius_km=2.0,
    dropoff_radius_km=2.0,
    departure_window_minutes=60,
    verify_road_routes=False,
):
    """
    Retrieve, screen and optionally verify passenger matches.

    Preserves the original list-based return format.
    """

    offer, requests, matches = _retrieve_and_screen_matches(
        offer_id,
        driver_id,
        pickup_radius_km,
        dropoff_radius_km,
        departure_window_minutes,
    )

    if offer is None:
        return []

    if verify_road_routes:
        _verify_individual_matches(offer, matches)

    return matches


def find_matching_results_for_offer(
    offer_id,
    driver_id,
    pickup_radius_km=2.0,
    dropoff_radius_km=2.0,
    departure_window_minutes=60,
    verify_road_routes=True,
):
    """
    Return individual matches and the best feasible passenger group.
    """

    offer, requests, matches = _retrieve_and_screen_matches(
        offer_id,
        driver_id,
        pickup_radius_km,
        dropoff_radius_km,
        departure_window_minutes,
    )

    if offer is None:
        return {
            "matches": [],
            "selected_group": None,
            "group_optimisation_status": "offer_not_found",
            "group_optimisation_message": (
                "The ride offer could not be found."
            ),
        }

    if not verify_road_routes:
        return {
            "matches": matches,
            "selected_group": None,
            "group_optimisation_status": "not_run",
            "group_optimisation_message": (
                "Road verification is required before group optimisation."
            ),
        }

    _verify_individual_matches(offer, matches)

    candidates = _prepare_group_candidates(matches, requests)

    if not candidates:
        return {
            "matches": matches,
            "selected_group": None,
            "group_optimisation_status": "no_verified_candidates",
            "group_optimisation_message": (
                "No individually road-verified passengers are available "
                "for group optimisation."
            ),
        }

    try:
        selected_group = select_best_passenger_group(
            offer,
            candidates,
        )

        if selected_group is None:
            return {
                "matches": matches,
                "selected_group": None,
                "group_optimisation_status": "no_feasible_group",
                "group_optimisation_message": (
                    "No passenger group satisfies the available seats "
                    "and individual detour limits."
                ),
            }

        return {
            "matches": matches,
            "selected_group": selected_group,
            "group_optimisation_status": "success",
            "group_optimisation_message": (
                "The best feasible passenger group has been selected."
            ),
        }

    except (
        RouteVerificationError,
        GroupOptimisationError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return {
            "matches": matches,
            "selected_group": None,
            "group_optimisation_status": "unavailable",
            "group_optimisation_message": (
                "Group optimisation is temporarily unavailable. "
                "Please try again."
            ),
        }
