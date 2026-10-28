import logging
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.dependencies import get_db
from packages.shared.schema import Contact, DoNotContact
from packages.shared.unsubscribe import decode_unsubscribe_token

logger = logging.getLogger("mailorbit.unsubscribe")
router = APIRouter(prefix="/api/v1/unsubscribe", tags=["Opt-out & Deliverability"])


class UnsubscribeResponse(BaseModel):
    status: str = "ok"
    email: str
    message: str


@router.get("", response_class=HTMLResponse)
def handle_unsubscribe_get(
    token: str = Query(..., description="Signed unsubscribe token from email footer"),
    db: Session = Depends(get_db),
):
    """
    Public opt-out endpoint. Clicking the email link adds recipient to DoNotContact table,
    marks lead as UNSUBSCRIBED in the database, and returns a friendly HTML confirmation.
    """
    try:
        data = decode_unsubscribe_token(token, secret_key=settings.ENCRYPTION_MASTER_KEY)
    except Exception as exc:
        logger.warning("Invalid unsubscribe token: %s", exc)
        return HTMLResponse(
            content="<h3>Invalid or expired unsubscribe link.</h3>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user_id = uuid.UUID(data["user_id"])
    email = data["email"].lower().strip()
    contact_id = uuid.UUID(data["sub"]) if data.get("sub") else None

    # 1. Add to DoNotContact table if not already present
    existing_dnc = (
        db.query(DoNotContact)
        .filter(DoNotContact.user_id == user_id, DoNotContact.email == email)
        .first()
    )
    if not existing_dnc:
        dnc = DoNotContact(
            user_id=user_id,
            email=email,
            reason="Clicked email unsubscribe link",
        )
        db.add(dnc)

    # 2. Update contact status to UNSUBSCRIBED
    if contact_id:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            contact.status = "UNSUBSCRIBED"
            contact.status_reason = "Recipient clicked unsubscribe link"

    db.commit()

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Unsubscribed - MailOrbit</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 80vh; background: #0f172a; color: #f8fafc; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 12px; border: 1px solid #334155; text-align: center; max-width: 440px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h2 {{ color: #38bdf8; margin-top: 0; }}
        p {{ color: #94a3b8; line-height: 1.5; }}
        .badge {{ display: inline-block; background: #0284c7; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">Unsubscribed</div>
        <h2>You're all set</h2>
        <p><strong>{email}</strong> has been successfully removed from this outreach list. You will not receive any further emails.</p>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)


@router.post("", response_model=UnsubscribeResponse)
def handle_unsubscribe_post(
    token: str = Query(..., description="Signed unsubscribe token for RFC 8058 one-click opt-out"),
    db: Session = Depends(get_db),
):
    """
    RFC 8058 One-Click List-Unsubscribe POST endpoint called by email clients (Gmail, Apple Mail).
    """
    try:
        data = decode_unsubscribe_token(token, secret_key=settings.ENCRYPTION_MASTER_KEY)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid unsubscribe token",
        )

    user_id = uuid.UUID(data["user_id"])
    email = data["email"].lower().strip()
    contact_id = uuid.UUID(data["sub"]) if data.get("sub") else None

    existing_dnc = (
        db.query(DoNotContact)
        .filter(DoNotContact.user_id == user_id, DoNotContact.email == email)
        .first()
    )
    if not existing_dnc:
        dnc = DoNotContact(
            user_id=user_id,
            email=email,
            reason="One-click List-Unsubscribe POST",
        )
        db.add(dnc)

    if contact_id:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            contact.status = "UNSUBSCRIBED"
            contact.status_reason = "One-click List-Unsubscribe POST"

    db.commit()

    return UnsubscribeResponse(
        status="ok",
        email=email,
        message="Successfully unsubscribed via one-click protocol",
    )

