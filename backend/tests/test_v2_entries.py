import pytest

_FULL_ENTRY = {
    "date": "2026-02-01",
    "itch": 4.0, "redness": 3.0, "scaling": 2.0,
    "joint_pain": 5.0, "fatigue": 3.0, "stress_level": 4.0,
    "sleep_quality": 6.0, "diet_quality": 7.0,
    "missed_medication": 0, "topical_applied": 1,
    "morning_stiffness_minutes": 30,
    "affected_joints": ["wrist", "knee"],
    "functional_limitation": 3,
    "bsa_estimate": 15.5,
    "plaque_locations": ["scalp", "elbows"],
}

_MINIMAL_ENTRY = {
    "date": "2026-02-02",
    "itch": 2.0, "redness": 1.0, "scaling": 1.0,
    "joint_pain": 1.0, "fatigue": 1.0, "stress_level": 2.0,
    "sleep_quality": 8.0, "diet_quality": 8.0,
    "missed_medication": 0, "topical_applied": 1,
}


def test_v2_create_with_clinical_fields(client, auth_headers):
    r = client.post("/v2/entries/", json=_FULL_ENTRY, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["morning_stiffness_minutes"] == 30
    assert data["affected_joints"] == ["wrist", "knee"]
    assert data["functional_limitation"] == 3
    assert data["bsa_estimate"] == 15.5
    assert data["plaque_locations"] == ["scalp", "elbows"]


def test_v2_create_minimal(client, auth_headers):
    r = client.post("/v2/entries/", json=_MINIMAL_ENTRY, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["morning_stiffness_minutes"] is None
    assert data["bsa_estimate"] is None


def test_v1_still_works(client, auth_headers):
    r = client.post("/entries/", json=_MINIMAL_ENTRY, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["date"] == "2026-02-02"


def test_morning_stiffness_out_of_range(client, auth_headers):
    r = client.post("/v2/entries/", json={**_FULL_ENTRY, "morning_stiffness_minutes": 481}, headers=auth_headers)
    assert r.status_code == 422


def test_functional_limitation_out_of_range(client, auth_headers):
    r = client.post("/v2/entries/", json={**_FULL_ENTRY, "functional_limitation": 11}, headers=auth_headers)
    assert r.status_code == 422


def test_bsa_out_of_range(client, auth_headers):
    r = client.post("/v2/entries/", json={**_FULL_ENTRY, "bsa_estimate": 100.5}, headers=auth_headers)
    assert r.status_code == 422
