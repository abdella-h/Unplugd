from conftest import (
    create_datacenter,
    global_admin_headers,
    operator_headers,
    per_dc_admin_headers,
)


def _create_device(client, datacenter_id, name="srv-01", **overrides):
    payload = {"name": name, "datacenter_id": datacenter_id, "type": "server"}
    payload.update(overrides)
    r = client.post("/devices", json=payload, headers=global_admin_headers())
    assert r.status_code == 201, r.text
    return r.json()


def _two_dcs_with_devices(client):
    dc1 = create_datacenter(client, global_admin_headers(), name="dc-ams").json()["id"]
    dc2 = create_datacenter(
        client, global_admin_headers(), name="dc-fra", location="Frankfurt"
    ).json()["id"]
    d1 = _create_device(client, dc1, name="srv-ams")
    d2 = _create_device(client, dc2, name="srv-fra")
    return dc1, dc2, d1, d2


# --- Operator scoped list ---


def test_operator_list_shows_only_own_datacenter(client):
    dc1, dc2, d1, d2 = _two_dcs_with_devices(client)

    r = client.get("/devices", headers=operator_headers(dc1))
    assert r.status_code == 200, r.text
    ids = {d["id"] for d in r.json()}
    assert ids == {d1["id"]}


def test_operator_list_empty_when_no_devices_in_scope(client):
    dc1, dc2, d1, d2 = _two_dcs_with_devices(client)
    dc3 = create_datacenter(
        client, global_admin_headers(), name="dc-lon", location="London"
    ).json()["id"]

    r = client.get("/devices", headers=operator_headers(dc3))
    assert r.status_code == 200
    assert r.json() == []


def test_operator_list_without_datacenter_forbidden(client):
    r = client.get("/devices", headers=operator_headers(None))
    assert r.status_code == 403


# --- Operator scoped read ---


def test_operator_read_device_in_own_datacenter(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.get(f"/devices/{d1['id']}", headers=operator_headers(dc1))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == d1["id"]


def test_operator_read_device_in_other_datacenter_forbidden(client):
    dc1, _, _, d2 = _two_dcs_with_devices(client)

    r = client.get(f"/devices/{d2['id']}", headers=operator_headers(dc1))
    assert r.status_code == 403


# --- State reporting via sub-resource ---


def test_operator_reports_state_in_own_datacenter(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d1['id']}/state",
        json={"state": "warning"},
        headers=operator_headers(dc1),
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "warning"
    assert r.json()["name"] == d1["name"]

    r = client.get(f"/devices/{d1['id']}", headers=global_admin_headers())
    assert r.json()["state"] == "warning"


def test_operator_reports_state_alert_and_ok(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    for state in ("alert", "ok"):
        r = client.put(
            f"/devices/{d1['id']}/state",
            json={"state": state},
            headers=operator_headers(dc1),
        )
        assert r.status_code == 200, r.text
        assert r.json()["state"] == state


def test_operator_state_report_other_datacenter_forbidden(client):
    dc1, _, _, d2 = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d2['id']}/state",
        json={"state": "alert"},
        headers=operator_headers(dc1),
    )
    assert r.status_code == 403


def test_state_report_invalid_state_rejected(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d1['id']}/state",
        json={"state": "onfire"},
        headers=operator_headers(dc1),
    )
    assert r.status_code == 422


def test_state_report_missing_state_rejected(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d1['id']}/state", json={}, headers=operator_headers(dc1)
    )
    assert r.status_code == 422


def test_state_report_cannot_change_inventory_fields(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    for field, value in (
        ("name", "hacked"),
        ("type", "hacked"),
        ("description", "hacked"),
        ("serial_number", "SN-HACK"),
    ):
        r = client.put(
            f"/devices/{d1['id']}/state",
            json={"state": "alert", field: value},
            headers=operator_headers(dc1),
        )
        assert r.status_code == 422, field

    r = client.get(f"/devices/{d1['id']}", headers=global_admin_headers())
    assert r.json()["name"] == d1["name"]


def test_state_report_unknown_device_not_found(client):
    dc1, _, _, _ = _two_dcs_with_devices(client)

    r = client.put(
        "/devices/9999/state",
        json={"state": "ok"},
        headers=operator_headers(dc1),
    )
    assert r.status_code == 404


def test_operator_state_report_without_datacenter_forbidden(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d1['id']}/state",
        json={"state": "ok"},
        headers=operator_headers(None),
    )
    assert r.status_code == 403


# --- Admin state writes follow scope rules ---


def test_global_admin_reports_state_anywhere(client):
    _, dc2, _, d2 = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d2['id']}/state",
        json={"state": "alert"},
        headers=global_admin_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "alert"


def test_per_dc_admin_reports_state_in_own_datacenter(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d1['id']}/state",
        json={"state": "warning"},
        headers=per_dc_admin_headers(dc1),
    )
    assert r.status_code == 200, r.text


def test_per_dc_admin_state_report_other_datacenter_forbidden(client):
    dc1, _, _, d2 = _two_dcs_with_devices(client)

    r = client.put(
        f"/devices/{d2['id']}/state",
        json={"state": "alert"},
        headers=per_dc_admin_headers(dc1),
    )
    assert r.status_code == 403


# --- Unauthenticated rejected on all inventory paths ---


def test_anonymous_rejected_on_all_device_paths(client):
    dc1, _, d1, _ = _two_dcs_with_devices(client)

    responses = [
        client.get("/devices"),
        client.get(f"/devices/{d1['id']}"),
        client.post("/devices", json={"name": "x", "datacenter_id": dc1, "type": "t"}),
        client.patch(f"/devices/{d1['id']}", json={"name": "y"}),
        client.delete(f"/devices/{d1['id']}"),
        client.put(f"/devices/{d1['id']}/state", json={"state": "ok"}),
    ]
    for r in responses:
        assert r.status_code == 401, (r.request.method, r.request.url)
