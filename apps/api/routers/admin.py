from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db, require_superuser
from packages.shared.schema import AIKey, Attachment, Batch, Contact, Profile, SenderRelay, User

router = APIRouter(prefix="/api/v1/admin", tags=["Superuser Admin"])


@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> Dict[str, Any]:
    """Returns platform-wide statistics for superusers."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_batches = db.query(func.count(Batch.id)).scalar() or 0
    total_contacts = db.query(func.count(Contact.id)).scalar() or 0
    total_relays = db.query(func.count(SenderRelay.id)).scalar() or 0
    total_ai_keys = db.query(func.count(AIKey.id)).scalar() or 0
    total_attachments = db.query(func.count(Attachment.id)).scalar() or 0

    # Status breakdown
    status_counts_raw = (
        db.query(Contact.status, func.count(Contact.id))
        .group_by(Contact.status)
        .all()
    )
    status_counts = {status: count for status, count in status_counts_raw}

    # Batch status breakdown
    batch_status_raw = (
        db.query(Batch.status, func.count(Batch.id))
        .group_by(Batch.status)
        .all()
    )
    batch_statuses = {b_status: count for b_status, count in batch_status_raw}

    return {
        "authenticated_as": admin_user.email,
        "is_superuser": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "users": total_users,
            "batches": total_batches,
            "contacts": total_contacts,
            "sender_relays": total_relays,
            "ai_keys": total_ai_keys,
            "attachments": total_attachments,
        },
        "contacts_by_status": status_counts,
        "batches_by_status": batch_statuses,
    }


@router.get("/system")
def get_system_health(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> Dict[str, Any]:
    """Returns underlying infrastructure telemetry for superusers."""
    # Test DB roundtrip
    db_ok = False
    try:
        db.execute(func.now()).scalar()
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": {
            "provider": "Neon Serverless PostgreSQL 16 (Ohio)",
            "connected": db_ok,
        },
        "host": {
            "platform": "Render Cloud Container",
            "region": "Oregon / US-West",
        },
        "egress": {
            "protocol": "Google Apps Script HTTPS Relay (443)",
            "circuit_breaker": "10% Batch Safety Pause active",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
