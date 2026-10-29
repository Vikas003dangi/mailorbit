with open('B:/mailorbit/docs/M2_CAMPAIGN_ENGINE_DESIGN.md', 'r', encoding='utf-8') as f:
    text = f.read()

appendix = """
---

### System Mail Egress & Zero Auto-Verification Invariant (Design-Only Specification)

#### Dedicated System Mailer Infrastructure
1. **Platform Isolation**: System emails (Account Verification, Password Reset Tokens) are dispatched exclusively via a dedicated platform sender (Brevo HTTP API free tier or dedicated platform-owned Google Apps Script relay). A user's personal egress relay is **NEVER** touched for platform system mail.
2. **Dedicated Account**: The platform relay operates on a dedicated administrative mailbox (e.g. `noreply@mailorbit.io` or dedicated platform Google Workspace identity) with separate quotas and independent monitoring.

#### Zero Auto-Verification Rule
1. **Strict Invariant**: No grace period, no quota-exhausted bypass, and no simulated delivery is ever permitted to auto-verify an account.
2. **Service Downtime Behavior**: When the system transactional mailer is unavailable, missing API keys, or over quota:
   - User signup completes, but the account remains strictly `is_email_verified = False` (UNVERIFIED) with restricted workspace access.
   - The UI displays: *"Email verification is temporarily unavailable. Account registered in unverified mode with limited access."*
   - Sending campaigns requires a verified email address; batches will not dispatch without email verification.
3. **Admin Privilege Lock**:
   - Access to `/api/v1/admin/*` strictly requires `user.email in settings.ADMIN_EMAILS` **AND** `user.is_email_verified == True`.
   - Being listed in `ADMIN_EMAILS` alone grants **ZERO** admin access if the email is unverified.
4. **Emergency Admin Bootstrap**:
   - While system transactional mail is offline, the designated superuser can elevate and verify their account using a one-time secret bootstrap token passed via Render environment variable `ADMIN_BOOTSTRAP_TOKEN`.
   - The token is submitted to `POST /api/v1/auth/bootstrap-admin`. Upon successful verification, the token is consumed and erased in memory immediately, rendering it single-use.

---

**END OF REVISED SPECIFICATION - STOPPED AND WAITING FOR USER APPROVAL BEFORE COMMENCING M2a CODE**
"""

idx = text.rfind('---')
new_text = text[:idx] + appendix.strip() + "\n"
with open('B:/mailorbit/docs/M2_CAMPAIGN_ENGINE_DESIGN.md', 'w', encoding='utf-8') as f:
    f.write(new_text)
print('Successfully updated M2 design document.')

