from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.users import User

router = APIRouter()


@router.get("/setup")
def setup(db: Session = Depends(get_db)):
    admin_exists = db.query(User).filter(User.role == "admin").first() is not None

    if not admin_exists:
        return {"admin_exists": False, "message": "no admin exists yet."}

    return {"admin_exists": True, "message": "admin already exists"}
