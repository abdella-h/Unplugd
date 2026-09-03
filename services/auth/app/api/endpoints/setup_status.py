from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.users import User

router = APIRouter()


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    admin_exists = (
        db.query(User).filter(User.role == "admin", User.is_active == True).first()
        is not None
    )

    return {"needs_setup": not admin_exists}
