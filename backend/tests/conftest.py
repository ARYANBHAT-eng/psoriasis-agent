import os
import random

# Must be set BEFORE any app import — Settings() reads these at import time
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-abcdef123456789012")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app


def _make_test_engine():
    # StaticPool: single shared connection — required for in-memory SQLite
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def db_engine():
    engine = _make_test_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    TestSession = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Patch main.SessionLocal so the lifespan handler also uses the test DB
    with patch("main.SessionLocal", TestSession):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    # Exercise the real auth flow — no direct DB insertion
    client.post("/auth/setup", json={"username": "testuser", "password": "testpassword-123"})
    r = client.post("/auth/token", data={"username": "testuser", "password": "testpassword-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def seeded_entries(client, auth_headers):
    random.seed(42)
    entries = []
    for i in range(12):
        entry = {
            "date": f"2026-01-{i + 1:02d}",
            "itch": round(random.uniform(1, 9), 1),
            "redness": round(random.uniform(1, 9), 1),
            "scaling": round(random.uniform(1, 9), 1),
            "joint_pain": round(random.uniform(1, 9), 1),
            "fatigue": round(random.uniform(1, 9), 1),
            "stress_level": round(random.uniform(1, 9), 1),
            "sleep_quality": round(random.uniform(1, 9), 1),
            "diet_quality": round(random.uniform(1, 9), 1),
            "missed_medication": random.randint(0, 1),
            "topical_applied": random.randint(0, 1),
            "psoriasis_flare": 1 if i < 4 else 0,  # 4 flares, 8 non-flares
            "notes": "",
        }
        entries.append(entry)
        client.post("/entries/", json=entry, headers=auth_headers)
    return entries
