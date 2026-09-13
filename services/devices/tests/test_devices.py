from conftest import (
    create_datacenter,
    global_admin_headers,
    operator_headers,
    per_dc_admin_headers,
)


def _create_device(client, headers, datacenter_id, **overrides):
    payload = {"name": "srv-01", "datacenter_id": datacenter_id, "type": "server"}
    payload.update(overrides)
    return client.post("/devices", json=payload, headers=headers)


def _setup_dc(client):
    return create_datacenter(client, global_admin_headers()).json()["id"]


# --- Global admin: create ---


def test_create_device_global_admin_defaults(client):
    dc_id = _setup_dc(client)

    r = _create_device(client, global_admin_headers(), dc_id)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "srv-01"
    assert body["datacenter_id"] == dc_id
    assert body["type"] == "server"
    assert body["state"] == "ok"
    assert body["description"] is None
    assert body["serial_number"] is None
    assert "id" in body
    assert "created_at" in body


def test_create_device_with_all_fields(client):
    dc_id = _setup_dc(client)

    r = _create_device(
        client,
        global_admin_headers(),
        dc_id,
        description="rack A3",
        serial_number="SN-001",
        state="warning",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["description"] == "rack A3"
    assert body["serial_number"] == "SN-001"
    assert body["state"] == "warning"


# --- Validation ---


def test_create_device_missing_name(client):
    dc_id = _setup_dc(client)

    r = client.post(
        "/devices",
        json={"datacenter_id": dc_id, "type": "server"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422


def test_create_device_missing_datacenter_id(client):
    r = client.post(
        "/devices",
        json={"name": "srv-01", "type": "server"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422


def test_create_device_missing_type(client):
    dc_id = _setup_dc(client)

    r = client.post(
        "/devices",
        json={"name": "srv-01", "datacenter_id": dc_id},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422


def test_create_device_invalid_state(client):
    dc_id = _setup_dc(client)

    r = _create_device(client, global_admin_headers(), dc_id, state="broken")
    assert r.status_code == 422, r.text


def test_create_device_in_missing_datacenter(client):
    r = _create_device(client, global_admin_headers(), 999)
    assert r.status_code == 404, r.text


# --- Uniqueness: name and serial number per datacenter ---


def test_create_device_duplicate_name_same_dc(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()

    _create_device(client, headers, dc_id, name="srv-01")
    r = _create_device(client, headers, dc_id, name="srv-01")
    assert r.status_code == 409, r.text


def test_create_device_same_name_different_dc(client):
    headers = global_admin_headers()
    dc1 = create_datacenter(
        client, headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(client, headers, name="dc-ber", location="Berlin").json()[
        "id"
    ]

    _create_device(client, headers, dc1, name="srv-01")
    r = _create_device(client, headers, dc2, name="srv-01")
    assert r.status_code == 201, r.text


def test_create_device_duplicate_serial_same_dc(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()

    _create_device(client, headers, dc_id, serial_number="SN-001")
    r = _create_device(client, headers, dc_id, name="srv-02", serial_number="SN-001")
    assert r.status_code == 409, r.text


def test_create_device_same_serial_different_dc(client):
    headers = global_admin_headers()
    dc1 = create_datacenter(
        client, headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(client, headers, name="dc-ber", location="Berlin").json()[
        "id"
    ]

    _create_device(client, headers, dc1, serial_number="SN-001")
    r = _create_device(client, headers, dc2, serial_number="SN-001")
    assert r.status_code == 201, r.text


def test_create_device_null_serials_do_not_conflict(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()

    r1 = _create_device(client, headers, dc_id, name="srv-01")
    r2 = _create_device(client, headers, dc_id, name="srv-02")
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text


# --- Authorization: create scoping ---


def test_create_device_per_dc_admin_own_dc(client):
    dc_id = _setup_dc(client)

    r = _create_device(client, per_dc_admin_headers(dc_id), dc_id)
    assert r.status_code == 201, r.text


def test_create_device_per_dc_admin_other_dc_forbidden(client):
    headers = global_admin_headers()
    dc1 = create_datacenter(
        client, headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(client, headers, name="dc-ber", location="Berlin").json()[
        "id"
    ]

    r = _create_device(client, per_dc_admin_headers(dc2), dc1)
    assert r.status_code == 403, r.text


def test_create_device_operator_forbidden(client):
    dc_id = _setup_dc(client)

    r = _create_device(client, operator_headers(dc_id), dc_id)
    assert r.status_code == 403, r.text


def test_create_device_anonymous_unauthorized(client):
    dc_id = _setup_dc(client)

    r = _create_device(client, None, dc_id)
    assert r.status_code == 401


# --- List and read ---


def test_list_devices_global_admin_sees_all(client):
    headers = global_admin_headers()
    dc1 = create_datacenter(
        client, headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(client, headers, name="dc-ber", location="Berlin").json()[
        "id"
    ]

    _create_device(client, headers, dc1, name="srv-01")
    _create_device(client, headers, dc2, name="srv-02")

    r = client.get("/devices", headers=headers)
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert "srv-01" in names and "srv-02" in names


def test_list_devices_per_dc_admin_sees_only_own_dc(client):
    headers = global_admin_headers()
    dc1 = create_datacenter(
        client, headers, name="dc-ams", location="Amsterdam"
    ).json()["id"]
    dc2 = create_datacenter(client, headers, name="dc-ber", location="Berlin").json()[
        "id"
    ]

    _create_device(client, headers, dc1, name="srv-01")
    _create_device(client, headers, dc2, name="srv-02")
    _create_device(client, per_dc_admin_headers(dc2), dc2, name="srv-03")

    r = client.get("/devices", headers=per_dc_admin_headers(dc2))
    assert r.status_code == 200, r.text
    names = [d["name"] for d in r.json()]
    assert names == ["srv-02", "srv-03"]


def test_list_devices_operator_forbidden(client):
    r = client.get("/devices", headers=operator_headers(1))
    assert r.status_code == 403


def test_list_devices_anonymous_unauthorized(client):
    r = client.get("/devices")
    assert r.status_code == 401


def test_read_device_global_admin(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id).json()["id"]

    r = client.get(f"/devices/{device_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "srv-01"


def test_read_device_per_dc_admin_own_dc(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, per_dc_admin_headers(dc_id), dc_id).json()["id"]

    r = client.get(f"/devices/{device_id}", headers=per_dc_admin_headers(dc_id))
    assert r.status_code == 200


def test_read_device_per_dc_admin_other_dc_forbidden(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.get(f"/devices/{device_id}", headers=per_dc_admin_headers(dc_id + 1))
    assert r.status_code == 403, r.text


def test_read_device_not_found(client):
    r = client.get("/devices/999", headers=global_admin_headers())
    assert r.status_code == 404


def test_read_device_operator_forbidden(client):
    r = client.get("/devices/1", headers=operator_headers(1))
    assert r.status_code == 403


def test_read_device_anonymous_unauthorized(client):
    r = client.get("/devices/1")
    assert r.status_code == 401


# --- Update ---


def test_update_device_fields(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={
            "name": "srv-01-renamed",
            "type": "switch",
            "description": "rack B1",
            "serial_number": "SN-777",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "srv-01-renamed"
    assert body["type"] == "switch"
    assert body["description"] == "rack B1"
    assert body["serial_number"] == "SN-777"
    assert body["datacenter_id"] == dc_id


def test_update_device_state(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"state": "alert"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "alert"


def test_update_device_invalid_state(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"state": "critical"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422, r.text


def test_update_device_null_state_rejected(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"state": None},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422, r.text


def test_update_device_null_name_rejected(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"name": None},
        headers=global_admin_headers(),
    )
    assert r.status_code == 422, r.text


def test_update_device_clears_optional_fields(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(
        client, headers, dc_id, description="rack A3", serial_number="SN-001"
    ).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"description": None, "serial_number": None},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["description"] is None
    assert r.json()["serial_number"] is None


def test_update_device_duplicate_name_same_dc(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    _create_device(client, headers, dc_id, name="srv-01")
    other_id = _create_device(client, headers, dc_id, name="srv-02").json()["id"]

    r = client.patch(
        f"/devices/{other_id}",
        json={"name": "srv-01"},
        headers=headers,
    )
    assert r.status_code == 409, r.text


def test_update_device_keep_own_name(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id, name="srv-01").json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"description": "updated"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "srv-01"


def test_update_device_duplicate_serial_same_dc(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    _create_device(client, headers, dc_id, name="srv-01", serial_number="SN-001")
    other_id = _create_device(client, headers, dc_id, name="srv-02").json()["id"]

    r = client.patch(
        f"/devices/{other_id}",
        json={"serial_number": "SN-001"},
        headers=headers,
    )
    assert r.status_code == 409, r.text


def test_update_device_per_dc_admin_other_dc_forbidden(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"name": "hijack"},
        headers=per_dc_admin_headers(dc_id + 1),
    )
    assert r.status_code == 403, r.text


def test_update_device_not_found(client):
    r = client.patch(
        "/devices/999",
        json={"name": "ghost"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 404


def test_update_device_operator_forbidden(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.patch(
        f"/devices/{device_id}",
        json={"name": "nope"},
        headers=operator_headers(dc_id),
    )
    assert r.status_code == 403


def test_update_device_anonymous_unauthorized(client):
    r = client.patch("/devices/1", json={"name": "anon"})
    assert r.status_code == 401


# --- Delete ---


def test_delete_device(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id).json()["id"]

    r = client.delete(f"/devices/{device_id}", headers=headers)
    assert r.status_code == 204

    r2 = client.get(f"/devices/{device_id}", headers=headers)
    assert r2.status_code == 404


def test_delete_device_makes_datacenter_deletable(client):
    dc_id = _setup_dc(client)
    headers = global_admin_headers()
    device_id = _create_device(client, headers, dc_id).json()["id"]

    client.delete(f"/devices/{device_id}", headers=headers)

    r = client.delete(f"/datacenters/{dc_id}", headers=headers)
    assert r.status_code == 204, r.text


def test_delete_device_per_dc_admin_own_dc(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, per_dc_admin_headers(dc_id), dc_id).json()["id"]

    r = client.delete(f"/devices/{device_id}", headers=per_dc_admin_headers(dc_id))
    assert r.status_code == 204


def test_delete_device_per_dc_admin_other_dc_forbidden(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.delete(f"/devices/{device_id}", headers=per_dc_admin_headers(dc_id + 1))
    assert r.status_code == 403, r.text


def test_delete_device_not_found(client):
    r = client.delete("/devices/999", headers=global_admin_headers())
    assert r.status_code == 404


def test_delete_device_operator_forbidden(client):
    dc_id = _setup_dc(client)
    device_id = _create_device(client, global_admin_headers(), dc_id).json()["id"]

    r = client.delete(f"/devices/{device_id}", headers=operator_headers(dc_id))
    assert r.status_code == 403


def test_delete_device_anonymous_unauthorized(client):
    r = client.delete("/devices/1")
    assert r.status_code == 401
