from datetime import date, datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db
from packages.shared.schema import Purpose, User

router = APIRouter(prefix="/api/v1/purposes", tags=["Outreach Purposes"])


class PurposeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_subject_template: Optional[str] = None
    default_body_template: Optional[str] = None
    daily_limit: Optional[int] = 30
    start_date: Optional[date] = None
    stop_date: Optional[date] = None
    skip_dates: Optional[List[str]] = None
    is_repeating: Optional[bool] = False
    cooldown_days: Optional[int] = 7


class PurposeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_subject_template: Optional[str] = None
    default_body_template: Optional[str] = None
    daily_limit: Optional[int] = None
    start_date: Optional[date] = None
    stop_date: Optional[date] = None
    skip_dates: Optional[List[str]] = None
    is_repeating: Optional[bool] = None
    cooldown_days: Optional[int] = None
    is_active: Optional[bool] = None


class PurposeOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    default_subject_template: Optional[str] = None
    default_body_template: Optional[str] = None
    daily_limit: int = 30
    start_date: Optional[date] = None
    stop_date: Optional[date] = None
    skip_dates: List[str] = []
    is_repeating: bool = False
    cooldown_days: int = 7
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=PurposeOut, status_code=status.HTTP_201_CREATED)
def create_purpose(
    payload: PurposeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new general outreach campaign purpose (Job Application, Referral, Pitch, etc.)."""
    purpose = Purpose(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description,
        default_subject_template=payload.default_subject_template,
        default_body_template=payload.default_body_template,
        daily_limit=payload.daily_limit or 30,
        start_date=payload.start_date,
        stop_date=payload.stop_date,
        skip_dates=payload.skip_dates or [],
        is_repeating=payload.is_repeating or False,
        cooldown_days=payload.cooldown_days or 7,
    )
    db.add(purpose)
    db.commit()
    db.refresh(purpose)
    return purpose


@router.get("", response_model=List[PurposeOut])
def list_purposes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all outreach purposes defined by the authenticated user."""
    return db.query(Purpose).filter(Purpose.user_id == current_user.id).order_by(Purpose.created_at.desc()).all()


@router.get("/{purpose_id}", response_model=PurposeOut)
def get_purpose(
    purpose_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purpose = db.query(Purpose).filter(
        Purpose.id == purpose_id,
        Purpose.user_id == current_user.id,
    ).first()
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")
    return purpose


@router.put("/{purpose_id}", response_model=PurposeOut)
def update_purpose(
    purpose_id: uuid.UUID,
    payload: PurposeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purpose = db.query(Purpose).filter(
        Purpose.id == purpose_id,
        Purpose.user_id == current_user.id,
    ).first()
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")

    if payload.name is not None:
        purpose.name = payload.name.strip()
    if payload.description is not None:
        purpose.description = payload.description
    if payload.default_subject_template is not None:
        purpose.default_subject_template = payload.default_subject_template
    if payload.default_body_template is not None:
        purpose.default_body_template = payload.default_body_template
    if payload.daily_limit is not None:
        purpose.daily_limit = payload.daily_limit
    if payload.start_date is not None:
        purpose.start_date = payload.start_date
    if payload.stop_date is not None:
        purpose.stop_date = payload.stop_date
    if payload.skip_dates is not None:
        purpose.skip_dates = payload.skip_dates
    if payload.is_repeating is not None:
        purpose.is_repeating = payload.is_repeating
    if payload.cooldown_days is not None:
        purpose.cooldown_days = payload.cooldown_days
    if payload.is_active is not None:
        purpose.is_active = payload.is_active

    db.commit()
    db.refresh(purpose)
    return purpose


@router.delete("/{purpose_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purpose(
    purpose_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purpose = db.query(Purpose).filter(
        Purpose.id == purpose_id,
        Purpose.user_id == current_user.id,
    ).first()
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")
    db.delete(purpose)
    db.commit()
    return None

