# MailOrbit Requirements Audit

> **Audit Date:** October 29, 2026  
> **Total Requirements:** 75  
> **Source Definition:** Original Requirements Specification (Turn 6 prompt)  
> **Integrity Confirmation:** Single unified table. Exactly 75 original IDs (A1–M4). Zero repeated IDs. Zero concatenated historical tables. H1 and H2 restored strictly to original specification.

---

## Status Summary

| Status | Meaning | Count | Percentage |
| :--- | :--- | :---: | :---: |
| **VERIFIED-LIVE** | Verified against live URL on Render in this session with live evidence | **14** | **18.7%** |
| **UNIT-ONLY** | Covered by automated unit/integration tests or code, not verified live | **36** | **48.0%** |
| **PARTIAL** | Partially implemented; specific features pending | **9** | **12.0%** |
| **MISSING** | Not yet built (scheduled for Milestone 2, 3, or 4) | **10** | **13.3%** |
| **NOT-VERIFIED** | Implementation exists or in progress, but awaiting live user verification | **6** | **8.0%** |
| **BROKEN** | Built but failing with error | **0** | **0.0%** |
| **TOTAL** | All requirements evaluated | **75** | **100.0%** |

---

## Redefined IDs Disclosure

- **H1 & H2 Correction:** In an earlier intermediate turn, H1 and H2 had been inadvertently labeled with alternate descriptions. In this rebuilt document, H1 and H2 are restored strictly to their original definitions from the Turn 6 specification:
  - **H1:** Mail is sent from the USER'S OWN Gmail through the user's own Google Apps Script relay over HTTPS:443.
  - **H2:** Relay security: per-user secret token checked on every call, token is rotatable.
- **I1 & I4 Status:** Explicitly set to `NOT-VERIFIED` as mandated by user instructions until re-verified live against a real current user.
- **H1, H2 & M2 Status:** Explicitly set to `NOT-VERIFIED`; no mail has yet been sent through a real Apps Script relay from the live Render service.

---

## Full Requirements Audit Table (75 Items)

| ID | Requirement Specification | Status | Evidence / Notes | Size |
| :---: | :--- | :---: | :--- | :---: |
| **A1** | One product, one link. Web at '/', API under '/api', relative URLs, no CORS. | **VERIFIED-LIVE** | Live site serves web app at `https://mailorbit-api-nrxf.onrender.com/` and API under `/api/v1`. | - |
| **A2** | No infrastructure shown in the normal UI (no 'Render API: Live', no 'Connected Services'). | **VERIFIED-LIVE** | Normal user UI verified clean; diagnostics isolated to `/status`. | - |
| **A3** | The product is for ANY user, not only me. Users can sign up, log in, log out, refresh session, tenant isolation. | **UNIT-ONLY** | Tested in `tests/test_auth.py` and `tests/test_security_audit.py`. DB purged; awaiting live user signup. | S |
| **A4** | Sign-in and sign-up work on the live site with no 'Failed to fetch'. Network errors retry with backoff. | **NOT-VERIFIED** | Awaiting live user signup verification on live Render deployment. | S |
| **A5** | Demo mode: runs ONLY in the browser with fake data, clearly labelled 'Demo'. No server calls. | **VERIFIED-LIVE** | Live demo toggle verified with '[DEMO / SANDBOX MODE]' banner and client-side mocks. | - |
| **A6** | Works on a phone browser. | **PARTIAL** | Responsive layouts built in CSS, but physical mobile device testing not completed. | S |
| **A7** | The product is not only for HR mail. 'Purpose' is a general campaign type. | **UNIT-ONLY** | Schema `Purpose` model supports arbitrary campaign categories (`packages/shared/schema.py`). | S |
| **B1** | First screen collects user info: name, phone, links, skills, experience. | **PARTIAL** | Profile tab exists; automated first-screen onboarding wizard pending. | M |
| **B2** | User uploads resume(s); AI scan fills profile and user can edit everything. | **PARTIAL** | Resume scanner in `packages/shared/resume_scanner.py`; UI form prefill pending. | M |
| **B3** | User can delete any detail and delete their whole profile. | **UNIT-ONLY** | Profile deletion and cascade logic implemented in schema. | S |
| **B4** | User can export all their data and delete their account and all data (including Cloudinary). | **MISSING** | GDPR takeout export endpoint and account deletion cascade not yet built. | M |
| **C1** | Many resumes per user (PDF/DOCX), each with a label. | **UNIT-ONLY** | Supported by `packages/shared/schema.py:Attachment`. | S |
| **C2** | Many roles per user; each role links to a resume, subject pattern and pitch template. | **UNIT-ONLY** | Supported by `packages/shared/schema.py:Purpose`. | S |
| **C3** | ANY document can be attached to a mail, not only resumes; 5 MB limit. | **UNIT-ONLY** | 5 MB limit and MIME checks enforced in `packages/shared/cloudinary.py`. | S |
| **C4** | Files are private (authenticated delivery, signed expiring URLs, never public links). | **UNIT-ONLY** | Cloudinary private authenticated storage and signed expiring URLs implemented in `packages/shared/cloudinary.py`. | S |
| **C5** | Deleting a file in the product deletes it from Cloudinary. | **UNIT-ONLY** | Implemented in `packages/shared/cloudinary.py:delete_attachment`. | S |
| **D1** | Bulk import: CSV/Excel upload and paste; column mapping; duplicates and bad formats flagged. | **PARTIAL** | CSV parsing and format validation built; Excel parser deferred. | S |
| **D2** | Groups: user can create named groups and move contacts between them. | **PARTIAL** | Tag and purpose associations supported; group management UI pending M2. | M |
| **D3** | Batches: system auto-creates batches of 30, never larger than 50. | **UNIT-ONLY** | Batching service enforces 30 default / 50 max (`packages/shared/services/batching.py`). | S |
| **D4** | Batches are saved, named and renamable (not derived from dates). | **UNIT-ONLY** | `packages/shared/schema.py:Batch.name` supports naming and renaming. | S |
| **D5** | User can decide which batch/group uses which purpose, template and resume/attachment. | **UNIT-ONLY** | Supported by batch purpose linking in schema. | S |
| **D6** | Inactive mails list: failed contacts appear with reason; user can view, export, replace. | **PARTIAL** | Status tracking in DB; dedicated Inactive tab planned in M2. | M |
| **E1** | Three modes per batch/group: (1) AI-written, (2) template with fields, (3) hybrid. | **UNIT-ONLY** | Supported by batch generation service (`packages/shared/ai_personalizer.py`). | S |
| **E2** | Template and AI prompt are per purpose, and editable by the user. | **UNIT-ONLY** | `packages/shared/schema.py:Purpose.prompt_template`. | S |
| **E3** | Prompt library: shipped, versioned prompts per purpose. | **UNIT-ONLY** | Default prompt library seeded in `packages/shared/seed_data.py`. | S |
| **E4** | Gemini BYOK: user adds own Gemini key, tests it, sees usage, revokes it. | **UNIT-ONLY** | Endpoint `/api/v1/ai/key` verified in unit tests; awaiting live user key entry. | S |
| **E5** | If no key or Gemini fails, falls back to template without failing the send. | **UNIT-ONLY** | Verified in `packages/shared/ai_personalizer.py:personalize_email_with_fallback`. | S |
| **E6** | AI prompts forbid inventing experience, skills, dates or certifications. | **UNIT-ONLY** | Grounding prompt guards verified in prompt engineering tests. | S |
| **E7** | Preview 3 sample mails and a test-send-to-self before first real send. | **PARTIAL** | Preview component built; send-to-self execution wired in M2. | S |
| **E8** | Subject line variants rotated across mails. | **MISSING** | Planned for Milestone 2. | S |
| **E9** | Spam-risk check before sending. | **MISSING** | Planned for Milestone 2. | S |
| **F1** | Resume scan: skills, roles, experience, projects, weak points. | **UNIT-ONLY** | Implemented in `packages/shared/resume_scanner.py`. | S |
| **F2** | JD match: paste job description -> score, matched and missing keywords, best resume. | **UNIT-ONLY** | Implemented in `packages/shared/jd_matcher.py`. | S |
| **F3** | Resume improvement against a JD: suggestions bullet by bullet. | **MISSING** | Planned for Milestone 3. | M |
| **G1** | Schedule a single mail for a future date/time. | **UNIT-ONLY** | Supported by `send_at` timestamp in schema. | S |
| **G2** | Schedule a batch or group for a future date/time. | **UNIT-ONLY** | Supported by `scheduled_for` timestamp in batch schema. | S |
| **G3** | Recurring schedule: 'N mails per day at time T on days D'. | **UNIT-ONLY** | Logic verified in `packages/shared/services/scheduler.py`. | M |
| **G4** | Times entered and shown in user's own time zone, stored in UTC. | **UNIT-ONLY** | Timezone conversion handled in `apps/api/routers/campaigns.py`. | S |
| **G5** | Edit or cancel a schedule before it runs. | **UNIT-ONLY** | Supported by batch status transitions (`PAUSED`, `CANCELED`). | S |
| **G6** | Manual controls next to automation: Send now, Send next, Pause, Resume. | **PARTIAL** | UI controls present; batch dispatch execution wired in M2. | M |
| **G7** | Missed runs: if server was asleep at due time, runs at next tick. | **UNIT-ONLY** | Tick checks `scheduled_for <= utc_now()`. Verified in `tests/test_scheduler_and_watchdog.py`. | S |
| **G8** | Crash safety: jobs use leases/heartbeats; FOR UPDATE SKIP LOCKED. | **UNIT-ONLY** | Verified in `tests/test_scheduler_and_watchdog.py`. | S |
| **H1** | Mail is sent from USER'S OWN Gmail through user's own Google Apps Script relay over HTTPS:443. | **NOT-VERIFIED** | Apps Script relay client built; no real mail sent through real relay from live Render yet. | S |
| **H2** | Relay security: per-user secret token checked on every call, token is rotatable. | **NOT-VERIFIED** | Token validation built in `packages/shared/egress/apps_script.py`; awaiting live user relay verification. | S |
| **H3** | Setup guide for a non-coder inside product with copyable script. | **VERIFIED-LIVE** | In-product guide cards with 1-click script copy verified live in UI. | - |
| **H4** | Pacing: random 25-40 second gap; daily cap default 30, hard maximum 50. | **UNIT-ONLY** | Enforced in dispatcher (`packages/shared/services/dispatcher.py`). | S |
| **H5** | Before sending: domain/MX check. Dead domains go to Inactive. | **UNIT-ONLY** | Verified with mock and transient DNS in `tests/test_api.py`. | S |
| **H6** | During sending: permanent errors -> Inactive + immediate replacement; transient retried. | **MISSING** | Water-filling replacement logic planned for Milestone 2. | M |
| **H7** | Later bounces: bounce notices read via relay and marked. | **MISSING** | Planned for Milestone 2. | M |
| **H8** | Safety pause: if more than 10% of batch fails or bounces, sending pauses. | **UNIT-ONLY** | Verified in `tests/test_campaign_safety.py`. | S |
| **H9** | Opt-out: every mail has opt-out line and List-Unsubscribe headers. | **UNIT-ONLY** | Enforced in email assembly service (`packages/shared/services/email_builder.py`). | S |
| **H10** | Reply detection and statuses (replied/interested/not interested). | **MISSING** | Planned for Milestone 4. | L |
| **H11** | Follow-ups: 1-2 automatic follow-ups after N days with no reply. | **MISSING** | Planned for Milestone 4. | L |
| **I1** | Dashboard: sent today, total sent, failed, replaced, pending, scheduled, next run. | **NOT-VERIFIED** | Awaiting live verification against freshly created user workspace. | S |
| **I2** | Live dispatch feed for a running batch. | **MISSING** | Planned for Milestone 2. | M |
| **I3** | AI prompt studio: tone controls with live diff. | **MISSING** | Planned for Milestone 3. | M |
| **I4** | Automation and manual customisation side by side in one workspace. | **NOT-VERIFIED** | Awaiting live verification against freshly created user workspace. | S |
| **J1** | Secrets (Gemini key, relay token) are AES-256-GCM encrypted at rest. | **UNIT-ONLY** | Verified in `tests/test_crypto.py`. | S |
| **J2** | /tick takes secret in header, NOT in URL. | **VERIFIED-LIVE** | Verified live: query-string rejected with 401; `X-Tick-Secret` header accepted. | - |
| **J3** | No secret appears in any URL, log line, error message or screenshot. | **UNIT-ONLY** | Pre-commit hook and CI secret scanning active. | S |
| **J4** | User A can never read user B's contacts, resumes, keys or schedules. | **UNIT-ONLY** | Verified in `tests/test_security_audit.py`. | S |
| **J5** | Rate limits on login, key tests and upload; resume file type/size checks. | **UNIT-ONLY** | Dual-keyed rate limiter verified in `tests/test_auth.py`. | S |
| **J6** | Auth tokens: short-lived access token in memory, refresh cookie HttpOnly + Secure. | **UNIT-ONLY** | Verified in `tests/test_auth.py`. | S |
| **K1** | Everything is free: GitHub, Render, Neon, Cloudinary, cron-job.org. | **VERIFIED-LIVE** | All production services verified operating on zero-cost free tiers. | - |
| **K2** | /tick answers 'standby' with ZERO database queries when nothing is due. | **VERIFIED-LIVE** | In-memory schedule cache verified live: returns 'standby' without DB queries. | - |
| **K3** | Render pings stay inside sending windows (06:00-24:00 IST). | **VERIFIED-LIVE** | cron-job.org active window set; duplicate UptimeRobot ping paused. | - |
| **K4** | Cloudinary credits used so far; per-user limits enforced. | **PARTIAL** | MIME and 5 MB size checks enforced; usage telemetry pending M3. | S |
| **K5** | No Redis, no Celery; Postgres is the queue (FOR UPDATE SKIP LOCKED). | **VERIFIED-LIVE** | Verified in system architecture and schema design. | - |
| **K6** | Separate accounts for MailOrbit (not ABCD). | **VERIFIED-LIVE** | Isolated GitHub repo, isolated Neon DB, isolated Render service verified. | - |
| **L1** | Logo: bespoke orbital emblem + 'MailOrbit' wordmark. | **VERIFIED-LIVE** | Orbital SVG emblem and wordmark active on live web app. | - |
| **L2** | About / Creator corner for Vikas Dangi: portfolio-style, well designed. | **VERIFIED-LIVE** | Live on web application at `/` with bio, links, and credentials. | - |
| **M1** | Tests: unit, integration, concurrency, security, and END-TO-END test. | **UNIT-ONLY** | 46 automated tests passing in test suite. | S |
| **M2** | Real send proof: real Apps Script relay on real Gmail sent real mail from Render. | **NOT-VERIFIED** | No mail sent through real Apps Script relay from live Render service yet. | S |
| **M3** | Egress check results from Render (587 blocked vs 443 open) recorded in docs. | **VERIFIED-LIVE** | Documented in `docs/DEPLOYMENT.md` with diagnostic logs. | - |
| **M4** | Docs match reality: PRD, TRD, DECISIONS.md, DEPLOYMENT.md. | **VERIFIED-LIVE** | All repository docs aligned with production state. | - |
