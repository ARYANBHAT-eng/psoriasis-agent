import pytest


def test_profile_auto_created(client, auth_headers):
    r = client.get("/v2/profile", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["has_psoriasis"] is True
    assert data["has_psa"] is False
    assert data["tracks_cycle"] is False
    assert data["timezone"] == "UTC"
    assert "id" in data


def test_profile_update_conditions(client, auth_headers):
    client.patch("/v2/profile", json={"has_psa": True}, headers=auth_headers)
    r = client.get("/v2/profile", headers=auth_headers)
    assert r.json()["has_psa"] is True


def test_profile_update_location(client, auth_headers):
    r = client.patch(
        "/v2/profile",
        json={"location_city": "Jammu", "location_lat": 32.7338, "location_lon": 74.8580},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["location_city"] == "Jammu"
    assert data["location_lat"] == round(32.7338, 2)
    assert data["location_lon"] == round(74.8580, 2)


def test_profile_location_out_of_range(client, auth_headers):
    r = client.patch("/v2/profile", json={"location_lat": 999.0}, headers=auth_headers)
    assert r.status_code == 422


def test_profile_update_timezone(client, auth_headers):
    r = client.patch("/v2/profile", json={"timezone": "Asia/Kolkata"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["timezone"] == "Asia/Kolkata"
