from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    REFRESH_TOKEN_TTL_SECONDS,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.users import User
from app.schemas.users import UserLogin

router = APIRouter()


@router.post("/login", status_code=status.HTTP_200_OK)
def user_login(
    response: Response, login_cred: UserLogin, db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.username == login_cred.username, User.is_active == True)
        .first()
    )
    if not user or not verify_password(login_cred.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    payload = {"sub": user.username, "role": user.role}

    access_token = create_access_token(payload=payload)

    refresh_token = create_refresh_token(db, user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        path="/",
    )

    return {"access_token": access_token, "token_type": "Bearer"}
