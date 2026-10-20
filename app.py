from datetime import date, time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/find-ride", methods=["GET"])
def find_ride():
    today = date.today().isoformat()

    # Collect submitted journey details.
    form_data = request.args

    # Open a blank form when no journey details are provided.
    if not request.args or not any(request.args.values()):
        return render_template("find_ride.html", today=today)

    # When editing, reopen the form with the existing details.
    if request.args.get("edit") == "1":
        return render_template(
            "find_ride.html",
            today=today,
            form_data=form_data
        )

    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get("travel_date", "")
    departure_time = request.args.get("departure_time", "")
    max_detour = request.args.get("max_detour", "")
    passengers = request.args.get("passengers", "")

    error = None

    # Validate locations.
    if not origin or not destination:
        error = "Starting location and destination are required."
    elif len(origin) > 200 or len(destination) > 200:
        error = "Locations must be 200 characters or fewer."

    # Validate the travel date.
    selected_date = None

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
        return render_template(
            "find_ride.html",
            today=today,
            error=error,
            form_data=form_data
        ), 400

    # Prepare journey details for the results page.
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
        "status": "healthy"
    })


if __name__ == "__main__":
    app.run(debug=True)