
import os
from datetime import date, time

from flask import Flask, jsonify, render_template, request

from auth import (
    get_authenticated_clerk_user_id,
    get_clerk_user_profile,
)
from db import get_db_connection, get_or_create_user


app = Flask(__name__)


@app.route("/")
def home():
    return render_template(
        "home.html",
        clerk_publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY", ""),
    )


@app.route("/find-ride", methods=["GET"])
def find_ride():
    today = date.today().isoformat()
    form_data = request.args

    # Open a blank form when no journey details are provided.
    if not request.args or not any(request.args.values()):
        return render_template("find_ride.html", today=today)

    # When editing, reopen the form with the existing details.
    if request.args.get("edit") == "1":
        return render_template(
            "find_ride.html",
            today=today,
            form_data=form_data,
        )

    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get("travel_date", "")
    departure_time = request.args.get("departure_time", "")
    max_detour = request.args.get("max_detour", "")
    passengers = request.args.get("passengers", "")

    error = None
    selected_date = None

    # Validate locations.
    if not origin or not destination:
        error = "Starting location and destination are required."
    elif len(origin) > 200 or len(destination) > 200:
        error = "Locations must be 200 characters or fewer."

    # Validate the travel date.
    if error is None:
        try:
            selected_date = date.fromisoformat(travel_date)
        except ValueError:
            error = "Please provide a valid travel date."
        else:
            if selected_date < date.today():
                error = "Travel date cannot be in the past."

    # Validate the departure time.
    if error is None:
        try:
            time.fromisoformat(departure_time)
        except ValueError:
            error = "Please provide a valid departure time."

    # Validate the selected options.
    if error is None and max_detour not in {"5", "10", "15", "20", "30"}:
        error = "Please select a valid maximum extra travel time."

    if error is None and passengers not in {"1", "2", "3", "4", "5"}:
        error = "Please select a valid passenger count."

    # Redisplay the form with submitted values if validation fails.
    if error:
        submitted_form_data = {
            "origin": origin,
            "destination": destination,
            "travel_date": travel_date,
            "departure_time": departure_time,
            "max_detour": max_detour,
            "passengers": passengers,
        }

        return render_template(
            "find_ride.html",
            today=today,
            error=error,
            form_data=submitted_form_data,
        ), 400

    journey = {
        "origin": origin,
        "destination": destination,
        "travel_date": selected_date.strftime("%d %B %Y"),
        "travel_date_iso": selected_date.isoformat(),
        "departure_time": departure_time,
        "max_detour": int(max_detour),
        "passengers": int(passengers),
    }

    return render_template("ride_results.html", journey=journey)


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
