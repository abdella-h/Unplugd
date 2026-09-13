from fastapi.testclient import TestClient

from app.api.deps import get_hub
from app.api.endpoints.alerts import get_device_reset
from app.core.broker import EventHub
from app.core.store import persist_state_changed_event
from tests.conftest import dc_admin_headers, global_admin_headers, operator_headers

EVENT = {
    "type": "device_status_changed",
    "device_id": 7,
    "datacenter_id": 3,
    "old_state": "ok",
    "new_state": "alert",
    "reporter": "operator",
    "occurred_at": "2026-09-13T10:00:00Z",
}


def seed_alert(db_session, **overrides):
    payload = dict(EVENT)
    payload.update(overrides)
    return persist_state_changed_event(db_session, payload)


def test_persist_ignores_ok_recovery(db_session):
    event = dict(EVENT, new_state="ok")
    assert persist_state_changed_event(db_session, event) is None


def test_list_requires_admin(app, db_session):
    seed_alert(db_session)
    with TestClient(app) as client:
        resp = client.get("/alerts", headers=operator_headers(dc_id=3))
    assert resp.status_code == 403


def test_list_scoping(app, db_session):
    seed_alert(db_session, datacenter_id=3)
    seed_alert(db_session, datacenter_id=4)
    with TestClient(app) as client:
        resp = client.get("/alerts", headers=dc_admin_headers(dc_id=3))
    assert resp.status_code == 200
    assert [a["datacenter_id"] for a in resp.json()] == [3]

    with TestClient(app) as client:
        resp = client.get("/alerts", headers=global_admin_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_acknowledge_resets_device_and_broadcasts(app, db_session):
    alert = seed_alert(db_session)
    hub = EventHub()
    app.dependency_overrides[get_hub] = lambda: hub
    app.dependency_overrides[get_device_reset] = lambda: (lambda _id, _auth: True)

    with TestClient(app) as client:
        resp = client.post(
            f"/alerts/{alert.id}/acknowledge",
            headers={
                **global_admin_headers(),
                "Authorization": global_admin_headers()["Authorization"],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["acknowledged_by"] == "admin"
    assert body["device_reset_ok"] is True

    queue = hub.subscribe()
    # broadcast happened before subscribe, so seed a second alert for live check
    alert2 = seed_alert(db_session, device_id=8)
    with TestClient(app) as client:
        app.dependency_overrides[get_hub] = lambda: hub
        resp = client.post(
            f"/alerts/{alert2.id}/acknowledge",
            headers=global_admin_headers(),
        )
    assert resp.status_code == 200
    assert queue.qsize() == 1
    event = queue.get_nowait()
    assert event["type"] == "alert_acknowledged_and_resolved"


def test_acknowledge_scoped_admin_forbidden_outside_dc(app, db_session):
    alert = seed_alert(db_session, datacenter_id=3)
    app.dependency_overrides[get_device_reset] = lambda: (lambda _id, _auth: True)
    with TestClient(app) as client:
        resp = client.post(
            f"/alerts/{alert.id}/acknowledge", headers=dc_admin_headers(dc_id=4)
        )
    assert resp.status_code == 403


def test_acknowledge_device_reset_failure_still_acks(app, db_session):
    alert = seed_alert(db_session)
    app.dependency_overrides[get_device_reset] = lambda: (lambda _id, _auth: False)
    with TestClient(app) as client:
        resp = client.post(
            f"/alerts/{alert.id}/acknowledge", headers=global_admin_headers()
        )
    assert resp.status_code == 200
    assert resp.json()["device_reset_ok"] is False
    assert resp.json()["acknowledged_by"] == "admin"


def test_acknowledge_reset_exception_still_acks(app, db_session):
    def boom(_device_id, _auth):
        raise TimeoutError("devices unreachable")

    alert = seed_alert(db_session)
    app.dependency_overrides[get_device_reset] = lambda: boom
    with TestClient(app) as client:
        resp = client.post(
            f"/alerts/{alert.id}/acknowledge", headers=global_admin_headers()
        )
    assert resp.status_code == 200
    assert resp.json()["device_reset_ok"] is False
    assert resp.json()["acknowledged_by"] == "admin"


def test_repeat_acknowledge_keeps_first_ack_and_rebroadcasts(app, db_session):
    calls = []

    def reset(_device_id, _auth):
        calls.append(True)
        return True

    alert = seed_alert(db_session)
    hub = EventHub()
    app.dependency_overrides[get_hub] = lambda: hub
    app.dependency_overrides[get_device_reset] = lambda: reset
    with TestClient(app) as client:
        first = client.post(
            f"/alerts/{alert.id}/acknowledge", headers=global_admin_headers()
        )
        assert first.status_code == 200
        first_by = first.json()["acknowledged_by"]

        queue = hub.subscribe()
        second = client.post(
            f"/alerts/{alert.id}/acknowledge", headers=global_admin_headers()
        )
    assert second.status_code == 200
    assert second.json()["acknowledged_by"] == first_by
    assert second.json()["device_reset_ok"] is True
    assert len(calls) == 2
    assert queue.qsize() == 1
    assert queue.get_nowait()["type"] == "alert_acknowledged_and_resolved"
