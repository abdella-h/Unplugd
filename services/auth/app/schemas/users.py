from pydantic import BaseModel, EmailStr


class InitialAdminCreate(BaseModel):
    first_name: str | None
    last_name: str | None
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str
