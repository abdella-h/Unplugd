import json
import os
from typing import Protocol

import pika  # type: ignore[import-untyped]
from dotenv import load_dotenv

from app.core.events import DeviceStateChanged

load_dotenv()

BROKER_URL = os.getenv("BROKER_URL", "amqp://guest:guest@localhost:5672/")

DASHBOARD_EXCHANGE = "dashboard"


def routing_key(datacenter_id: int, device_id: int) -> str:
    return f"datacenter.{datacenter_id}.device.{device_id}"


class StatePublisher(Protocol):
    def publish_device_state_changed(self, event: DeviceStateChanged) -> None: ...


class RabbitMQStatePublisher:
    """Best-effort publisher: opens a short-lived connection per event.

    Raises on broker failure; callers are expected to catch and log so a
    broker outage never blocks field reporting.
    """

    def __init__(self, broker_url: str = BROKER_URL):
        self._parameters = pika.URLParameters(broker_url)

    def publish_device_state_changed(self, event: DeviceStateChanged) -> None:
        connection = pika.BlockingConnection(self._parameters)
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=DASHBOARD_EXCHANGE, exchange_type="topic", durable=True
            )
            channel.basic_publish(
                exchange=DASHBOARD_EXCHANGE,
                routing_key=routing_key(event.datacenter_id, event.device_id),
                body=json.dumps(event.model_dump(mode="json")),
                properties=pika.BasicProperties(
                    content_type="application/json", delivery_mode=2
                ),
            )
        finally:
            connection.close()
