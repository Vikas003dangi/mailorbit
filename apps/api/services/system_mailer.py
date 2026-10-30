"""
Platform-Level System Mailer for Transactional Mail (Brevo HTTP API & Direct Platform SMTP/Gmail).

Used STRICTLY for platform system mail (Email Verification, OTPs, Password Reset, Security Notices).
Never uses a user's relay.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Any, Dict, Optional
import httpx

from apps.api.config import settings

logger = logging.getLogger("mailorbit.system_mailer")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_system_email(
    to_email: str,
    subject: str,
    html_content: str,
) -> Dict[str, Any]:
    """
    Sends a system transactional email via Brevo HTTP API or Platform SMTP (e.g. Gmail),
    with graceful fallback to secure local logging in development.
    """
    # 1. Option A: Brevo HTTP API
    if settings.BREVO_API_KEY:
        sender_email = settings.BREVO_SENDER_EMAIL or "noreply@mailorbit.io"
        payload = {
            "sender": {
                "name": "MailOrbit Platform",
                "email": sender_email,
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
        }
        headers = {
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(BREVO_API_URL, json=payload, headers=headers)
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                message_id = data.get("messageId", "unknown")
                logger.info("Brevo system email delivered to %s (messageId: %s)", to_email, message_id)
                return {
                    "success": True,
                    "status": "DELIVERED",
                    "message_id": message_id,
                    "to": to_email,
                }
            else:
                logger.error("Brevo API error (%s): %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.error("Exception calling Brevo API for %s: %s", to_email, exc)

    # 2. Option B: Platform SMTP / Gmail App Password
    if settings.SYSTEM_SMTP_USER and settings.SYSTEM_SMTP_PASSWORD:
        host = settings.SYSTEM_SMTP_HOST or "smtp.gmail.com"
        port = settings.SYSTEM_SMTP_PORT or 587
        sender_addr = settings.SYSTEM_SMTP_FROM or settings.SYSTEM_SMTP_USER
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"MailOrbit Platform <{sender_addr}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(host, port, timeout=15.0) as server:
                server.starttls()
                server.login(settings.SYSTEM_SMTP_USER, settings.SYSTEM_SMTP_PASSWORD)
                server.send_message(msg)

            logger.info("Platform SMTP email delivered to %s via %s:%s", to_email, host, port)
            return {
                "success": True,
                "status": "DELIVERED",
                "message_id": f"smtp-{to_email}",
                "to": to_email,
            }
        except Exception as exc:
            logger.error("Platform SMTP send failure to %s: %s", to_email, exc)

    # 3. Fallback / Dev Logging
    logger.warning(
        "Transactional mailer credentials not set. System transactional email to %s queued/logged: %s",
        to_email,
        subject,
    )
    return {
        "success": False,
        "status": "UNAVAILABLE",
        "detail": "No transactional mailer credentials configured (BREVO_API_KEY or SYSTEM_SMTP_USER).",
        "to": to_email,
    }


def send_otp_email(to_email: str, otp: str, purpose_label: str) -> Dict[str, Any]:
    """Sends a responsive, beautifully styled HTML OTP email."""
    subject = f"[MailOrbit] Your Verification Code: {otp}"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{purpose_label}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #090d16; color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 520px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <div style="text-align: center; margin-bottom: 24px; border-bottom: 1px solid #1e293b; padding-bottom: 20px;">
      <div style="font-size: 13px; color: #38bdf8; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">MailOrbit • Autonomous Cold Outreach</div>
      <h2 style="font-size: 22px; font-weight: 800; color: #ffffff; margin: 0;">{purpose_label}</h2>
    </div>
    <p style="font-size: 14px; color: #cbd5e1; line-height: 1.6; margin: 0 0 18px;">
      Use the following 6-digit one-time verification code to complete your request:
    </p>
    <div style="font-size: 36px; font-weight: 800; letter-spacing: 10px; color: #38bdf8; background: rgba(56, 189, 248, 0.08); border: 2px dashed #0284c7; border-radius: 10px; padding: 18px 24px; text-align: center; margin: 24px 0; font-family: 'Courier New', Courier, monospace;">
      {otp}
    </div>
    <div style="font-size: 13px; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 12px 14px; border-radius: 8px; margin: 20px 0; line-height: 1.5;">
      ⏱️ <strong>Security Notice:</strong> This single-use code expires in <strong>15 minutes</strong>. If you did not make this request, please safely disregard this email.
    </div>
    <div style="font-size: 12px; color: #64748b; margin-top: 26px; padding-top: 16px; border-top: 1px solid #1e293b; text-align: center;">
      MailOrbit Platform Security • Zero hardcoded credentials • Strict User Tenant Isolation
    </div>
  </div>
</body>
</html>"""
    return send_system_email(to_email=to_email, subject=subject, html_content=html)


def send_verification_email(to_email: str, token: str, base_url: str = "") -> Dict[str, Any]:
    url = f"{base_url}/api/v1/auth/verify-email?token={token}"
    subject = "Verify your MailOrbit account"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #0f172a; color: #f8fafc; border-radius: 10px;">
      <h2 style="color: #38bdf8;">Welcome to MailOrbit</h2>
      <p style="color: #cbd5e1; font-size: 15px;">Please verify your email address to activate your account and full workspace features.</p>
      <div style="margin: 25px 0;">
        <a href="{url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
          Verify Email Address
        </a>
      </div>
      <p style="color: #64748b; font-size: 12px;">Or copy and paste this link in your browser:<br/><a href="{url}" style="color: #38bdf8;">{url}</a></p>
    </div>
    """
    return send_system_email(to_email=to_email, subject=subject, html_content=html)


def send_password_reset_email(to_email: str, token: str, base_url: str = "") -> Dict[str, Any]:
    url = f"{base_url}/?reset_token={token}#reset"
    subject = "Reset your MailOrbit password"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #0f172a; color: #f8fafc; border-radius: 10px;">
      <h2 style="color: #38bdf8;">Password Reset Request</h2>
      <p style="color: #cbd5e1; font-size: 15px;">We received a request to reset your password. This link is single-use and will expire in 30 minutes.</p>
      <div style="margin: 25px 0;">
        <a href="{url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
          Reset Password
        </a>
      </div>
      <p style="color: #94a3b8; font-size: 13px;">If you did not request a password reset, you can safely ignore this email.</p>
      <p style="color: #64748b; font-size: 12px;">Link: <a href="{url}" style="color: #38bdf8;">{url}</a></p>
    </div>
    """
    return send_system_email(to_email=to_email, subject=subject, html_content=html)


