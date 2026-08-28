# Smart Property & Facility Management Platform

A FastAPI backend for managing properties, buildings, units, tenants, leases,
rent collection, maintenance, utilities, visitors, parking, and facility
bookings — built to the 17-level assignment spec.

This was built and verified end-to-end: the app boots, a full
create-property → lease → invoice → payment → maintenance → facility-booking
flow was exercised against a live server (see `smoke_test.sh`), and the
automated test suite (20 tests) passes.

## What's actually implemented (read this first)

Everything below is real, working code — not stubs — **except** the three
items explicitly called out in "Honest limitations" further down.

| Level | Feature | Status |
|---|---|---|
| 1 | Auth (JWT + refresh tokens, RBAC, activate/deactivate) | ✅ |
| 2 | Properties CRUD | ✅ |
| 3 | Buildings & Units CRUD + business rules | ✅ |
| 4 | Tenants CRUD + rental history | ✅ |
| 5 | Leases + overlap/deposit/auto-occupancy rules | ✅ |
| 6 | Rent invoices, payments, overdue detection | ✅ |
| 7 | Maintenance requests, assignment, status, history | ✅ |
| 8 | Utility readings & invoices with validation | ✅ |
| 9 | Visitors (check-in/out, history) | ✅ |
| 10 | Parking (assign/release, uniqueness) | ✅ |
| 11 | Facility booking (overlap + capacity) | ✅ |
| 12 | Notifications (persisted + BackgroundTasks) | ✅ (see note) |
| 13 | Search/filter/pagination | ✅ (generic, reused everywhere) |
| 14 | Dashboard & reports | ✅ |
| 15 | Security & data integrity | ✅ |
| 16 | Layered architecture | ✅ |
| 17 | DB/perf (indexes, Alembic, session handling) | ✅ |
| Bonus | PDF receipt | ✅ (reportlab) |
| Bonus | Excel report export | ✅ (openpyxl) |
| Bonus | WebSocket maintenance updates | ✅ (real broadcast, wired in) |
| Bonus | Docker & Docker Compose | ✅ |
| Bonus | API versioning `/api/v1/` | ✅ |
| Bonus | Pytest suite | ✅ (20 tests, all passing) |
| Bonus | Redis caching, Celery | ❌ not built (see below) |
| Bonus | QR-based visitor entry | ❌ not built (see below) |
| Bonus | Real email/SMS delivery | ❌ stubbed (see below) |

### Honest limitations

- **Email/SMS notifications are stubbed.** `notify_*` functions persist a
  `Notification` row (queryable via the data model) and log the message —
  they don't call a real provider. Swap `_dispatch()` in
  `app/services/notification_service.py` for SendGrid/SES/Twilio calls to go
  live.
- **No Celery/Redis.** Background work uses FastAPI's built-in
  `BackgroundTasks`, which is fine for a single-instance deployment but
  doesn't retry or survive a crash. The notification service is already
  isolated behind a small interface, so swapping in Celery later is a
  contained change.
- **No QR-code visitor entry.** The visitor check-in/out flow is normal REST;
  no QR generation/scanning was built.
- **Redis caching** was not implemented; the dashboard queries run directly
  against the DB (they're aggregate `COUNT`/`SUM` queries with indexes on
  the relevant filter/foreign-key columns, so this is fine at moderate
  scale, but a high-traffic dashboard would benefit from caching).

Everything else in the spec is implemented with real business logic, not
placeholder code.

## Tech stack

Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, JWT
(`python-jose`), `passlib[bcrypt]`, `slowapi` (rate limiting), `reportlab`
(PDF), `openpyxl` (Excel), pytest.

## Quick start (SQLite, zero setup)

```bash
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Option A: let the app create tables automatically (dev/demo)
uvicorn app.main:app --reload

# Option B: use Alembic migrations (recommended, mirrors production)
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger UI.

The app defaults to a local SQLite file (`property_management.db`) — nothing
else to install. Copy `.env.example` to `.env` if you want to override
settings (e.g. point `DATABASE_URL` at Postgres).

## Quick start (Docker Compose, PostgreSQL)

```bash
docker compose up --build
```

This starts Postgres + the API, runs Alembic migrations automatically on
container start, and serves the API on `http://localhost:8000`.

## Running the tests

```bash
pytest                 # 20 tests covering auth, business rules, and workflows
```

Tests run against an isolated SQLite file (`test_property_management.db`,
auto-created/destroyed) — they never touch your dev database.

## Smoke-testing the full workflow manually

`smoke_test.sh` exercises the entire property → lease → invoice → payment →
maintenance → utility → visitor → parking → facility → dashboard flow via
curl, including the negative cases (duplicate unit numbers, overlapping
leases, overpayment, invalid utility readings, over-capacity bookings).

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
./smoke_test.sh
```

## Project structure

```
app/
├── main.py            # app assembly: CORS, rate limiting, routers, startup
├── config.py           # environment-driven settings (pydantic-settings)
├── database.py          # SQLAlchemy engine/session/Base
├── dependencies.py       # auth + RBAC dependencies
├── exceptions.py         # AppError hierarchy + global exception handlers
├── models/              # SQLAlchemy ORM models (one file per domain)
├── schemas/              # Pydantic request/response models
├── routes/               # FastAPI routers (one file per domain)
├── services/              # business logic (lease rules, rent calc, etc.)
├── repositories/           # generic CRUD repository (soft-delete aware)
├── utils/                # security, pagination, audit logging, rate limiting
└── tests/                # pytest suite
alembic/                  # migrations
```

Routes stay thin (auth + validation + delegate); business rules live in
`services/`; raw DB access is centralized in `repositories/base.py` for
entities that don't need custom logic, and directly in services where
domain rules require it (leases, rent, maintenance, facilities).

## Auth & roles

Roles: `super_admin`, `property_manager`, `facility_manager`,
`maintenance_staff`, `security_staff`, `tenant`.

1. `POST /api/v1/auth/register` — create a user (pick a role for testing;
   in a real deployment you'd restrict who can self-register as staff/admin)
2. `POST /api/v1/auth/login` — returns `access_token` + `refresh_token`
3. Send `Authorization: Bearer <access_token>` on subsequent requests
4. `POST /api/v1/auth/refresh` — exchange a refresh token for a new access
   token when the old one expires

Most write endpoints require `super_admin` or `property_manager` (see
`app/dependencies.py` for the exact role sets per endpoint).

## Notable business rules enforced (not just field validation)

- Unit numbers are unique **within a building**, not globally.
- A unit under `Maintenance` status cannot be leased; an `Occupied` unit
  can't be double-leased.
- Leases on the same unit cannot have overlapping date ranges.
- Activating a lease automatically flips the unit to `Occupied`; terminating
  one frees it back to `Available`.
- Rent invoices are unique per `(lease, billing_month)` — no duplicates.
- Payments can't exceed the remaining invoice balance; an invoice
  auto-flips to `Paid` once fully covered, and pending invoices past their
  due date auto-flip to `Overdue` (checked on every invoice list call).
- Only users with the `maintenance_staff` role (and active accounts) can be
  assigned to a maintenance request; emergency-priority requests sort first
  by default.
- Utility invoices are computed from readings
  (`units_consumed = current − previous`, `amount = units_consumed × rate`);
  a reading can't have `current < previous`.
- Facility bookings respect per-slot capacity and reject overlaps beyond it;
  cancelling a booking frees the slot for others.
- Parking vehicle numbers are unique across active assignments; slots can't
  be double-assigned.

## Security & data integrity (Level 15)

- Passwords hashed with bcrypt; JWT access + refresh tokens (refresh tokens
  are persisted and revocable, each with a unique `jti`).
- Role-based access control via FastAPI dependencies (`require_roles(...)`).
- Global exception handlers return a consistent JSON error envelope for
  validation errors, business-rule errors, DB integrity errors, and
  unhandled exceptions (with server-side logging).
- Soft delete (`is_deleted` flag) on core entities instead of hard deletes.
- Audit log (`audit_logs` table) records who did what, to which entity,
  and when, on every mutating action.
- CORS configured via `CORS_ORIGINS` env var.
- Rate limiting via `slowapi` (`RATE_LIMIT_DEFAULT` env var, default
  100/minute).
- SQLAlchemy foreign keys + unique constraints enforced at the DB level
  (e.g. `(building_id, unit_number)`, `(lease_id, billing_month)`).

## API versioning

All REST endpoints are namespaced under `/api/v1/` (`app.config.settings.API_V1_PREFIX`).
The WebSocket endpoint (`/ws/maintenance`) is intentionally unversioned since
it isn't a REST resource.

## What I'd do differently with more time

- Move `notifications`/background delivery onto Celery + Redis for retry
  semantics and to decouple delivery from the request/response cycle.
- Add Redis caching for the dashboard summary endpoint.
- Build the QR-code visitor flow (generate on visitor creation, validate on
  scan at a gate-side endpoint).
- Add integration tests for the WebSocket broadcast and the reporting
  endpoints (currently covered manually/via smoke test, not pytest).
- Tighten registration: in production, `super_admin`/staff roles shouldn't
  be self-assignable at `/auth/register` — that'd move to an admin-only
  "create staff user" endpoint.
