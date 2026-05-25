"""
Migration integration test: upgrade head → verify tables → downgrade base → verify clean.
Requires docker-compose Postgres running on localhost:5433.
Automatically skipped if Postgres is unreachable.

Run: cd backend && pytest tests/test_migration.py -v
"""
from pathlib import Path

import psycopg2
import pytest
from alembic import command
from alembic.config import Config

_BASE_URL = "postgresql://psoriasis:psoriasis@localhost:5433/postgres"
_TEST_DB  = "psoriasis_migration_test"
_TEST_URL = f"postgresql://psoriasis:psoriasis@localhost:5433/{_TEST_DB}"
_EXPECTED = {
    "entries",
    "users",
    "audit_logs",
    "model_artifacts",
    "user_profiles",
    "weather_captures",
    "medication_events",
    "flare_events",
}


def _postgres_available() -> bool:
    try:
        psycopg2.connect(_BASE_URL, connect_timeout=2).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def migration_db():
    if not _postgres_available():
        pytest.skip("Postgres not running on localhost:5433")

    conn = psycopg2.connect(_BASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB}"')
        cur.execute(f'CREATE DATABASE "{_TEST_DB}"')
    conn.close()

    yield _TEST_URL

    conn = psycopg2.connect(_BASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB}"')
    conn.close()


def _get_tables(url: str) -> set:
    conn = psycopg2.connect(url)
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        tables = {row[0] for row in cur.fetchall()}
    conn.close()
    return tables


def test_migration_upgrade_then_downgrade(migration_db):
    from pathlib import Path
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", migration_db)

    command.upgrade(cfg, "head")
    after_upgrade = _get_tables(migration_db)
    assert _EXPECTED.issubset(after_upgrade), \
        f"Missing tables after upgrade: {_EXPECTED - after_upgrade}"

    command.downgrade(cfg, "base")
    after_downgrade = _get_tables(migration_db)
    assert not (_EXPECTED & after_downgrade), \
        f"Tables still present after downgrade: {_EXPECTED & after_downgrade}"
