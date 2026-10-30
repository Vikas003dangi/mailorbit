"""
Platform-Level System Mailer for Transactional Mail.

Used STRICTLY for platform system mail:
1. Email Verification OTPs (signup, reset, change password, delete account) - HIGH PRIORITY
2. Password Changed Confirmations - HIGH PRIORITY
3. Account Deletion Notices - HIGH PRIORITY
4. New Sign-in from Unrecognized Device - HIGH PRIORITY
5. Account Welcome & Onboarding (post-verification) - LOW PRIORITY
6. Campaign Finished Notifications - LOW PRIORITY
7. Batch Paused by Safety Limit / Quota - LOW PRIORITY
8. Relay Disconnected or Failing - LOW PRIORITY
9. Data Export Ready - LOW PRIORITY

Operational Guarantees:
- Database-backed audit trail and quota telemetry (system_mail_logs table).
- Zero tracking pixels and zero link shorteners.
- Text wordmark with CSS logo fallback (optional hosted PNG).
- Rolling 24-hour platform cap (90 emails/day) with priority floor reservation:
  A floor of 60 emails is strictly reserved for OTP & security verifications,
  supporting 30 to 60 verified new users or password resets per rolling day.
  Low-priority notifications are capped at 30/day and automatically dropped to the
  database (status="DROPPED_NEAR_CAP") when remaining capacity is <= 60.
- Authoritative relay quota: When the relay reports remaining quota is exhausted,
  dispatching halts immediately.
- In Production: Dispatches exclusively via Platform Google Apps Script System Relay
  (SYSTEM_RELAY_URL and SYSTEM_RELAY_TOKEN over HTTPS:443).
- In Development: Dispatches to local Mailpit (SMTP on localhost:1025) or safe debug logs.
"""

from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import re
import smtplib
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.orm import Session

from apps.api.config import settings
from packages.shared.schema import SystemMailLog

logger = logging.getLogger("mailorbit.system_mailer")

# Budget & Capacity Constants
SYSTEM_DAILY_CAP: int = 90
OTP_SECURITY_FLOOR: int = 60       # Dedicated reserve floor for OTP and security emails
LOW_PRIORITY_DAILY_CAP: int = 30   # Low-priority mail capped below the reserved floor
STOP_THRESHOLD: int = 2            # Halt sending when effective remaining quota is <= 2


def _get_budget_state(db: Session) -> Dict[str, Any]:
    """Computes live database-backed relay budget metrics over rolling 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    try:
        sent_24h = (
            db.query(SystemMailLog)
            .filter(SystemMailLog.status == "SENT", SystemMailLog.created_at >= cutoff)
            .count()
        )
        low_priority_sent_24h = (
            db.query(SystemMailLog)
            .filter(
                SystemMailLog.status == "SENT",
                SystemMailLog.priority == "LOW",
                SystemMailLog.created_at >= cutoff,
            )
            .count()
        )
        dropped_24h = (
            db.query(SystemMailLog)
            .filter(
                SystemMailLog.status == "DROPPED_NEAR_CAP",
                SystemMailLog.created_at >= cutoff,
            )
            .count()
        )
        last_report = (
            db.query(SystemMailLog.relay_reported_remaining)
            .filter(
                SystemMailLog.relay_reported_remaining.isnot(None),
                SystemMailLog.created_at >= cutoff,
            )
            .order_by(SystemMailLog.created_at.desc())
            .first()
        )
        relay_reported = last_report[0] if last_report else None
    except Exception as e:
        logger.warning("Could not query system_mail_logs: %s", e)
        sent_24h = 0
        low_priority_sent_24h = 0
        dropped_24h = 0
        relay_reported = None

    calculated_remaining = max(0, SYSTEM_DAILY_CAP - sent_24h)
    if relay_reported is not None:
        effective_remaining = min(calculated_remaining, relay_reported)
    else:
        effective_remaining = calculated_remaining

    is_low_priority_suppressed = (
        effective_remaining <= OTP_SECURITY_FLOOR or low_priority_sent_24h >= LOW_PRIORITY_DAILY_CAP
    )

    return {
        "platform_daily_cap": SYSTEM_DAILY_CAP,
        "otp_security_floor": OTP_SECURITY_FLOOR,
        "supported_new_users_per_day": f"{OTP_SECURITY_FLOOR // 2} to {OTP_SECURITY_FLOOR}",
        "low_priority_daily_cap": LOW_PRIORITY_DAILY_CAP,
        "sent_rolling_24h": sent_24h,
        "low_priority_sent_24h": low_priority_sent_24h,
        "dropped_notifications_rolling_24h": dropped_24h,
        "calculated_remaining": calculated_remaining,
        "relay_reported_remaining": relay_reported,
        "effective_remaining": effective_remaining,
        "low_priority_suppressed": is_low_priority_suppressed,
    }


def get_system_relay_budget(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Returns platform transactional relay budget telemetry.
    Restricted to verified superusers only.
    """
    if db is not None:
        return _get_budget_state(db)
    try:
        from packages.shared.db import SessionLocal
        with SessionLocal() as session:
            return _get_budget_state(session)
    except Exception:
        return {
            "platform_daily_cap": SYSTEM_DAILY_CAP,
            "otp_security_floor": OTP_SECURITY_FLOOR,
            "supported_new_users_per_day": f"{OTP_SECURITY_FLOOR // 2} to {OTP_SECURITY_FLOOR}",
            "low_priority_daily_cap": LOW_PRIORITY_DAILY_CAP,
            "sent_rolling_24h": 0,
            "effective_remaining": SYSTEM_DAILY_CAP,
            "low_priority_suppressed": False,
        }


def _record_log(
    db: Optional[Session],
    recipient: str,
    event_type: str,
    priority: str,
    status: str,
    detail: Optional[str] = None,
    relay_remaining: Optional[int] = None,
) -> None:
    """Helper to persist transactional event to system_mail_logs table."""
    if db is None:
        return
    try:
        log_entry = SystemMailLog(
            recipient=recipient.strip().lower(),
            event_type=event_type,
            priority=priority,
            status=status,
            detail=detail,
            relay_reported_remaining=relay_remaining,
        )
        db.add(log_entry)
        db.commit()
    except Exception as exc:
        logger.warning("Could not persist system_mail_log: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def send_system_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    is_high_priority: bool = False,
    event_type: str = "generic",
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Sends a system transactional email with database-backed quota guard,
    priority floor reservations, and dropped notification logging.
    """
    priority_label = "HIGH" if is_high_priority else "LOW"

    # 1. Evaluate Budget & Floor Reservations in Database
    if db is not None:
        budget = _get_budget_state(db)

        # A. Low-Priority Mail Capped / Reserved Floor Guard
        if not is_high_priority and budget["low_priority_suppressed"]:
            reason = "Low-priority notification suppressed to reserve floor of 60 emails for OTP and security."
            _record_log(
                db=db,
                recipient=to_email,
                event_type=event_type,
                priority=priority_label,
                status="DROPPED_NEAR_CAP",
                detail=reason,
                relay_remaining=budget["relay_reported_remaining"],
            )
            logger.warning("Notification %s dropped for %s: %s", event_type, to_email, reason)
            return {
                "success": False,
                "status": "DROPPED_NEAR_CAP",
                "detail": "Notification paused to preserve platform capacity for security OTPs.",
                "to": to_email,
            }

        # B. Absolute Quota Exhaustion Guard
        if budget["effective_remaining"] <= STOP_THRESHOLD:
            reason = f"Platform system relay quota exhausted (effective remaining: {budget['effective_remaining']})."
            _record_log(
                db=db,
                recipient=to_email,
                event_type=event_type,
                priority=priority_label,
                status="QUOTA_EXCEEDED",
                detail=reason,
                relay_remaining=budget["relay_reported_remaining"],
            )
            logger.error("System mail rejected: %s", reason)
            return {
                "success": False,
                "status": "QUOTA_EXCEEDED",
                "detail": "System email capacity is temporarily exhausted. Please try again later.",
                "to": to_email,
            }

    # 2. Plain Text Generator
    if not plain_content:
        plain_content = re.sub(r"<[^>]*>", " ", html_content)
        plain_content = re.sub(r"\s+", " ", plain_content).strip()

    # 3. Production Path: Platform Apps Script System Relay
    if settings.SYSTEM_RELAY_URL and settings.SYSTEM_RELAY_TOKEN:
        payload = {
            "token": settings.SYSTEM_RELAY_TOKEN,
            "to": to_email,
            "subject": subject,
            "html_body": html_content,
            "plain_body": plain_content,
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                resp = client.post(
                    settings.SYSTEM_RELAY_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    msg_id = data.get("message_id", "gas-sys-ok")
                    rem_quota = data.get("remaining_quota")
                    _record_log(
                        db=db,
                        recipient=to_email,
                        event_type=event_type,
                        priority=priority_label,
                        status="SENT",
                        detail=f"Message ID: {msg_id}",
                        relay_remaining=rem_quota,
                    )
                    logger.info("Platform system relay delivered email to %s (id: %s)", to_email, msg_id)
                    return {
                        "success": True,
                        "status": "DELIVERED",
                        "message_id": msg_id,
                        "to": to_email,
                        "remaining_quota": rem_quota,
                    }
                else:
                    err_code = data.get("error", "RELAY_REJECTED")
                    err_msg = data.get("message", "Relay returned unsuccess response")
                    _record_log(
                        db=db,
                        recipient=to_email,
                        event_type=event_type,
                        priority=priority_label,
                        status="FAILED",
                        detail=f"{err_code}: {err_msg}",
                    )
                    logger.error("Platform system relay error (%s): %s", err_code, err_msg)
                    return {
                        "success": False,
                        "status": err_code,
                        "detail": err_msg,
                        "to": to_email,
                    }
            elif resp.status_code == 429:
                _record_log(
                    db=db,
                    recipient=to_email,
                    event_type=event_type,
                    priority=priority_label,
                    status="QUOTA_EXCEEDED",
                    detail="Relay returned HTTP 429 Quota Exceeded.",
                    relay_remaining=0,
                )
                logger.warning("Platform system relay daily quota exceeded for %s", to_email)
                return {
                    "success": False,
                    "status": "QUOTA_EXCEEDED",
                    "detail": "System email capacity is temporarily exhausted. Please try again later.",
                    "to": to_email,
                }
            else:
                err_text = f"Relay responded with status code {resp.status_code}"
                _record_log(
                    db=db,
                    recipient=to_email,
                    event_type=event_type,
                    priority=priority_label,
                    status="FAILED",
                    detail=err_text,
                )
                logger.error("Platform system relay HTTP error: %s", err_text)
                return {
                    "success": False,
                    "status": "RELAY_HTTP_ERROR",
                    "detail": err_text,
                    "to": to_email,
                }
        except Exception as exc:
            err_text = f"System email relay network error: {str(exc)}"
            _record_log(
                db=db,
                recipient=to_email,
                event_type=event_type,
                priority=priority_label,
                status="FAILED",
                detail=err_text,
            )
            logger.error("Exception dispatching system email via relay to %s: %s", to_email, exc)
            return {
                "success": False,
                "status": "RELAY_UNAVAILABLE",
                "detail": err_text,
                "to": to_email,
            }

    # 4. Local Dev / Mailpit SMTP (Only in non-production)
    if settings.ENVIRONMENT != "production" and (settings.USE_FAKE_SMTP or settings.SYSTEM_SMTP_HOST):
        host = settings.FAKE_SMTP_HOST if settings.USE_FAKE_SMTP else settings.SYSTEM_SMTP_HOST
        port = settings.FAKE_SMTP_PORT if settings.USE_FAKE_SMTP else (settings.SYSTEM_SMTP_PORT or 1025)
        sender_addr = settings.SYSTEM_SMTP_FROM or "system@mailorbit.local"
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"MailOrbit <{sender_addr}>"
            msg["To"] = to_email
            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(host, port, timeout=5.0) as server:
                server.send_message(msg)

            _record_log(
                db=db,
                recipient=to_email,
                event_type=event_type,
                priority=priority_label,
                status="SENT",
                detail=f"Dev SMTP via {host}:{port}",
            )
            logger.info("Local dev system email delivered to %s via %s:%s", to_email, host, port)
            return {
                "success": True,
                "status": "DELIVERED",
                "message_id": f"dev-smtp-{to_email}",
                "to": to_email,
            }
        except Exception as exc:
            logger.warning("Local dev SMTP failed for %s (%s:%s): %s", to_email, host, port, exc)
            if settings.ENVIRONMENT != "production":
                _record_log(
                    db=db,
                    recipient=to_email,
                    event_type=event_type,
                    priority=priority_label,
                    status="SENT",
                    detail=f"Local dev simulated dispatch ({exc})",
                )
                logger.info("Local dev simulated system email recorded for %s: %s", to_email, subject)
                return {
                    "success": True,
                    "status": "DELIVERED",
                    "message_id": f"dev-test-mock-{to_email}",
                    "to": to_email,
                }

    # 5. Unavailable in Production (Honest failure - never auto-verify)
    _record_log(
        db=db,
        recipient=to_email,
        event_type=event_type,
        priority=priority_label,
        status="UNAVAILABLE",
        detail="System mailer relay credentials not configured.",
    )
    logger.warning("System mailer relay not configured. Email to %s not delivered: %s", to_email, subject)
    return {
        "success": False,
        "status": "UNAVAILABLE",
        "detail": "System transactional email service is currently unavailable. Please contact the administrator.",
        "to": to_email,
    }


def _render_email_base(
    to_email: str,
    title: str,
    body_content: str,
    action_button: Optional[str] = None,
    footer_note: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> str:
    """
    Renders a responsive dark-mode email template.
    Includes text wordmark + logo placeholder, consistent footer explaining
    why the recipient received the mail, and strictly zero tracking pixels.
    """
    logo_markup = (
        f'<img src="{logo_url}" alt="MailOrbit" width="32" height="32" style="border: 0; display: inline-block; vertical-align: middle;" />'
        if logo_url
        else '<div style="width: 32px; height: 32px; background: #0284c7; border-radius: 6px; text-align: center; line-height: 32px; font-size: 16px; font-weight: 800; color: #ffffff; display: inline-block; vertical-align: middle;">M</div>'
    )

    action_markup = f'<div style="text-align: center; margin: 28px 0;">{action_button}</div>' if action_button else ""
    note_markup = (
        f'<div style="font-size: 13px; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 12px 14px; border-radius: 8px; margin: 20px 0; line-height: 1.5;">{footer_note}</div>'
        if footer_note
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #090d16; color: #f8fafc; margin: 0; padding: 32px 16px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center">
        <div style="max-width: 540px; width: 100%; background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 36px 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: left;">
          
          <!-- Header with Wordmark and Logo Fallback -->
          <div style="border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 24px; text-align: center;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin: 0 auto 8px auto;">
              <tr>
                <td valign="middle" style="padding-right: 10px;">
                  {logo_markup}
                </td>
                <td valign="middle">
                  <span style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">MailOrbit</span>
                </td>
              </tr>
            </table>
            <div style="font-size: 11px; color: #38bdf8; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 700;">
              Autonomous Cold Outreach Platform
            </div>
            <h1 style="font-size: 21px; font-weight: 700; color: #ffffff; margin: 18px 0 0 0;">
              {title}
            </h1>
          </div>

          <!-- Body Content -->
          <div style="font-size: 14px; color: #cbd5e1; line-height: 1.6; margin-bottom: 24px;">
            {body_content}
          </div>

          {action_markup}
          {note_markup}

          <!-- Consistent Transactional Footer -->
          <div style="font-size: 11px; color: #64748b; margin-top: 28px; padding-top: 18px; border-top: 1px solid #1e293b; text-align: center; line-height: 1.5;">
            <strong>Why you received this:</strong> You are receiving this transactional notification because an action or security event occurred on your MailOrbit account ({to_email}).<br>
            MailOrbit never sends unsolicited marketing or uses tracking pixels.
          </div>

        </div>
      </td>
    </tr>
  </table>
</body>
</html>"""


# =========================================================================
# Event 1: Email Verification OTP (HIGH PRIORITY)
# =========================================================================
def send_otp_email(
    to_email: str,
    otp: str,
    purpose_label: str,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """1. OTP Verification Email (15 minute validity)."""
    subject = f"[MailOrbit] Your Verification Code: {otp}"
    body = f"""
    <p style="margin: 0 0 16px;">Use the following 6-digit verification code to complete your request: <strong>{purpose_label}</strong></p>
    <div style="font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; background: rgba(56, 189, 248, 0.08); border: 2px dashed #0284c7; border-radius: 10px; padding: 16px 20px; text-align: center; margin: 20px 0; font-family: 'Courier New', Courier, monospace;">
      {otp}
    </div>
    """
    footer = "⏱️ <strong>Security Notice:</strong> This single-use code expires in <strong>15 minutes</strong>. Never share this code with anyone."
    html = _render_email_base(to_email=to_email, title=purpose_label, body_content=body, footer_note=footer)
    plain = f"MailOrbit Verification Code: {otp}\n\nPurpose: {purpose_label}\nValid for 15 minutes.\nDo not share this code.\n\nWhy you received this: Action requested for {to_email}."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=True,
        event_type="otp",
        db=db,
    )


# =========================================================================
# Event 2: Welcome Email (LOW PRIORITY)
# =========================================================================
def send_welcome_email(
    to_email: str,
    user_name: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """2. Account Welcome Email upon verified registration."""
    name_str = f" {user_name}" if user_name else ""
    subject = "Welcome to MailOrbit - Your Autonomous Cold Outreach Platform"
    body = f"""
    <p style="margin: 0 0 14px;">Hello{name_str},</p>
    <p style="margin: 0 0 14px;">Welcome to <strong>MailOrbit</strong>! Your workspace account has been verified and is ready for use.</p>
    <p style="margin: 0 0 14px;">Platform capabilities enabled on your workspace:</p>
    <ul style="padding-left: 20px; margin: 0 0 16px; color: #94a3b8;">
      <li style="margin-bottom: 6px;"><strong style="color: #e2e8f0;">Autonomous Batch Campaigns:</strong> Fair-Share water-filling scheduler respecting Gmail sending limits.</li>
      <li style="margin-bottom: 6px;"><strong style="color: #e2e8f0;">Google Apps Script Relays:</strong> Zero port blocks and zero password exposure.</li>
      <li style="margin-bottom: 6px;"><strong style="color: #e2e8f0;">BYOK AI Personalization:</strong> Tailored recruiter and client outreach.</li>
      <li style="margin-bottom: 6px;"><strong style="color: #e2e8f0;">ATS Resume Scanner:</strong> Instant scoring and keyword optimization.</li>
    </ul>
    <p style="margin: 0;">To begin, configure your outbound sender relay under the Sender Relay & Keys section.</p>
    """
    html = _render_email_base(to_email=to_email, title="Welcome to MailOrbit", body_content=body)
    plain = f"Hello{name_str},\n\nWelcome to MailOrbit! Your workspace account is verified and ready.\nConfigure your outbound sender relay in the dashboard to begin."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=False,
        event_type="welcome",
        db=db,
    )


# =========================================================================
# Event 3: Password Changed Notice (HIGH PRIORITY)
# =========================================================================
def send_password_changed_email(
    to_email: str,
    user_name: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """3. Password Changed Confirmation (Security Notice)."""
    name_str = f" {user_name}" if user_name else ""
    subject = "[MailOrbit Security] Your account password was updated"
    body = f"""
    <p style="margin: 0 0 14px;">Hello{name_str},</p>
    <p style="margin: 0 0 14px;">This is a confirmation that the password for your MailOrbit account (<strong>{to_email}</strong>) was recently changed.</p>
    <p style="margin: 0 0 14px;">All previous active sessions have been automatically invalidated across all devices.</p>
    """
    footer = "🛡️ <strong>Security Warning:</strong> If you did NOT make this change, please reset your password immediately."
    html = _render_email_base(to_email=to_email, title="Password Updated Successfully", body_content=body, footer_note=footer)
    plain = f"Hello{name_str},\n\nYour MailOrbit account password has been updated. All active sessions have been revoked.\nIf you did not make this change, reset your password immediately."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=True,
        event_type="password_changed",
        db=db,
    )


# =========================================================================
# Event 4: Account Deleted Notice (HIGH PRIORITY)
# =========================================================================
def send_account_deleted_email(
    to_email: str,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """4. Account Deletion Confirmation."""
    subject = "[MailOrbit] Your workspace account has been deleted"
    body = f"""
    <p style="margin: 0 0 14px;">This email confirms that your MailOrbit workspace account (<strong>{to_email}</strong>) and all associated data have been permanently erased.</p>
    <p style="margin: 0 0 14px;">All campaigns, contacts, uploaded resumes, AI keys, and relay credentials have been purged from the database.</p>
    <p style="margin: 0;">Thank you for using MailOrbit.</p>
    """
    html = _render_email_base(to_email=to_email, title="Workspace Permanently Erased", body_content=body)
    plain = f"Your MailOrbit workspace ({to_email}) and all associated records have been permanently erased.\nThank you for using MailOrbit."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=True,
        event_type="account_deleted",
        db=db,
    )


# =========================================================================
# Event 5: New Sign-in from Unrecognized Device (HIGH PRIORITY)
# =========================================================================
def send_new_device_login_email(
    to_email: str,
    device_info: str,
    ip_address: str,
    timestamp: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """5. Security Notice for sign-in from a new device or browser."""
    subject = "[MailOrbit Security] New sign-in detected from an unrecognized device"
    time_str = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""
    <p style="margin: 0 0 14px;">A new sign-in was detected for your account <strong>{to_email}</strong>:</p>
    <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 16px; margin: 18px 0;">
      <div style="margin-bottom: 8px;"><strong style="color: #94a3b8;">Device / Client:</strong> <span style="color: #ffffff;">{device_info}</span></div>
      <div style="margin-bottom: 8px;"><strong style="color: #94a3b8;">IP Address:</strong> <span style="color: #38bdf8;">{ip_address}</span></div>
      <div><strong style="color: #94a3b8;">Timestamp:</strong> <span style="color: #cbd5e1;">{time_str}</span></div>
    </div>
    <p style="margin: 0;">If this was you, you can safely ignore this notification. If you did not sign in from this device, please change your password immediately.</p>
    """
    footer = "🛡️ <strong>Security Tip:</strong> Unauthorized sign-ins can be stopped immediately by changing your password."
    html = _render_email_base(to_email=to_email, title="Unrecognized Device Sign-In", body_content=body, footer_note=footer)
    plain = f"New sign-in detected for {to_email}.\nDevice: {device_info}\nIP: {ip_address}\nTime: {time_str}\nIf this wasn't you, reset your password immediately."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=True,
        event_type="new_device_login",
        db=db,
    )


# =========================================================================
# Event 6: Campaign Finished (LOW PRIORITY)
# =========================================================================
def send_campaign_finished_email(
    to_email: str,
    campaign_name: str,
    total_sent: int,
    success_count: int,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """6. Campaign Finished Notification."""
    subject = f"[MailOrbit] Campaign Completed: {campaign_name}"
    body = f"""
    <p style="margin: 0 0 14px;">All scheduled outreach batches for campaign <strong>{campaign_name}</strong> have finished dispatching.</p>
    <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 16px; margin: 18px 0;">
      <div style="margin-bottom: 8px;"><strong style="color: #94a3b8;">Campaign:</strong> <span style="color: #ffffff;">{campaign_name}</span></div>
      <div style="margin-bottom: 8px;"><strong style="color: #94a3b8;">Total Dispatched:</strong> <span style="color: #38bdf8; font-weight: 700;">{total_sent}</span></div>
      <div><strong style="color: #94a3b8;">Successful Deliveries:</strong> <span style="color: #4ade80; font-weight: 700;">{success_count}</span></div>
    </div>
    <p style="margin: 0;">Detailed per-lead delivery statuses and bounce audit trails are available in your workspace dashboard.</p>
    """
    html = _render_email_base(to_email=to_email, title=f"Campaign Completed: {campaign_name}", body_content=body)
    plain = f"Campaign Completed: {campaign_name}\nTotal Sent: {total_sent}\nSuccessful: {success_count}\nView analytics in your dashboard."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=False,
        event_type="campaign_finished",
        db=db,
    )


# =========================================================================
# Event 7: Batch Paused by Safety Limit / Quota (LOW PRIORITY)
# =========================================================================
def send_batch_paused_email(
    to_email: str,
    batch_id: str,
    campaign_name: str,
    reason: str,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """7. Notification when an automated batch is paused."""
    subject = f"[MailOrbit Alert] Outreach Batch Paused: {campaign_name}"
    body = f"""
    <p style="margin: 0 0 14px;">An outreach batch in campaign <strong>{campaign_name}</strong> was automatically paused by safety guardrails:</p>
    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 16px; margin: 18px 0; color: #fde68a;">
      <div style="margin-bottom: 6px;"><strong>Batch Identifier:</strong> {batch_id}</div>
      <div><strong>Reason:</strong> {reason}</div>
    </div>
    <p style="margin: 0;">Dispatching will resume automatically on the next scheduled window or once the sender quota resets.</p>
    """
    html = _render_email_base(to_email=to_email, title="Outreach Batch Paused", body_content=body)
    plain = f"Batch Paused for {campaign_name}.\nBatch ID: {batch_id}\nReason: {reason}\nDispatching will resume on the next window."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=False,
        event_type="batch_paused",
        db=db,
    )


# =========================================================================
# Event 8: Relay Disconnected or Failing (LOW PRIORITY)
# =========================================================================
def send_relay_failure_email(
    to_email: str,
    relay_name: str,
    error_details: str,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """8. Notification when a configured sender relay fails authentication or execution."""
    subject = f"[MailOrbit Alert] Sender Relay Disconnected: {relay_name}"
    body = f"""
    <p style="margin: 0 0 14px;">Your sender relay <strong>{relay_name}</strong> encountered an error during dispatch:</p>
    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 16px; margin: 18px 0; color: #fca5a5;">
      <strong>Error:</strong> {error_details}
    </div>
    <p style="margin: 0;">Please verify your Google Apps Script Web App URL and RELAY_AUTH_TOKEN in the Sender Relay settings to resume sending.</p>
    """
    html = _render_email_base(to_email=to_email, title="Sender Relay Warning", body_content=body)
    plain = f"Sender relay error for {relay_name}:\n{error_details}\nPlease check your relay configuration in MailOrbit settings."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=False,
        event_type="relay_failure",
        db=db,
    )


# =========================================================================
# Event 9: Data Export Ready (LOW PRIORITY)
# =========================================================================
def send_data_export_ready_email(
    to_email: str,
    export_type: str,
    details: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """9. Notification when requested workspace data export is generated."""
    subject = f"[MailOrbit] Your {export_type} Data Export is Ready"
    detail_markup = f"<p style='margin: 0 0 14px;'>{details}</p>" if details else ""
    body = f"""
    <p style="margin: 0 0 14px;">Your requested <strong>{export_type}</strong> data export has been prepared and is ready for download in your workspace settings.</p>
    {detail_markup}
    <p style="margin: 0;">For security, export download links expire after 24 hours.</p>
    """
    html = _render_email_base(to_email=to_email, title="Data Export Prepared", body_content=body)
    plain = f"Your {export_type} data export has been prepared.\nLog into your workspace to download your files."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=False,
        event_type="data_export_ready",
        db=db,
    )


# =========================================================================
# Security Alert (Generic)
# =========================================================================
def send_security_alert_email(
    to_email: str,
    alert_title: str,
    alert_details: str,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Security Alert Notification (Lockouts, suspicious activity, policy violations)."""
    subject = f"[MailOrbit Security Alert] {alert_title}"
    body = f"""
    <p style="margin: 0 0 14px;">A security event was detected on your MailOrbit account:</p>
    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 16px; margin: 18px 0; color: #fca5a5;">
      <strong>{alert_title}</strong>
      <p style="margin: 8px 0 0; font-size: 13px; color: #fecaca; line-height: 1.5;">{alert_details}</p>
    </div>
    <p style="margin: 0;">If this was initiated by you, no action is necessary. If you suspect unauthorized access, please reset your password immediately.</p>
    """
    html = _render_email_base(to_email=to_email, title=f"Security Alert: {alert_title}", body_content=body)
    plain = f"MailOrbit Security Alert: {alert_title}\n\n{alert_details}\n\nIf you did not initiate this, reset your password immediately."
    return send_system_email(
        to_email=to_email,
        subject=subject,
        html_content=html,
        plain_content=plain,
        is_high_priority=True,
        event_type="security_alert",
        db=db,
    )


# Backward-compatibility wrappers
def send_verification_email(to_email: str, token: str, base_url: str = "", db: Optional[Session] = None) -> Dict[str, Any]:
    url = f"{base_url}/api/v1/auth/verify-email?token={token}"
    subject = "[MailOrbit] Verify your email address"
    body = f"""
    <p style="margin: 0 0 14px;">Please verify your email address to activate your MailOrbit workspace.</p>
    <p style="margin: 0;">Click below to confirm your address:</p>
    """
    action = f'<a href="{url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 700; display: inline-block;">Verify Email Address</a>'
    footer = f"Link: {url}"
    html = _render_email_base(to_email=to_email, title="Verify Your Account", body_content=body, action_button=action, footer_note=footer)
    plain = f"Verify your MailOrbit account:\n{url}"
    return send_system_email(to_email=to_email, subject=subject, html_content=html, plain_content=plain, is_high_priority=True, event_type="verification", db=db)


def send_password_reset_email(to_email: str, token: str, base_url: str = "", db: Optional[Session] = None) -> Dict[str, Any]:
    url = f"{base_url}/?reset_token={token}#reset"
    subject = "[MailOrbit] Reset your account password"
    body = f"""
    <p style="margin: 0 0 14px;">We received a request to reset your password. This link is single-use and will expire in 30 minutes.</p>
    <p style="margin: 0;">Click below to choose a new password:</p>
    """
    action = f'<a href="{url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 700; display: inline-block;">Reset Password</a>'
    footer = f"Link: {url}"
    html = _render_email_base(to_email=to_email, title="Password Reset Request", body_content=body, action_button=action, footer_note=footer)
    plain = f"Reset your MailOrbit password:\n{url}"
    return send_system_email(to_email=to_email, subject=subject, html_content=html, plain_content=plain, is_high_priority=True, event_type="password_reset", db=db)
