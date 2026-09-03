import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.refresh_tokens import RefreshToken

router = APIRouter()


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    db_token = (
        db.query(RefreshToken).filter(RefreshToken.hashed_token == token_hash).first()
    )
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if db_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    db_token.revoked_at = datetime.now(timezone.utc)
    db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return {"message": "Logged out"}
