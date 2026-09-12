from datetime import datetime, timedelta, timezone

import jwt

from app.core.security import ALGORITHM, SECRET_KEY
from app.models.devices import Device

DC_PAYLOAD = {"name": "dc-ams", "location": "Amsterdam"}


def make_token(role="admin", dc_id=None, username="admin"):
    payload = {
        "sub": username,
        "role": role,
        "dc_id": dc_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def admin_headers():
    return {"Authorization": f"Bearer {make_token(role='admin', dc_id=None)}"}


def per_dc_admin_headers():
    return {"Authorization": f"Bearer {make_token(role='admin', dc_id=3)}"}


def operator_headers():
    return {"Authorization": f"Bearer {make_token(role='operator', dc_id=3)}"}


def _create_dc(client, headers, name="dc-ams", location="Amsterdam"):
    return client.post(
        "/datacenters",
        json={"name": name, "location": location},
        headers=headers,
    )


# --- Global admin: create, list, read, update, delete ---


def test_create_datacenter_global_admin(client):
    r = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "dc-ams"
    assert body["location"] == "Amsterdam"
    assert "id" in body
    assert "created_at" in body


def test_list_datacenters_global_admin(client):
    _create_dc(client, admin_headers(), **DC_PAYLOAD)
    _create_dc(client, admin_headers(), name="dc-ber", location="Berlin")

    r = client.get("/datacenters", headers=admin_headers())
    assert r.status_code == 200
    assert len(r.json()) == 2
    names = [dc["name"] for dc in r.json()]
    assert "dc-ams" in names and "dc-ber" in names


def test_read_single_datacenter_global_admin(client):
    created = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.get(f"/datacenters/{dc_id}", headers=admin_headers())
    assert r.status_code == 200
    assert r.json()["name"] == "dc-ams"


def test_update_datacenter_global_admin(client):
    created = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.patch(
        f"/datacenters/{dc_id}",
        json={"location": "Rotterdam"},
        headers=admin_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["location"] == "Rotterdam"
    assert r.json()["name"] == "dc-ams"


def test_delete_datacenter_global_admin(client):
    created = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.delete(f"/datacenters/{dc_id}", headers=admin_headers())
    assert r.status_code == 204

    r2 = client.get(f"/datacenters/{dc_id}", headers=admin_headers())
    assert r2.status_code == 404


# --- Validation: uniqueness, required fields ---


def test_create_datacenter_duplicate_name(client):
    _create_dc(client, admin_headers(), **DC_PAYLOAD)
    r = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    assert r.status_code == 409, r.text


def test_create_datacenter_missing_name(client):
    r = client.post(
        "/datacenters",
        json={"location": "Amsterdam"},
        headers=admin_headers(),
    )
    assert r.status_code == 422


def test_create_datacenter_missing_location(client):
    r = client.post(
        "/datacenters",
        json={"name": "dc-ams"},
        headers=admin_headers(),
    )
    assert r.status_code == 422


def test_update_datacenter_duplicate_name(client):
    dc1 = _create_dc(client, admin_headers(), name="dc-one", location="Ams")
    _create_dc(client, admin_headers(), name="dc-two", location="Ber")

    r = client.patch(
        f"/datacenters/{dc1.json()['id']}",
        json={"name": "dc-two"},
        headers=admin_headers(),
    )
    assert r.status_code == 409, r.text


# --- Delete blocked while devices remain ---


def test_delete_datacenter_with_devices_blocked(client, db_session):
    created = _create_dc(client, admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    db_session.add(Device(datacenter_id=dc_id))
    db_session.commit()

    r = client.delete(f"/datacenters/{dc_id}", headers=admin_headers())
    assert r.status_code == 409, r.text


# --- Not-found cases ---


def test_read_datacenter_not_found(client):
    r = client.get("/datacenters/999", headers=admin_headers())
    assert r.status_code == 404


def test_update_datacenter_not_found(client):
    r = client.patch(
        "/datacenters/999",
        json={"location": "nowhere"},
        headers=admin_headers(),
    )
    assert r.status_code == 404


def test_delete_datacenter_not_found(client):
    r = client.delete("/datacenters/999", headers=admin_headers())
    assert r.status_code == 404


# --- Authorization: all endpoints require global admin ---


def test_create_datacenter_per_dc_admin_forbidden(client):
    r = _create_dc(client, per_dc_admin_headers(), **DC_PAYLOAD)
    assert r.status_code == 403


def test_create_datacenter_operator_forbidden(client):
    r = _create_dc(client, operator_headers(), **DC_PAYLOAD)
    assert r.status_code == 403


def test_create_datacenter_anonymous_unauthorized(client):
    r = client.post("/datacenters", json=DC_PAYLOAD)
    assert r.status_code == 401


def test_list_datacenters_per_dc_admin_forbidden(client):
    r = client.get("/datacenters", headers=per_dc_admin_headers())
    assert r.status_code == 403


def test_list_datacenters_operator_forbidden(client):
    r = client.get("/datacenters", headers=operator_headers())
    assert r.status_code == 403


def test_list_datacenters_anonymous_unauthorized(client):
    r = client.get("/datacenters")
    assert r.status_code == 401


def test_read_datacenter_per_dc_admin_forbidden(client):
    r = client.get("/datacenters/1", headers=per_dc_admin_headers())
    assert r.status_code == 403


def test_read_datacenter_operator_forbidden(client):
    r = client.get("/datacenters/1", headers=operator_headers())
    assert r.status_code == 403


def test_read_datacenter_anonymous_unauthorized(client):
    r = client.get("/datacenters/1")
    assert r.status_code == 401


def test_update_datacenter_per_dc_admin_forbidden(client):
    r = client.patch(
        "/datacenters/1",
        json={"location": "x"},
        headers=per_dc_admin_headers(),
    )
    assert r.status_code == 403


def test_update_datacenter_operator_forbidden(client):
    r = client.patch(
        "/datacenters/1",
        json={"location": "x"},
        headers=operator_headers(),
    )
    assert r.status_code == 403


def test_update_datacenter_anonymous_unauthorized(client):
    r = client.patch("/datacenters/1", json={"location": "x"})
    assert r.status_code == 401


def test_delete_datacenter_per_dc_admin_forbidden(client):
    r = client.delete("/datacenters/1", headers=per_dc_admin_headers())
    assert r.status_code == 403


def test_delete_datacenter_operator_forbidden(client):
    r = client.delete("/datacenters/1", headers=operator_headers())
    assert r.status_code == 403


def test_delete_datacenter_anonymous_unauthorized(client):
    r = client.delete("/datacenters/1")
    assert r.status_code == 401


def test_invalid_role_token_rejected(client):
    token = make_token(role="guard", dc_id=None)
    r = client.get(
        "/datacenters", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401
