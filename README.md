# SuperQuest

SuperQuest is an original superhero mission game built with Flask. Choose a power, solve timed field challenges, earn score and experience, unlock achievements, and climb a database-backed leaderboard. The app uses original names and CSS-built artwork; it does not depend on external game images or paid services.

## Features

- Player registration and login with Werkzeug password hashing, Flask-Login sessions, CSRF-protected forms, and duplicate account checks.
- Five selectable powers with distinct gameplay effects.
- Three seeded missions, with Neon Harbor Evacuation playable as a timed five-question challenge.
- Server-owned attempt state, answer validation, scoring, score persistence, experience/levels, and achievements. Client-submitted scores are ignored; completed attempts cannot be rewarded twice.
- Player dashboard, profile/history, achievement collection, and database-backed leaderboard.
- Administrator dashboard with user activation controls, mission create/activate/deactivate/delete actions, attempt overview, and achievement overview. Admin accounts are created only through the CLI.
- SQLite by default; PostgreSQL URLs are normalized for psycopg. Other SQLAlchemy dialects may be configurable when the matching dialect and driver are installed, but Oracle deployment is not certified by this project.
- Responsive HTML/CSS/JavaScript interface, custom error pages, pytest suite, and Render configuration.

## Technology

Python 3, Flask, Flask-SQLAlchemy/SQLAlchemy, Flask-Login, Flask-WTF CSRF, Jinja2, SQLite, PostgreSQL (psycopg), pytest, Gunicorn.

## Project layout

```text
app/
  admin/       Administrator routes and access control
  auth/        Registration, login, logout
  game/        Attempt lifecycle and score rules
  main/        Dashboard, powers, profile, leaderboard
  static/      Responsive CSS and small JavaScript enhancements
  templates/   Jinja pages
  extensions.py
  models.py
tests/         Isolated pytest application tests
config.py      Environment-backed configuration
run.py         WSGI application entry point
```

## Run locally on Windows PowerShell

Use Python 3.10 or newer. From the project root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a private random `SECRET_KEY`. The example uses SQLite and works locally. The application creates the SQLite tables and starter content on first startup. Explicit setup commands are also available:

```powershell
flask --app run init-db
flask --app run seed
```

Seeding is idempotent. It adds missing original powers, missions, and achievements without duplicating existing records.

Create the initial administrator from a private terminal prompt. You will be prompted for a username, email, and password; no default credentials exist:

```powershell
flask --app run create-admin
```

Start the development server:

```powershell
flask --app run run --debug
```

Then visit `http://127.0.0.1:5000`. A player registers through the landing page, selects a power, opens the mission board, and launches Neon Harbor Evacuation.

## Scoring rules

- Each question is worth an equal share of the mission's `base_reward`, rounded to the nearest integer.
- Super Strength adds 10% to the earned score.
- Velocity adds up to 20 points based on remaining time, only when at least one answer is correct.
- Energy Shield forgives one wrong answer for scoring only when the player gets all but one question correct. It does not change the recorded correct count or perfect-run achievement.
- Telekinesis can eliminate one randomly chosen incorrect option on the first question, once per attempt.
- Elemental Control adds 15% to a perfect-run score.
- Answers submitted later than the mission time limit plus a 15-second network allowance receive zero. The server measures elapsed time from the persisted attempt start; the browser timer is a convenience, not a trusted score input.
- Every valid submission transitions its attempt from `started` to `completed` in one database transaction. A later submission redirects to the existing result and cannot add score again.
- Experience increases by points earned; level is `experience_points // 500 + 1`.
- Achievements are awarded from server-calculated completed mission count, total score, and true correct-answer count.
- Leaderboard order is score descending, then level descending, then username ascending for deterministic ties.

The seeded missions share the starter challenge question set. The admin form creates missions using that question set; editing the actual question bank is not exposed in the current admin UI.

## Tests

Tests use a separate in-memory SQLite database; they do not read or modify the local game database.

```powershell
python -m pytest -q
```

Coverage includes app startup, registration/login, duplicate users, password hashing, protected routes, mission and power flow, server-side scoring, malformed answer rejection, duplicate reward prevention, achievements, Telekinesis hint use, admin access/mission creation, and leaderboard ranking.

## Configuration and production

Supported environment variables:

- `SECRET_KEY`: required private production secret.
- `DATABASE_URL`: defaults to `sqlite:///superquest.db`. For PostgreSQL use a SQLAlchemy PostgreSQL URL, for example `postgresql://user:password@host:5432/dbname`; it is adapted to psycopg.
- `SESSION_COOKIE_SECURE`: set to `true` behind HTTPS.

`Procfile` and `render.yaml` use Gunicorn and a Render-managed PostgreSQL database. Deploy by creating the Render Blueprint from `render.yaml`; set any deployment-specific environment values in the Render dashboard. After deployment, run `flask --app run seed` and `flask --app run create-admin` in the service shell (or equivalent one-off command) to provision content and the initial administrator. Keep the database persistent; local SQLite on an ephemeral cloud filesystem is not suitable for production data.

Do not reuse the development secret or commit `.env`. Set secure cookies when HTTPS is enabled. Use database backups and restrict administrator credentials. Oracle may be considered by setting a suitable SQLAlchemy dialect URL and installing a compatible driver, but this repository does not claim turnkey Oracle support.

## Troubleshooting

- If PowerShell blocks venv activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` in a PowerShell session you control, or use `.venv\Scripts\python.exe` directly.
- If imports fail, confirm the venv is activated and rerun `python -m pip install -r requirements.txt`.
- If PostgreSQL cannot connect, verify the full `DATABASE_URL`, network access, and installed driver.
- For local database resets during development only, stop the app and remove `instance/superquest.db`; this deletes local player data.
- For an expired form message, reload the page to obtain a fresh CSRF token.