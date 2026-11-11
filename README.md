# SmartRide - Intelligent Student Ride Group Optimisation

**Student journeys, made smarter.**

SmartRide is an MSc Computing group project focused on developing an intelligent carpooling platform exclusively for university students.

The platform connects students travelling along compatible routes and helps drivers share available vehicle seats with other students. Its main objective is to make student travel more affordable, efficient and accessible through intelligent passenger matching and route-based group optimisation.

The project's central differentiator is its **explainable ride-group optimisation engine**, which evaluates possible passenger combinations while considering vehicle capacity, journey duration, route detours and individual passenger constraints.

---

## Project Status

**Current development stage:** Core application, authentication, database integration, driver ride offers, passenger matching, road-route verification and group optimisation.

### Implemented functionality

- Flask web application and responsive frontend.
- Clerk authentication integration.
- Student profile creation and database persistence.
- TiDB Cloud database connectivity.
- Passenger ride-request submission.
- Driver ride-offer submission.
- Address geocoding using OpenStreetMap Nominatim.
- Geographic passenger matching.
- Departure-time and vehicle-capacity checks.
- Road-route verification using OSRM.
- Passenger detour validation.
- Intelligent passenger group selection.
- Optimised pickup and drop-off sequencing.
- Matching results dashboard.
- Interactive Leaflet maps.
- Automated backend and algorithm tests.

**Latest recorded test result: 169 tests passed.**

The application has also been tested in a browser, including the passenger matching and group optimisation results.

### Remaining development work

Student and driver verification workflows, women-only matching, accessibility features, ratings, SmartPoints, complete booking management and cost-sharing functionality remain part of the planned development.

SmartRide is currently a development prototype, not a live ride-booking service.

---

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML5, CSS3 and JavaScript |
| Backend | Python 3.13 and Flask |
| Authentication | Clerk |
| Database | TiDB Cloud (MySQL-compatible) |
| Database driver | PyMySQL |
| Environment configuration | python-dotenv |
| Address geocoding | OpenStreetMap Nominatim |
| Mapping | Leaflet |
| Map data | OpenStreetMap |
| Road routing | OSRM |
| HTTP requests | Requests |
| Automated testing | pytest |

---

## Core Features

### 1. Web Application

- SmartRide landing page.
- Find a Ride journey submission page.
- Offer a Ride journey submission page.
- Ride request and offer results pages.
- Responsive frontend layouts.
- Journey input validation.
- Interactive matching results dashboard.
- Application health-check endpoint.

### 2. Authentication and Student Profiles

- Clerk sign-in and sign-up integration.
- Authenticated API requests using Clerk session tokens.
- Student profile creation and retrieval.
- University information stored in TiDB Cloud.
- Account status handling.
- Profile validation before journey submission.

Creating a profile does not automatically establish that a student's university eligibility has been independently verified.

### 3. Passenger Ride Requests

Passengers can submit:

- Starting location.
- Destination.
- Travel date.
- Departure time.
- Number of passengers.
- Maximum acceptable detour.

The application validates journey information, checks authentication and profile requirements, geocodes the submitted locations and stores the journey request in the database.

### 4. Driver Ride Offers

Drivers can publish journeys containing:

- Starting location.
- Destination.
- Travel date.
- Departure time.
- Available vehicle seats.
- Maximum acceptable detour.

Ride offers are validated and stored in TiDB Cloud for subsequent matching.

### 5. Intelligent Passenger Matching

SmartRide includes a passenger matching engine that identifies potentially compatible ride requests for a driver's published journey.

The initial matching stage considers:

- Journey date compatibility.
- Departure-time compatibility.
- Available vehicle capacity.
- Passenger pickup proximity to the driver's route.
- Passenger drop-off proximity to the driver's route.
- Pickup and drop-off ordering.
- Matching scores.

The system uses geographical distance calculations based on the Haversine formula to screen potential matches.

Compatible requests are ranked using their pickup distance, drop-off distance and departure-time difference.

This initial screening identifies potential matches; it does not by itself guarantee that a complete road journey is feasible.

### 6. Road-Route Verification

SmartRide integrates OSRM to evaluate actual road routes.

The verification process considers:

- Driver journey duration.
- Passenger pickup and drop-off locations.
- Additional journey time.
- Individual passenger detour limits.
- Route accessibility and reachability.

The system uses road-route information to verify potential matches rather than relying exclusively on straight-line geographical distances.

### 7. Intelligent Group Optimisation

**This is the central research and technical feature of SmartRide.**

Rather than simply matching passengers travelling in a similar direction, the optimisation engine evaluates different possible combinations of passenger requests.

The algorithm considers:

1. Available vehicle seats.
2. Passenger counts within each request.
3. Maximum supported passenger requests.
4. Pickup and drop-off coordinates.
5. Individual passenger detour limits.
6. Original driver journey duration.
7. Shared journey duration.
8. Additional travel time.

The implementation evaluates possible passenger combinations and valid pickup/drop-off sequences.

It uses an OSRM duration matrix to evaluate route legs efficiently and avoid making a separate matrix request for every possible sequence.

The group selection process prioritises:

- The highest feasible passenger count.
- The lowest additional travel time.
- The shortest shared journey duration.
- Consistent selection when multiple combinations have equivalent results.

The current implementation supports evaluating up to four passenger requests in a group and screens up to ten matching candidates.

The selected group includes information about its passengers, route stops, journey duration and additional travel time.

### 8. Matching Results Dashboard and Maps

The driver-facing matching results page displays:

- Potential passenger requests.
- Passenger counts.
- Pickup and drop-off information.
- Matching and road-verification results.
- Selected passenger group.
- Original journey duration.
- Shared journey duration.
- Additional travel time.
- Maximum detour.
- Optimised group information.

Leaflet is used to display the journey map and passenger location markers, with OpenStreetMap providing map data.

The interface also communicates that an optimisation recommendation is not the same as a confirmed passenger booking.

### 9. Address Geocoding

SmartRide uses OpenStreetMap Nominatim to convert submitted addresses into geographic coordinates.

The geocoding service includes:

- Address validation.
- Latitude and longitude retrieval.
- Location-not-found handling.
- Request timeout handling.
- In-memory caching.
- Request throttling.
- External service error handling.

Nominatim usage must follow its usage policy, including appropriate identification, attribution and request limits.

### 10. Database Integration

TiDB Cloud provides persistent storage for application data.

Implemented database functionality includes:

- User and student profile persistence.
- Passenger ride-request persistence.
- Driver ride-offer persistence.
- Database connectivity verification.
- Transaction handling and rollback on failures.
- Geographic coordinate validation.

The database also contains supporting structures for planned group and booking functionality. The existence of a database table does not necessarily mean its complete application workflow has been implemented.

---

## Group Optimisation Workflow

The main matching and optimisation process can be represented as follows:

```text
Driver publishes a ride offer
              |
              v
Retrieve compatible passenger requests
              |
              v
Initial geographical and time screening
              |
              v
Verify passenger routes using OSRM
              |
              v
Prepare feasible group candidates
              |
              v
Generate possible passenger combinations
              |
              v
Check vehicle capacity and detour limits
              |
              v
Evaluate route durations and sequences
              |
              v
Rank feasible passenger groups
              |
              v
Select the best feasible group
              |
              v
Display recommendation and route details
```

The system separates initial geographical screening from actual road-route verification and group optimisation.

This provides a structured approach to evaluating passenger compatibility and explaining why a particular group is recommended.

---

## Project Structure

```text
SmartRide/
│
├── app.py
├── auth.py
├── db.py
├── requirements.txt
├── README.md
├── .gitignore
├── test_tidb_connection.py
│
├── services/
│   ├── __init__.py
│   ├── geocoding.py
│   ├── matching.py
│   ├── matching_service.py
│   ├── route_verification.py
│   ├── group_optimisation.py
│   ├── group_route_optimiser.py
│   └── group_selection.py
│
├── templates/
│   ├── home.html
│   ├── find_ride.html
│   ├── ride_results.html
│   ├── offer_ride.html
│   └── ride_offer_results.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       ├── clerk-auth.js
│       ├── journey-auth.js
│       ├── ride-matches.js
│       └── scroll.js
│
└── tests/
    ├── test_app.py
    ├── test_auth.py
    ├── test_auth_routes.py
    ├── test_clerk_profile.py
    ├── test_db.py
    ├── test_geocoding.py
    ├── test_matching.py
    ├── test_matching_service.py
    ├── test_group_optimisation.py
    ├── test_group_route_optimiser.py
    ├── test_group_selection.py
    ├── test_route_verification.py
    └── test_profile_routes.py
```

The local `.venv` directory, `.env` file, Python cache directories and generated files should not be committed to Git.

---

## Prerequisites

Install the following:

- Python 3.13.
- Git.
- Visual Studio Code or another suitable code editor.
- A TiDB Cloud account with a configured database.
- A Clerk development application.

Check the installations:

```powershell
py --version
git --version
```

## Clone the Repository

```powershell
git clone https://github.com/CampusCodeHub/SmartRide.git

cd SmartRide
```

If the repository is private, obtain access from the repository owner first.

## Set Up the Python Environment

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Alternatively, use the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure Environment Variables

Create a `.env` file in the project root.

Example configuration:

```dotenv
TIDB_HOST=your_tidb_host
TIDB_PORT=4000
TIDB_USER=your_tidb_username
TIDB_PASSWORD=your_tidb_password
TIDB_DATABASE=your_database_name

CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_AUTHORIZED_PARTIES=http://127.0.0.1:5000

NOMINATIM_URL=https://nominatim.openstreetmap.org/search
NOMINATIM_USER_AGENT=SmartRide/1.0 (contact: your_real_contact_email)
```

Replace the placeholders with your actual configuration.

Before running the application, ensure:

- Your TiDB Cloud database and required tables are available.
- Database credentials and network access are configured.
- Your Clerk application keys are valid.
- Clerk is configured for your local development origin.
- Your Nominatim User-Agent contains an appropriate contact address.

**Security considerations:**

- Never commit `.env`, database passwords or Clerk secret keys.
- Keep `.env` excluded through `.gitignore`.
- Never expose secret credentials in frontend JavaScript.
- Do not use development credentials for production deployment.
- Follow the usage policies of external services.

## Run SmartRide Locally

Start the Flask development server:

```powershell
python app.py
```

Open the application:

| Page | URL |
|---|---|
| Homepage | http://127.0.0.1:5000/ |
| Find a Ride | http://127.0.0.1:5000/find-ride |
| Offer a Ride | http://127.0.0.1:5000/offer-ride |
| Application health | http://127.0.0.1:5000/health |
| Database health | http://127.0.0.1:5000/db-health |

The Flask development server is intended for local development, not production hosting.

Stop the server using `Ctrl+C`.

## Verify the TiDB Connection

Ensure your `.env` values are configured, then run:

```powershell
python test_tidb_connection.py
```

A successful check should report the connected database and TiDB version.

If the connection fails, check:

- Database credentials.
- TLS configuration.
- TiDB Cloud network access.
- Database availability.

## Run Automated Tests

From the project root:

```powershell
python -m pytest -v
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

**Latest recorded development checkpoint:**

```text
169 passed
```

The test suite covers:

- Flask application routes.
- Authentication and profile management.
- Database operations.
- Journey validation and submission.
- Address geocoding.
- Individual passenger matching.
- Group optimisation.
- Passenger group selection.
- Route verification.

Test results may change as the application develops. Always run the test suite locally before committing changes.

---

## Current Limitations and Future Development

The following capabilities remain planned or require further development:

- Complete university student verification.
- Driver eligibility and driving licence verification.
- Women-only ride matching.
- Accessibility-based passenger matching.
- Ratings and feedback.
- SmartPoints rewards.
- Complete booking and cancellation workflows.
- Cost-sharing calculations.
- Payment integration.
- Dynamic regrouping and alternative group recommendations.
- Production deployment and operational monitoring.
- Extensive testing with multiple simultaneous passenger requests.

SmartRide is a development prototype. Matching recommendations do not represent confirmed bookings, and the application is not yet a production-ready transport service.

---

## Development Roadmap

1. Complete the application foundation and authentication.
2. Develop student and driver verification workflows.
3. Expand passenger and driver journey management.
4. Improve passenger matching and route compatibility.
5. Evaluate and refine the group optimisation algorithm.
6. Add explainable recommendations and alternative groups.
7. Develop cost-sharing calculations.
8. Implement booking and cancellation workflows.
9. Add accessibility and women-only travel preferences.
10. Introduce ratings, feedback and SmartPoints.
11. Complete integration testing, evaluation and project demonstration.

---

## Team Responsibilities

| Team member | Main responsibility |
|---|---|
| Raj | Frontend and user interface |
| Rohith | Backend development |
| Nitin | Optimisation and integration |
| Solomon | Database development |
| Nikhil | Quality assurance and evaluation |

Team members should coordinate API contracts, database changes and shared-file modifications before integration.

---

## Git Workflow

Check the current branch and working tree:

```powershell
git status
git branch
```

Retrieve the latest changes:

```powershell
git pull origin main
```

Create a feature branch:

```powershell
git switch -c feature/your-feature-name
```

After implementing and testing changes:

```powershell
git status

git add <your-changed-files>

git commit -m "Describe your changes"

git push -u origin feature/your-feature-name
```

Coordinate with the team before merging changes into `main`.

Avoid committing secrets, virtual environments, generated files or unrelated changes.

---

## Project Repository

GitHub: https://github.com/CampusCodeHub/SmartRide

**SmartRide — MSc Computing Group Project**

*Student journeys, made smarter.*
