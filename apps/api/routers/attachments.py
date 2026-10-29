from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from apps.api.dependencies import get_current_user, get_db
from apps.api.services.rate_limiter import rate_limiter
from packages.shared.schema import User, Attachment, Purpose, purpose_attachments
from packages.shared.cloudinary import upload_attachment, delete_attachment, validate_attachment, MAX_FILE_SIZE_BYTES

router = APIRouter(prefix="/api/v1", tags=["Attachments & Document Library"])


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_url: str
    cloudinary_public_id: str
    size_bytes: int
    content_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurposeAttachmentLinkResponse(BaseModel):
    purpose_id: uuid.UUID
    attachment_id: uuid.UUID
    message: str


@router.post("/attachments/upload", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a resume, portfolio, or proposal document to Cloudinary authenticated storage.
    Enforces 5 MB size limit and accepted document/image formats.
    Rate limited to 10 requests per minute per IP.
    """
    rate_limiter.check(request, "upload", max_requests=10, window_seconds=60)
    contents = await file.read()
    filename = file.filename or "attachment.pdf"
    content_type = file.content_type or "application/pdf"

    try:
        validate_attachment(filename, content_type, len(contents))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    try:
        meta = upload_attachment(contents, filename, content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudinary upload failed: {str(exc)}",
        )

    attachment = Attachment(
        user_id=user.id,
        filename=meta["filename"],
        file_url=meta["file_url"],
        cloudinary_public_id=meta["cloudinary_public_id"],
        size_bytes=meta["size_bytes"],
        content_type=meta["content_type"],
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return attachment


@router.get("/attachments", response_model=List[AttachmentResponse])
def list_attachments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all document attachments uploaded by the authenticated user."""
    return (
        db.query(Attachment)
        .filter(Attachment.user_id == user.id)
        .order_by(Attachment.created_at.desc())
        .all()
    )


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
def get_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a single attachment."""
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.user_id == user.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return attachment


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an attachment from Cloudinary and the database."""
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.user_id == user.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    # Delete from Cloudinary
    delete_attachment(attachment.cloudinary_public_id, attachment.content_type)

    # Delete from DB (cascades purpose_attachments links)
    db.delete(attachment)
    db.commit()
    return None


@router.post("/purposes/{purpose_id}/attachments/{attachment_id}", response_model=PurposeAttachmentLinkResponse)
def link_attachment_to_purpose(
    purpose_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link a document attachment to a campaign purpose profile."""
    purpose = (
        db.query(Purpose)
        .filter(Purpose.id == purpose_id, Purpose.user_id == user.id)
        .first()
    )
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.user_id == user.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if attachment not in purpose.attachments:
        purpose.attachments.append(attachment)
        db.commit()

    return PurposeAttachmentLinkResponse(
        purpose_id=purpose.id,
        attachment_id=attachment.id,
        message="Attachment linked to purpose successfully",
    )


@router.delete("/purposes/{purpose_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_attachment_from_purpose(
    purpose_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink a document attachment from a campaign purpose profile."""
    purpose = (
        db.query(Purpose)
        .filter(Purpose.id == purpose_id, Purpose.user_id == user.id)
        .first()
    )
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.user_id == user.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if attachment in purpose.attachments:
        purpose.attachments.remove(attachment)
        db.commit()

    return None


@router.get("/purposes/{purpose_id}/attachments", response_model=List[AttachmentResponse])
def list_purpose_attachments(
    purpose_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all attachments currently linked to a campaign purpose."""
    purpose = (
        db.query(Purpose)
        .filter(Purpose.id == purpose_id, Purpose.user_id == user.id)
        .first()
    )
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")

    return purpose.attachments

