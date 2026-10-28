from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
import jwt

UNSUBSCRIBE_TOKEN_ALGORITHM = "HS256"


def generate_unsubscribe_token(
    user_id: uuid.UUID,
    contact_id: uuid.UUID,
    email: str,
    secret_key: str,
) -> str:
    """Creates a signed, non-expiring JWT token for one-click email unsubscribe."""
    payload = {
        "sub": str(contact_id),
        "user_id": str(user_id),
        "email": email.lower().strip(),
        "action": "unsubscribe",
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret_key, algorithm=UNSUBSCRIBE_TOKEN_ALGORITHM)


def decode_unsubscribe_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Validates and decodes an unsubscribe token, extracting contact and user info."""
    return jwt.decode(token, secret_key, algorithms=[UNSUBSCRIBE_TOKEN_ALGORITHM])


def generate_unsubscribe_headers(unsubscribe_url: str, mailto_email: str = "unsubscribe@mailorbit.local") -> Dict[str, str]:
    """
    Returns RFC 2369 and RFC 8058 compliant email headers for one-click unsubscribe.
    Protects sender deliverability and complies with Google & Yahoo 2024+ sender guidelines.
    """
    return {
        "List-Unsubscribe": f"<{unsubscribe_url}>, <mailto:{mailto_email}?subject=unsubscribe>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def append_unsubscribe_footer(body_text: str, unsubscribe_url: str) -> str:
    """Appends a clear, frictionless unsubscribe footer to the email body."""
    footer = (
        f"\n\n---\n"
        f"If you'd prefer not to hear from me, click here to opt out: {unsubscribe_url}"
    )
    return body_text + footer

