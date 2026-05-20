import pytest


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["database"] == "connected"


# ---------------------------------------------------------------------------
# Auth — setup
# ---------------------------------------------------------------------------

def test_setup_creates_user(client):
    r = client.post("/auth/setup", json={"username": "aryan", "password": "strongpass-123"})
    assert r.status_code == 201
    assert r.json()["username"] == "aryan"


def test_setup_rejects_duplicate(client):
    client.post("/auth/setup", json={"username": "aryan", "password": "strongpass-123"})
    r = client.post("/auth/setup", json={"username": "other", "password": "otherpass-456"})
    assert r.status_code == 409


def test_setup_rejects_weak_password(client):
    r = client.post("/auth/setup", json={"username": "aryan", "password": "short"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Auth — token
# ---------------------------------------------------------------------------

def test_token_success(client):
    client.post("/auth/setup", json={"username": "aryan", "password": "strongpass-123"})
    r = client.post("/auth/token", data={"username": "aryan", "password": "strongpass-123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_token_wrong_password(client):
    client.post("/auth/setup", json={"username": "aryan", "password": "strongpass-123"})
    r = client.post("/auth/token", data={"username": "aryan", "password": "wrongpassword-999"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Protected routes — no token
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET",  "/entries/"),
    ("POST", "/entries/"),
    ("GET",  "/entries/summary"),
    ("GET",  "/entries/export"),
    ("GET",  "/ml/predict"),
    ("POST", "/ml/train"),
])
def test_protected_routes_require_auth(client, method, path):
    r = client.request(method, path)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth — me
# ---------------------------------------------------------------------------

def test_auth_me(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

_BASE_ENTRY = {
    "date": "2026-01-01",
    "itch": 3.0,
    "redness": 2.0,
    "scaling": 2.0,
    "joint_pain": 1.0,
    "fatigue": 2.0,
    "stress_level": 3.0,
    "sleep_quality": 7.0,
    "diet_quality": 7.0,
    "missed_medication": 0,
    "topical_applied": 1,
    "psoriasis_flare": 0,
    "notes": "",
}


def test_create_entry(client, auth_headers):
    r = client.post("/entries/", json=_BASE_ENTRY, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["date"] == "2026-01-01"


def test_upsert_same_date(client, auth_headers):
    client.post("/entries/", json=_BASE_ENTRY, headers=auth_headers)
    updated = {**_BASE_ENTRY, "itch": 7.0}
    r = client.post("/entries/", json=updated, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["itch"] == 7.0


def test_list_entries(client, auth_headers, seeded_entries):
    r = client.get("/entries/", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 12


def test_entries_summary(client, auth_headers, seeded_entries):
    r = client.get("/entries/summary?weeks=4", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "avg_symptom" in data
    assert "avg_sleep" in data


# ---------------------------------------------------------------------------
# ML
# ---------------------------------------------------------------------------

def test_ml_train_too_few_entries(client, auth_headers):
    r = client.post("/ml/train", headers=auth_headers)
    assert r.status_code == 400


def test_ml_train_success(client, auth_headers, seeded_entries):
    r = client.post("/ml/train", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "trained"
    assert 0.0 <= data["accuracy"] <= 1.0
    assert "model_trained_at" in data


def test_ml_predict_success(client, auth_headers, seeded_entries):
    client.post("/ml/train", headers=auth_headers)
    r = client.get("/ml/predict", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert data["model_trained_at"] is not None


def test_ml_predict_no_model_returns_422(client, auth_headers):
    # Fresh DB, no training done — predict raises ValueError → 422
    r = client.get("/ml/predict", headers=auth_headers)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_structure(client, auth_headers, seeded_entries):
    r = client.get("/entries/export", headers=auth_headers)
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    data = r.json()
    assert "user" in data and "entries" in data
    assert data["user"]["username"] == "testuser"
    assert len(data["entries"]) == 12


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------

def test_delete_account_wrong_password(client, auth_headers):
    r = client.request("DELETE", "/auth/account",
                       json={"password": "wrongpassword-999"},
                       headers=auth_headers)
    assert r.status_code == 401


def test_delete_account_success(client, auth_headers):
    r = client.request("DELETE", "/auth/account",
                       json={"password": "testpassword-123"},
                       headers=auth_headers)
    assert r.status_code == 204
    # Subsequent request with the now-invalid user's token is rejected
    r2 = client.get("/auth/me", headers=auth_headers)
    assert r2.status_code == 401
