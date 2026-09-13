from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.device_state import DeviceState


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    datacenter_id: int
    type: str = Field(min_length=1, max_length=255)
    description: str | None = None
    serial_number: str | None = Field(default=None, min_length=1, max_length=255)
    state: DeviceState = "ok"


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    datacenter_id: int
    name: str
    type: str
    description: str | None = None
    serial_number: str | None = None
    state: DeviceState
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: DeviceState


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    serial_number: str | None = Field(default=None, min_length=1, max_length=255)
    state: DeviceState | None = None

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for field in ("name", "type", "state"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"'{field}' cannot be null")
        return self
