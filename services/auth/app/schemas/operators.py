from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OperatorInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    datacenter_id: int


class OperatorAccept(BaseModel):
    token: str
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
