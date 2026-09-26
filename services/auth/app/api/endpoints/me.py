from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.users import UserProfile

router = APIRouter()


@router.get("/me", response_model=UserProfile)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
