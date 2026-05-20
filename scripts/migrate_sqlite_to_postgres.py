"""
One-time migration: copy rows from psoriasis.db (SQLite) into the configured
PostgreSQL database. Safe to run multiple times — duplicate dates are skipped.

Usage (from project root):
    DATABASE_URL=postgresql://... python scripts/migrate_sqlite_to_postgres.py
"""
import os
import sqlite3
import sys

import psycopg2


SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "psoriasis.db")
COLUMNS = [
    "date", "itch", "redness", "scaling", "joint_pain", "fatigue",
    "stress_level", "sleep_quality", "diet_quality",
    "missed_medication", "topical_applied", "psoriasis_flare", "notes",
]

INSERT_SQL = f"""
    INSERT INTO daily_entries ({", ".join(COLUMNS)})
    VALUES ({", ".join(["%s"] * len(COLUMNS))})
    ON CONFLICT (date) DO NOTHING
"""


def main() -> None:
    sqlite_path = os.path.abspath(SQLITE_PATH)
    if not os.path.exists(sqlite_path):
        print("no SQLite file found, skipping")
        sys.exit(0)

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url or "sqlite" in database_url:
        print("ERROR: set DATABASE_URL to a PostgreSQL connection string before running this script")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    rows = sqlite_conn.execute(
        f"SELECT {', '.join(COLUMNS)} FROM daily_entries"
    ).fetchall()
    sqlite_conn.close()

    if not rows:
        print("SQLite file exists but daily_entries is empty, nothing to migrate")
        sys.exit(0)

    pg_conn = psycopg2.connect(database_url)
    pg_conn.autocommit = False
    inserted = 0
    try:
        with pg_conn.cursor() as cur:
            for row in rows:
                cur.execute(INSERT_SQL, [row[col] for col in COLUMNS])
                inserted += cur.rowcount
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()

    print(f"attempted {len(rows)} rows, inserted {inserted} (skipped {len(rows) - inserted} duplicates)")


if __name__ == "__main__":
    main()
