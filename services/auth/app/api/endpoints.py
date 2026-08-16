from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.models.users import User
from app.schemas.users import InitialAdminCreate

router = APIRouter()


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup(admin_in: InitialAdminCreate, db: Session = Depends(get_db)):
    admin_exists = db.query(User).filter(User.role == "admin").first() is not None

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
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created"}
