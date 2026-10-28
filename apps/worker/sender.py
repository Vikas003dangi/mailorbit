from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
import smtplib
from typing import Any, Dict, List, Optional
import uuid

from apps.api.config import settings

logger = logging.getLogger("mailorbit.sender")


class LocalMailpitSender:
    """
    SMTP client dispatching outbound emails to local Axllent Mailpit on port 1025.
    Guarantees zero outbound emails leave development environments.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.host = host or settings.FAKE_SMTP_HOST
        self.port = port or settings.FAKE_SMTP_PORT

    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Sends MIME formatted email to Mailpit SMTP server.
        """
        msg = MIMEMultipart("mixed")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["X-Mailer"] = "MailOrbit/0.1.0"
        message_id = f"<{uuid.uuid4()}@mailorbit.local>"
        msg["Message-ID"] = message_id

        # Text/HTML alternative body
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            alt_part.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt_part)

        # Attachments if provided
        if attachments:
            for att in attachments:
                filename = att.get("filename", "attachment.pdf")
                content = att.get("content", b"")
                content_type = att.get("content_type", "application/pdf")

                maintype, _, subtype = content_type.partition("/")
                part = MIMEBase(maintype or "application", subtype or "octet-stream")
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                msg.attach(part)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.send_message(msg)

            logger.info("Email delivered to Mailpit: %s -> %s (%s)", from_email, to_email, subject)
            return {
                "status": "SENT",
                "message_id": message_id,
                "recipient": to_email,
                "sender": from_email,
                "subject": subject,
            }
        except Exception as exc:
            logger.error("Failed to send email to Mailpit (%s:%s): %s", self.host, self.port, exc)
            raise RuntimeError(f"Mailpit delivery failed: {str(exc)}") from exc

