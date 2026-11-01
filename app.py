
import os
from datetime import date, time

from flask import Flask, jsonify, render_template, request

from auth import (
    get_authenticated_clerk_user_id,
    get_clerk_user_profile,
)
from db import (
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


def validate_journey(data):
    """Validate submitted journey details and return cleaned values."""
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


@app.route("/")
def home():
    return render_template(
        "home.html",
        clerk_publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY", ""),
    )


@app.route("/find-ride", methods=["GET", "POST"])
def find_ride():
    today = date.today().isoformat()

    # GET requests display the blank form or reopen an existing journey.
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

        # Preserve the existing GET validation behaviour.
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

    # POST requests are the only requests that save journeys.
    journey, submitted_data, error = validate_journey(request.form)

    if error:
        return render_template(
            "find_ride.html",
            today=today,
            error=error,
            form_data=submitted_data,
        ), 400

    # Verify the student's Clerk identity.
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

    # Retrieve the internal SmartRide user ID from the verified Clerk ID.
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

    # Convert both addresses into geographic coordinates.
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

    # Save the complete request using the internal database user ID.
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


if __name__ == "__main__":
    app.run(debug=True)
