from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db
from apps.api.services.batch_generator import auto_generate_batches
from apps.api.services.contact_importer import (
    ImportResult,
    parse_csv_content,
    process_contact_import,
)
from packages.shared.schema import Contact, User

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts & Leads"])


class ContactItemInput(BaseModel):
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    custom_pitch: Optional[Dict[str, Any]] = None


class BatchImportRequest(BaseModel):
    purpose_id: Optional[uuid.UUID] = None
    contacts: List[ContactItemInput]
    auto_batch: bool = True
    batch_size: int = 30
    daily_send_time: str = "10:00"
    active_days: List[str] = ["mon", "tue", "wed", "thu", "fri"]


class ContactOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    purpose_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    status: str
    status_reason: Optional[str] = None
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None


class ImportResponse(BaseModel):
    summary: ImportResult
    created_batches_count: int = 0
    assigned_to_batches_count: int = 0


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
def import_contacts_json(
    payload: BatchImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Imports bulk contacts from JSON. Performs email validation, deduplication,
    and optional auto-batching.
    """
    raw_dicts = [c.model_dump() for c in payload.contacts]
    summary, imported_contacts = process_contact_import(
        db=db,
        user_id=current_user.id,
        raw_rows=raw_dicts,
        purpose_id=payload.purpose_id,
    )

    created_batches_count = 0
    assigned_count = 0
    if payload.auto_batch and imported_contacts:
        imported_ids = [c.id for c in imported_contacts]
        batches, assigned = auto_generate_batches(
            db=db,
            user_id=current_user.id,
            purpose_id=payload.purpose_id,
            batch_size=payload.batch_size,
            daily_send_time=payload.daily_send_time,
            active_days=payload.active_days,
            contact_ids=imported_ids,
        )
        created_batches_count = len(batches)
        assigned_count = assigned

    return ImportResponse(
        summary=summary,
        created_batches_count=created_batches_count,
        assigned_to_batches_count=assigned_count,
    )


@router.post("/import-csv", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
async def import_contacts_csv(
    file: UploadFile = File(...),
    purpose_id: Optional[uuid.UUID] = Form(None),
    auto_batch: bool = Form(True),
    batch_size: int = Form(30),
    daily_send_time: str = Form("10:00"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Imports contacts from an uploaded CSV file with automatic column header mapping."""
    content_bytes = await file.read()
    try:
        csv_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        csv_text = content_bytes.decode("latin-1")

    raw_rows = parse_csv_content(csv_text)
    summary, imported_contacts = process_contact_import(
        db=db,
        user_id=current_user.id,
        raw_rows=raw_rows,
        purpose_id=purpose_id,
    )

    created_batches_count = 0
    assigned_count = 0
    if auto_batch and imported_contacts:
        imported_ids = [c.id for c in imported_contacts]
        batches, assigned = auto_generate_batches(
            db=db,
            user_id=current_user.id,
            purpose_id=purpose_id,
            batch_size=batch_size,
            daily_send_time=daily_send_time,
            contact_ids=imported_ids,
        )
        created_batches_count = len(batches)
        assigned_count = assigned

    return ImportResponse(
        summary=summary,
        created_batches_count=created_batches_count,
        assigned_to_batches_count=assigned_count,
    )


@router.get("", response_model=List[ContactOut])
def list_contacts(
    purpose_id: Optional[uuid.UUID] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists contacts with pagination and status/batch filtering."""
    query = db.query(Contact).filter(Contact.user_id == current_user.id)
    if purpose_id:
        query = query.filter(Contact.purpose_id == purpose_id)
    if batch_id:
        query = query.filter(Contact.batch_id == batch_id)
    if status_filter:
        query = query.filter(Contact.status == status_filter.upper())

    return query.order_by(Contact.created_at.asc()).offset(offset).limit(limit).all()


@router.get("/inactive", response_model=List[ContactOut])
def list_inactive_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dedicated endpoint returning all inactive, bounced, and invalid domain leads
    along with their specific failure reasons.
    """
    inactive_statuses = ["INVALID_DOMAIN", "BOUNCED", "INACTIVE", "UNSUBSCRIBED"]
    return (
        db.query(Contact)
        .filter(
            Contact.user_id == current_user.id,
            Contact.status.in_(inactive_statuses),
        )
        .order_by(Contact.updated_at.desc())
        .all()
    )


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id,
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if payload.name is not None:
        contact.name = payload.name.strip()
    if payload.company is not None:
        contact.company = payload.company.strip()
    if payload.role is not None:
        contact.role = payload.role.strip()
    if payload.batch_id is not None:
        contact.batch_id = payload.batch_id
    if payload.status is not None:
        contact.status = payload.status.upper()
    if payload.status_reason is not None:
        contact.status_reason = payload.status_reason

    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/reactivate", response_model=ContactOut)
def reactivate_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reactivates an inactive or bounced contact back to PENDING status."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id,
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.status = "PENDING"
    contact.status_reason = None
    contact.error = None
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.user_id == current_user.id,
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    db.delete(contact)
    db.commit()
    return None

