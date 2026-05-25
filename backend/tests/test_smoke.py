import pytest
from unittest.mock import MagicMock, patch


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
    ("GET",  "/v2/entries/2026-01-01/context"),
    ("GET",  "/v2/medications/events"),
    ("POST", "/v2/medications/events"),
    ("GET",  "/v2/flares/"),
    ("POST", "/v2/flares/"),
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
    "legacy_flare_flag": 0,
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


# ---------------------------------------------------------------------------
# External triggers — context endpoint
# ---------------------------------------------------------------------------

def test_context_endpoint_no_weather(client, auth_headers, seeded_entries):
    r = client.get("/v2/entries/2026-01-01/context", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["entry"]["date"] == "2026-01-01"
    assert data["weather"] is None


def test_context_endpoint_missing_date(client, auth_headers):
    r = client.get("/v2/entries/2026-12-31/context", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["entry"] is None
    assert r.json()["weather"] is None


# ---------------------------------------------------------------------------
# External triggers — alcohol
# ---------------------------------------------------------------------------

def test_alcohol_zero_stored(client, auth_headers):
    r = client.post("/entries/", json={**_BASE_ENTRY, "alcohol_units": 0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["alcohol_units"] == 0


def test_alcohol_null_when_absent(client, auth_headers):
    r = client.post("/entries/", json=_BASE_ENTRY, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["alcohol_units"] is None


def test_alcohol_negative_rejected(client, auth_headers):
    r = client.post("/entries/", json={**_BASE_ENTRY, "alcohol_units": -1}, headers=auth_headers)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# External triggers — illness
# ---------------------------------------------------------------------------

def test_illness_description_too_long(client, auth_headers):
    r = client.post("/entries/", json={**_BASE_ENTRY, "illness_description": "x" * 501}, headers=auth_headers)
    assert r.status_code == 422


def test_illness_active_with_description(client, auth_headers):
    r = client.post("/entries/", json={**_BASE_ENTRY, "illness_active": True, "illness_description": "flu"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["illness_active"] is True
    assert r.json()["illness_description"] == "flu"


# ---------------------------------------------------------------------------
# External triggers — cycle gating
# ---------------------------------------------------------------------------

def test_cycle_day_dropped_when_not_tracked(client, auth_headers):
    # Default profile has tracks_cycle=False
    r = client.post("/entries/", json={**_BASE_ENTRY, "cycle_day_of_period": 5}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["cycle_day_of_period"] is None


def test_cycle_day_stored_when_tracked(client, auth_headers):
    client.patch("/v2/profile", json={"tracks_cycle": True}, headers=auth_headers)
    r = client.post("/entries/", json={**_BASE_ENTRY, "cycle_day_of_period": 5}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["cycle_day_of_period"] == 5


def test_cycle_day_out_of_range_rejected(client, auth_headers):
    client.patch("/v2/profile", json={"tracks_cycle": True}, headers=auth_headers)
    r = client.post("/entries/", json={**_BASE_ENTRY, "cycle_day_of_period": 61}, headers=auth_headers)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Medication events
# ---------------------------------------------------------------------------

_BASE_MED_EVENT = {
    "date": "2026-01-15",
    "medication_name": "Methotrexate",
    "event_type": "start",
    "dose": "15mg weekly",
}


def test_create_medication_event(client, auth_headers):
    r = client.post("/v2/medications/events", json=_BASE_MED_EVENT, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["medication_name"] == "Methotrexate"
    assert r.json()["event_type"] == "start"
    assert "id" in r.json()


def test_list_medication_events(client, auth_headers):
    client.post("/v2/medications/events", json=_BASE_MED_EVENT, headers=auth_headers)
    r = client.get("/v2/medications/events", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_medication_events_date_range(client, auth_headers):
    for evt_date, etype in [("2026-01-10", "start"), ("2026-02-01", "dose_increase"), ("2026-03-15", "stop")]:
        client.post("/v2/medications/events", json={**_BASE_MED_EVENT, "date": evt_date, "event_type": etype}, headers=auth_headers)
    assert len(client.get("/v2/medications/events?from=2026-02-01", headers=auth_headers).json()) == 2
    assert len(client.get("/v2/medications/events?to=2026-02-01", headers=auth_headers).json()) == 2
    assert len(client.get("/v2/medications/events?from=2026-01-10&to=2026-02-01", headers=auth_headers).json()) == 2


def test_delete_medication_event(client, auth_headers):
    event_id = client.post("/v2/medications/events", json=_BASE_MED_EVENT, headers=auth_headers).json()["id"]
    assert client.delete(f"/v2/medications/events/{event_id}", headers=auth_headers).status_code == 204
    assert len(client.get("/v2/medications/events", headers=auth_headers).json()) == 0


def test_delete_nonexistent_medication_event(client, auth_headers):
    assert client.delete("/v2/medications/events/9999", headers=auth_headers).status_code == 404


def test_invalid_event_type_rejected(client, auth_headers):
    assert client.post("/v2/medications/events", json={**_BASE_MED_EVENT, "event_type": "invalid"}, headers=auth_headers).status_code == 422


def test_medication_name_too_long(client, auth_headers):
    assert client.post("/v2/medications/events", json={**_BASE_MED_EVENT, "medication_name": "x" * 201}, headers=auth_headers).status_code == 422


def test_dose_too_long(client, auth_headers):
    assert client.post("/v2/medications/events", json={**_BASE_MED_EVENT, "dose": "x" * 101}, headers=auth_headers).status_code == 422


def test_export_includes_medication_events(client, auth_headers):
    client.post("/v2/medications/events", json=_BASE_MED_EVENT, headers=auth_headers)
    r = client.get("/entries/export", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "medication_events" in data
    assert len(data["medication_events"]) == 1
    assert data["medication_events"][0]["medication_name"] == "Methotrexate"


# ---------------------------------------------------------------------------
# Flare events
# ---------------------------------------------------------------------------

_BASE_FLARE = {
    "start_date":     "2026-01-10",
    "condition_type": "psoriasis",
    "severity":       7,
}


def test_create_flare_event(client, auth_headers):
    r = client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["start_date"] == "2026-01-10"
    assert r.json()["condition_type"] == "psoriasis"
    assert r.json()["confidence_source"] == "user_confirmed"
    assert r.json()["end_date"] is None
    assert "id" in r.json()


def test_create_open_flare(client, auth_headers):
    r = client.post("/v2/flares/", json={**_BASE_FLARE, "end_date": None}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["end_date"] is None


def test_list_flares(client, auth_headers):
    client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers)
    r = client.get("/v2/flares/", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_flares_from_filter(client, auth_headers):
    for d in ["2026-01-01", "2026-02-01", "2026-03-01"]:
        client.post("/v2/flares/", json={**_BASE_FLARE, "start_date": d}, headers=auth_headers)
    r = client.get("/v2/flares/?from=2026-02-01", headers=auth_headers)
    assert len(r.json()) == 2


def test_list_flares_condition_filter(client, auth_headers):
    client.post("/v2/flares/", json={**_BASE_FLARE, "condition_type": "psoriasis"}, headers=auth_headers)
    client.post("/v2/flares/", json={**_BASE_FLARE, "condition_type": "psa"}, headers=auth_headers)
    r = client.get("/v2/flares/?condition=psa", headers=auth_headers)
    assert len(r.json()) == 1
    assert r.json()[0]["condition_type"] == "psa"


def test_patch_close_flare(client, auth_headers):
    flare_id = client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers).json()["id"]
    r = client.patch(f"/v2/flares/{flare_id}", json={"end_date": "2026-01-15"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["end_date"] == "2026-01-15"


def test_patch_severity_notes(client, auth_headers):
    flare_id = client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers).json()["id"]
    r = client.patch(f"/v2/flares/{flare_id}", json={"severity": 9, "notes": "very bad"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["severity"] == 9
    assert r.json()["notes"] == "very bad"


def test_patch_nonexistent_flare(client, auth_headers):
    r = client.patch("/v2/flares/9999", json={"end_date": "2026-01-15"}, headers=auth_headers)
    assert r.status_code == 404


def test_delete_flare(client, auth_headers):
    flare_id = client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers).json()["id"]
    assert client.delete(f"/v2/flares/{flare_id}", headers=auth_headers).status_code == 204
    assert len(client.get("/v2/flares/", headers=auth_headers).json()) == 0


def test_delete_nonexistent_flare(client, auth_headers):
    assert client.delete("/v2/flares/9999", headers=auth_headers).status_code == 404


def test_invalid_condition_type(client, auth_headers):
    assert client.post("/v2/flares/", json={**_BASE_FLARE, "condition_type": "migraine"}, headers=auth_headers).status_code == 422


def test_severity_out_of_range(client, auth_headers):
    assert client.post("/v2/flares/", json={**_BASE_FLARE, "severity": 11}, headers=auth_headers).status_code == 422


def test_export_includes_flare_events(client, auth_headers):
    client.post("/v2/flares/", json=_BASE_FLARE, headers=auth_headers)
    r = client.get("/entries/export", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "flare_events" in data
    assert len(data["flare_events"]) == 1
    assert data["flare_events"][0]["condition_type"] == "psoriasis"


def test_backfill_creates_legacy_flare_events(db_session):
    from sqlalchemy import text
    from app.models import User, Entry, FlareEvent

    user = User(username="btest", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    for i, flag in [(1, 1), (2, 0), (3, 1)]:
        e = Entry(
            user_id=user.id, date=f"2026-0{i}-01",
            itch=3, redness=3, scaling=3, joint_pain=3, fatigue=3,
            stress_level=3, sleep_quality=7, diet_quality=7,
            missed_medication=0, topical_applied=1, legacy_flare_flag=flag,
        )
        db_session.add(e)
    db_session.commit()

    db_session.execute(text("""
        INSERT INTO flare_events (user_id, start_date, end_date, condition_type, confidence_source)
        SELECT user_id, date, date, 'psoriasis', 'legacy'
        FROM entries
        WHERE legacy_flare_flag IS NOT NULL AND legacy_flare_flag != 0
          AND user_id = :uid
    """), {"uid": user.id})
    db_session.commit()

    count = db_session.query(FlareEvent).filter_by(user_id=user.id, confidence_source="legacy").count()
    assert count == 2


# ---------------------------------------------------------------------------
# External triggers — weather service (direct unit tests, no HTTP)
# ---------------------------------------------------------------------------

def _make_mock_weather_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "daily": {
            "time": ["2026-01-01"],
            "temperature_2m_max": [25.0],
            "uv_index_max": [6.0],
            "precipitation_sum": [0.5],
        },
        "hourly": {
            "time": [f"2026-01-01T{h:02d}:00" for h in range(24)],
            "relative_humidity_2m": [65] * 24,
            "cloud_cover": [40] * 24,
            "pressure_msl": [1012.0] * 24,
        },
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_fetch_and_save_direct(db_session):
    from app.models import User, WeatherCapture
    from app.services.weather import fetch_and_save

    user = User(username="wtest", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with patch("app.services.weather.requests.get", return_value=_make_mock_weather_response()):
        fetch_and_save(user.id, 32.73, 74.86, "2026-01-01", db_session)

    capture = db_session.query(WeatherCapture).filter_by(user_id=user.id, date="2026-01-01").first()
    assert capture is not None
    assert capture.temperature_c == 25.0
    assert capture.humidity_pct == 65.0  # hourly index 12
    assert capture.uv_index == 6.0
    assert capture.precipitation_mm == 0.5
    assert capture.source == "open-meteo"


def test_fetch_and_save_idempotent(db_session):
    from app.models import User, WeatherCapture
    from app.services.weather import fetch_and_save

    user = User(username="wtest2", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with patch("app.services.weather.requests.get", return_value=_make_mock_weather_response()):
        fetch_and_save(user.id, 32.73, 74.86, "2026-01-01", db_session)
        fetch_and_save(user.id, 32.73, 74.86, "2026-01-01", db_session)

    count = db_session.query(WeatherCapture).filter_by(user_id=user.id, date="2026-01-01").count()
    assert count == 1


def test_weather_failure_no_crash(db_session):
    from app.models import User, WeatherCapture
    from app.services.weather import fetch_and_save

    user = User(username="wtest3", hashed_password="h")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with patch("app.services.weather.requests.get", side_effect=Exception("timeout")):
        fetch_and_save(user.id, 32.73, 74.86, "2026-01-01", db_session)  # must not raise

    count = db_session.query(WeatherCapture).filter_by(user_id=user.id, date="2026-01-01").count()
    assert count == 0
