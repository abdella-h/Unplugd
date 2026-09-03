import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.models.refresh_tokens import RefreshToken
from app.models.users import User

router = APIRouter()


@router.post("/refresh", status_code=status.HTTP_201_CREATED)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = (
        db.query(RefreshToken).filter(RefreshToken.hashed_token == token_hash).first()
    )
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    now = datetime.now(timezone.utc)

    # normalize SQLite naive datetimes to UTC-aware before comparison
    expires_at = refresh_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if refresh_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if refresh_token.rotated_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.id == refresh_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if user.role not in ("admin", "operator"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    refresh_token.rotated_at = now

    new_access_token = create_access_token(
        payload={"sub": user.username, "role": user.role, "dc_id": user.datacenter_id}
    )

    new_refresh_token = create_refresh_token(db, user.id, expires_at=expires_at)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int((expires_at - now).total_seconds()),
        path="/",
    )

    return {"access_token": new_access_token, "token_type": "Bearer"}
