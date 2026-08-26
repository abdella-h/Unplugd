from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, REFRESH_TOKEN_TTL_SECONDS
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
