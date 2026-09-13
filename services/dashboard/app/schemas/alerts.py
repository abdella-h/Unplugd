from datetime import datetime

from pydantic import BaseModel


class AlertRead(BaseModel):
    id: int
    device_id: int
    datacenter_id: int
    old_state: str
    new_state: str
    reporter: str
    occurred_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None

    model_config = {"from_attributes": True}


class AcknowledgeResponse(AlertRead):
    device_reset_ok: bool = True
