from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.dependencies import get_current_user, get_db
from packages.shared.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from packages.shared.schema import Profile, User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    timezone: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    timezone: str = Field(default="UTC", description="User preferred time zone")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Registers a new user workspace, initializes an empty profile, and returns auth tokens."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    pwd_hash = hash_password(payload.password)
    user = User(
        email=payload.email.lower(),
        password_hash=pwd_hash,
        timezone=payload.timezone,
    )
    db.add(user)
    db.flush()

    # Create associated profile
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    refresh_token = create_refresh_token(str(user.id), settings.TICK_SECRET)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues new access and refresh tokens."""
    user = db.query(User).filter(User.email == payload.email.lower(), User.is_active == True).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    refresh_token = create_refresh_token(str(user.id), settings.TICK_SECRET)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchanges a valid refresh token for a fresh access token."""
    try:
        decoded = decode_token(payload.refresh_token, settings.TICK_SECRET)
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = decoded.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token(str(user.id), user.email, settings.TICK_SECRET)
    new_refresh = create_refresh_token(str(user.id), settings.TICK_SECRET)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=user,
    )


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return current_user
