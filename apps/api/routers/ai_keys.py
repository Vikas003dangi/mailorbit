from datetime import datetime, timezone
import json
import logging
from typing import List, Optional
import urllib.error
import urllib.request
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db, get_encryption_service
from packages.shared.crypto import EncryptionService
from packages.shared.schema import AIKey, User

logger = logging.getLogger("mailorbit.ai_keys")
router = APIRouter(prefix="/api/v1/ai-keys", tags=["AI Keys"])


class AIKeyCreate(BaseModel):
    provider: str = "gemini"
    api_key: str
    model: str = "gemini-2.5-flash"


class AIKeyOut(BaseModel):
    id: uuid.UUID
    provider: str
    model: str
    status: str
    has_key: bool = True
    masked_key: str
    last_tested_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class KeyTestResult(BaseModel):
    success: bool
    status: str
    detail: str


@router.post("", response_model=AIKeyOut, status_code=status.HTTP_201_CREATED)
def create_ai_key(
    payload: AIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """
    Saves a user's BYOK Gemini API key.
    The key is encrypted at rest using AES-256-GCM envelope encryption.
    Plaintext and ciphertext are NEVER returned in API responses.
    """
    ciphertext = crypto.encrypt(payload.api_key.strip())
    masked = crypto.mask_secret(payload.api_key.strip())

    key_record = AIKey(
        user_id=current_user.id,
        provider=payload.provider.lower(),
        api_key_ciphertext=ciphertext,
        model=payload.model,
        status="PENDING_TEST",
    )
    db.add(key_record)
    db.commit()
    db.refresh(key_record)

    return AIKeyOut(
        id=key_record.id,
        provider=key_record.provider,
        model=key_record.model,
        status=key_record.status,
        has_key=True,
        masked_key=masked,
        last_tested_at=key_record.last_tested_at,
        created_at=key_record.created_at,
    )


@router.get("", response_model=List[AIKeyOut])
def list_ai_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """Lists all configured AI provider keys for the user, with keys masked."""
    keys = db.query(AIKey).filter(AIKey.user_id == current_user.id).all()
    out = []
    for k in keys:
        try:
            plain = crypto.decrypt(k.api_key_ciphertext)
            masked = crypto.mask_secret(plain)
        except Exception:
            masked = "••••••••????"

        out.append(
            AIKeyOut(
                id=k.id,
                provider=k.provider,
                model=k.model,
                status=k.status,
                has_key=True,
                masked_key=masked,
                last_tested_at=k.last_tested_at,
                created_at=k.created_at,
            )
        )
    return out


@router.post("/{key_id}/test", response_model=KeyTestResult)
def test_ai_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    crypto: EncryptionService = Depends(get_encryption_service),
):
    """
    Tests a Gemini API key against Google's API.
    Decrypts the key strictly in memory for the HTTP request, never logs it.
    """
    key_record = db.query(AIKey).filter(
        AIKey.id == key_id,
        AIKey.user_id == current_user.id,
    ).first()

    if not key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI key not found")

    try:
        api_key = crypto.decrypt(key_record.api_key_ciphertext)
    except Exception as e:
        logger.error("Failed to decrypt AI key for key %s: %s", key_record.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored AI key",
        )

    now = datetime.now(timezone.utc)
    # Test key against Gemini models endpoint
    test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "MailOrbit-Key-Test/1.0"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode())
            models_count = len(data.get("models", []))

            key_record.status = "ACTIVE"
            key_record.last_tested_at = now
            db.commit()

            return KeyTestResult(
                success=True,
                status="ACTIVE",
                detail=f"Key verified successfully with Gemini API ({models_count} models available)",
            )
    except urllib.error.HTTPError as e:
        key_record.status = "INVALID"
        key_record.last_tested_at = now
        db.commit()
        return KeyTestResult(
            success=False,
            status="INVALID",
            detail=f"Gemini API rejected key: HTTP {e.code} ({e.reason})",
        )
    except Exception as e:
        key_record.status = "ERROR"
        key_record.last_tested_at = now
        db.commit()
        return KeyTestResult(
            success=False,
            status="ERROR",
            detail=f"Failed to connect to Gemini API: {str(e)}",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes an AI key and permanently wipes its encrypted ciphertext."""
    key_record = db.query(AIKey).filter(
        AIKey.id == key_id,
        AIKey.user_id == current_user.id,
    ).first()

    if not key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI key not found")

    db.delete(key_record)
    db.commit()
    return None
