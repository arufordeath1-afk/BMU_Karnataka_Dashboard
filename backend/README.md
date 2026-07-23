# India Post — Karnataka Circle Revenue Intelligence: Backend

A working FastAPI + SQLAlchemy backend for the existing dashboard, with JWT
auth, role-based data scoping, real Excel upload/validation, a trend-based
forecast, rule-based AI insights, and Excel/CSV/PDF/PPT report export — all
backed by an actual database instead of client-side mock data.

## Quick start (local, SQLite — zero setup)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python -m app.seed_data      # creates india_post.db and demo accounts
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI): http://127.0.0.1:8000/docs

Open `dashboard.html` in a browser (or serve it with any static file server).
It's pre-configured to call `http://127.0.0.1:8000`. To point it at a
different backend, set `window.API_BASE = "https://your-api"` in a
`<script>` tag before the dashboard's own script, or edit the `API_BASE`
constant near the top of the script block directly.

### Demo logins (username / password / role / scope)

| Username | Password | Role | Sees |
|---|---|---|---|
| `karnataka.circle.rm` | `circle123` | Circle | All of Karnataka |
| `bengaluru.region.rm` | `region123` | Region | Bengaluru region only |
| `mysuru.division.rm` | `division123` | Division | Mysuru division only |
| `mysuru.ho.user` | `office123` | Office | Mysuru HO only |

Role scoping is enforced **server-side** on every query (customers, revenue,
divisions, offices, forecast, insights, reports) — a Region user cannot see
another region's data no matter what the frontend sends.

## Running with Postgres + Docker

```bash
cd backend
docker compose up --build
```

This starts Postgres, Redis (present but not wired into caching yet — see
below), and the API on `:8000`, running Alembic migrations and seeding demo
data automatically on first boot.

## Production notes

- Set a real `SECRET_KEY` and restrict `CORS_ORIGINS` — don't ship the `*`
  default.
- Put this behind a reverse proxy (nginx/Caddy) doing TLS termination.
- Run with multiple Uvicorn workers or under Gunicorn+Uvicorn workers for
  concurrency: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`.
- Point `DATABASE_URL` at managed Postgres; connection pooling is already
  configured in `app/database.py`.
- Run `alembic upgrade head` on deploy instead of `Base.metadata.create_all`
  for schema changes going forward.

## Database migrations (Alembic)

```bash
python -m alembic revision --autogenerate -m "describe your change"
python -m alembic upgrade head
```

An initial migration (`alembic/versions/..._initial_schema.py`) matching the
current models is already included.

## What's simplified vs. the original spec — read this

The original spec asked for a full enterprise stack (Celery, Redis caching,
Prophet, PDF/PPT reports, audit logs, rate limiting, background job
processing) alongside a working data pipeline. Doing all of that to a
production standard is a multi-week effort for a team, not one build. Here's
exactly what's real vs. stubbed, so nothing is overstated:

**Fully working, real (not mocked):**
- PostgreSQL-or-SQLite schema via SQLAlchemy, seeded with realistic data
  matching your original mock generator (same divisions, products, ~50
  named corporate/government customers, 12 months of revenue).
- JWT login, 4 roles, server-side scoping enforced on every endpoint.
- All spec'd dashboard endpoints (executive, kpi, monthly, quarterly,
  products, customers list/search/profile, divisions, offices, regions).
- Excel/CSV upload with real column validation, duplicate detection, and
  actual inserts into the database (tested end-to-end).
- Trend-based revenue forecast with confidence bands.
- Rule-based AI insights computed from live data (growth/decline/risk/
  opportunity) plus a plain-language summary.
- CSV, Excel (multi-sheet), PDF, and PowerPoint report export — all
  generate real files from live data (tested end-to-end).
- Alembic migration scaffolding with a working initial migration.
- A basic in-process rate limiter and CORS middleware.

**Simplified / stubbed — swap in before relying on these in production:**
- **Prophet forecasting**: replaced with a linear-trend model. Prophet
  needs a heavier native toolchain (cmdstan) that's overkill for a single
  short monthly series and often fails to install in minimal containers.
  The forecast router docstring shows exactly where to swap it in.
- **Celery + Redis background jobs**: Redis is included in
  `docker-compose.yml` but nothing uses it yet. Excel upload currently runs
  synchronously in the request (fine for the file sizes a circle office
  actually uploads; wire in Celery if you expect very large files).
- **Audit logs**: the `AuditLog` table exists but nothing writes to it yet —
  add a small middleware or per-router `db.add(AuditLog(...))` call.
- **Redis caching**: no caching layer is wired in; add
  `fastapi-cache2` + Redis around the dashboard endpoints if query volume
  grows.
- **AI insights**: rule-based, not an LLM call. The insights router
  docstring notes where to layer an LLM-written narrative on top of the
  same computed numbers.

## Folder structure

```
backend/
  app/
    main.py            # FastAPI app, middleware, router wiring
    config.py           database.py
    security.py         schemas.py       seed_data.py
    models/__init__.py  # all ORM models
    routers/            # auth, dashboard, customers, products, geo,
                         # forecast, insights, upload, reports
    services/
      analytics_service.py   # shared scoped/filtered query helpers
  alembic/              # migrations
  requirements.txt  .env.example  Dockerfile  docker-compose.yml
```
