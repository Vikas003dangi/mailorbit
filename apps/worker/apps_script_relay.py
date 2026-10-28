import logging
from typing import Any, Dict, List, Optional
import uuid
import httpx

logger = logging.getLogger("mailorbit.apps_script_relay")


class RelayError(Exception):
    """Base exception for Google Apps Script relay failures."""
    pass


class QuotaExceededError(RelayError):
    """Raised when Gmail daily quota has been exhausted."""
    pass


class RelayAuthError(RelayError):
    """Raised when relay secret token is invalid or unauthorized."""
    pass


class AppsScriptRelayClient:
    """
    HTTP client for dispatching outbound emails via Google Apps Script Web App over HTTPS:443.
    Bypasses cloud provider port 587 blocks and sends directly from user's Gmail account.
    """

    def __init__(self, script_url: str, auth_token: str, timeout: float = 30.0):
        self.script_url = script_url
        self.auth_token = auth_token
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """
        Pings relay Web App GET endpoint to verify reachability and inspect remaining daily quota.
        """
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                res = client.get(self.script_url)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "status": "ok",
                        "remaining_quota": data.get("remaining_quota"),
                        "service": data.get("service"),
                    }
                raise RelayError(f"Health check failed with HTTP {res.status_code}: {res.text}")
        except Exception as exc:
            logger.error("Relay health check failed: %s", exc)
            raise RelayError(f"Could not connect to Apps Script relay: {str(exc)}") from exc

    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches an email through Google Apps Script Web App.
        Follows 302 redirects automatically (required for script.googleusercontent.com).
        """
        payload = {
            "token": self.auth_token,
            "to": to_email,
            "subject": subject,
            "body": body_text,
            "html_body": body_html or body_text,
            "idempotency_key": idempotency_key or str(uuid.uuid4()),
        }

        if attachments:
            payload["attachments"] = attachments

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                res = client.post(self.script_url, json=payload)

            status_code = res.status_code
            try:
                data = res.json()
            except Exception:
                data = {"message": res.text}

            if status_code == 200 and data.get("success"):
                logger.info(
                    "Email dispatched via Apps Script relay to %s (Remaining Quota: %s)",
                    to_email,
                    data.get("remaining_quota"),
                )
                return {
                    "status": "SENT",
                    "recipient": to_email,
                    "sender": from_email,
                    "subject": subject,
                    "remaining_quota": data.get("remaining_quota"),
                    "relay_message": data.get("message"),
                }

            if status_code == 429 or data.get("error") == "QUOTA_EXCEEDED":
                raise QuotaExceededError(data.get("message") or "Gmail daily sending quota exceeded")

            if status_code == 401 or data.get("error") == "UNAUTHORIZED":
                raise RelayAuthError(data.get("message") or "Invalid relay authentication token")

            error_msg = data.get("message") or f"Relay returned HTTP {status_code}"
            raise RelayError(error_msg)

        except (QuotaExceededError, RelayAuthError):
            raise
        except Exception as exc:
            logger.error("Apps Script relay error for %s: %s", to_email, exc)
            raise RelayError(f"Apps Script relay delivery failed: {str(exc)}") from exc

