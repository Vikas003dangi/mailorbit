from datetime import datetime, timezone
import json
import logging
from typing import List, Optional
import urllib.error
import urllib.request
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db, get_encryption_service
from packages.shared.crypto import EncryptionService
from packages.shared.schema import SenderRelay, User

logger = logging.getLogger("mailorbit.senders")
router = APIRouter(prefix="/api/v1/senders", tags=["Senders & Relays"])


class SenderRelayCreate(BaseModel):
    email: EmailStr
    script_url: str
    auth_token: str
    daily_cap: int = 30


class SenderRelayOut(BaseModel):
    id: uuid.UUID
    email: str
    provider: str
    script_url: str
    daily_cap: int
    remaining_quota: int
    status: str
    has_token: bool = True
    masked_token: str
    last_tested_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RelayTestResult(BaseModel):
    success: bool
    status: str
    remaining_quota: int
    detail: str


@router.post("", response_model=SenderRelayOut, status_code=status.HTTP_201_CREATED)
def create_sender_relay(
    payload: SenderRelayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """
    Connects a new Google Apps Script email relay.
    The secret auth token is encrypted at rest using AES-256-GCM.
    NEVER logs or returns the token in plain form or ciphertext.
    """
    ciphertext = crypto.encrypt(payload.auth_token)
    masked = crypto.mask_secret(payload.auth_token)

    relay = SenderRelay(
        user_id=current_user.id,
        email=payload.email.lower(),
        provider="google_apps_script",
        script_url=payload.script_url.strip(),
        auth_token_ciphertext=ciphertext,
        daily_cap=payload.daily_cap,
        remaining_quota=0,
        status="PENDING_TEST",
    )
    db.add(relay)
    db.commit()
    db.refresh(relay)

    return SenderRelayOut(
        id=relay.id,
        email=relay.email,
        provider=relay.provider,
        script_url=relay.script_url,
        daily_cap=relay.daily_cap,
        remaining_quota=relay.remaining_quota,
        status=relay.status,
        has_token=True,
        masked_token=masked,
        last_tested_at=relay.last_tested_at,
        created_at=relay.created_at,
    )


@router.get("", response_model=List[SenderRelayOut])
def list_sender_relays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """Lists all sender relays for the authenticated user, with masked tokens."""
    relays = db.query(SenderRelay).filter(SenderRelay.user_id == current_user.id).all()
    out = []
    for r in relays:
        # Decrypt only to mask the suffix, never expose full token or ciphertext
        try:
            plain = crypto.decrypt(r.auth_token_ciphertext)
            masked = crypto.mask_secret(plain)
        except Exception:
            masked = "••••••••????"

        out.append(
            SenderRelayOut(
                id=r.id,
                email=r.email,
                provider=r.provider,
                script_url=r.script_url,
                daily_cap=r.daily_cap,
                remaining_quota=r.remaining_quota,
                status=r.status,
                has_token=True,
                masked_token=masked,
                last_tested_at=r.last_tested_at,
                created_at=r.created_at,
            )
        )
    return out


@router.post("/{relay_id}/test", response_model=RelayTestResult)
def test_sender_relay(
    relay_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """
    Tests connectivity to the Google Apps Script Web App relay.
    Decrypts the secret token strictly in memory, executes the request,
    and updates quota/status without logging the secret.
    """
    relay = db.query(SenderRelay).filter(
        SenderRelay.id == relay_id,
        SenderRelay.user_id == current_user.id,
    ).first()

    if not relay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender relay not found")

    try:
        token = crypto.decrypt(relay.auth_token_ciphertext)
    except Exception as e:
        logger.error("Failed to decrypt relay token for relay %s: %s", relay.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored relay credentials",
        )

    # Perform GET request to verify script is deployed and check quota
    now = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(
            relay.script_url,
            headers={"User-Agent": "MailOrbit-Relay-Test/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode())
            quota = data.get("remaining_quota", 100)

            relay.remaining_quota = quota
            relay.status = "ACTIVE" if quota > 0 else "QUOTA_EXCEEDED"
            relay.last_tested_at = now
            db.commit()

            return RelayTestResult(
                success=True,
                status=relay.status,
                remaining_quota=quota,
                detail=f"Relay verified successfully. Remaining quota: {quota}",
            )
    except urllib.error.HTTPError as e:
        relay.status = "ERROR"
        relay.last_tested_at = now
        db.commit()
        return RelayTestResult(
            success=False,
            status="ERROR",
            remaining_quota=0,
            detail=f"Relay returned HTTP {e.code} ({e.reason})",
        )
    except Exception as e:
        relay.status = "ERROR"
        relay.last_tested_at = now
        db.commit()
        return RelayTestResult(
            success=False,
            status="ERROR",
            remaining_quota=0,
            detail=f"Relay connection failed: {str(e)}",
        )


@router.delete("/{relay_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sender_relay(
    relay_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently deletes a sender relay and deletes the encrypted ciphertext."""
    relay = db.query(SenderRelay).filter(
        SenderRelay.id == relay_id,
        SenderRelay.user_id == current_user.id,
    ).first()

    if not relay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender relay not found")

    db.delete(relay)
    db.commit()
    return None
