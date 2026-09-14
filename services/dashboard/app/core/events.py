from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DeviceState = Literal["ok", "warning", "alert"]


class DeviceStateChanged(BaseModel):
    """Consumer-side copy of the event contract published by the devices
    service (see docs/events/device-state-changed.md)."""

    type: Literal["device_status_changed"] = "device_status_changed"
    device_id: int
    datacenter_id: int
    old_state: DeviceState
    new_state: DeviceState
    reporter: str
    occurred_at: datetime
