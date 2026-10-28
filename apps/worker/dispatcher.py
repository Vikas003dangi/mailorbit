from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from apps.worker.pacer import Pacer
from apps.worker.sender import LocalMailpitSender
from packages.shared.schema import Batch, Contact, Purpose

logger = logging.getLogger("mailorbit.dispatcher")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def verify_email_domain(email: str) -> Tuple[bool, Optional[str]]:
    """
    Pre-send email verification check:
    1. Validates syntactic email format.
    2. Validates domain syntax and rejects invalid/prohibited TLDs.
    """
    if not email or not EMAIL_REGEX.match(email):
        return False, "Invalid email address format"

    _, _, domain = email.partition("@")
    domain = domain.lower().strip()

    # Reject placeholder/test invalid domains
    if domain in ("nodomain.com", "invalid_no_at_sign.com", "example.invalid", "localhost"):
        return False, f"Prohibited or unreachable domain: {domain}"

    if "." not in domain or domain.endswith("."):
        return False, f"Domain missing valid top-level domain: {domain}"

    return True, None


def render_template(template: Optional[str], contact: Contact, default: str) -> str:
    """Renders placeholders in email subject and body."""
    raw = template or default
    return (
        raw.replace("{name}", contact.name or "there")
        .replace("{company}", contact.company or "your team")
        .replace("{role}", contact.role or "Hiring Team")
    )


def dispatch_batch(
    session: Session,
    batch_id: uuid.UUID,
    sender: Optional[LocalMailpitSender] = None,
    pacer: Optional[Pacer] = None,
    from_email: str = "outreach@mailorbit.local",
) -> Dict[str, Any]:
    """
    Executes an outreach batch:
    - Pre-send verifies each lead.
    - If verification fails: immediately marks lead INACTIVE and auto-tops up the batch
      from pending unassigned contacts for that purpose.
    - Paces dispatches with randomized human-like delay.
    - Dispatches to Mailpit SMTP.
    - Marks contacts as SENT and updates batch progress.
    """
    batch = session.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"status": "ERROR", "message": f"Batch {batch_id} not found"}

    sender = sender or LocalMailpitSender()
    pacer = pacer or Pacer(min_seconds=0.0, max_seconds=0.0)  # default 0 delay unless specified

    purpose = None
    if batch.purpose_id:
        purpose = session.query(Purpose).filter(Purpose.id == batch.purpose_id).first()

    subject_tpl = purpose.default_subject_template if purpose else "Quick question regarding {company}"
    body_tpl = purpose.default_body_template if purpose else "Hi {name},\n\nHope this finds you well at {company}."

    # Fetch contacts assigned to this batch that are ready to send
    contacts = (
        session.query(Contact)
        .filter(Contact.batch_id == batch.id, Contact.status.in_(["PENDING", "QUEUED"]))
        .order_by(Contact.created_at.asc())
        .all()
    )

    sent_count = 0
    replaced_count = 0
    failed_count = 0

    queue: List[Contact] = list(contacts)

    while queue:
        contact = queue.pop(0)

        # 1. Pre-send verification
        is_valid, fail_reason = verify_email_domain(contact.email)

        if not is_valid:
            failed_count += 1
            contact.status = "INACTIVE"
            contact.status_reason = f"Pre-send verification failed: {fail_reason}"
            session.commit()

            # 2. Immediate auto-topup replacement
            replacement = (
                session.query(Contact)
                .filter(
                    Contact.user_id == batch.user_id,
                    Contact.purpose_id == batch.purpose_id,
                    Contact.batch_id == None,
                    Contact.status == "PENDING",
                )
                .order_by(Contact.created_at.asc())
                .first()
            )

            if replacement:
                replacement.batch_id = batch.id
                session.commit()
                queue.append(replacement)
                replaced_count += 1
                logger.info(
                    "Auto-replaced inactive contact %s with %s in batch %s",
                    contact.email,
                    replacement.email,
                    batch.name,
                )
            continue

        # 3. Pacing delay
        pacer.pace()

        # 4. Render email content
        subject = render_template(subject_tpl, contact, f"Introduction for {contact.name}")
        body_text = render_template(body_tpl, contact, f"Hello {contact.name},\n\nConnecting from MailOrbit.")

        # 5. Dispatch email
        try:
            sender.send_email(
                from_email=from_email,
                to_email=contact.email,
                subject=subject,
                body_text=body_text,
            )
            contact.status = "SENT"
            contact.sent_at = utc_now()
            contact.error = None
            sent_count += 1
        except Exception as exc:
            contact.status = "FAILED"
            contact.error = str(exc)
            logger.error("Failed sending email to %s: %s", contact.email, exc)

        session.commit()

    # If all contacts in the batch have been processed, complete the batch
    remaining_pending = (
        session.query(Contact)
        .filter(Contact.batch_id == batch.id, Contact.status.in_(["PENDING", "QUEUED"]))
        .count()
    )
    if remaining_pending == 0:
        batch.status = "COMPLETED"
        batch.updated_at = utc_now()
        session.commit()

    return {
        "batch_id": str(batch.id),
        "batch_name": batch.name,
        "sent_count": sent_count,
        "replaced_count": replaced_count,
        "failed_count": failed_count,
        "batch_status": batch.status,
    }
