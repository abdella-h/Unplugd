import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ALGORITHM, SECRET_KEY
from app.models.users import User

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or user.role not in ("admin", "operator"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user

    

    
        