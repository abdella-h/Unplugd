import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(payload: dict) -> str:

    payload_to_encode = payload.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    payload_to_encode.update({"exp": expire})

    return jwt.encode(payload_to_encode, SECRET_KEY, ALGORITHM)
