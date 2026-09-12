from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatacenterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)


class DatacenterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DatacenterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)
