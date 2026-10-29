from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db
from apps.api.services.batch_generator import auto_generate_batches
from apps.api.services.schedule_cache import schedule_cache
from packages.shared.schema import Batch, Contact, User

router = APIRouter(prefix="/api/v1/batches", tags=["Batches & Scheduling"])


class BatchOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    purpose_id: Optional[uuid.UUID] = None
    name: str
    size: int
    position: int
    scheduled_time: Optional[str] = "10:00"
    scheduled_days: List[str]
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    size: Optional[int] = None
    scheduled_time: Optional[str] = None
    scheduled_days: Optional[List[str]] = None
    status: Optional[str] = None


class AutoGenerateBatchesRequest(BaseModel):
    purpose_id: Optional[uuid.UUID] = None
    batch_size: int = 30
    daily_send_time: str = "10:00"
    active_days: List[str] = ["mon", "tue", "wed", "thu", "fri"]


class AutoGenerateResponse(BaseModel):
    created_batches_count: int
    contacts_assigned_count: int
    batches: List[BatchOut]


@router.get("", response_model=List[BatchOut])
def list_batches(
    purpose_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists batches created by the authenticated user."""
    query = db.query(Batch).filter(Batch.user_id == current_user.id)
    if purpose_id:
        query = query.filter(Batch.purpose_id == purpose_id)
    if status_filter:
        query = query.filter(Batch.status == status_filter.upper())
    return query.order_by(Batch.position.asc()).all()


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.user_id == current_user.id,
    ).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


@router.patch("/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: uuid.UUID,
    payload: BatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Renames a batch, adjusts size, or modifies schedule parameters."""
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.user_id == current_user.id,
    ).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    if payload.name is not None:
        batch.name = payload.name.strip()
    if payload.size is not None:
        batch.size = max(1, payload.size)
    if payload.scheduled_time is not None:
        batch.scheduled_time = payload.scheduled_time.strip()
    if payload.scheduled_days is not None:
        batch.scheduled_days = payload.scheduled_days
    if payload.status is not None:
        batch.status = payload.status.upper()

    db.commit()
    db.refresh(batch)
    schedule_cache.refresh_from_db(db)
    return batch


@router.post("/auto-generate", response_model=AutoGenerateResponse)
def auto_generate(
    payload: AutoGenerateBatchesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Slices all unassigned pending contacts into daily batches of size N
    scheduled for time T on days D.
    """
    batches, assigned = auto_generate_batches(
        db=db,
        user_id=current_user.id,
        purpose_id=payload.purpose_id,
        batch_size=payload.batch_size,
        daily_send_time=payload.daily_send_time,
        active_days=payload.active_days,
    )
    schedule_cache.refresh_from_db(db)
    return AutoGenerateResponse(
        created_batches_count=len(batches),
        contacts_assigned_count=assigned,
        batches=batches,
    )


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a batch and unassigns contacts from it (contacts remain intact)."""
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.user_id == current_user.id,
    ).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    # Unlink contacts from this batch
    db.query(Contact).filter(Contact.batch_id == batch.id).update({"batch_id": None})
    db.delete(batch)
    db.commit()
    schedule_cache.refresh_from_db(db)
    return None


@router.post("/{batch_id}/dispatch", response_model=Dict[str, Any])
def dispatch_single_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dispatches a batch immediately through the send engine.
    Applies pre-send lead verification, auto-topup replacement on failure,
    and dispatches via the active sender relay.
    """
    batch = db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.user_id == current_user.id,
    ).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    from apps.worker.dispatcher import dispatch_batch

    result = dispatch_batch(session=db, batch_id=batch.id)
    schedule_cache.refresh_from_db(db)
    return result

