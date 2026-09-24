from conftest import (
    create_datacenter,
    global_admin_headers,
    make_token,
    operator_headers,
    per_dc_admin_headers,
)

from app.models.devices import Device

DC_PAYLOAD = {"name": "dc-ams", "location": "Amsterdam"}


# --- Global admin: create, list, read, update, delete ---


def test_create_datacenter_global_admin(client):
    r = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "dc-ams"
    assert body["location"] == "Amsterdam"
    assert "id" in body
    assert "created_at" in body


def test_list_datacenters_global_admin(client):
    create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    create_datacenter(client, global_admin_headers(), name="dc-ber", location="Berlin")

    r = client.get("/datacenters", headers=global_admin_headers())
    assert r.status_code == 200
    assert len(r.json()) == 2
    names = [dc["name"] for dc in r.json()]
    assert "dc-ams" in names and "dc-ber" in names


def test_read_single_datacenter_global_admin(client):
    created = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.get(f"/datacenters/{dc_id}", headers=global_admin_headers())
    assert r.status_code == 200
    assert r.json()["name"] == "dc-ams"


def test_update_datacenter_global_admin(client):
    created = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.patch(
        f"/datacenters/{dc_id}",
        json={"location": "Rotterdam"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["location"] == "Rotterdam"
    assert r.json()["name"] == "dc-ams"


def test_delete_datacenter_global_admin(client):
    created = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    r = client.delete(f"/datacenters/{dc_id}", headers=global_admin_headers())
    assert r.status_code == 204

    r2 = client.get(f"/datacenters/{dc_id}", headers=global_admin_headers())
    assert r2.status_code == 404


# --- Validation: uniqueness, required fields ---


def test_create_datacenter_duplicate_name(client):
    create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    r = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    assert r.status_code == 409, r.text


def test_create_datacenter_missing_name(client):
    r = client.post(
        "/datacenters",
        json={"location": "Amsterdam"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422


def test_create_datacenter_missing_location(client):
    r = client.post(
        "/datacenters",
        json={"name": "dc-ams"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422


def test_update_datacenter_duplicate_name(client):
    dc1 = create_datacenter(
        client, global_admin_headers(), name="dc-one", location="Ams"
    )
    create_datacenter(client, global_admin_headers(), name="dc-two", location="Ber")

    r = client.patch(
        f"/datacenters/{dc1.json()['id']}",
        json={"name": "dc-two"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 409, r.text


# --- Delete blocked while devices remain ---


def test_delete_datacenter_with_devices_blocked(client, db_session):
    created = create_datacenter(client, global_admin_headers(), **DC_PAYLOAD)
    dc_id = created.json()["id"]

    db_session.add(Device(datacenter_id=dc_id, name="srv-01", type="server"))
    db_session.commit()

    r = client.delete(f"/datacenters/{dc_id}", headers=global_admin_headers())
    assert r.status_code == 409, r.text


# --- Not-found cases ---


def test_read_datacenter_not_found(client):
    r = client.get("/datacenters/999", headers=global_admin_headers())
    assert r.status_code == 404


def test_update_datacenter_not_found(client):
    r = client.patch(
        "/datacenters/999",
        json={"location": "nowhere"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 404


def test_delete_datacenter_not_found(client):
    r = client.delete("/datacenters/999", headers=global_admin_headers())
    assert r.status_code == 404


def test_create_datacenter_per_dc_admin_forbidden(client):
    r = create_datacenter(client, per_dc_admin_headers(3), **DC_PAYLOAD)
    assert r.status_code == 403


def test_create_datacenter_operator_forbidden(client):
    r = create_datacenter(client, operator_headers(3), **DC_PAYLOAD)
    assert r.status_code == 403


def test_create_datacenter_anonymous_unauthorized(client):
    r = client.post("/datacenters", json=DC_PAYLOAD)
    assert r.status_code == 401


def test_list_datacenters_per_dc_admin_sees_only_own_datacenter(client):
    global_headers = global_admin_headers()
    dc1 = create_datacenter(
        client, global_headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(
        client, global_headers, name="dc-ber", location="Berlin"
    ).json()["id"]

    r = client.get("/datacenters", headers=per_dc_admin_headers(dc1))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == dc1
    assert dc2 != body[0]["id"]


def test_list_datacenters_operator_sees_only_own_datacenter(client):
    global_headers = global_admin_headers()
    dc1 = create_datacenter(
        client, global_headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    create_datacenter(
        client, global_headers, name="dc-ber", location="Berlin"
    )

    r = client.get("/datacenters", headers=operator_headers(dc1))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == dc1


def test_list_datacenters_unscoped_operator_forbidden(client):
    r = client.get("/datacenters", headers=operator_headers(None))
    assert r.status_code == 403


def test_datacenter_mutations_remain_global_admin_only(client):
    global_headers = global_admin_headers()
    dc1 = create_datacenter(
        client, global_headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    create_datacenter(
        client, global_headers, name="dc-ber", location="Berlin"
    )

    for headers in (per_dc_admin_headers(dc1), operator_headers(dc1)):
        responses = [
            client.post(
                "/datacenters",
                json={"name": "dc-new", "location": "Utrecht"},
                headers=headers,
            ),
            client.patch(
                f"/datacenters/{dc1}",
                json={"location": "Rotterdam"},
                headers=headers,
            ),
            client.delete(f"/datacenters/{dc1}", headers=headers),
        ]
        for r in responses:
            assert r.status_code == 403, (r.request.method, r.request.url, r.text)


def test_list_datacenters_anonymous_unauthorized(client):
    r = client.get("/datacenters")
    assert r.status_code == 401


def test_read_datacenter_per_dc_admin_forbidden(client):
    r = client.get("/datacenters/1", headers=per_dc_admin_headers(3))
    assert r.status_code == 403


def test_read_datacenter_operator_forbidden(client):
    r = client.get("/datacenters/1", headers=operator_headers(3))
    assert r.status_code == 403


def test_read_datacenter_anonymous_unauthorized(client):
    r = client.get("/datacenters/1")
    assert r.status_code == 401


def test_update_datacenter_per_dc_admin_forbidden(client):
    r = client.patch(
        "/datacenters/1",
        json={"location": "x"},
        headers=per_dc_admin_headers(3),
    )
    assert r.status_code == 403


def test_update_datacenter_operator_forbidden(client):
    r = client.patch(
        "/datacenters/1",
        json={"location": "x"},
        headers=operator_headers(3),
    )
    assert r.status_code == 403


def test_update_datacenter_anonymous_unauthorized(client):
    r = client.patch("/datacenters/1", json={"location": "x"})
    assert r.status_code == 401


def test_delete_datacenter_per_dc_admin_forbidden(client):
    r = client.delete("/datacenters/1", headers=per_dc_admin_headers(3))
    assert r.status_code == 403


def test_delete_datacenter_operator_forbidden(client):
    r = client.delete("/datacenters/1", headers=operator_headers(3))
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
