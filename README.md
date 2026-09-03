# ACME Salary Management

Employee salary management system for a 10,000-employee, multi-country
organization. See [`docs/requirements.md`](docs/requirements.md) for full
scope and reasoning, and [`docs/design-notes.md`](docs/design-notes.md) for
trade-off decisions made along the way.

## Stack

- **Backend**: Python, FastAPI, SQLite, SQLModel
- **Frontend**: React + Vite + TypeScript, MUI (analytics dashboard)
- **Auth**: JWT-based, custom
- **Containerization**: Docker Compose

## Running with Docker Compose

1. Copy the env file and fill in values as needed (defaults work out of the
   box for local development):

   ```
   cp .env.example .env
   ```

2. Start both services:

   ```
   docker compose up --build
   ```

   `--build` matters here, not just on the first run: `node_modules` and the
   Python venv are baked into each image at build time, not volume-mounted
   (mounting them risks host/container native-binary mismatches), so a
   dependency change (new npm/pip package) needs a rebuild to actually take
   effect — a plain `docker compose up` will silently keep using the old
   image and error on the missing package.

3. Open the app:

   - Frontend: http://localhost:5173
   - Backend health check: http://localhost:8000/health

The frontend landing page calls the backend's `/health` endpoint on load and
displays the result, to confirm the two services are wired together.

**No manual seed step is needed.** On first startup against an empty
database, the backend automatically seeds 10,000 correlated employees,
salary history, and the 3 demo users below — so `docker compose up` alone
gives you a fully populated dashboard. On later restarts it detects the
existing data and skips, so nothing is duplicated or reset. See
[Seed script](#seed-script) below only if you want to force a re-seed.

The SQLite database file is written to a named Docker volume (`db-data`)
mounted at `/data` in the backend container, so it persists across
`docker compose down` / `up` cycles. Use `docker compose down -v` to reset it.

> **Upgrading an existing volume:** schema-index changes (e.g. the analytics
> composite index) are only applied when the tables are created. If you have
> a `db-data` volume from an earlier build, run `docker compose down -v`
> once so it's recreated (the database re-seeds automatically on next start).

## Running locally without Docker

**Backend**

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

**Frontend**

```
cd frontend
npm install
npm run dev
```

## Environment variables

See [`.env.example`](.env.example) for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_PATH` | Path to the SQLite database file |
| `JWT_SECRET` | Secret used to sign auth tokens |
| `OPENROUTER_API_KEY` | Required only for the stretch NL-query feature |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `VITE_API_URL` | Backend URL the frontend calls |

`.env` is gitignored — never commit real secrets.

## Seed script

The database is seeded **automatically on first startup** (see above), so
you normally never need to run this by hand. It's kept as a standalone
script for forcing a deliberate re-seed during development — it clears and
repopulates Employee/SalaryRecord/User each time (same result every run,
since the random seed is fixed).

```
cd backend
source .venv/bin/activate
python -m app.seed
```

In Docker Compose: `docker compose exec backend python -m app.seed`.

Populates 10,000 correlated employees, realistic salary history for
~15–20% of them, and the 3 demo users below.

## Tests

Backend:

```
cd backend
source .venv/bin/activate
pytest
```

<!-- Frontend test commands will be added once the frontend has tests. -->

## Demo login credentials

`POST /auth/login` with `{"email": ..., "password": ...}`, all sharing the
same password:

| Role | Email | Password |
|---|---|---|
| admin | `admin@acme-corp.example` | `Password123!@#` |
| hr_manager | `hr.manager@acme-corp.example` | `Password123!@#` |
| executive_viewer | `exec.viewer@acme-corp.example` | `Password123!@#` |

`admin` and `hr_manager` have full read/write on employee & salary data;
`executive_viewer` can only reach the `/analytics/*` endpoints (read-only,
aggregate data — individual employee records are blocked).
