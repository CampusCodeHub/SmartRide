# SmartRide - Intelligent Student Ride Group Optimisation

SmartRide is an MSc Computing group project focused on helping students find compatible shared journeys. The long-term goal is to optimise ride groups while respecting route detours, departure times, vehicle capacity and cost-sharing constraints.

This repository currently contains the initial Flask application, responsive frontend pages, journey form validation and automated tests.

## 1. Technology Stack

- **Frontend:** HTML, CSS and JavaScript
- **Backend:** Python and Flask
- **Testing:** pytest
- **Planned database:** TiDB Cloud (MySQL-compatible)
- **Planned maps:** Leaflet and OpenStreetMap

The database, authentication and intelligent ride-matching engine are planned features and are not yet implemented.

## 2. Project Structure

```text
SmartRide/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── home.html
│   ├── find_ride.html
│   └── ride_results.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── scroll.js
└── tests/
    └── test_app.py
```

The `.venv` virtual environment is created locally by each team member and should not be committed to Git.

## 3. Prerequisites

Install Python 3.13 or a compatible Python version supported by the project's dependencies, and install Git.

Check that Python and Git are available:

```powershell
py --version
git --version
```

If the `py` command is unavailable, use the Python installation path configured on your computer.

## 4. Clone the Repository

Open PowerShell or the VS Code terminal and navigate to the folder where you want the project.

Clone the repository:

```powershell
git clone https://github.com/CampusCodeHub/SmartRide.git
cd SmartRide
```

If the repository is private, make sure you have been granted access and authenticate with GitHub when prompted.

## 5. Create a Virtual Environment

On Windows, run:

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this command in the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again.

Alternatively, you can use the environment's Python executable directly without activating it.

## 6. Install Dependencies

With the virtual environment activated, run:

```powershell
python -m pip install -r requirements.txt
```

If the `python` command is unavailable, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This installs the dependencies listed in `requirements.txt`, including Flask and pytest.

## 7. Run SmartRide Locally

Start the Flask development server:

```powershell
python app.py
```

If the `python` command is unavailable, use:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open the application in your browser:

- Homepage: http://127.0.0.1:5000/
- Find a Ride: http://127.0.0.1:5000/find-ride
- Health check: http://127.0.0.1:5000/health

To stop the development server, press `Ctrl+C` in the terminal.

The Flask development server is intended for local development, not production deployment.

## 8. Current Functionality

### Homepage
Displays the SmartRide landing page and project introduction.

### Find a Ride
Allows users to enter:
- Starting location
- Destination
- Travel date
- Departure time
- Maximum additional travel time
- Number of people travelling

The backend validates the submitted journey details.

### Journey Summary
Displays the submitted journey details after successful validation.

### Edit Journey
Allows users to return to the form with their previous values preserved, change their details and submit the updated journey.

### Health Check
The `/health` endpoint returns the application's name and health status.

### Current Limitations
- Ride matching is not implemented.
- Journey submissions are not stored in a database.
- Authentication and user accounts are not implemented.
- Cost estimates and bookings are not yet implemented.

Do not treat the current prototype as a live ride-booking service.

## 9. Run Automated Tests

From the project root, run:

```powershell
python -m pytest -v
```

Alternatively:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The test suite currently covers:
- Homepage loading
- Find a Ride page loading
- Health endpoint response
- Preserving journey details in edit mode
- Rejecting missing locations
- Rejecting past travel dates
- Rejecting invalid passenger counts

The current development checkpoint has seven passing tests. Run the tests on your own machine to verify your local setup.

## 10. Team Git Workflow

Before starting work, check the current branch and working tree:

```powershell
git status
git branch
```

Get the latest changes from the shared repository:

```powershell
git pull origin main
```

Create a separate branch for your feature instead of working directly on `main`:

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

Replace the branch name and commit message with ones appropriate to your task.

Coordinate with the team before integrating changes into `main`. Avoid committing `.venv`, secrets, local configuration files or unrelated changes.

## 11. Planned Development

The project roadmap includes:

1. Project foundation and automated testing
2. Database design and TiDB Cloud integration
3. Authentication and user eligibility
4. Ride offers and ride requests
5. Constraint-aware ride matching and optimisation
6. Explainable recommendations and alternative groups
7. Routing, maps and cost-sharing estimates
8. Bookings, cancellations and dynamic regrouping
9. Accessibility, safety and SmartPoints
10. Integration, evaluation and final demonstration

Features will be implemented incrementally and tested as the project develops.

## 12. Team Responsibilities

- **Frontend/UI:** Raj
- **Backend:** Rohith
- **Optimisation and integration:** Nitin
- **Testing and evaluation:** Nikhil
- **Database:** Solomon

Coordinate API contracts, database changes and shared-file modifications before integrating modules.

---

**SmartRide MSc Computing Project**

Student journeys, made smarter.