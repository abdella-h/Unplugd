from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class InitialAdminCreate(BaseModel):
    first_name: str | None
    last_name: str | None
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str | None
    last_name: str | None
    username: str
    email: EmailStr
    role: str
    datacenter_id: int | None
    is_active: bool
    last_login_at: datetime | None

    @field_validator("last_login_at")
    @classmethod
    def normalize_last_login_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
