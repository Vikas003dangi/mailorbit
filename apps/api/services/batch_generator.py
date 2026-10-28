import math
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from packages.shared.schema import Batch, Contact


def auto_generate_batches(
    db: Session,
    user_id: uuid.UUID,
    purpose_id: Optional[uuid.UUID] = None,
    batch_size: int = 30,
    daily_send_time: str = "10:00",
    active_days: Optional[List[str]] = None,
    contact_ids: Optional[List[uuid.UUID]] = None,
) -> Tuple[List[Batch], int]:
    """
    Auto-slices unassigned pending contacts into named daily batches of `batch_size`.
    Implements: 'N mails per day, at time T, on days D' with zero manual steps.
    """
    days = active_days or ["mon", "tue", "wed", "thu", "fri"]
    safe_size = max(1, min(batch_size, 100))

    # Query target contacts
    query = db.query(Contact).filter(
        Contact.user_id == user_id,
        Contact.status == "PENDING",
    )
    if contact_ids:
        query = query.filter(Contact.id.in_(contact_ids))
    else:
        query = query.filter(Contact.batch_id == None)
        if purpose_id:
            query = query.filter(Contact.purpose_id == purpose_id)

    # Order contacts deterministically by creation time
    contacts = query.order_by(Contact.created_at.asc()).all()
    if not contacts:
        return [], 0

    # Determine next batch sequence number
    existing_batches_count = (
        db.query(Batch)
        .filter(Batch.user_id == user_id)
        .count()
    )

    created_batches: List[Batch] = []
    total_contacts_assigned = 0

    # Slice into chunks of batch_size
    chunks = [contacts[i : i + safe_size] for i in range(0, len(contacts), safe_size)]

    for idx, chunk in enumerate(chunks, start=existing_batches_count + 1):
        batch = Batch(
            user_id=user_id,
            purpose_id=purpose_id,
            name=f"Batch {idx}",
            size=len(chunk),
            position=idx,
            scheduled_time=daily_send_time,
            scheduled_days=days,
            status="PENDING",
        )
        db.add(batch)
        db.flush()

        for c in chunk:
            c.batch_id = batch.id
            total_contacts_assigned += 1

        created_batches.append(batch)

    db.commit()
    for b in created_batches:
        db.refresh(b)

    return created_batches, total_contacts_assigned
