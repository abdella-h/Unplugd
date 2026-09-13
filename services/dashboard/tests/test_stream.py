import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_hub
from app.api.endpoints.stream import stream as stream_endpoint
from app.core.broker import EventHub
from tests.conftest import operator_headers

EVENT = {
    "type": "device_status_changed",
    "device_id": 7,
    "datacenter_id": 3,
    "old_state": "ok",
    "new_state": "alert",
    "reporter": "operator",
    "occurred_at": "2026-09-13T10:00:00Z",
}


def test_stream_requires_token(app):
    with TestClient(app) as client:
        resp = client.get("/stream")
    assert resp.status_code in (401, 403)


def test_stream_rejects_operator(app):
    with TestClient(app) as client:
        resp = client.get("/stream", headers=operator_headers())
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_stream_scoped_admin_only_receives_own_dc():
    # httpx ASGITransport buffers streaming responses, so drive the
    # endpoint generator directly instead of going through HTTP.
    hub = EventHub()
    resp = await stream_endpoint(
        {"username": "admin", "role": "admin", "dc_id": 3}, hub
    )
    assert resp.media_type == "text/event-stream"
    assert hub._subscribers, "subscriber never registered"

    other = dict(EVENT)
    other["datacenter_id"] = 99
    hub.broadcast(other)
    hub.broadcast(dict(EVENT))

    chunk = await asyncio.wait_for(resp.body_iterator.__anext__(), timeout=5)
    assert chunk.startswith("data:")
    assert json.loads(chunk[len("data:"):].strip()) == EVENT
    await resp.body_iterator.aclose()


@pytest.mark.anyio
async def test_stream_allows_global_admin_and_delivers_events():
    hub = EventHub()
    resp = await stream_endpoint(
        {"username": "admin", "role": "admin", "dc_id": None}, hub
    )
    assert resp.media_type == "text/event-stream"
    assert hub._subscribers, "subscriber never registered"

    hub.broadcast(dict(EVENT))

    chunk = await asyncio.wait_for(resp.body_iterator.__anext__(), timeout=5)
    assert chunk.startswith("data:")
    assert json.loads(chunk[len("data:"):].strip()) == EVENT
    await resp.body_iterator.aclose()


def test_broadcast_drops_event_when_subscriber_queue_full(app):
    hub = EventHub()
    queue = hub.subscribe(maxsize=1)
    hub.broadcast({"n": 1})
    hub.broadcast({"n": 2})  # must not raise or block
    assert queue.qsize() == 1
    hub.unsubscribe(queue)
