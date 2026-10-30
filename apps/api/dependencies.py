from typing import Generator
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.api.config import settings
from packages.shared.auth import decode_token
from packages.shared.crypto import EncryptionService, EnvKeyManager
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import User

# Initialize singletons for API engine and encryption
engine = create_db_engine(settings.DATABASE_URL)
SessionFactory = create_session_factory(engine)
key_manager = EnvKeyManager(settings.ENCRYPTION_MASTER_KEY)
encryption_service = EncryptionService(key_manager)

security_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a clean SQLAlchemy session per request."""
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_encryption_service() -> EncryptionService:
    """Dependency providing the master AES-256-GCM encryption service."""
    return encryption_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that authenticates the user via JWT Bearer access token.
    Raises HTTP 401 if token is missing, expired, or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token, settings.TICK_SECRET)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier",
            )
        import uuid
        try:
            user_uuid = uuid.UUID(str(user_id))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user identifier format",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Session Invalidation Guard: Validate token_version
    user_token_version = getattr(user, "token_version", 1) or 1
    token_version = payload.get("token_version", 1)
    if token_version != user_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_admin_emails() -> set[str]:
    """
    Parses administrative email addresses from settings.ADMIN_EMAILS.
    Tolerates both:
      1. JSON array format: '["vikassdangi@gmail.com", "vd19055@gmail.com"]'
      2. Comma-separated format: 'vikassdangi@gmail.com, vd19055@gmail.com'
    Normalizes to lower-case and strips quotes/whitespace.
    Explicitly guards against mailorbit.support@gmail.com (system sender is NEVER an admin).
    """
    raw = getattr(settings, "ADMIN_EMAILS", "") or ""
    admins: set[str] = set()
    if raw:
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    admins = {str(e).strip().strip("'\"").lower() for e in parsed if e and str(e).strip()}
            except Exception:
                pass
        if not admins:
            # Handles comma, semicolon, newline delimiters and surrounding quotes
            normalized = raw.replace(";", ",").replace("\n", ",").replace("\r", ",")
            admins = {e.strip().strip("'\"").lower() for e in normalized.split(",") if e.strip().strip("'\"")}
    else:
        admins = {"vikassdangi@gmail.com", "vd19055@gmail.com"}

    # Explicit safeguard: Platform system sender mailbox is strictly prohibited from admin elevation
    admins.discard("mailorbit.support@gmail.com")
    return admins


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the authenticated user has admin privileges via ADMIN_EMAILS and verified email."""
    admin_emails = get_admin_emails()
    if not current_user.email or current_user.email.lower() not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privilege required to access this resource",
        )
    if not getattr(current_user, "is_email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified email address required for administrative access",
        )
    return current_user

