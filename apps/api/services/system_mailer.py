"""
Platform-Level System Mailer for Transactional Mail (Brevo HTTP API).

Used STRICTLY for system mail (Email Verification, Password Reset).
Never uses a user's relay.
"""

import logging
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
    Sends a system email via Brevo HTTP API.
    Returns dict with status, success, and response details.
    """
    api_key = settings.BREVO_API_KEY
    sender_email = settings.BREVO_SENDER_EMAIL or "noreply@mailorbit.io"

    if not api_key:
        logger.warning(
            "BREVO_API_KEY not configured. System transactional email to %s unavailable: %s",
            to_email,
            subject,
        )
        return {
            "success": False,
            "status": "UNAVAILABLE",
            "detail": "BREVO_API_KEY not configured; system transactional email service is unavailable.",
            "to": to_email,
        }

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
        "api-key": api_key,
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
            err_text = resp.text
            logger.error("Brevo API error (%s): %s", resp.status_code, err_text)
            return {
                "success": False,
                "status": f"BREVO_HTTP_{resp.status_code}",
                "detail": err_text,
                "to": to_email,
            }
    except Exception as exc:
        logger.error("Exception calling Brevo API for %s: %s", to_email, exc)
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "detail": str(exc),
            "to": to_email,
        }


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

