# Phase 0 — Engineering Specification
## Psoriasis Agent · Structural Integrity

> This document is the engineering specification for Phase 0 of the Psoriasis Agent project.
> It is written to be consumed by Claude Code (the VS Code agent) operating in the project repository.
> Phase 0's purpose is to make the existing application trustworthy enough to handle real patient data,
> without changing user-visible behavior.

---

## How to use this document

This spec is structured for **read-then-propose-then-execute** workflow. For each task:

1. Read the entire task section before touching code.
2. Read the actual files in the repository to understand current state.
3. **Propose a plan** in chat before making any file edits. The plan must reference real file paths and real symbols from the codebase.
4. Wait for explicit approval before executing.
5. Make the changes.
6. Run the acceptance criteria.
7. Show the output.
8. Stop. Do not proceed to the next task until approved.

If anything in this spec contradicts what the codebase actually contains, **ask before assuming**. The spec describes intent; the codebase is the source of truth for current state.

---

## Strategic context

The existing application is a working proof-of-concept built on assumptions appropriate for a portfolio demo:
SQLite on ephemeral disk, no authentication, model artifact on local filesystem, no test suite. These choices
are fine for a one-person demo but they are incompatible with the project's long-term goal of being a real
patient-facing application.

Phase 0 fixes the foundation. Nothing in Phase 0 changes user-visible behavior. The Streamlit dashboard,
the API contract, the prediction output — all of these remain identical from a user's perspective.
What changes is what happens underneath: data is durable, access is authenticated, the model survives
redeploys, and a test suite exists to catch regressions.

This phase is invisible by design. Successful infrastructure work is invisible.

---

## Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Database | PostgreSQL via psycopg2, synchronous SQLAlchemy | Async adds complexity without benefit at this scale. PostgreSQL is the only durable option on Render free tier. |
| Migration tool | Alembic | Industry standard. Required for any schema changes after this point. |
| Auth model | Single-user JWT (HS256, 7-day expiry) | One account per deployment. Personal health app, not SaaS. Stateless tokens avoid session storage complexity. |
| Password hashing | bcrypt via passlib, default cost factor | Industry standard. Cost factor 12 is appropriate for current hardware. |
| Model persistence | Binary blob in PostgreSQL (`model_artifacts` table) | Survives redeploys. Avoids S3/R2 complexity. Model is small (~10KB). |
| Local dev DB | PostgreSQL via Docker (not SQLite) | Avoids the SQLite/Postgres migration footgun where Alembic autogenerate produces incompatible migrations. |
| Test DB | SQLite in-memory | Acceptable here because tests use `Base.metadata.create_all()` not Alembic. One test will explicitly verify migrations against Postgres. |
| Audit logging | Yes, from Phase 0 | Required for any application that handles health data, even single-user. |
| Data export / deletion | Yes, from Phase 0 | GDPR Article 17 (right to erasure) and Article 20 (data portability) are baseline expectations for health apps, not optional. |
| Frontend auth | Streamlit `session_state` token + login form | Interim solution. Phase 3 replaces Streamlit entirely. |

---

## Pre-flight checklist

Before starting Task 1, Claude Code should:

1. Run `git status --short` and report the current working tree state.
2. Read `backend/app/config.py`, `backend/app/database.py`, `backend/app/models.py`, `backend/main.py`, and `backend/ml_model.py` in full.
3. Read `backend/app/routers/entries.py` and `backend/app/routers/ml.py` in full.
4. Read `frontend/app.py` in full.
5. Read `render.yaml`, `runtime.txt`, and both `requirements.txt` files.
6. Report import patterns used in the codebase (e.g. `from app.config import settings` vs. `from backend.app.config import settings`). Use whatever pattern is already in place — do not invent a new one.
7. Confirm the Python version and SQLAlchemy version actually in use.
8. Report any deviations from what context.md describes.

Only after this is complete should Task 1 begin.

---

## Task 1 — PostgreSQL with Alembic

### Goal
Replace SQLite with PostgreSQL as the persistent store. Add Alembic for schema management.
Keep the engine synchronous. Make the local development experience use PostgreSQL via Docker
so dev and production share the same database engine.

### Architectural constraints

- Synchronous SQLAlchemy only. Do not introduce `asyncpg` or `AsyncSession`.
- All configuration must come from environment variables via the existing `Settings` class. No hardcoded connection strings anywhere.
- `Settings` must use Pydantic v2's `pydantic-settings` package (added as dependency).
- Production environment (`APP_ENV=production`) must reject any `DATABASE_URL` containing `sqlite`. This validation runs at startup.
- Production environment must reject any `SECRET_KEY` equal to a default placeholder. Provide a clear error message naming the env var.
- Connection pooling: `pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`. Skip these args for SQLite (they are invalid for SQLite).
- The `/healthz` endpoint must report database connectivity status. It must remain public (no auth).

### Deliverables

1. Updated `backend/requirements.txt` with `psycopg2-binary`, `alembic`, `pydantic-settings`.
2. Updated `backend/app/config.py` with the production validation logic described above.
3. Updated `backend/app/database.py` with the new engine configuration and a `check_db_connection()` helper.
4. Initialized Alembic in `backend/alembic/` with a working `env.py` that imports all models from `app.models`. Use the import style the codebase already uses.
5. Initial migration generated from the current schema, applied successfully against a local Postgres database.
6. Updated `backend/main.py` `/healthz` route reporting DB status.
7. Updated `render.yaml` referencing a Render-managed Postgres database (`fromDatabase` syntax).
8. A `docker-compose.yml` at the project root for local Postgres development (single service, named volume for persistence, default credentials documented).
9. A `.env.example` file at the project root documenting all required environment variables.
10. A one-off `scripts/migrate_sqlite_to_postgres.py` that reads existing SQLite data (if `psoriasis.db` exists) and inserts it into the configured Postgres database. Must be idempotent — running it twice does not duplicate rows.

### Acceptance criteria

```bash
# 1. Local Postgres starts
docker-compose up -d
# Expected: postgres container running

# 2. Migrations apply cleanly
cd backend && alembic upgrade head
# Expected: zero errors, "Running upgrade ... -> <revision>, initial_schema"

# 3. Optional SQLite → Postgres data migration runs cleanly
python scripts/migrate_sqlite_to_postgres.py
# Expected: reports row count migrated, or "no SQLite file found, skipping"

# 4. App starts and reports DB connectivity
uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir backend
curl http://localhost:8000/healthz
# Expected: {"status": "ok", "database": "connected"}

# 5. Production validation works
APP_ENV=production DATABASE_URL=sqlite:///./test.db python -c "from app.config import Settings; Settings()"
# Expected: ValidationError mentioning SQLite is not permitted in production

# 6. Schema parity check
psql $DATABASE_URL -c "\dt"
# Expected: daily_entries table visible
```

### Rollback

If this task fails partway:
```bash
cd backend && alembic downgrade base
git checkout -- backend/ render.yaml
docker-compose down
```

---

## Task 2 — Authentication, audit logging, data rights

### Goal
Add single-user JWT authentication. Add audit logging for security-relevant events.
Add data export and account deletion endpoints. Protect all existing routes except `/healthz` and `/auth/setup`.

### Architectural constraints

- JWT algorithm: HS256. Signing key from `settings.secret_key`. Expiry from `settings.access_token_expire_days` (default 7).
- Passwords hashed with bcrypt via passlib. Minimum password length: 12 characters. Must contain at least one digit and one letter (enforced in Pydantic schema, not in business logic).
- `/auth/setup` is callable exactly once per deployment. After the first user is created, subsequent calls return HTTP 409.
- All authenticated routes use a `get_current_user` dependency. The token is read from the `Authorization: Bearer <token>` header (OAuth2PasswordBearer pattern).
- Audit log table records: timestamp, event type, username, IP address, success/failure, optional details. Event types in this phase: `auth.setup`, `auth.login.success`, `auth.login.failure`, `auth.token.invalid`, `data.export`, `data.delete_account`.
- IP address comes from `X-Forwarded-For` header if present (Render is behind a proxy), else from `request.client.host`.
- Audit log writes must never raise — they are best-effort. A failed audit write logs at ERROR but does not fail the originating request.
- Never log passwords, tokens, or hashed values. Never include them in audit log details.

### Deliverables

1. New dependencies in `requirements.txt`: `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`.
2. New `User` model in `backend/app/models.py` (id, username, hashed_password, created_at, is_active). Use `datetime.now(timezone.utc)` for defaults, not the deprecated `datetime.utcnow`.
3. New `AuditLog` model in `backend/app/models.py` (id, timestamp, event_type, username, ip_address, success, details_json).
4. Alembic migration adding both tables.
5. New `backend/app/auth.py` containing: `verify_password`, `hash_password`, `create_access_token`, `authenticate_user`, `get_current_user`, `log_audit_event` (best-effort writer).
6. New `backend/app/routers/auth.py` with:
   - `POST /auth/setup` — create the single user account; rejects if any user exists
   - `POST /auth/token` — OAuth2 password flow; returns access token
   - `GET /auth/me` — returns current user
   - `GET /entries/export` — returns all user data as JSON (Content-Disposition: attachment)
   - `DELETE /auth/account` — deletes the user account and all associated health entries; requires confirmation token in request body
7. Apply `Depends(get_current_user)` to every route in `entries.py` and `ml.py`. Do not modify business logic.
8. Update CORS configuration in `main.py` to include `Authorization` in allowed headers.
9. Update `frontend/app.py`: add a login form that captures username/password, calls `/auth/token`, stores the token in `st.session_state.token`, attaches `Authorization: Bearer <token>` to all subsequent backend requests. Add a logout button. Handle 401 responses by clearing the token and showing the login form again. On first run (no account exists), show a "Create account" form instead.

### Acceptance criteria

```bash
# 1. Setup flow
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username":"aryan","password":"strong-password-123"}'
# Expected: 201 with user object

# 2. Setup is one-shot
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username":"other","password":"another-pass-456"}'
# Expected: 409 Conflict

# 3. Weak password rejected
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username":"aryan","password":"short"}'
# Expected: 422 with clear validation error

# 4. Login + protected route
TOKEN=$(curl -X POST http://localhost:8000/auth/token \
  -d "username=aryan&password=strong-password-123" | jq -r .access_token)
curl http://localhost:8000/entries/ -H "Authorization: Bearer $TOKEN"
# Expected: 200 (empty list is fine)

# 5. Unauthenticated request blocked
curl http://localhost:8000/entries/
# Expected: 401

# 6. Data export
curl http://localhost:8000/entries/export -H "Authorization: Bearer $TOKEN" -o my-data.json
# Expected: file downloaded with valid JSON containing user profile and all entries

# 7. Audit log populated
psql $DATABASE_URL -c "SELECT event_type, username, success FROM audit_logs ORDER BY timestamp;"
# Expected: rows for auth.setup, auth.login.success, auth.token.invalid (from step 5), data.export

# 8. Streamlit dashboard works end-to-end
streamlit run frontend/app.py
# Manual: open in browser, see login screen, log in, see dashboard, log out, see login screen again
```

### Rollback

```bash
cd backend && alembic downgrade -1  # drops users + audit_logs tables
git checkout -- backend/ frontend/
```

---

## Task 3 — Model artifact persistence

### Goal
Eliminate disk-based model storage. Store the trained scikit-learn pipeline as a binary blob in PostgreSQL.
Auto-recover the model on application startup. Make the model artifact a first-class versioned entity.

### Architectural constraints

- Model artifact table stores the full `Pipeline(StandardScaler, LogisticRegression)` object, not separate components.
- Multiple artifacts may exist in the table for historical traceability, but only one is `is_active=True` at a time. New training deactivates all previous artifacts atomically (single transaction).
- `predict_flare` and `train_model` never touch the filesystem. No `joblib.dump('model.pkl')` anywhere.
- Auto-train on startup runs only if no active artifact exists. It must not run if an active artifact is already present.
- Startup auto-train wraps the work in a try/except that logs ERROR and continues — startup must never fail because of training issues.
- `predict_flare` raises `ValueError` (caught by the router as HTTP 422) when no model exists or no entries exist. Never returns HTTP 500.
- Boolean feature columns (`missed_medication`, `topical_applied`) must be handled explicitly — do not use `value or 0` patterns that conflate `False` with missing data.
- The model artifact must store metadata: `sample_count`, `accuracy`, feature names, class labels, training timestamp. Stored as JSON in `metrics_json`.
- The `/ml/predict` response must include `model_trained_at` and `model_sample_count` so the frontend can surface model freshness.

### Deliverables

1. New `ModelArtifact` model in `backend/app/models.py`.
2. Alembic migration for the new table.
3. Rewritten `backend/ml_model.py` preserving the public interface (`train_model`, `predict_flare`, `get_key_factors`, `get_recommendations`) so the router needs no changes.
4. New `maybe_auto_train(db)` startup helper.
5. `backend/main.py` `lifespan` context manager calling `maybe_auto_train` on startup.
6. Router `backend/app/routers/ml.py` updated to translate `ValueError` into HTTP 422 with the error message as the detail.
7. `model.pkl` removed from disk and added to `.gitignore` if not already.

### Acceptance criteria

```bash
# 1. Train succeeds
curl -X POST http://localhost:8000/ml/train -H "Authorization: Bearer $TOKEN"
# Expected: {"status": "trained", "sample_count": N, "accuracy": X, ...}

# 2. Artifact persisted
psql $DATABASE_URL -c "SELECT id, sample_count, is_active, trained_at FROM model_artifacts;"
# Expected: one row, is_active=true

# 3. Predict works and reports model metadata
curl http://localhost:8000/ml/predict -H "Authorization: Bearer $TOKEN"
# Expected: risk_level + model_trained_at NOT NULL

# 4. Cross-restart persistence (the critical test)
TRAINED_AT_1=$(curl -s http://localhost:8000/ml/predict -H "Authorization: Bearer $TOKEN" | jq -r .model_trained_at)
# Restart the app
pkill -f uvicorn && sleep 2 && uvicorn main:app --app-dir backend --port 8000 &
sleep 3
TRAINED_AT_2=$(curl -s http://localhost:8000/ml/predict -H "Authorization: Bearer $TOKEN" | jq -r .model_trained_at)
[ "$TRAINED_AT_1" = "$TRAINED_AT_2" ] && echo "PASS: model survived restart" || echo "FAIL: model was retrained"
# Expected: PASS

# 5. Predict without model returns 422, not 500
psql $DATABASE_URL -c "UPDATE model_artifacts SET is_active = false;"
curl -i http://localhost:8000/ml/predict -H "Authorization: Bearer $TOKEN"
# Expected: HTTP 422, body contains a clear message

# 6. No model.pkl on disk
test ! -f backend/model.pkl && echo "PASS: no disk artifact"
# Expected: PASS
```

### Rollback

```bash
cd backend && alembic downgrade -1
git checkout -- backend/ml_model.py backend/main.py backend/app/routers/ml.py
```

---

## Task 4 — Test suite

### Goal
Add a pytest test suite covering the three critical paths (auth, entries, ML) plus one migration verification test.
Tests must be runnable with a single command. CI is not in scope for this phase but tests should be CI-ready.

### Architectural constraints

- pytest only. No async test framework — the app is synchronous.
- Tests use FastAPI's `TestClient` with `app.dependency_overrides[get_db]` to inject an in-memory SQLite session.
- `Base.metadata.create_all()` builds the test schema. This bypasses Alembic — acceptable for unit tests, BUT one separate integration test must run Alembic migrations against a real Postgres database to catch migration bugs.
- Tests must not mock SQLAlchemy or the database. They must use real query execution.
- The auth fixture creates a real user via the API; do not insert users directly into the DB.
- Seed data for ML tests must produce both flare and non-flare days (otherwise training fails the label variety check). Use a fixed random seed (`random.seed(42)`) for reproducibility.
- ML accuracy assertions must use a range (0.0 ≤ accuracy ≤ 1.0), never exact values.

### Deliverables

1. `backend/tests/__init__.py` (empty).
2. `backend/tests/conftest.py` with fixtures: `db_engine`, `db_session`, `client`, `auth_headers`, `seeded_entries`.
3. `backend/tests/test_smoke.py` covering:
   - `/healthz` is public and returns 200
   - `/auth/setup` creates a user, rejects duplicate setup, rejects weak passwords
   - `/auth/token` issues tokens, rejects bad credentials
   - All non-auth routes return 401 without a token
   - Entries: create, upsert by date, list, summary
   - ML: training fails below threshold, succeeds with seed data, predict returns valid risk levels, predict returns 422 when no model exists
   - Data export endpoint returns valid JSON with the expected structure
   - Audit log entries are written for auth events
4. `backend/tests/test_migrations.py` — single test that spins up a Postgres test database via testcontainers OR docker-compose, runs `alembic upgrade head`, verifies the expected tables exist, runs `alembic downgrade base`, verifies tables are dropped. This catches migration bugs that the SQLite-based tests would miss.
5. Updated `requirements.txt` with `pytest`, `httpx`. Add `testcontainers[postgres]` only if Task 4 deliverable 4 uses testcontainers.

### Acceptance criteria

```bash
cd backend
pytest tests/ -v --tb=short
# Expected: all tests pass, zero failures, zero errors, zero warnings about deprecations
```

### Rollback

Tests are additive only. No rollback needed.

---

## Final — Commit and documentation

### Goal
Commit Phase 0 cleanly. Update documentation to reflect the new reality. Document the rollback procedure.

### Deliverables

1. Update `README.md`:
   - Add an "Authentication" section describing the `/auth/setup` flow and password requirements.
   - Update the "Setup Instructions" section: Docker Postgres for local dev, `alembic upgrade head` before first run, `SECRET_KEY` generation command.
   - Update the "Environment Variables" section with the full Phase 0 set.
   - Add an "Audit Logging" subsection explaining what is logged and why.
   - Add a "Data Rights" subsection explaining the export and account deletion endpoints.
2. Update `context.md`:
   - Move resolved items out of "Known Risks / Gaps".
   - Add a new "Phase 0 Completion State" section documenting what changed.
   - Update the "Tech Stack" section with the new dependencies.
3. Update `render.yaml` with all required environment variables documented.
4. Create `docs/ROLLBACK.md` documenting how to roll back each task independently.
5. Generate the production `SECRET_KEY` value and note it in a secure password manager (do NOT commit it). Update the README with the command:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
6. Single commit with the message:
   ```
   phase-0: structural integrity — postgres, jwt auth, audit logs, model persistence, tests

   - Replace SQLite with PostgreSQL (psycopg2 + Alembic migrations)
   - Add single-user JWT auth with bcrypt password hashing
   - Add audit logging for security-relevant events
   - Add data export and account deletion endpoints
   - Store ML model artifacts in postgres, eliminate disk persistence
   - Auto-retrain on startup if model missing and data sufficient
   - Add streamlit login flow with session-state token storage
   - Add pytest smoke suite and migration integration test
   - Add docker-compose for local postgres development
   - Add sqlite → postgres one-time migration script
   ```

### Acceptance criteria

```bash
git status --short
# Expected: clean working tree

git log -1 --stat
# Expected: phase-0 commit visible with all expected files

# Full end-to-end on a fresh clone:
git clone <repo> /tmp/fresh-clone
cd /tmp/fresh-clone
cp .env.example .env  # then fill in values
docker-compose up -d
cd backend && pip install -r requirements.txt && alembic upgrade head
pytest tests/ -v  # all green
uvicorn main:app --app-dir . --port 8000 &
curl http://localhost:8000/healthz  # ok
# Manual: open Streamlit, complete signup, log entry, train, predict
```

---

## Environment variables (Phase 0 complete set)

| Variable | Required | Example | Notes |
|---|---|---|---|
| `APP_ENV` | yes | `production` | Triggers strict validation in production |
| `DATABASE_URL` | yes | `postgresql://user:pass@host:5432/db` | Render auto-injects from managed Postgres |
| `SECRET_KEY` | yes | 64 hex chars | Generate with `secrets.token_hex(32)`. Never commit. |
| `ALLOWED_ORIGINS` | yes | `https://psoriasis-ui.onrender.com` | Comma-separated. Wildcard `*` rejected. |
| `ACCESS_TOKEN_EXPIRE_DAYS` | no | `7` | JWT expiry. Default 7. |
| `API_BASE_URL` | yes (frontend) | `https://psoriasis-api.onrender.com` | Backend URL for the Streamlit frontend |

---

## Out of scope for Phase 0

These items are explicitly deferred to later phases. Do not implement them in Phase 0 even if tempting:

- Rate limiting on `/auth/token` (Phase 1 or sooner if security review demands it)
- Email verification, password reset flows (Phase 1)
- Multi-user support (never — this is a single-user app by design)
- Refresh tokens (acceptable to defer; 7-day access tokens are fine for personal use)
- Temporal features in ML model (Phase 2)
- Separate models for psoriasis vs PsA (Phase 1)
- New data model fields like weather, alcohol, cycle phase (Phase 1)
- React/Next.js frontend (Phase 3 — Streamlit auth is the interim solution)
- Clinical PDF export (Phase 4)
- Personalized insights (Phase 5)

If something feels in scope but isn't on the deliverables list above, **ask before implementing**.