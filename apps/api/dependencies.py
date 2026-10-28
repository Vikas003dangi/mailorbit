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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


SUPERUSER_EMAILS = {"vikassdangi@gmail.com", "vd19055@gmail.com"}

def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the authenticated user has superuser privileges."""
    if current_user.email.lower() not in SUPERUSER_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privilege required to access this resource",
        )
    return current_user

