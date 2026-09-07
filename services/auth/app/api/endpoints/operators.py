import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import hash_password
from app.models.invites import InviteToken
from app.models.users import User
from app.schemas.operators import OperatorAccept, OperatorInvite

router = APIRouter()

INVITE_TTL_HOURS = 48


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/register/operator/invite", status_code=status.HTTP_201_CREATED)
def invite_operator(
    invite_in: OperatorInvite,
    db: Session = Depends(get_db),
    caller: User = Depends(get_current_user),
):
    if caller.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can invite operators",
        )

    if caller.datacenter_id is not None and invite_in.datacenter_id != caller.datacenter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Per-datacenter admins can only invite to their own datacenter",
        )

    existing = db.query(User).filter(User.email == invite_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already exists",
        )

    # Placeholder username + unusable password until accept.
    # Username is operator-chosen at accept; we need a unique NOT NULL value now.
    placeholder_username = f"pending-{secrets.token_hex(8)}"
    while db.query(User).filter(User.username == placeholder_username).first():
        placeholder_username = f"pending-{secrets.token_hex(8)}"
    placeholder = hash_password(secrets.token_urlsafe(32))
    new_user = User(
        first_name=None,
        last_name=None,
        username=placeholder_username,
        email=invite_in.email,
        hashed_password=placeholder,
        role="operator",
        datacenter_id=invite_in.datacenter_id,
        is_active=False,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already exists",
        )
    db.refresh(new_user)

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = _now() + timedelta(hours=INVITE_TTL_HOURS)

    invite = InviteToken(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "user_id": new_user.id,
        "invite_token": raw_token,
        "invite_link": f"/register/operator/accept?token={raw_token}",
        "expires_at": expires_at.isoformat(),
    }


@router.post("/register/operator/accept", status_code=status.HTTP_200_OK)
def accept_operator_invite(accept_in: OperatorAccept, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(accept_in.token.encode()).hexdigest()

    invite = (
        db.query(InviteToken).filter(InviteToken.token_hash == token_hash).first()
    )
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )

    if invite.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite already used",
        )

    if _as_aware(invite.expires_at) < _now():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )

    user = db.query(User).filter(User.id == invite.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )

    username_taken = (
        db.query(User).filter(User.username == accept_in.username).first()
    )
    if username_taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists",
        )

    user.username = accept_in.username
    user.first_name = accept_in.first_name
    user.last_name = accept_in.last_name
    user.hashed_password = hash_password(accept_in.password)
    user.is_active = True
    invite.used_at = _now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists",
        )

    return {"message": "Operator activated"}
