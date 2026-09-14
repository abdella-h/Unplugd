import asyncio
import json
import logging
import os
import threading
import time

import pika  # type: ignore[import-untyped]
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BROKER_URL = os.getenv("BROKER_URL", "amqp://guest:guest@localhost:5672/")

DASHBOARD_EXCHANGE = "dashboard"
BINDING_KEY = "datacenter.*.device.*"


class EventHub:
    """Fan-out: each subscriber gets its own asyncio.Queue; the consumer
    thread delivers into queues via each subscriber's own event loop
    (call_soon_threadsafe), so cross-thread broadcast wakes up waiters."""

    def __init__(self) -> None:
        self._subscribers: dict[asyncio.Queue, asyncio.AbstractEventLoop | None] = {}

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (sync endpoint, TestClient, or plain thread):
            # store None so broadcast() delivers directly instead of
            # scheduling onto a stale get_event_loop() loop that never runs
            # (on Python 3.12 get_event_loop() still returns such a loop
            # with a DeprecationWarning; on 3.14+ it raises, i.e. None).
            loop = None
        self._subscribers[queue] = loop
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.pop(queue, None)

    def broadcast(self, event: dict) -> None:
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        for queue, loop in list(self._subscribers.items()):
            if loop is None or loop is running:
                self._deliver(queue, event)
            else:
                loop.call_soon_threadsafe(self._deliver, queue, event)

    @staticmethod
    def _deliver(queue: asyncio.Queue, event: dict) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # Slow consumer: drop the event rather than block the stream
            # for everyone. The devices publisher is best-effort anyway.
            logger.warning("SSE subscriber queue full; dropping event")


hub = EventHub()


class DashboardConsumer:
    """Consumes device state-change events from the `dashboard` topic
    exchange in a background thread and broadcasts them to SSE subscribers
    via the event loop."""

    def __init__(self, hub_: EventHub, loop: asyncio.AbstractEventLoop):
        self._hub = hub_
        self._loop = loop
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="dashboard-consumer", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def wait_ready(self, timeout: float = 5) -> bool:
        return self._ready.wait(timeout)

    def _run(self) -> None:
        parameters = pika.URLParameters(BROKER_URL)
        while not self._stop.is_set():
            try:
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.exchange_declare(
                    exchange=DASHBOARD_EXCHANGE, exchange_type="topic", durable=True
                )
                result = channel.queue_declare(queue="", exclusive=True)
                queue_name = result.method.queue
                channel.queue_bind(
                    exchange=DASHBOARD_EXCHANGE,
                    queue=queue_name,
                    routing_key=BINDING_KEY,
                )
                channel.basic_consume(
                    queue=queue_name, on_message_callback=self._on_message
                )
                self._ready.set()
                logger.info("Dashboard consumer started on exchange %r", DASHBOARD_EXCHANGE)
                while not self._stop.is_set():
                    connection.process_data_events(time_limit=1)
                connection.close()
            except pika.exceptions.AMQPError:
                logger.warning("Broker unavailable; retrying in 5s")
                for _ in range(50):
                    if self._stop.is_set():
                        break
                    time.sleep(0.1)

    def _on_message(self, channel, method, properties, body: bytes) -> None:
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Discarding undecodable message on %s", method.routing_key)
            return
        # Persist alert-worthy events best-effort; broadcast regardless so
        # the live stream still shows recoveries (ok) even when not stored.
        try:
            from app.core.database import SessionLocal
            from app.core.store import persist_state_changed_event

            db = SessionLocal()
            try:
                persist_state_changed_event(db, event)
            finally:
                db.close()
        except Exception:  # noqa: BLE001 best-effort: broker path never crashes
            logger.warning("Failed to persist dashboard event %r", event)
        self._loop.call_soon_threadsafe(self._hub.broadcast, event)
