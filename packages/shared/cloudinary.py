import io
import logging
from typing import Dict, Any, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.utils

from apps.api.config import settings

logger = logging.getLogger("mailorbit.cloudinary")

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}


def configure_cloudinary() -> bool:
    """Configures Cloudinary SDK if credentials are present in settings."""
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
        return False

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    return True


def validate_attachment(filename: str, content_type: Optional[str], size_bytes: int) -> None:
    """Validates file size and MIME type for attachment uploads."""
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size {size_bytes} exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES} bytes (5 MB)")

    if not content_type:
        content_type = "application/pdf"

    clean_content_type = content_type.lower().split(";")[0].strip()
    if clean_content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Unsupported file type '{content_type}'. Allowed: PDF, DOC, DOCX, TXT, PNG, JPEG")


def upload_attachment(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    """
    Uploads document to Cloudinary authenticated storage and returns metadata.
    """
    validate_attachment(filename, content_type, len(file_bytes))

    if not configure_cloudinary():
        # Fallback for offline dev testing if Cloudinary credentials are not configured in local environment
        logger.warning("Cloudinary credentials not configured; using offline simulated URL")
        return {
            "file_url": f"https://res.cloudinary.com/simulated/image/upload/v1/mailorbit/{filename}",
            "cloudinary_public_id": f"mailorbit/attachments/simulated_{filename}",
            "size_bytes": len(file_bytes),
            "filename": filename,
            "content_type": content_type,
        }

    # Upload to Cloudinary with resource_type auto/raw for documents
    clean_type = content_type.lower().split(";")[0].strip()
    resource_type = "image" if clean_type.startswith("image/") else "raw"

    upload_result = cloudinary.uploader.upload(
        file_bytes,
        resource_type=resource_type,
        folder="mailorbit/attachments",
        public_id=None,
        use_filename=True,
        unique_filename=True,
    )

    secure_url = upload_result.get("secure_url") or upload_result.get("url")
    public_id = upload_result.get("public_id")
    size = upload_result.get("bytes", len(file_bytes))

    return {
        "file_url": secure_url,
        "cloudinary_public_id": public_id,
        "size_bytes": size,
        "filename": filename,
        "content_type": content_type,
    }


def delete_attachment(public_id: str, content_type: Optional[str] = None) -> bool:
    """Deletes an asset from Cloudinary storage."""
    if not configure_cloudinary():
        return True

    clean_type = (content_type or "").lower().split(";")[0].strip()
    resource_type = "image" if clean_type.startswith("image/") else "raw"

    try:
        res = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return res.get("result") in ("ok", "not found")
    except Exception as exc:
        logger.error("Failed to delete Cloudinary asset %s: %s", public_id, exc)
        return False

