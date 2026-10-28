from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db
from packages.shared.schema import Profile, User

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


class ProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: Optional[str] = None
    phone: Optional[str] = None
    links: Dict[str, Any] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    links: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None


class JDMatchRequest(BaseModel):
    jd_text: str
    resume_text: Optional[str] = ""


class JDMatchResponse(BaseModel):
    match_score: int
    matched_skills: List[str]
    missing_skills: List[str]
    total_jd_skills_found: int
    pitch_angle: str


@router.get("", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves the full profile for the authenticated user."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates the user profile details."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    if payload.full_name is not None:
        profile.full_name = payload.full_name
    if payload.phone is not None:
        profile.phone = payload.phone
    if payload.links is not None:
        profile.links = payload.links
    if payload.skills is not None:
        profile.skills = payload.skills
    if payload.experience is not None:
        profile.experience = payload.experience
    if payload.summary is not None:
        profile.summary = payload.summary

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/match-jd", response_model=JDMatchResponse)
def match_jd(
    payload: JDMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Scans a job description against the user's profile skills and resume,
    identifying overlapping keywords, gaps, and match percentage.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    skills = profile.skills if profile and profile.skills else []

    from apps.api.services.keyword_matcher import match_profile_to_jd

    res = match_profile_to_jd(
        profile_skills=skills,
        jd_text=payload.jd_text,
        resume_text=payload.resume_text or (profile.summary if profile else ""),
    )
    return JDMatchResponse(**res)
