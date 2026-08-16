from pydantic import BaseModel, EmailStr


class InitialAdminCreate(BaseModel):
    first_name: str | None
    last_name: str | None
    username: str
    email: EmailStr
    password: str
