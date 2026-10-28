
# SmartRide — Intelligent Student Ride Group Optimisation

SmartRide is an MSc Computing group project focused on helping university students find compatible shared journeys. The project aims to make student travel more affordable, efficient and accessible through intelligent ride-group optimisation.

The long-term goal is to group compatible journeys while respecting route detours, departure times, vehicle capacity, cost-sharing constraints and passenger preferences.

## Project Status

**Current stage:** Application foundation, authentication, student profiles and database integration.

The current implementation includes a Flask web application, journey form validation, Clerk authentication, student profile saving and TiDB Cloud connectivity. Intelligent ride matching and the full booking workflow remain under development.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML5, CSS3 and JavaScript |
| Backend | Python and Flask |
| Authentication | Clerk |
| Database | TiDB Cloud (MySQL-compatible) |
| Database driver | PyMySQL |
| Environment configuration | python-dotenv |
| Automated testing | pytest |
| Planned mapping | Leaflet and OpenStreetMap |

## Current Features

### Web application
- SmartRide landing page.
- Find a Ride form with journey details.
- Journey input validation and editable journey summaries.
- Health-check endpoint for basic application status.

### Authentication and student profiles
- Clerk sign-in and sign-up integration.
- Authenticated API requests.
- Student profile setup with university selection.
- Profile creation in TiDB Cloud.
- Student verification status tracking, including the initial `pending` status.

### Database integration
- Secure configuration through environment variables.
- TLS-enabled TiDB Cloud connections.
- Database tables for users, ride requests, ride offers, ride groups, bookings, cost shares and SmartPoints transactions.
- A standalone database connectivity check.

### Automated testing
- Flask application route tests.
- Journey validation and editing tests.
- Authentication and API tests.
- Database-related tests using the project's test suite.

Run the tests locally to verify the current result.

## Project Structure

```text
SmartRide/
├── app.py
├── auth.py
├── db.py
├── requirements.txt
├── README.md
├── .gitignore
├── test_tidb_connection.py
├── templates/
│   ├── home.html
│   ├── find_ride.html
│   └── ride_results.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── clerk-auth.js
│       └── scroll.js
└── tests/
    └── test_app.py
```

The local `.venv` directory and `.env` file must not be committed to Git.

## Prerequisites

Install:
- Python 3.13, matching the development environment.
- Git.
- Visual Studio Code or another suitable editor.

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

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If necessary, use the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure Environment Variables

SmartRide uses a local `.env` file for database credentials and Clerk keys.

Create a file named `.env` in the project root:

```dotenv
TIDB_HOST=your_tidb_host
TIDB_PORT=4000
TIDB_USER=your_tidb_username
TIDB_PASSWORD=your_tidb_password
TIDB_DATABASE=your_database_name

CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
```

Replace the placeholder values with the credentials from your own TiDB Cloud and Clerk development applications.

Before running the application, ensure that:
- Your TiDB Cloud database and required tables are available.
- Your database credentials and network access are configured.
- Your Clerk application keys are valid.
- The Clerk application is configured for the local development origin.

**Security:** Never commit `.env`, database passwords or Clerk secret keys. The `.env` file should remain excluded through `.gitignore`. Do not use development credentials for production deployment.

## Run SmartRide Locally

Start the Flask development server:

```powershell
python app.py
```

Open these local URLs:

| Page | URL |
|---|---|
| Homepage | http://127.0.0.1:5000/ |
| Find a Ride | http://127.0.0.1:5000/find-ride |
| Health check | http://127.0.0.1:5000/health |

The Flask development server is for local development only, not production hosting. Stop it with `Ctrl+C`.

## Verify the TiDB Connection

Ensure your `.env` values are configured, then run:

```powershell
python test_tidb_connection.py
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe test_tidb_connection.py
```

A successful check reports the connected database and TiDB version. If it fails, check your credentials, TLS configuration and TiDB Cloud network access.

## Run Automated Tests

From the project root, run:

```powershell
python -m pytest -v
```

Or use:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The latest recorded development checkpoint passed **39 tests**. Test results can change as the application develops, so run the suite locally to verify the current code.

## Current Limitations

The following capabilities are not yet complete:
- Intelligent ride-group matching and route optimisation.
- Live route calculation and map integration.
- Finalised detour-aware group recommendations.
- Complete ride booking, cancellation and payment workflows.
- Production-ready student verification.
- Full SmartPoints rewards and accessibility workflows.
- Production deployment and operational monitoring.

The current application is a development prototype, not a live ride-booking service. A `pending` verification status does not mean that a student's eligibility has been confirmed.

## Planned Development Roadmap

1. Complete the application foundation and automated tests.
2. Improve authentication and student profile management.
3. Integrate and validate the database models.
4. Implement ride offers and ride requests.
5. Develop constraint-aware ride-group optimisation.
6. Add explainable recommendations and alternative groups.
7. Integrate mapping, routing and cost-sharing estimates.
8. Implement bookings, cancellations and dynamic regrouping.
9. Develop accessibility, safety and SmartPoints features.
10. Complete integration testing, evaluation and demonstration.

## Team Responsibilities

| Team member | Main responsibility |
|---|---|
| Raj | Frontend and user interface |
| Rohith | Backend development |
| Nitin | Optimisation and integration |
| Solomon | Database development |
| Nikhil | Quality assurance and evaluation |

Team members should coordinate API contracts, database changes and shared-file modifications before integration.

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

Create a branch for your work:

```powershell
git switch -c feature/your-feature-name
```

After implementing and testing your changes:

```powershell
git status
git add .
git commit -m "Describe your changes"
git push -u origin feature/your-feature-name
```

Replace the example branch name and commit message with appropriate values. Coordinate with the team before merging changes into `main`. Avoid committing secrets, virtual environments or unrelated files.

---

**SmartRide — MSc Computing Group Project**

*Student journeys, made smarter.*
