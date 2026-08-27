import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.refresh_tokens import RefreshToken

REFRESH_TOKEN_TTL_DAYS = 7
REFRESH_TOKEN_TTL_SECONDS = REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60

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


def create_refresh_token(db: Session, user_id: int, expires_at: datetime | None = None):
    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)

    refresh_token = RefreshToken(
        user_id=user_id,
        hashed_token=token_hash,
        expires_at=expires_at,
    )

    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)

    return raw_token
