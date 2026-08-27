import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    REFRESH_TOKEN_TTL_SECONDS,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.refresh_tokens import RefreshToken
from app.models.users import User
from app.schemas.users import InitialAdminCreate, UserLogin

router = APIRouter()


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    admin_exists = (
        db.query(User).filter(User.role == "admin", User.is_active == True).first()
        is not None
    )

    return {"needs_setup": not admin_exists}


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup(admin_in: InitialAdminCreate, db: Session = Depends(get_db)):
    admin_exists = (
        db.query(User).filter(User.role == "admin", User.is_active == True).first()
        is not None
    )

    if admin_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="admin already exists",
        )

    new_user = User(
        first_name=admin_in.first_name,
        last_name=admin_in.last_name,
        username=admin_in.username,
        email=admin_in.email,
        hashed_password=hash_password(admin_in.password),
        role="admin",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created"}


@router.post("/login", status_code=status.HTTP_200_OK)
def user_login(response: Response, login_cred: UserLogin, db: Session = Depends(get_db)):
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


@router.post("/refresh", status_code=status.HTTP_201_CREATED)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = db.query(RefreshToken).filter(RefreshToken.hashed_token == token_hash).first()
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

    # the bound user must still be active with a valid role (closure check)
    user = db.query(User).filter(User.id == refresh_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if user.role not in ("admin", "operator"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # consume the presented token (rotation per ADR-0004 §2)
    refresh_token.rotated_at = now

    # issue a fresh access token with scoping claims (ADR-0003 §1)
    new_access_token = create_access_token(
        payload={"sub": user.username, "role": user.role, "dc_id": user.datacenter_id}
    )

    # issue a new refresh token, inheriting the original 7-day deadline (ADR-0004 §4)
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

