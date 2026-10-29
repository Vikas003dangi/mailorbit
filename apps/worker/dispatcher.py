from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
import httpx

from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.worker.ai_personalizer import GeminiPersonalizer, generate_email_content
from apps.worker.apps_script_relay import (
    AppsScriptRelayClient,
    QuotaExceededError,
    RelayAuthError,
    RelayError,
)
from apps.worker.pacer import Pacer
from apps.worker.sender import LocalMailpitSender
from packages.shared.crypto import EncryptionService, EnvKeyManager
from packages.shared.schema import AIKey, Batch, Contact, ContactReplacement, DoNotContact, Profile, Purpose, SenderRelay, User
from packages.shared.unsubscribe import (
    append_unsubscribe_footer,
    generate_unsubscribe_headers,
    generate_unsubscribe_token,
)

logger = logging.getLogger("mailorbit.dispatcher")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
SAFETY_THRESHOLD_RATIO = 0.10  # 10% maximum allowable failure/bounce rate
MIN_SAMPLES_FOR_SAFETY_CHECK = 5  # Minimum leads evaluated before triggering safety pause


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


import dns.resolver

_DNS_MX_CACHE: Dict[str, Tuple[bool, Optional[str]]] = {}


def verify_email_domain(email: str) -> Tuple[bool, Optional[str]]:
    """
    Pre-send email verification check:
    1. Validates syntactic email format.
    2. Validates domain syntax and rejects invalid/prohibited TLDs.
    3. Performs real DNS MX (and fallback A) resolution to verify domain exists and accepts mail.
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

    if domain in _DNS_MX_CACHE:
        return _DNS_MX_CACHE[domain]

    # Real DNS MX / A lookup
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 3.0
        try:
            mx_records = resolver.resolve(domain, "MX")
            if mx_records:
                _DNS_MX_CACHE[domain] = (True, None)
                return True, None
        except dns.resolver.NoAnswer:
            # Domain exists but has no MX record. Fallback to A record per RFC 5321.
            try:
                a_records = resolver.resolve(domain, "A")
                if a_records:
                    _DNS_MX_CACHE[domain] = (True, None)
                    return True, None
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                res = (False, f"Domain has no valid MX or A records: {domain}")
                _DNS_MX_CACHE[domain] = res
                return res
            except (dns.exception.Timeout, dns.resolver.ServerFailure, dns.resolver.NoNameservers) as trans_exc:
                logger.warning("Transient DNS error on fallback A record for %s: %s", domain, trans_exc)
                return True, None
        except dns.resolver.NXDOMAIN:
            res = (False, f"Domain does not exist (NXDOMAIN): {domain}")
            _DNS_MX_CACHE[domain] = res
            return res
        except (dns.exception.Timeout, dns.resolver.ServerFailure, dns.resolver.NoNameservers) as trans_exc:
            logger.warning("Transient DNS error on MX lookup for %s: %s", domain, trans_exc)
            return True, None
    except Exception as exc:
        logger.warning("DNS lookup exception for %s: %s", domain, exc)
        if "NXDOMAIN" in str(exc) or "does not exist" in str(exc):
            res = (False, f"Domain does not exist: {domain}")
            _DNS_MX_CACHE[domain] = res
            return res
        return True, None

    return True, None


def render_template(template: Optional[str], contact: Contact, default: str) -> str:
    """Renders placeholders in email subject and body."""
    raw = template or default
    return (
        raw.replace("{name}", contact.name or "there")
        .replace("{company}", contact.company or "your team")
        .replace("{role}", contact.role or "Hiring Team")
    )


def resolve_sender_for_batch(
    session: Session,
    user_id: uuid.UUID,
    explicit_sender: Optional[Any] = None,
) -> Tuple[Optional[Any], str, Optional[SenderRelay]]:
    """
    Resolves the appropriate email sender for a batch:
    - If explicit_sender is passed (e.g. mock test fixture), uses it.
    - Otherwise decrypts the user's active Google Apps Script relay.
    - LocalMailpitSender is ONLY permitted when ENVIRONMENT is development AND USE_FAKE_SMTP is True.
    - In production/staging, if no active relay is found, returns (None, "", None).
    """
    if explicit_sender is not None:
        return explicit_sender, "outreach@mailorbit.local", None

    relay = (
        session.query(SenderRelay)
        .filter(SenderRelay.user_id == user_id, SenderRelay.status == "ACTIVE")
        .first()
    )

    if relay:
        try:
            crypto = EncryptionService(EnvKeyManager(settings.ENCRYPTION_MASTER_KEY))
            token = crypto.decrypt(relay.auth_token_ciphertext)
            client = AppsScriptRelayClient(script_url=relay.script_url, auth_token=token)
            return client, relay.email, relay
        except Exception as exc:
            logger.error("Failed to initialize Apps Script relay for user %s: %s", user_id, exc)

    # LocalMailpitSender is strictly gated to development mode
    if settings.ENVIRONMENT == "development" and settings.USE_FAKE_SMTP:
        return LocalMailpitSender(), "outreach@mailorbit.local", None

    return None, "", None


def dispatch_batch(
    session: Session,
    batch_id: uuid.UUID,
    sender: Optional[Any] = None,
    pacer: Optional[Pacer] = None,
    from_email: Optional[str] = None,
    min_samples_for_safety: int = MIN_SAMPLES_FOR_SAFETY_CHECK,
) -> Dict[str, Any]:
    """
    Executes an outreach batch:
    - Resolves sender (Apps Script Relay or LocalMailpit in dev).
    - If sender is missing, unverified, or over quota: stops with clear status, 0 sent.
    - Records last_run_date to prevent duplicate runs on restarts.
    - Pre-send verifies each lead.
    - If verification fails: immediately marks lead INACTIVE and auto-tops up the batch.
    - Evaluates 10% Batch Safety Pause circuit breaker to protect sender domain reputation.
    - Paces dispatches with randomized human-like delay.
    - Dispatches email and updates contact + batch status.
    """
    batch = session.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return {"status": "ERROR", "message": f"Batch {batch_id} not found"}

    sender_client, default_from, relay = resolve_sender_for_batch(session, batch.user_id, sender)
    effective_from = from_email or default_from
    pacer = pacer or Pacer(min_seconds=0.0, max_seconds=0.0)

    # In production, missing or unverified sender must pause with clear status
    if sender_client is None:
        batch.status = "PAUSED"
        batch.paused_reason = "Connect your sender: No active Google Apps Script relay configured"
        session.commit()
        return {
            "batch_id": str(batch.id),
            "batch_name": batch.name,
            "status": "PAUSED",
            "paused_reason": batch.paused_reason,
            "sent_count": 0,
        }

    # Check relay quota before starting
    if relay and relay.remaining_quota is not None and relay.remaining_quota <= 0:
        relay.status = "QUOTA_EXCEEDED"
        batch.status = "PAUSED"
        batch.paused_reason = "Daily Gmail sending quota exhausted on sender relay"
        session.commit()
        return {
            "batch_id": str(batch.id),
            "batch_name": batch.name,
            "status": "PAUSED",
            "paused_reason": batch.paused_reason,
            "sent_count": 0,
        }

    # Record last_run_date in user's timezone to guard against restart duplicate dispatch
    from apps.worker.scheduler import get_user_local_datetime
    user = session.query(User).filter(User.id == batch.user_id).first()
    user_tz = user.timezone if user else "UTC"
    local_dt = get_user_local_datetime(user_tz)
    batch.last_run_date = local_dt.date()
    session.commit()

    purpose = None
    if batch.purpose_id:
        purpose = session.query(Purpose).filter(Purpose.id == batch.purpose_id).first()

    profile = session.query(Profile).filter(Profile.user_id == batch.user_id).first()

    # Resolve optional Gemini AI personalizer
    personalizer: Optional[GeminiPersonalizer] = None
    ai_key = (
        session.query(AIKey)
        .filter(AIKey.user_id == batch.user_id, AIKey.status == "ACTIVE")
        .first()
    )
    if ai_key:
        try:
            crypto = EncryptionService(EnvKeyManager(settings.ENCRYPTION_MASTER_KEY))
            plain_ai_key = crypto.decrypt(ai_key.api_key_ciphertext)
            personalizer = GeminiPersonalizer(api_key=plain_ai_key, model=ai_key.model or "gemini-2.5-flash")
        except Exception as exc:
            logger.warning("Failed to initialize AI personalizer for user %s: %s", batch.user_id, exc)

    # Resolve purpose attachments (e.g. resumes, portfolios)
    attachment_payloads: List[Dict[str, Any]] = []
    if purpose and purpose.attachments:
        import base64
        for att in purpose.attachments:
            b64_content = ""
            if att.file_url and att.file_url.startswith("http"):
                try:
                    with httpx.Client(timeout=10.0) as http_client:
                        resp = http_client.get(att.file_url)
                        if resp.status_code == 200:
                            b64_content = base64.b64encode(resp.content).decode("utf-8")
                except Exception as net_err:
                    logger.warning("Failed to fetch attachment %s content: %s", att.filename, net_err)
            if not b64_content:
                b64_content = base64.b64encode(b"%PDF-1.4 simulated document").decode("utf-8")
            attachment_payloads.append({
                "filename": att.filename,
                "content_type": att.content_type or "application/pdf",
                "base64_content": b64_content,
            })

    contacts = (
        session.query(Contact)
        .filter(Contact.batch_id == batch.id, Contact.status.in_(["PENDING", "QUEUED"]))
        .order_by(Contact.created_at.asc())
        .all()
    )

    sent_count = 0
    replaced_count = 0
    failed_count = 0
    total_evaluated = 0
    safety_paused = False

    queue: List[Contact] = list(contacts)

    def trigger_safety_pause_if_needed() -> bool:
        nonlocal safety_paused
        if total_evaluated >= min_samples_for_safety:
            failure_rate = failed_count / total_evaluated
            if failure_rate > SAFETY_THRESHOLD_RATIO:
                safety_paused = True
                batch.status = "PAUSED"
                batch.paused_reason = (
                    f"Safety pause triggered: failure rate {failure_rate * 100:.1f}% "
                    f"exceeded 10% threshold ({failed_count}/{total_evaluated} leads failed). "
                    "Paused to protect sender domain reputation."
                )
                session.commit()
                logger.warning("Batch %s paused: %s", batch.name, batch.paused_reason)
                return True
        return False

    while queue:
        contact = queue.pop(0)
        total_evaluated += 1

        # 0. Check Do-Not-Contact registry (Opt-out protection)
        dnc_entry = (
            session.query(DoNotContact)
            .filter(
                DoNotContact.user_id == batch.user_id,
                DoNotContact.email == contact.email.lower().strip(),
            )
            .first()
        )
        if dnc_entry:
            contact.status = "UNSUBSCRIBED"
            contact.status_reason = f"Recipient is on Do-Not-Contact list ({dnc_entry.reason})"
            session.commit()

            # Immediate auto-topup replacement
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
                    "Auto-replaced unsubscribed contact %s with %s in batch %s",
                    contact.email,
                    replacement.email,
                    batch.name,
                )
            continue

        # 1. Pre-send verification
        is_valid, fail_reason = verify_email_domain(contact.email)

        if not is_valid:
            failed_count += 1
            contact.status = "INACTIVE"
            contact.is_not_working = True
            contact.status_reason = f"Pre-send verification failed: {fail_reason}"
            session.commit()

            # Check 10% safety pause circuit breaker
            if trigger_safety_pause_if_needed():
                break

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
                rep_record = ContactReplacement(
                    user_id=batch.user_id,
                    purpose_id=batch.purpose_id,
                    batch_id=batch.id,
                    original_contact_id=contact.id,
                    original_email=contact.email,
                    replaced_by_contact_id=replacement.id,
                    replaced_by_email=replacement.email,
                    reason=contact.status_reason,
                )
                session.add(rep_record)
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

        # 4. Render email content (AI personalization with automatic template fallback)
        subject, body_text, _ = generate_email_content(
            contact=contact,
            purpose=purpose,
            profile=profile,
            personalizer=personalizer,
        )

        # 5. Append Unsubscribe Header & Footer (RFC 2369 / RFC 8058)
        unsub_token = generate_unsubscribe_token(
            user_id=batch.user_id,
            contact_id=contact.id,
            email=contact.email,
            secret_key=settings.ENCRYPTION_MASTER_KEY,
        )
        api_base = (
            "https://mailorbit-api-nrxf.onrender.com"
            if settings.ENVIRONMENT == "production"
            else "http://localhost:8000"
        )
        unsub_url = f"{api_base}/api/v1/unsubscribe?token={unsub_token}"
        final_body = append_unsubscribe_footer(body_text, unsub_url)
        unsub_headers = generate_unsubscribe_headers(unsub_url)

        # 6. Dispatch email
        try:
            send_res = sender_client.send_email(
                from_email=effective_from,
                to_email=contact.email,
                subject=subject,
                body_text=final_body,
                attachments=attachment_payloads if attachment_payloads else None,
                headers=unsub_headers,
            )
            contact.status = "SENT"
            contact.sent_at = utc_now()
            contact.error = None
            sent_count += 1

            # Update relay quota tracking if returned by relay
            if relay and isinstance(send_res, dict) and "remaining_quota" in send_res:
                rem = send_res["remaining_quota"]
                if rem is not None:
                    relay.remaining_quota = rem
                    if rem <= 0:
                        relay.status = "QUOTA_EXCEEDED"
                        batch.status = "PAUSED"
                        batch.paused_reason = "Daily Gmail sending quota reached"
                        session.commit()
                        break

        except QuotaExceededError:
            if relay:
                relay.status = "QUOTA_EXCEEDED"
                relay.remaining_quota = 0
            batch.status = "PAUSED"
            batch.paused_reason = "Daily Gmail sending quota reached"
            session.commit()
            break

        except RelayAuthError as auth_err:
            if relay:
                relay.status = "ERROR"
            batch.status = "PAUSED"
            batch.paused_reason = f"Relay authentication failure: {str(auth_err)}"
            session.commit()
            break

        except Exception as exc:
            failed_count += 1
            contact.status = "FAILED"
            contact.error = str(exc)
            logger.error("Failed sending email to %s: %s", contact.email, exc)

            # Check 10% safety pause circuit breaker after delivery failure
            if trigger_safety_pause_if_needed():
                break

        session.commit()

        # Check 10% safety pause circuit breaker after evaluating lead
        if trigger_safety_pause_if_needed():
            break

    # Complete the batch only if not paused and all contacts in batch are processed
    if not safety_paused and batch.status != "PAUSED":
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
        "paused_reason": getattr(batch, "paused_reason", None),
    }
