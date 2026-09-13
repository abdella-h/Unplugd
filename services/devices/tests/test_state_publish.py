import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_state_publisher
from app.api.endpoints import router
from app.core.database import Base, get_db
from tests.conftest import (
    TestSession,
    create_datacenter,
    engine,
    global_admin_headers,
    operator_headers,
)


class StubPublisher:
    def __init__(self):
        self.events = []

    def publish_device_state_changed(self, event):
        self.events.append(event)


class BrokenPublisher:
    def publish_device_state_changed(self, event):
        raise ConnectionError("broker unreachable")


@pytest.fixture
def publisher():
    return StubPublisher()


@pytest.fixture
def pub_client(publisher):
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_state_publisher] = lambda: publisher

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)


def make_device(client, dc_id, name="pdu-1", state="ok"):
    resp = client.post(
        "/devices",
        json={
            "name": name,
            "datacenter_id": dc_id,
            "type": "pdu",
            "state": state,
        },
        headers=global_admin_headers(),
    )
    assert resp.status_code == 201
    return resp.json()


def test_state_change_publishes_event(pub_client, publisher):
    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    device = make_device(pub_client, dc_id)

    resp = pub_client.put(
        f"/devices/{device['id']}/state",
        json={"state": "alert"},
        headers=operator_headers(dc_id),
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "alert"

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.type == "device_status_changed"
    assert event.device_id == device["id"]
    assert event.datacenter_id == dc_id
    assert event.old_state == "ok"
    assert event.new_state == "alert"
    assert event.reporter == "operator"
    assert event.occurred_at is not None


def test_noop_state_write_emits_nothing(pub_client, publisher):
    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    device = make_device(pub_client, dc_id)

    resp = pub_client.put(
        f"/devices/{device['id']}/state",
        json={"state": "ok"},
        headers=operator_headers(dc_id),
    )
    assert resp.status_code == 200
    assert publisher.events == []


def test_create_emits_nothing(pub_client, publisher):
    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    make_device(pub_client, dc_id, state="warning")
    assert publisher.events == []


def test_patch_without_state_change_emits_nothing(pub_client, publisher):
    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    device = make_device(pub_client, dc_id)

    resp = pub_client.patch(
        f"/devices/{device['id']}",
        json={"description": "new description"},
        headers=global_admin_headers(),
    )
    assert resp.status_code == 200
    assert publisher.events == []


def test_patch_changing_state_publishes(pub_client, publisher):
    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    device = make_device(pub_client, dc_id)

    resp = pub_client.patch(
        f"/devices/{device['id']}",
        json={"state": "warning"},
        headers=global_admin_headers(),
    )
    assert resp.status_code == 200

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.old_state == "ok"
    assert event.new_state == "warning"
    assert event.reporter == "admin"


def test_broker_outage_still_succeeds(pub_client, caplog):
    pub_client.app.dependency_overrides[get_state_publisher] = lambda: BrokenPublisher()

    dc_id = create_datacenter(pub_client, global_admin_headers()).json()["id"]
    device = make_device(pub_client, dc_id)

    with caplog.at_level(logging.WARNING):
        resp = pub_client.put(
            f"/devices/{device['id']}/state",
            json={"state": "alert"},
            headers=operator_headers(dc_id),
        )

    assert resp.status_code == 200
    assert resp.json()["state"] == "alert"  # persisted despite the outage
    assert any("broker" in r.message.lower() for r in caplog.records)
