import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import ALGORITHM, SECRET_KEY, VALID_ROLES

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    username: str | None = payload.get("sub")
    role: str | None = payload.get("role")
    dc_id = payload.get("dc_id")

    if not username or not role or role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    return {"username": username, "role": role, "dc_id": dc_id}


def require_global_admin(token_data: dict = Depends(get_current_user)):
    if token_data["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    if token_data["dc_id"] is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin access required",
        )
    return token_data


def require_admin(token_data: dict = Depends(get_current_user)):
    if token_data["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data


def require_scoped_user(token_data: dict = Depends(get_current_user)):
    """Any authenticated user; operators must be datacenter-scoped."""
    if token_data["role"] == "operator" and token_data["dc_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator must be assigned to a datacenter",
        )
    return token_data


def ensure_device_scope(admin: dict, datacenter_id: int):
    if admin["dc_id"] is not None and admin["dc_id"] != datacenter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device outside your datacenter scope",
        )
