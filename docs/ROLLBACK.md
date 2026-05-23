# Rollback Procedures

This document describes how to roll back the Psoriasis Agent backend to a previous
state. Intended for use during incident response or after a failed deployment.

## When to roll back vs. hotfix

Roll back when: a new migration broke the schema, a new deployment is crashing at
startup, or data integrity is at risk. Hotfix instead when: the bug is in application
code only (no schema change), the fix can be deployed in under 30 minutes, and the
DB is healthy.

---

## Rollback ordering principle

Code rollback is usually safe and sufficient. The new code can almost always read the
new schema, and the old code can usually read the new schema too (extra columns are
tolerated). DB schema rollback should **only** happen if the new schema itself is
causing the problem.

If both are needed, **roll back code first, then schema**. Rolling back schema while
new code is still running will cause runtime errors as the code tries to use columns
that no longer exist.

---

## Alembic migration rollback

### Downgrade one step

```bash
cd backend
alembic downgrade -1
```

### Downgrade to a specific revision

```bash
alembic history          # list all revision IDs
alembic downgrade <rev>  # e.g. alembic downgrade a7bfb241e40e
```

### Downgrade to base (empty schema)

```bash
alembic downgrade base
```

> **Warning:** Downgrading past a migration that added a table will DROP that table
> and all its data. There is no automatic backup. Export data first if needed
> (see Data export section below).

---

## Migration revision map

| Revision | Description | Tables added | Dropped on downgrade |
|---|---|---|---|
| `776b153928a9` | add_model_artifacts | `model_artifacts` | `model_artifacts` |
| `a7bfb241e40e` | add_users_and_audit_logs | `users`, `audit_logs` | `users`, `audit_logs` |
| `829ad91aeefd` | initial_schema | `daily_entries` | `daily_entries` |

Downgrading to `base` drops all three tables in reverse order.

---

## Render deployment rollback

1. Go to the Render dashboard → `psoriasis-api` service → **Deploys** tab.
2. Find the last known-good deploy.
3. Click **Rollback to this deploy**.
4. If the rolled-back code targets a different schema revision, connect to the Render
   managed Postgres via a one-off process or psql and run the downgrade manually:

```bash
# In Render shell or one-off process (set DATABASE_URL first):
cd backend && alembic downgrade <target-rev>
```

---

## Testing a rollback locally

```bash
# Start local Postgres
docker-compose up -d

# Upgrade to head
cd backend && alembic upgrade head

# Verify tables exist
psql postgresql://psoriasis:psoriasis@localhost:5433/psoriasis -c "\dt"

# Downgrade one step
alembic downgrade -1

# Verify downgraded table is gone
psql postgresql://psoriasis:psoriasis@localhost:5433/psoriasis -c "\dt"

# Full downgrade
alembic downgrade base

# Verify empty schema
psql postgresql://psoriasis:psoriasis@localhost:5433/psoriasis -c "\dt"
```

The migration integration test (`backend/tests/test_migration.py`) automates this
check against a dedicated `psoriasis_migration_test` database on localhost:5433.
Run it with:

```bash
cd backend && pytest tests/test_migration.py -v
```

---

## Data export before rollback

Always export user data before any destructive downgrade:

```bash
# Get a token first
curl -s -X POST http://localhost:8000/auth/token \
  -d "username=<your_username>&password=<your_password>" \
  | python -m json.tool

# Export data
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/entries/export \
  -o backup-$(date +%Y%m%d).json
```
