OWNER CONFIRMATIONS (edited by the owner to the truth; if NO or blank, treat as not done):
- Repo is private: YES/NO
- vd19055 app password revoked: YES/NO
- Neon password reset and DATABASE_URL updated on Render: YES/NO
- ENCRYPTION_MASTER_KEY and TICK_SECRET replaced on Render: YES/NO
- ADMIN_EMAILS = vikassdangi@gmail.com only: YES/NO
- cron-job.org sends the new tick secret in the X-Tick-Secret header: YES/NO

==================== MASTER BUILD BRIEF ====================

0. HOW TO WORK
- After every step update docs/PROGRESS.md: done, next, blockers, commit hashes,
  timestamps with timezone. If your context resets, a fresh session must be
  able to continue from MASTER_BUILD_BRIEF.md + PROGRESS.md alone.
- If a GATE is waiting on me, keep building anything that does not depend on it,
  but do not deploy past it.
- Push to main only after the local gate passes (Python 3.11.9 tests, ruff F821,
  alembic check, production-mode boot, CI green). After each push poll /api/v1/health
  until it shows the new commit hash (max 10 minutes). If it does not, stop and ask me
  for the Render log lines. Keep deploys to the minimum (free build minutes).
- One logical commit per step.

1. DECISIONS (final; log them in DECISIONS.md)
a. System mail (OTP, welcome, password changed, account deleted, security alerts):
   a platform-owned Google Apps Script relay on a dedicated MailOrbit Gmail that
   I will create. Only SYSTEM_RELAY_URL and SYSTEM_RELAY_TOKEN env vars. Remove Brevo and
   SMTP from the production system-mail path (Render blocks 587; Brevo with a Gmail
   sender fails sender checks). SMTP only in dev (Mailpit).
b. Database: Alembic only. The app applies "alembic upgrade head" at startup
   before serving. CI fails if models and migrations differ (alembic check).
   NO manual SQL against production and no write access through DB tools; read-only
   inspection only. Before the first migration on production I take a Neon branch
   snapshot (GATE: give me exact steps).
c. Admin: ONE variable, ADMIN_EMAILS (remove SUPERUSER_EMAILS), verified email
   required, aggregate counts only, never any user's content.
d. Logo: OrbitalLogo is a PLACEHOLDER, not approved. L1 stays NOT-VERIFIED
   until I approve a design.
e. Free tier only. Python 3.11.9. No Redis/Celery.
f. Signup shows "an account already exists, log in" (UX I want). Mitigate
   enumeration with per-IP and per-email rate limits; document it.

2. GUARDRAILS (never break)
- Never print, log, commit or put in a URL any secret, token, key, password or
  relay URL. Secret scan stays clean.
- No mail to addresses I do not own. Tests use plus-addresses of
  vikassdangi@gmail.com. Exception only with my explicit OK at a GATE (the
  bounce test).
- Never create accounts on production for me and never ask for my passwords.
  I sign up through the UI. When you need authenticated live checks, write a
  script I run locally that asks for logins with getpass and prints results for me
  to paste. Never ask for passwords, tokens or URLs in chat.
- Tests must refuse to run against a non-local database (keep the guard).
- No auto-verification of accounts, ever.
- Never say "deployed" or "live" without the commit hash from /health.
- Log every deviation in DECISIONS.md.

3. STATUS RULES
- Statuses: VERIFIED-LIVE, UNIT-ONLY, PARTIAL, MISSING, BROKEN, NOT-VERIFIED.
- VERIFIED-LIVE needs output from the live site on the current /health commit
  (or my confirmed acceptance result). UI items need a rendered check with
  Playwright screenshots saved in docs/evidence/ (dark and light, desktop and
  390px wide), not a search of JS bundles. A 401 on an unauthenticated call is
  not authorization proof; tenant isolation needs two real users (script I run).
- Completion percentage: VERIFIED-LIVE 1.0, UNIT-ONLY 0.5, PARTIAL 0.25, others 0.
  Print the counts and the percentage with a script. Keep the 102-item audit in
  REQUIREMENTS_AUDIT.md (75 original IDs A1..M4 plus P1..P7 and N1..N20 as in my
  earlier requirements).

4. MILESTONES

M1 PRODUCTION WORKS: DATABASE, ACCOUNTS, SYSTEM MAIL (N4-N11, N17, A3, A4)
1. Alembic revisions covering ALL current models (email_otps, users.sender_name,
   bootstrap_records, last_run_date, contact_replacements, everything else); test
   fresh DB + upgrade head equals models; compare against a read-only dump of the
   production schema; startup applies; CI alembic check.
2. scripts/mailorbit_system_relay.js (token only in Script Properties, quota
   check, idempotency key, recipient validation, never logs the token) and
   docs/SYSTEM_RELAY_SETUP.md for a non-coder: create the new Gmail, turn on
   2-step verification, deploy the script, set SYSTEM_RELAY_URL/TOKEN on Render.
   Honest errors when the relay is down or quota is exhausted; platform-wide cap
   of 90 system mails per rolling day; resend cooldowns. Never auto-verify.
3. Flows: signup (email pre-check, OTP, verify, password + confirm, workspace),
   login, forgot password (OTP), change password (OTP), delete workspace (OTP +
   typed confirmation; removes Cloudinary files too). OTP: CSPRNG 6 digits, stored
   hashed, 10 min expiry, single use, 5 attempts, resend cooldown, rate limits,
   never logged. All sessions invalidated after a password change or delete.
4. Rate limits and lockouts stored in the database so deploys do not reset them.
5. HTML + plain-text system emails with consistent branding: OTP, welcome,
   password changed, account deleted, campaign finished, security alert.
6. Admin bootstrap token (database-backed) tested.
GATE M1 (me): Neon snapshot; create the system Gmail and relay; set env vars; then you
push and verify /health.
DONE WHEN: /status shows the Alembic head; live signup, OTP mail, verify, login,
forgot password, change password and delete work with an address I name (I confirm
each mail arrived, with a checklist you write with exact clicks); 401/403/429
behaviours verified live by you.

M2 SECURITY AND AUTHORIZATION (N14, N15, J-series)
- Headers (CSP that works with the static export, HSTS, nosniff, frame-ancestors none,
  referrer and permissions policy), same-origin CORS, cookie flags, CSRF protection
  for cookie-authenticated endpoints, validation limits on every input, output
  escaping, upload magic-byte checks, per-user Cloudinary folders, audit log of
  security events, token versioning, no debug endpoints, no stack traces to users,
  pip-audit and npm audit with highs fixed, gitleaks clean, OWASP ZAP baseline
  scan against a local instance.
- Generate from OpenAPI a two-user isolation test matrix over EVERY endpoint
  (other user's IDs answer 404, no auth 401, IDOR on UUIDs, mass-assignment).
  Also script scripts/live_isolation_check.py that I run against the live site
  with two accounts I create.
DONE WHEN: matrix green locally; ZAP and audit reports in docs/evidence; my live
run of the script passes. In your report state plainly what has NOT been
independently tested.

M3 REAL RELAY PROOF (H1, H2, H3, M2, E4)
- Update the in-product relay guide (including Google's "unverified app"
  screen), per-user token rotation, "Send test mail to myself" button showing
  result, remaining quota and Message-ID.
GATE M3 (me): I set up my relay and Gemini key in the product.
DONE WHEN: real mails sent from the live service arrive in my inbox with the
Message-ID stored; real Gemini output shown, and a forced fallback.

M4 CAMPAIGN ENGINE, LIVE (P1-P7, D, G, H4-H6, H8, I1, I2, I4)
- Everything in P1..P7 as in my requirements, with screens and no demo data:
  manual or automatic batch creation, resize, move contacts, paste comma/line
  separated emails, CSV and Excel (openpyxl, 2 MB, 5000 rows), calendar plus
  Today/Tomorrow, skip dates, stop date, repeat with guardrails, water-filling
  split across sub-batches and campaigns on one sender, one-click auto-balance,
  risk modal above 30, ceiling at the relay's real quota, "Not working" folder
  per campaign with replacement trail, send next batch / by name, run lateness,
  one-off and JD sends, scheduled single mail, finish notifications, paused
  states, live dispatch feed from real events (SSE or polling).
DONE WHEN (live, using plus-addresses; minimum quota use): 10 contacts incl. one
dead domain, cap 6: balance shown, replacement trail visible, nothing sent twice;
GATE: I restart the Render service mid-batch and you prove no duplicate and
correct resume.

M5 RESUMES, TEMPLATES, AI (B1, B2, C, E, F, N18-N20)
- Onboarding wizard (profile, resumes, relay, AI key, first campaign); resume
  library with scan and template generation; roles (C2); attachments of any
  document, forwarded to the relay (download once per batch via signed
  Cloudinary URL; 5 MB per file, 20 MB and 15 files per user); prompt library
  with versions; tone studio; multi-provider keys (Gemini, OpenAI-compatible,
  Anthropic) behind one interface with usage counters; fallback flag and
  prompt version stored per mail; subject variants; spam-risk check; 3-mail
  preview and test-send; JD match with best resume; resume improvement with
  accept/reject saved as a new version; anti-invention guard with adversarial
  tests (prompt injection in resume or JD).
GATE M5 (me): Cloudinary env vars and my keys.
DONE WHEN: I upload a resume, see the scan and a template, match a JD, accept one
suggestion; a real mail with the attachment arrives intact.

M6 DELIVERABILITY AND DATA RIGHTS (H7, H10, H11, B3, B4, N8)
- Bounce reader inside the user relay script (time-triggered; posts events to
  the API with the token; matched by Message-ID): contact goes to Inactive, replacement
  and trail, shortfall topped up. Reply detection (marks Replied, stops follow-ups).
  Follow-ups (max 2, only non-replied, varied text, inside the daily cap).
  Data export (JSON/ZIP) and full delete.
GATE M6 (me): I approve sending one test mail to a made-up non-existent
address and I reply to one mail.
DONE WHEN: bounce and reply handled live, evidence shown.

M7 UI COMPLETION (N1, N2, N3, N12, N13, N16, A6, L2)
- Fixed sidebar that never scrolls with the page (internal scroll only if its
  own content overflows; "Built by Vikas Dangi" always visible); mobile drawer;
  complete Settings (profile, optional sender name, relay, AI keys, theme,
  password, sessions with revoke, export, delete, admin section for admins);
  full light and dark theme via CSS variables (audit and remove hard-coded
  colours; SVG, code blocks, scrollbars, focus rings, modals, tables, badges,
  banners); no flash on load; axe-core contrast check passing in both themes;
  tutorials never horizontally scroll; no horizontal overflow at 390px on any
  route or tab; eye icon on every password field; loading, empty and error
  states; redesigned overview.
- About page: only facts from docs/about_facts.md written by me and real links
  I give you; anything else removed. Until I approve, mark L2 NOT-VERIFIED.
GATE M7 (me): about_facts.md, logo approval.
DONE WHEN: Playwright screenshots of every screen (dark, light, 390px) and axe
results in docs/evidence; I review them.

M8 RELEASE READINESS
- PRD, TRD, DECISIONS, DEPLOYMENT and runbook updated to the code; Neon restore
  notes; cron-job.org and pinger settings documented; final regenerated audit;
  security statement.

5. REPORT FORMAT (also write it to docs/STATUS_REPORT.md)
Keep to 60 lines max: commit hash from /health, date; per-milestone status;
audit counts and percentage from the script; GATES waiting on me with exact
steps; top 5 risks; what is NOT verified. No long explanations.

==================== END OF BRIEF ====================
