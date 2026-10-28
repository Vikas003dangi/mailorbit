from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from packages.shared.schema import Contact, Profile, Purpose

logger = logging.getLogger("mailorbit.ai_personalizer")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def render_template(template: Optional[str], contact: Contact, default: str) -> str:
    """Renders placeholders in email subject and body."""
    raw = template or default
    return (
        raw.replace("{name}", contact.name or "there")
        .replace("{company}", contact.company or "your team")
        .replace("{role}", contact.role or "Hiring Team")
    )


class AIPersonalizationError(Exception):
    """Raised when AI personalization fails."""
    pass


class GeminiPersonalizer:
    """
    Lightweight, dependency-free Gemini client for generating hyper-personalized
    cold outreach email icebreakers and subject lines using user's BYOK key.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 12.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def personalize(
        self,
        contact: Contact,
        purpose: Optional[Purpose] = None,
        profile: Optional[Profile] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Calls Gemini to generate personalized subject line and email body.
        Returns a dict with 'subject' and 'body_text', or None if generation fails.
        """
        url = GEMINI_API_URL.format(model=self.model)

        sender_name = (profile.full_name if profile and profile.full_name else "Sender").strip()
        recipient_name = (contact.name or "there").strip()
        recipient_company = (contact.company or "your team").strip()
        recipient_role = (contact.role or "Hiring / Operations").strip()
        campaign_name = (purpose.name if purpose else "Cold Outreach").strip()
        subject_hint = (purpose.default_subject_template if purpose else "").strip()
        body_hint = (purpose.default_body_template if purpose else "").strip()

        # Extract matching skills if candidate profile and recipient role/notes exist
        matching_skills_str = ""
        if profile and profile.skills:
            from apps.api.services.keyword_matcher import match_profile_to_jd
            jd_sample = f"{recipient_role} {contact.company or ''} {json.dumps(contact.custom_pitch or {})}"
            match_res = match_profile_to_jd(profile_skills=profile.skills, jd_text=jd_sample)
            if match_res["matched_skills"]:
                matching_skills_str = f"- Overlapping Technical Skills to highlight: {', '.join(match_res['matched_skills'][:4])}\n"

        prompt = f"""You are an elite, concise B2B cold email copywriter.
Generate a high-converting, personalized cold outreach email from {sender_name} to {recipient_name}.

Recipient Details:
- Name: {recipient_name}
- Company: {recipient_company}
- Role / Department: {recipient_role}
{matching_skills_str}
Campaign Purpose: {campaign_name}
Subject Line Guideline: {subject_hint or "Quick question regarding " + recipient_company}
Body Template Reference:
\"\"\"
{body_hint or "Hi " + recipient_name + ", reaching out to explore opportunities at " + recipient_company + "."}
\"\"\"

Instructions:
1. Subject line: Short (3-6 words), conversational, lowercase or title case, no spam words.
2. Email Body: Keep under 120 words. Include a natural 1-sentence personalized icebreaker mentioning {recipient_company} or their {recipient_role} role. State value proposition clearly, then a frictionless low-friction call-to-action (CTA).
3. Do NOT include placeholders like '[Your Name]' or '[Link]'. Use '{sender_name}' as the sender.

Return ONLY valid JSON in this exact structure with no extra text or markdown formatting:
{{"subject": "...", "body_text": "..."}}
"""

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 350,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if resp.status_code == 429:
                logger.warning("Gemini rate limit (429) hit for contact %s. Will fallback to template.", contact.email)
                return None

            if resp.status_code != 200:
                logger.warning(
                    "Gemini API returned HTTP %s for contact %s. Will fallback to template.",
                    resp.status_code,
                    contact.email,
                )
                return None

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not raw_text:
                return None

            # Clean and parse JSON
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            subject = result.get("subject", "").strip()
            body = result.get("body_text", "").strip()

            if subject and body:
                return {"subject": subject, "body_text": body}

        except Exception as exc:
            logger.warning("Gemini personalization failed for contact %s: %s", contact.email, exc)

        return None


def generate_email_content(
    contact: Contact,
    purpose: Optional[Purpose] = None,
    profile: Optional[Profile] = None,
    personalizer: Optional[GeminiPersonalizer] = None,
) -> Tuple[str, str, bool]:
    """
    Renders email subject and body:
    1. If a GeminiPersonalizer is provided, attempts AI generation.
    2. If AI is absent or fails for any reason (quota, timeout, parse error),
       immediately and safely falls back to standard template interpolation.
    
    Returns (subject, body_text, is_ai_personalized).
    """
    # 1. Attempt AI Personalization
    if personalizer is not None:
        try:
            ai_res = personalizer.personalize(contact=contact, purpose=purpose, profile=profile)
            if ai_res and ai_res.get("subject") and ai_res.get("body_text"):
                logger.info("Successfully AI-personalized email for contact %s", contact.email)
                return ai_res["subject"], ai_res["body_text"], True
        except Exception as exc:
            logger.warning("AI personalization error, falling back to template: %s", exc)

    # 2. Template Fallback
    subject_tpl = purpose.default_subject_template if purpose else "Quick question regarding {company}"
    body_tpl = purpose.default_body_template if purpose else "Hi {name},\n\nHope this finds you well at {company}."

    fallback_subject = render_template(subject_tpl, contact, f"Introduction for {contact.name or 'there'}")
    fallback_body = render_template(body_tpl, contact, f"Hello {contact.name or 'there'},\n\nConnecting from MailOrbit.")

    return fallback_subject, fallback_body, False
