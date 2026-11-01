# SmartRide — Intelligent Student Ride Group Optimisation

SmartRide is an MSc Computing group project focused on helping university students find compatible shared journeys. The platform aims to make student travel more affordable, efficient and accessible through intelligent ride-group optimisation.

The long-term goal is to group compatible journeys while respecting route detours, departure times, vehicle capacity, cost-sharing constraints and passenger preferences.

Our main research focus is:

> Can optimisation-based grouping dynamically form student ride groups that minimise individual travel costs while maintaining acceptable route detours, time compatibility and essential safety and accessibility constraints?

---

## Project Status

**Current stage:** Application foundation, authentication, student profiles, database integration and passenger ride-request submission.

The current implementation includes:

- Flask web application.
- Clerk authentication integration.
- Student profile creation and database persistence.
- TiDB Cloud connectivity.
- Passenger journey form validation.
- Address geocoding using OpenStreetMap Nominatim.
- Passenger ride-request persistence in TiDB Cloud.
- Responsive frontend for the homepage, journey form and results page.
- Automated tests covering application routes, authentication, database operations and geocoding.

**Latest recorded test result: 82 tests passed.**

Driver ride offers, intelligent matching, group optimisation and the complete booking workflow remain under development.

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
| HTTP requests | Requests |
| Automated testing | pytest |
| Planned mapping | Leaflet |
| Planned route calculation | OSRM or another suitable routing provider |

## Current Features

### 1. Web application

- SmartRide landing page.
- Find a Ride journey submission page.
- Responsive layouts for desktop, tablet and mobile.
- Journey input validation and editable journey details.
- Journey results page displaying saved request information.
- Application health-check endpoint.

### 2. Authentication and student profiles

- Clerk sign-in and sign-up integration.
- Authenticated API requests.
- Student profile setup with university selection.
- Profile creation and retrieval through TiDB Cloud.
- Initial student verification status tracking.
- Account status handling.

A profile being created does not automatically mean that a student's university eligibility has been verified.

### 3. Passenger ride requests

Passengers can submit journey details including:

- Origin and destination.
- Travel date.
- Departure time.
- Number of passengers.
- Maximum acceptable detour.

The application validates submitted details and checks that the user is authenticated and has an eligible active application profile.

### 4. Address geocoding

SmartRide uses OpenStreetMap Nominatim to convert submitted addresses into geographic coordinates.

The geocoding service includes:

- Address validation.
- Latitude and longitude retrieval.
- Location-not-found handling.
- Request timeout handling.
- Basic in-memory caching.
- Request throttling.
- Error handling for geocoding service failures.

Geocoded coordinates are stored with passenger ride requests.

Nominatim usage must follow its usage policy, including appropriate identification, attribution and request limits.

### 5. Database integration

- Secure configuration using environment variables.
- TLS-enabled TiDB Cloud connections.
- User and profile persistence.
- Passenger ride-request persistence.
- Database connectivity verification.
- Database operations with transaction handling.

The current database schema also contains tables for future driver and booking functionality.

### 6. Automated testing

The project includes automated tests covering:

- Flask application routes.
- Journey validation and submission.
- Authentication and profile routes.
- Database operations.
- Geocoding behaviour and error handling.

Run the test suite locally to verify the current implementation.

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
│   └── geocoding.py
│
├── templates/
│   ├── home.html
│   ├── find_ride.html
│   └── ride_results.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── clerk-auth.js
│       └── scroll.js
│
└── tests/
    ├── test_app.py
    ├── test_auth.py
    ├── test_auth_routes.py
    ├── test_clerk_profile.py
    ├── test_db.py
    ├── test_geocoding.py
    └── test_profile_routes.py
```

The local `.venv` directory, `.env` file, Python cache directories and other generated files should not be committed to Git.

---

## Prerequisites

Install the following:

- Python 3.13.
- Git.
- Visual Studio Code or another suitable code editor.
- A TiDB Cloud account and configured database.
- A Clerk development application.

Check your installations in PowerShell:

```powershell
py --version
git --version
```

If `py` is unavailable, use the Python executable installed on your computer.

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

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again.

Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

Alternatively, use the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure Environment Variables

SmartRide uses a local `.env` file for database credentials, Clerk keys and geocoding configuration.

Create a file named `.env` in the project root.

Example configuration:

```dotenv
TIDB_HOST=your_tidb_host
TIDB_PORT=4000
TIDB_USER=your_tidb_username
TIDB_PASSWORD=your_tidb_password
TIDB_DATABASE=your_database_name

CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

NOMINATIM_URL=https://nominatim.openstreetmap.org/search
NOMINATIM_USER_AGENT=SmartRide/1.0 (contact: your_real_contact_email)
```

Replace the placeholder values with your own credentials and contact information.

Before running the application, ensure that:

- Your TiDB Cloud database and required tables are available.
- Database credentials and network access are configured.
- Your Clerk application keys are valid.
- Clerk is configured for your local development origin.
- The Nominatim User-Agent contains an appropriate contact address.

**Security considerations:**

- Never commit `.env`, database passwords or Clerk secret keys.
- Keep `.env` excluded through `.gitignore`.
- Do not expose secret credentials in frontend JavaScript.
- Do not use development credentials for production deployment.
- Follow the usage policy of external services.

## Run SmartRide Locally

Start the Flask development server:

```powershell
python app.py
```

Open the following URLs:

| Page | URL |
|---|---|
| Homepage | http://127.0.0.1:5000/ |
| Find a Ride | http://127.0.0.1:5000/find-ride |
| Application health check | http://127.0.0.1:5000/health |
| Database health check | http://127.0.0.1:5000/db-health |

The Flask development server is intended for local development, not production hosting.

Stop the server using `Ctrl+C`.

## Verify the TiDB Connection

Ensure that your `.env` values are configured, then run:

```powershell
python test_tidb_connection.py
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe test_tidb_connection.py
```

A successful check should report the connected database and TiDB version.

If the connection fails, check:

- Database credentials.
- TLS configuration.
- TiDB Cloud network access.
- Database availability.

## Run Automated Tests

From the project root, run:

```powershell
python -m pytest -v
```

Or use:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The latest recorded development checkpoint passed:

**82 passed.**

Test results may change as the application develops. Always run the test suite locally before committing changes.

---

## Database Overview

The current TiDB database contains the following main tables:

| Table | Purpose |
|---|---|
| `users` | User accounts and student profile information |
| `ride_requests` | Passenger journey requests |
| `ride_offers` | Planned driver journeys |
| `ride_groups` | Proposed shared journey groups |
| `ride_group_members` | Passenger membership within groups |
| `bookings` | Passenger booking records |

The existence of a database table does not mean its corresponding application functionality has already been implemented.

At the current development stage, passenger ride requests can be submitted and stored. Driver ride offers, group formation and booking workflows remain future development tasks.

---

## Current Limitations

The following capabilities are not yet complete:

- Driver profile and eligibility workflows.
- Driver ride-offer submission and management.
- Intelligent ride-group matching.
- Detour-aware pickup and drop-off sequencing.
- Live route calculation and interactive map integration.
- Explainable match recommendations.
- Complete booking and cancellation workflows.
- Cost-sharing calculations and payment integration.
- Production-ready student and driver verification.
- SmartPoints rewards.
- Full accessibility and safety workflows.
- Production deployment and operational monitoring.

SmartRide is currently a development prototype, not a live ride-booking service.

---

## Planned Development Roadmap

1. Complete the application foundation and automated tests.
2. Improve authentication and student profile management.
3. Complete passenger ride-request functionality.
4. Implement driver profiles and ride offers.
5. Develop constraint-aware ride-group optimisation.
6. Add explainable recommendations and alternative groups.
7. Integrate mapping and route calculation.
8. Implement cost-sharing estimates.
9. Develop bookings, cancellations and dynamic regrouping.
10. Add accessibility, safety and SmartPoints features.
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

Check your current branch and working tree:

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

After implementing and testing your changes:

```powershell
git status
git add <your-changed-files>
git commit -m "Describe your changes"
git push -u origin feature/your-feature-name
```

Replace the example branch name and commit message with appropriate values.

Coordinate with the team before merging changes into `main`.

Avoid committing secrets, virtual environments, generated files or unrelated changes.

---

## Project Repository

GitHub: https://github.com/CampusCodeHub/SmartRide

---

**SmartRide — MSc Computing Group Project**

*Student journeys, made smarter.*