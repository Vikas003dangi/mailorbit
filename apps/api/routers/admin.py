from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.dependencies import get_db, require_superuser
from apps.api.diagnostics import run_egress_check
from packages.shared.models import EgressReport
from packages.shared.schema import AIKey, Attachment, Batch, Contact, Profile, Purpose, SenderRelay, User

router = APIRouter(prefix="/api/v1/admin", tags=["Superuser Admin"])


@router.get("/debug-ip")
def debug_client_ip(
    request: Request,
    admin_user: User = Depends(require_superuser),
) -> Dict[str, Any]:
    """Temporary admin-only debug view of detected IP."""
    from apps.api.services.rate_limiter import get_client_ip
    detected_ip = get_client_ip(request)
    return {
        "detected_client_ip": detected_ip,
        "trusted_proxy_count": settings.TRUSTED_PROXY_COUNT,
    }


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
    status_counts = {st: count for st, count in status_counts_raw}

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


@router.get("/users")
def list_all_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> List[Dict[str, Any]]:
    """Returns detailed user accounts for administrative control via 4 aggregated queries."""
    users = db.query(User).order_by(desc(User.created_at)).limit(50).all()
    if not users:
        return []

    user_ids = [u.id for u in users]

    contact_counts = dict(
        db.query(Contact.user_id, func.count(Contact.id))
        .filter(Contact.user_id.in_(user_ids))
        .group_by(Contact.user_id)
        .all()
    )

    batch_counts = dict(
        db.query(Batch.user_id, func.count(Batch.id))
        .filter(Batch.user_id.in_(user_ids))
        .group_by(Batch.user_id)
        .all()
    )

    relay_counts = dict(
        db.query(SenderRelay.user_id, func.count(SenderRelay.id))
        .filter(SenderRelay.user_id.in_(user_ids))
        .group_by(SenderRelay.user_id)
        .all()
    )

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "total_contacts": contact_counts.get(u.id, 0),
            "total_batches": batch_counts.get(u.id, 0),
            "total_relays": relay_counts.get(u.id, 0),
        }
        for u in users
    ]


@router.post("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> Dict[str, Any]:
    """Admin capability to activate or suspend any user account."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Prevent self-suspension
    if target_user.id == admin_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate own admin account")

    target_user.is_active = not target_user.is_active
    db.commit()
    db.refresh(target_user)

    return {
        "user_id": str(target_user.id),
        "email": target_user.email,
        "is_active": target_user.is_active,
        "message": f"User {'activated' if target_user.is_active else 'suspended'} successfully",
    }


@router.get("/batches")
def list_all_batches(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> List[Dict[str, Any]]:
    """Admin capability to monitor batches across the whole platform using 2 efficient queries."""
    batches = db.query(Batch).order_by(desc(Batch.created_at)).limit(30).all()
    if not batches:
        return []

    batch_ids = [b.id for b in batches]
    user_ids = list({b.user_id for b in batches})
    users_by_id = {u.id: u.email for u in db.query(User.id, User.email).filter(User.id.in_(user_ids)).all()}

    contact_counts = dict(
        db.query(Contact.batch_id, func.count(Contact.id))
        .filter(Contact.batch_id.in_(batch_ids))
        .group_by(Contact.batch_id)
        .all()
    )

    return [
        {
            "id": str(b.id),
            "owner_email": users_by_id.get(b.user_id, "unknown"),
            "name": b.name,
            "position": b.position,
            "status": b.status,
            "scheduled_time": b.scheduled_time,
            "scheduled_days": b.scheduled_days,
            "contact_count": contact_counts.get(b.id, 0),
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in batches
    ]


@router.post("/trigger-tick")
def admin_trigger_tick(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_superuser),
) -> Dict[str, Any]:
    """Admin capability to manually invoke Watchdog batch evaluator on demand."""
    try:
        from apps.api.main import queue, worker
        from apps.worker.scheduler import evaluate_all_due_batches

        sched_result = evaluate_all_due_batches(session=db, queue=queue)
        batches_queued = sched_result.get("batches_queued", 0)
        evaluated_users = sched_result.get("evaluated_users", 0)
        processed = worker.tick(batch_size=10)

        return {
            "status": "success",
            "message": f"Watchdog tick evaluated across {evaluated_users} users: {batches_queued} batch(es) queued, {processed} job(s) processed.",
            "batches_queued": batches_queued,
            "jobs_processed": processed,
            "executed_by": admin_user.email,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "executed_by": admin_user.email,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/egress-test", response_model=EgressReport)
def admin_run_egress_test(
    admin_user: User = Depends(require_superuser),
) -> EgressReport:
    """Admin capability to execute live egress network probes on demand."""
    return run_egress_check()
