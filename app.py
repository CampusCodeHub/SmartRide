import os
from datetime import date, time

from flask import Flask, jsonify, render_template, request
from services.matching_service import find_matching_results_for_offer


from auth import (
    get_authenticated_clerk_user_id,
    get_clerk_user_profile,
)
from db import (
    create_ride_offer,
    create_ride_request,
    get_db_connection,
    get_or_create_user,
    get_user_by_clerk_id,
)
from services.geocoding import (
    GeocodingConfigurationError,
    GeocodingError,
    LocationNotFoundError,
    geocode_address,
)


app = Flask(__name__)


@app.context_processor
def inject_clerk_config():
    return {
        "clerk_publishable_key": os.getenv(
            "CLERK_PUBLISHABLE_KEY", ""
        )
    }



def validate_journey(data):
    """Validate submitted passenger journey details."""
    origin = data.get("origin", "").strip()
    destination = data.get("destination", "").strip()
    travel_date = data.get("travel_date", "")
    departure_time = data.get("departure_time", "")
    max_detour = data.get("max_detour", "")
    passengers = data.get("passengers", "")

    error = None
    selected_date = None

    if not origin or not destination:
        error = "Starting location and destination are required."
    elif len(origin) > 200 or len(destination) > 200:
        error = "Locations must be 200 characters or fewer."

    if error is None:
        try:
            selected_date = date.fromisoformat(travel_date)
        except (ValueError, TypeError):
            error = "Please provide a valid travel date."
        else:
            if selected_date < date.today():
                error = "Travel date cannot be in the past."

    if error is None:
        try:
            time.fromisoformat(departure_time)
        except (ValueError, TypeError):
            error = "Please provide a valid departure time."

    if error is None and max_detour not in {"5", "10", "15", "20", "30"}:
        error = "Please select a valid maximum extra travel time."

    if error is None and passengers not in {"1", "2", "3", "4", "5"}:
        error = "Please select a valid passenger count."

    form_data = {
        "origin": origin,
        "destination": destination,
        "travel_date": travel_date,
        "departure_time": departure_time,
        "max_detour": max_detour,
        "passengers": passengers,
    }

    if error:
        return None, form_data, error

    journey = {
        "origin": origin,
        "destination": destination,
        "travel_date": selected_date.strftime("%d %B %Y"),
        "travel_date_iso": selected_date.isoformat(),
        "departure_time": departure_time,
        "max_detour": int(max_detour),
        "passengers": int(passengers),
    }

    return journey, form_data, None


def validate_ride_offer(data):
    """Validate submitted driver offer details."""
    origin = data.get("origin", "").strip()
    destination = data.get("destination", "").strip()
    travel_date = data.get("travel_date", "")
    departure_time = data.get("departure_time", "")
    available_seats = data.get("available_seats", "")
    max_detour = data.get("max_detour", "")

    error = None
    selected_date = None

    if not origin or not destination:
        error = "Starting location and destination are required."
    elif len(origin) > 200 or len(destination) > 200:
        error = "Locations must be 200 characters or fewer."

    if error is None:
        try:
            selected_date = date.fromisoformat(travel_date)
        except (ValueError, TypeError):
            error = "Please provide a valid travel date."
        else:
            if selected_date < date.today():
                error = "Travel date cannot be in the past."

    if error is None:
        try:
            time.fromisoformat(departure_time)
        except (ValueError, TypeError):
            error = "Please provide a valid departure time."

    if error is None and available_seats not in {"1", "2", "3", "4", "5"}:
        error = "Please select a valid number of available seats."

    if error is None and max_detour not in {"5", "10", "15", "20", "30"}:
        error = "Please select a valid maximum extra travel time."

    form_data = {
        "origin": origin,
        "destination": destination,
        "travel_date": travel_date,
        "departure_time": departure_time,
        "available_seats": available_seats,
        "max_detour": max_detour,
    }

    if error:
        return None, form_data, error

    offer = {
        "origin": origin,
        "destination": destination,
        "travel_date": selected_date.strftime("%d %B %Y"),
        "travel_date_iso": selected_date.isoformat(),
        "departure_time": departure_time,
        "available_seats": int(available_seats),
        "max_detour": int(max_detour),
    }

    return offer, form_data, None


@app.route("/")
def home():
    return render_template(
        "home.html",
        clerk_publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY", ""),
    )


@app.route("/find-ride", methods=["GET", "POST"])
def find_ride():
    today = date.today().isoformat()

    if request.method == "GET":
        form_data = request.args

        if not request.args or not any(request.args.values()):
            return render_template("find_ride.html", today=today)

        if request.args.get("edit") == "1":
            return render_template(
                "find_ride.html",
                today=today,
                form_data=form_data,
            )

        journey, submitted_data, error = validate_journey(request.args)

        if error:
            return render_template(
                "find_ride.html",
                today=today,
                error=error,
                form_data=submitted_data,
            ), 400

        return render_template(
            "ride_results.html",
            journey=journey,
            saved=False,
        )

    journey, submitted_data, error = validate_journey(request.form)

    if error:
        return render_template(
            "find_ride.html",
            today=today,
            error=error,
            form_data=submitted_data,
        ), 400

    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)

    except Exception:
        app.logger.exception("Journey submission authentication failed")
        return render_template(
            "find_ride.html",
            today=today,
            error="Unable to verify your account. Please sign in again.",
            form_data=submitted_data,
        ), 401

    if clerk_user_id is None:
        return render_template(
            "find_ride.html",
            today=today,
            error="Please sign in before submitting a journey.",
            form_data=submitted_data,
        ), 401

    try:
        user = get_user_by_clerk_id(clerk_user_id)

        if user is None:
            return render_template(
                "find_ride.html",
                today=today,
                error="Please complete your SmartRide profile before submitting a journey.",
                form_data=submitted_data,
            ), 403

        if user["account_status"] != "active":
            return render_template(
                "find_ride.html",
                today=today,
                error="Your SmartRide account is not currently active.",
                form_data=submitted_data,
            ), 403

    except Exception:
        app.logger.exception("Unable to retrieve student account")
        return render_template(
            "find_ride.html",
            today=today,
            error="Unable to retrieve your student profile right now.",
            form_data=submitted_data,
        ), 500

    try:
        origin_location = geocode_address(journey["origin"])
        destination_location = geocode_address(journey["destination"])

    except LocationNotFoundError:
        return render_template(
            "find_ride.html",
            today=today,
            error="We couldn't find one of those locations. Please check the addresses and try again.",
            form_data=submitted_data,
        ), 400

    except GeocodingConfigurationError:
        app.logger.exception("Geocoding configuration error")
        return render_template(
            "find_ride.html",
            today=today,
            error="Location search is not configured correctly. Please try again later.",
            form_data=submitted_data,
        ), 500

    except GeocodingError:
        app.logger.exception("Geocoding service unavailable")
        return render_template(
            "find_ride.html",
            today=today,
            error="Location search is temporarily unavailable. Please try again later.",
            form_data=submitted_data,
        ), 503

    try:
        request_id = create_ride_request(
            passenger_id=user["id"],
            origin=journey["origin"],
            destination=journey["destination"],
            origin_latitude=origin_location["latitude"],
            origin_longitude=origin_location["longitude"],
            destination_latitude=destination_location["latitude"],
            destination_longitude=destination_location["longitude"],
            travel_date=journey["travel_date_iso"],
            departure_time=journey["departure_time"],
            passenger_count=journey["passengers"],
            max_detour_minutes=journey["max_detour"],
        )

    except Exception:
        app.logger.exception("Unable to save ride request")
        return render_template(
            "find_ride.html",
            today=today,
            error="We couldn't save your journey right now. Please try again.",
            form_data=submitted_data,
        ), 500

    journey["request_id"] = request_id
    journey["origin_display_name"] = origin_location["display_name"]
    journey["destination_display_name"] = destination_location["display_name"]

    return render_template(
        "ride_results.html",
        journey=journey,
        saved=True,
    ), 201


@app.route("/offer-ride", methods=["GET", "POST"])
def offer_ride():
    """Display and process a driver's ride offer."""
    today = date.today().isoformat()

    if request.method == "GET":
        return render_template("offer_ride.html", today=today)

    offer, submitted_data, error = validate_ride_offer(request.form)

    if error:
        return render_template(
            "offer_ride.html",
            today=today,
            error=error,
            form_data=submitted_data,
        ), 400

    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)

    except Exception:
        app.logger.exception("Ride offer authentication failed")
        return render_template(
            "offer_ride.html",
            today=today,
            error="Unable to verify your account. Please sign in again.",
            form_data=submitted_data,
        ), 401

    if clerk_user_id is None:
        return render_template(
            "offer_ride.html",
            today=today,
            error="Please sign in before publishing a ride offer.",
            form_data=submitted_data,
        ), 401

    try:
        user = get_user_by_clerk_id(clerk_user_id)

        if user is None:
            return render_template(
                "offer_ride.html",
                today=today,
                error="Please complete your SmartRide profile before publishing an offer.",
                form_data=submitted_data,
            ), 403

        # Pending student verification is allowed at this stage.
        # Only suspended or inactive accounts are blocked.
        if user["account_status"] != "active":
            return render_template(
                "offer_ride.html",
                today=today,
                error="Your SmartRide account is not currently active.",
                form_data=submitted_data,
            ), 403

    except Exception:
        app.logger.exception("Unable to retrieve driver account")
        return render_template(
            "offer_ride.html",
            today=today,
            error="Unable to retrieve your profile right now.",
            form_data=submitted_data,
        ), 500

    try:
        origin_location = geocode_address(offer["origin"])
        destination_location = geocode_address(offer["destination"])

    except LocationNotFoundError:
        return render_template(
            "offer_ride.html",
            today=today,
            error="We couldn't find one of those locations. Please check the addresses and try again.",
            form_data=submitted_data,
        ), 400

    except GeocodingConfigurationError:
        app.logger.exception("Ride offer geocoding configuration error")
        return render_template(
            "offer_ride.html",
            today=today,
            error="Location search is not configured correctly. Please try again later.",
            form_data=submitted_data,
        ), 500

    except GeocodingError:
        app.logger.exception("Ride offer geocoding service unavailable")
        return render_template(
            "offer_ride.html",
            today=today,
            error="Location search is temporarily unavailable. Please try again later.",
            form_data=submitted_data,
        ), 503

    try:
        offer_id = create_ride_offer(
            driver_id=user["id"],
            origin=offer["origin"],
            destination=offer["destination"],
            origin_latitude=origin_location["latitude"],
            origin_longitude=origin_location["longitude"],
            destination_latitude=destination_location["latitude"],
            destination_longitude=destination_location["longitude"],
            travel_date=offer["travel_date_iso"],
            departure_time=offer["departure_time"],
            available_seats=offer["available_seats"],
            max_detour_minutes=offer["max_detour"],
        )

    except Exception:
        app.logger.exception("Unable to save driver ride offer")
        return render_template(
            "offer_ride.html",
            today=today,
            error="We couldn't publish your ride offer right now. Please try again.",
            form_data=submitted_data,
        ), 500

    offer["offer_id"] = offer_id
    offer["origin_display_name"] = origin_location["display_name"]
    offer["destination_display_name"] = destination_location["display_name"]

    # Coordinates for the Leaflet journey map
    offer["origin_latitude"] = origin_location["latitude"]
    offer["origin_longitude"] = origin_location["longitude"]
    offer["destination_latitude"] = destination_location["latitude"]
    offer["destination_longitude"] = destination_location["longitude"]

    return render_template(
       "ride_offer_results.html",
        offer=offer,
    ), 201


@app.route("/health")
def health():
    return jsonify({
        "application": "SmartRide",
        "status": "healthy",
    })


@app.route("/api/me", methods=["GET"])
def current_user():
    """Return the verified Clerk identity for the current session."""
    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)
    except Exception:
        app.logger.exception("Clerk authentication failed")
        return jsonify({
            "authenticated": False,
            "error": "Authentication could not be verified.",
        }), 401

    if clerk_user_id is None:
        return jsonify({
            "authenticated": False,
            "error": "Sign-in required.",
        }), 401

    return jsonify({
        "authenticated": True,
        "clerk_user_id": clerk_user_id,
    })


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Retrieve the saved SmartRide profile for the signed-in user."""
    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)

    except Exception:
        app.logger.exception("Profile authentication failed")
        return jsonify({
            "error": "Unable to verify your account.",
        }), 401

    if clerk_user_id is None:
        return jsonify({
            "error": "Sign-in required.",
        }), 401

    try:
        user = get_user_by_clerk_id(clerk_user_id)

        if user is None:
            return jsonify({
                "error": "Student profile not found.",
            }), 404

        profile = {
            "id": user["id"],
            "clerk_user_id": user["clerk_user_id"],
            "display_name": user["display_name"],
            "email": user["email"],
            "university": user["university"],
            "verification_status": user["verification_status"],
            "account_status": user["account_status"],
        }

        return jsonify({
            "profile": profile,
        }), 200

    except Exception:
        app.logger.exception("SmartRide profile retrieval failed")
        return jsonify({
            "error": "Unable to retrieve your profile right now.",
        }), 500


@app.route("/api/profile", methods=["POST"])
def create_profile():
    """Create or retrieve a SmartRide profile for the signed-in user."""
    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)

        if clerk_user_id is None:
            return jsonify({
                "error": "Sign-in required.",
            }), 401

        profile = get_clerk_user_profile(clerk_user_id)

    except Exception:
        app.logger.exception("Profile authentication failed")
        return jsonify({
            "error": "Unable to verify your account.",
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON request body is required.",
        }), 400

    university = data.get("university")

    if not isinstance(university, str) or not university.strip():
        return jsonify({
            "error": "Please provide your university.",
        }), 400

    university = university.strip()

    if len(university) > 150:
        return jsonify({
            "error": "University must be 150 characters or fewer.",
        }), 400

    try:
        user = get_or_create_user(
            clerk_user_id=profile["clerk_user_id"],
            email=profile["email"],
            display_name=profile["display_name"],
            university=university,
        )

        return jsonify({
            "profile": {
                "id": user["id"],
                "clerk_user_id": user["clerk_user_id"],
                "display_name": user["display_name"],
                "email": user["email"],
                "university": user["university"],
                "verification_status": user["verification_status"],
                "account_status": user["account_status"],
            },
        }), 200

    except ValueError as error:
        return jsonify({
            "error": str(error),
        }), 400

    except Exception:
        app.logger.exception("SmartRide profile creation failed")
        return jsonify({
            "error": "Unable to save your profile right now.",
        }), 500


@app.route("/db-health")
def db_health():
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS database_name")
            result = cursor.fetchone()

        return jsonify({
            "application": "SmartRide",
            "database_status": "connected",
            "database": result["database_name"],
        })

    except Exception:
        app.logger.exception("Database health check failed")

        return jsonify({
            "application": "SmartRide",
            "database_status": "unavailable",
        }), 503

    finally:
        if connection is not None:
            connection.close()


@app.route("/api/ride-offers/<int:offer_id>/matches", methods=["GET"])
def get_ride_offer_matches(offer_id):
    """Return ranked potential passenger matches for a driver's offer."""

    try:
        clerk_user_id = get_authenticated_clerk_user_id(request)

    except Exception:
        app.logger.exception("Matching endpoint authentication failed")
        return jsonify({
            "error": "Unable to verify your account.",
        }), 401

    if clerk_user_id is None:
        return jsonify({
            "error": "Sign-in required.",
        }), 401

    try:
        user = get_user_by_clerk_id(clerk_user_id)

        if user is None:
            return jsonify({
                "error": "SmartRide profile not found.",
            }), 403

        if user["account_status"] != "active":
            return jsonify({
                "error": "Your SmartRide account is not currently active.",
            }), 403

        matching_results = find_matching_results_for_offer(
            offer_id=offer_id,
            driver_id=user["id"],
            verify_road_routes=True,
        )

        matches = matching_results["matches"]
        selected_group = matching_results["selected_group"]

        return jsonify({
            "offer_id": offer_id,

            # Individual passenger matches
            "match_count": len(matches),
            "matches": matches,

            # Road-route verification summary
            "matching_status": "road_route_verification",
            "verified_match_count": sum(
                match.get("road_route_status") == "accepted"
                for match in matches
            ),
            "rejected_match_count": sum(
                match.get("road_route_status") == "rejected"
                for match in matches
            ),
            "pending_verification_count": sum(
                match.get("road_route_status") == "unavailable"
                for match in matches
            ),

            # Optimised passenger group
            "selected_group": selected_group,
            "group_size": (
                selected_group["group_size"]
                if selected_group else 0
            ),
            "group_passenger_count": (
                selected_group["passenger_count"]
                if selected_group else 0
            ),
            "group_optimisation_status": (
                matching_results["group_optimisation_status"]
            ),
            "group_optimisation_message": (
                matching_results["group_optimisation_message"]
            ),

            "message": (
                "Potential passenger matches have been screened, "
                "road-route verification has been attempted, "
                "and passenger-group optimisation has been processed."
            ),
        }), 200

    except Exception:
        app.logger.exception("Ride offer matching failed")
        return jsonify({
            "error": "Unable to retrieve potential matches right now.",
        }), 500



if __name__ == "__main__":
    app.run(debug=True)
