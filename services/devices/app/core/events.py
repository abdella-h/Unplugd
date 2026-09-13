from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.device_state import DeviceState


class DeviceStateChanged(BaseModel):
    type: Literal["device_status_changed"] = "device_status_changed"
    device_id: int
    datacenter_id: int
    old_state: DeviceState
    new_state: DeviceState
    reporter: str
    occurred_at: datetime
