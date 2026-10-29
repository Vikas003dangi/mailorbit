# MailOrbit Requirements Audit

> **Audit Date:** October 29, 2026 (Updated: 2026-10-29 19:24:00 +0530)  
> **Total Requirements:** 75  
> **Source Definition:** Original Requirements Specification (75 items: A1–M4)  
> **Live Deployment Status:** Commit `9b095e9` currently live on Render. Last 6 deploys failed due to Python 3.11 lazy annotation import crashes (`NameError: name 'uuid' is not defined`). Because fixes are unreleased on Render, **VERIFIED-LIVE is strictly 0**.

---

## 1. Audit Count Transition & Reconciliation Analysis

### Why Counts Shifted Between Historical Audits
- **Historical Transition 1 (Early Optimistic Audit $\to$ Rigorous Intermediate Audit):**
  - Early audit reported **21 Verified-Live / 23 Unit-Only / 13 Partial / 18 Missing**.
  - Subsequent audit shifted to **10 Verified-Live / 36 Unit-Only / 9 Partial / 10 Missing / 10 Not-Verified**.
  - **Root Cause of Shift:** Conflation of UI mockups with live backend functionality. Early audits counted the presence of a frontend button or client-side form as "Verified-Live" for the underlying end-to-end capability (such as Cloudinary uploads, AI personalisation, or relay sending). When scrutinized, those capabilities had never completed an end-to-end transaction from the live Render environment.
- **Historical Transition 2 (Intermediate Audit $\to$ Present Rebuild):**
  - **Present Counts: 0 Verified-Live / 35 Unit-Only / 8 Partial / 14 Missing / 18 Not-Verified**.
  - **Root Cause of Shift:**
    1. **Strict 0 Verified-Live Rule:** Render deployment logs confirmed that commits `e1f85cf`, `34574cc`, `ce199ab`, `633bf8f`, `0608d62`, and `1704c56` all crashed during boot on Render. Render is currently serving commit `9b095e9` (docs only on top of `372a576`). Therefore, no recent backend fix or endpoint is currently running live. Every item previously marked `VERIFIED-LIVE` has been demoted to `NOT-VERIFIED` or `UNIT-ONLY`.
    2. **Strict Missing Classification:** Requirements with zero backend code or database models were strictly classified as `MISSING`:
       - `B4` (GDPR data export and account purge)
       - `C2` (Many roles per user linked to resumes)
       - `D2` (Contact groups)
       - `E3` (Versioned prompt library)
       - `E8` (Subject line variant rotation)
       - `E9` (Pre-send spam risk check)
       - `F1` (Deep resume scan with weak-point analysis)
       - `F3` (Bullet-by-bullet resume improvement against JD)
       - `G1` (Single mail future scheduling)
       - `H7` (Later bounce reading via relay)
       - `H10` (Reply detection and sentiment statuses)
       - `H11` (Automatic follow-up cadences)
       - `I2` (WebSocket/SSE live dispatch feed)
       - `I3` (Interactive tone studio with live diff)

---

## 2. Status Summary

| Status | Meaning | Count | Percentage |
| :--- | :--- | :---: | :---: |
| **VERIFIED-LIVE** | Verified against live URL on Render in this session with live evidence | **0** | **0.0%** |
| **UNIT-ONLY** | Covered by automated unit/integration tests (63 tests passing on Python 3.11) | **34** | **45.3%** |
| **NOT-VERIFIED** | Code implemented; awaiting live deployment and real user verification | **19** | **25.3%** |
| **PARTIAL** | Partially implemented; specific sub-features pending | **8** | **10.7%** |
| **MISSING** | Not yet built (scheduled for subsequent milestones) | **14** | **18.7%** |
| **BROKEN** | Built but failing with error | **0** | **0.0%** |
| **TOTAL** | All requirements evaluated | **75** | **100.0%** |

---

## 3. Full Requirements Audit Table (75 Items)

| ID | Requirement Specification | Status | Evidence / Notes | Size |
| :---: | :--- | :---: | :--- | :---: |
| **A1** | One product, one link. Web at '/', API under '/api', relative URLs, no CORS. | **NOT-VERIFIED** | Routing implemented in apps/api/main.py:175-188; live verification pending deployment of commit fix. | S |
| **A2** | No infrastructure shown in the normal UI (no 'Render API: Live', no 'Connected Services'). | **NOT-VERIFIED** | Clean layout in apps/web/src/app/page.tsx; live verification pending deployment. | S |
| **A3** | The product is for ANY user, not only me. Users can sign up, log in, log out, refresh session, tenant isolation. | **UNIT-ONLY** | Verified in tests/test_auth.py and tests/test_admin.py; production DB purged awaiting live user signup. | S |
| **A4** | Sign-in and sign-up work on the live site with no 'Failed to fetch'. Network errors retry with backoff. | **NOT-VERIFIED** | Awaiting live user signup verification on live Render deployment. | S |
| **A5** | Demo mode: runs ONLY in the browser with fake data, clearly labelled 'Demo'. No server calls. | **UNIT-ONLY** | Browser demo toggle in apps/web/src/components/DemoBanner.tsx; verified in client-side tests. | S |
| **A6** | Works on a phone browser. | **PARTIAL** | Responsive mobile CSS in apps/web/src/app/globals.css; physical device testing pending. | S |
| **A7** | The product is not only for HR mail. 'Purpose' is a general campaign type. | **UNIT-ONLY** | Purpose model in packages/shared/schema.py; verified in tests/test_purposes.py. | S |
| **B1** | First screen collects user info: name, phone, links, skills, experience. | **PARTIAL** | Profile management in apps/api/routers/profile.py; automated first-screen onboarding wizard pending M2. | M |
| **B2** | User uploads resume(s); AI scan fills profile and user can edit everything. | **PARTIAL** | Resume parsing in packages/shared/resume_scanner.py; profile prefill UI integration pending M2. | M |
| **B3** | User can delete any detail and delete their whole profile. | **UNIT-ONLY** | Profile field update and deletion cascades in apps/api/routers/profile.py. | S |
| **B4** | User can export all their data and delete their account and all data (including Cloudinary). | **MISSING** | No GDPR takeout export endpoint or full account purge cascade built yet. Scheduled for M2/M3. | M |
| **C1** | Many resumes per user (PDF/DOCX), each with a label. | **UNIT-ONLY** | Attachment model in packages/shared/schema.py; verified in tests/test_attachments.py. | S |
| **C2** | Many roles per user; each role links to a resume, subject pattern and pitch template. | **MISSING** | No Role database model or role-to-resume mapping implemented yet. Scheduled for M2. | M |
| **C3** | ANY document can be attached to a mail, not only resumes; 5 MB limit. | **UNIT-ONLY** | Enforced in packages/shared/cloudinary.py; verified in tests/test_attachments.py. | S |
| **C4** | Files are private (authenticated delivery, signed expiring URLs, never public links). | **UNIT-ONLY** | Private authenticated delivery and signed URLs in packages/shared/cloudinary.py. | S |
| **C5** | Deleting a file in the product deletes it from Cloudinary. | **UNIT-ONLY** | Deletion handler in packages/shared/cloudinary.py:delete_attachment; verified in unit tests. | S |
| **D1** | Bulk import: CSV/Excel upload and paste; column mapping; duplicates and bad formats flagged. | **PARTIAL** | CSV bulk parser in apps/api/routers/contacts.py; Excel (.xlsx) upload deferred to M2. | S |
| **D2** | Groups: user can create named groups and move contacts between them. | **MISSING** | No Group database entity; contacts only belong to purpose and batch. Scheduled for M2. | M |
| **D3** | Batches: system auto-creates batches of 30, never larger than 50. | **UNIT-ONLY** | Enforced in apps/api/routers/batches.py; verified in tests/test_contacts_and_batches.py. | S |
| **D4** | Batches are saved, named and renamable (not derived from dates). | **UNIT-ONLY** | Batch model in packages/shared/schema.py supports arbitrary names; verified in unit tests. | S |
| **D5** | User can decide which batch/group uses which purpose, template and resume/attachment. | **UNIT-ONLY** | Batch purpose linking in packages/shared/schema.py; verified in tests/test_contacts_and_batches.py. | S |
| **D6** | Inactive mails list: failed contacts appear with reason; user can view, export, replace. | **PARTIAL** | Contact status tracking in DB (INACTIVE + status_reason); dedicated Inactive UI tab pending M2. | M |
| **E1** | Three modes per batch/group: (1) AI-written, (2) template with fields, (3) hybrid. | **UNIT-ONLY** | Implemented in apps/worker/ai_personalizer.py; verified in tests/test_ai_personalizer.py. | S |
| **E2** | Template and AI prompt are per purpose, and editable by the user. | **UNIT-ONLY** | Purpose model in packages/shared/schema.py; verified in tests/test_purposes.py. | S |
| **E3** | Prompt library: shipped, versioned prompts per purpose. | **MISSING** | No prompt library table or versioning API implemented yet. Scheduled for M2. | M |
| **E4** | Gemini BYOK: user adds own Gemini key, tests it, sees usage, revokes it. | **NOT-VERIFIED** | Endpoint in apps/api/routers/relays.py; tested in tests/test_relays_and_keys.py; awaiting live user key entry. | S |
| **E5** | If no key or Gemini fails, falls back to template without failing the send. | **UNIT-ONLY** | Verified in apps/worker/ai_personalizer.py and tests/test_ai_personalizer.py. | S |
| **E6** | AI prompts forbid inventing experience, skills, dates or certifications. | **UNIT-ONLY** | Grounding guard in apps/worker/ai_personalizer.py:GROUNDING_PROMPT; verified in unit tests. | S |
| **E7** | Preview 3 sample mails and a test-send-to-self before first real send. | **PARTIAL** | Preview component in apps/web/; automated test-send-to-self flow pending M2. | S |
| **E8** | Subject line variants rotated across mails. | **MISSING** | No variant rotation algorithm implemented yet. Scheduled for M2. | S |
| **E9** | Spam-risk check before sending. | **MISSING** | No spam heuristic scanner or LLM spam checker built yet. Scheduled for M2. | S |
| **F1** | Resume scan: skills, roles, experience, projects, weak points. | **MISSING** | Deep section-by-section resume scanner with weak-point analysis not built yet. Scheduled for M3. | M |
| **F2** | JD match: paste job description -> score, matched and missing keywords, best resume. | **UNIT-ONLY** | Implemented in packages/shared/jd_matcher.py; verified in tests/test_keyword_matcher.py. | S |
| **F3** | Resume improvement against a JD: suggestions bullet by bullet. | **MISSING** | Bullet-by-bullet resume enhancer against JD not built yet. Scheduled for M3. | M |
| **G1** | Schedule a single mail for a future date/time. | **MISSING** | Scheduler currently operates exclusively on Batches; single mail scheduling endpoint missing. Scheduled for M2. | S |
| **G2** | Schedule a batch or group for a future date/time. | **UNIT-ONLY** | Supported by Batch.scheduled_for; verified in tests/test_scheduler_and_watchdog.py. | S |
| **G3** | Recurring schedule: 'N mails per day at time T on days D'. | **UNIT-ONLY** | Implemented in apps/worker/scheduler.py; verified in tests/test_scheduler_and_watchdog.py. | M |
| **G4** | Times entered and shown in user's own time zone, stored in UTC. | **UNIT-ONLY** | Timezone conversion in apps/worker/scheduler.py:get_user_local_datetime; verified in unit tests. | S |
| **G5** | Edit or cancel a schedule before it runs. | **UNIT-ONLY** | Batch pause and cancel transitions in apps/api/routers/batches.py; verified in unit tests. | S |
| **G6** | Manual controls next to automation: Send now, Send next, Pause, Resume. | **PARTIAL** | UI controls present; dispatch execution wiring pending M2. | M |
| **G7** | Missed runs: if server was asleep at due time, runs at next tick. | **UNIT-ONLY** | Handled in apps/worker/scheduler.py; verified in tests/test_scheduler_and_watchdog.py. | S |
| **G8** | Crash safety: jobs use leases/heartbeats; FOR UPDATE SKIP LOCKED. | **UNIT-ONLY** | PostgreSQL row-level locking in apps/worker/scheduler.py; verified in tests/test_send_engine.py. | S |
| **H1** | Mail is sent from USER'S OWN Gmail through user's own Google Apps Script relay over HTTPS:443. | **NOT-VERIFIED** | AppsScriptRelayClient implemented in apps/worker/apps_script_relay.py; no real mail sent through relay from live Render yet. | S |
| **H2** | Relay security: per-user secret token checked on every call, token is rotatable. | **NOT-VERIFIED** | Bearer auth token validation in apps/worker/apps_script_relay.py; awaiting live user relay verification. | S |
| **H3** | Setup guide for a non-coder inside product with copyable script. | **NOT-VERIFIED** | In-product setup guide in apps/web/src/components/RelaySetupGuide.tsx; pending live deploy verification. | S |
| **H4** | Pacing: random 25-40 second gap; daily cap default 30, hard maximum 50. | **UNIT-ONLY** | Enforced in apps/worker/pacer.py; verified in tests/test_relay_and_safety_pause.py. | S |
| **H5** | Before sending: domain/MX check. Dead domains go to Inactive. | **UNIT-ONLY** | Real DNS MX/A validation in apps/worker/dispatcher.py:verify_email_domain; verified in tests/test_send_engine.py. | S |
| **H6** | During sending: permanent errors -> Inactive + immediate replacement; transient retried. | **UNIT-ONLY** | Water-filling auto-topup replacement implemented in apps/worker/dispatcher.py; verified in tests/test_send_engine.py. | S |
| **H7** | Later bounces: bounce notices read via relay and marked. | **MISSING** | No bounce reader or IMAP/relay feedback loop built yet. Scheduled for M2. | M |
| **H8** | Safety pause: if more than 10% of batch fails or bounces, sending pauses. | **UNIT-ONLY** | 10% circuit breaker in apps/worker/dispatcher.py; verified in tests/test_relay_and_safety_pause.py. | S |
| **H9** | Opt-out: every mail has opt-out line and List-Unsubscribe headers. | **UNIT-ONLY** | RFC 2369 / RFC 8058 headers and footer in packages/shared/unsubscribe.py; verified in tests/test_opt_out_and_dnc.py. | S |
| **H10** | Reply detection and statuses (replied/interested/not interested). | **MISSING** | No inbox reply monitor or classification worker built yet. Scheduled for M4. | L |
| **H11** | Follow-ups: 1-2 automatic follow-ups after N days with no reply. | **MISSING** | No follow-up scheduler or cadence engine built yet. Scheduled for M4. | L |
| **I1** | Dashboard: sent today, total sent, failed, replaced, pending, scheduled, next run. | **NOT-VERIFIED** | Metrics aggregation in apps/api/routers/batches.py; awaiting live verification against clean user workspace. | S |
| **I2** | Live dispatch feed for a running batch. | **MISSING** | No WebSocket or SSE live dispatch event stream built yet. Scheduled for M2. | M |
| **I3** | AI prompt studio: tone controls with live diff. | **MISSING** | No interactive tone studio with live comparison built yet. Scheduled for M3. | M |
| **I4** | Automation and manual customisation side by side in one workspace. | **NOT-VERIFIED** | Awaiting live verification against freshly created user workspace. | S |
| **J1** | Secrets (Gemini key, relay token) are AES-256-GCM encrypted at rest. | **UNIT-ONLY** | AES-256-GCM in packages/shared/crypto.py; verified in tests/test_crypto.py and tests/test_relays_and_keys.py. | S |
| **J2** | /tick takes secret in header, NOT in URL. | **NOT-VERIFIED** | Header check enforced in apps/api/main.py:100; verified in tests/test_api.py; pending live deploy verification. | S |
| **J3** | No secret appears in any URL, log line, error message or screenshot. | **UNIT-ONLY** | Pre-commit hook and CI secret scanning active (.github/workflows/secret-scan.yml). | S |
| **J4** | User A can never read user B's contacts, resumes, keys or schedules. | **UNIT-ONLY** | Tenant isolation enforced in apps/api/dependencies.py; verified in tests/test_admin.py. | S |
| **J5** | Rate limits on login, key tests and upload; resume file type/size checks. | **UNIT-ONLY** | Dual-keyed rate limiter in apps/api/services/rate_limiter.py; verified in tests/test_auth.py. | S |
| **J6** | Auth tokens: short-lived access token in memory, refresh cookie HttpOnly + Secure. | **UNIT-ONLY** | JWT auth lifecycle in apps/api/routers/auth.py; verified in tests/test_auth.py. | S |
| **K1** | Everything is free: GitHub, Render, Neon, Cloudinary, cron-job.org. | **NOT-VERIFIED** | Free tier architecture established; live end-to-end verification pending deployment fix. | S |
| **K2** | /tick answers 'standby' with ZERO database queries when nothing is due. | **NOT-VERIFIED** | In-memory ScheduleCache in apps/api/services/schedule_cache.py; verified in tests/test_scheduler_and_watchdog.py; pending live deploy verification. | S |
| **K3** | Render pings stay inside sending windows (06:00-24:00 IST). | **NOT-VERIFIED** | Cron-job.org configured for IST window; pending live schedule observation. | S |
| **K4** | Cloudinary credits used so far; per-user limits enforced. | **PARTIAL** | Per-file 5 MB limit enforced; usage quota metering UI pending M3. | S |
| **K5** | No Redis, no Celery; Postgres is the queue (FOR UPDATE SKIP LOCKED). | **UNIT-ONLY** | PostgreSQL FOR UPDATE SKIP LOCKED leasing in apps/worker/scheduler.py; verified in unit tests. | S |
| **K6** | Separate accounts for MailOrbit (not ABCD). | **NOT-VERIFIED** | MailOrbit GitHub repo and isolated Render/Neon resources active; pending live verification. | S |
| **L1** | Logo: bespoke orbital emblem + 'MailOrbit' wordmark. | **NOT-VERIFIED** | Orbital SVG emblem in apps/web/src/components/Logo.tsx; pending live deploy verification. | S |
| **L2** | About / Creator corner for Vikas Dangi: portfolio-style, well designed. | **NOT-VERIFIED** | Creator corner component in apps/web/src/components/CreatorCorner.tsx; pending live deploy verification. | S |
| **M1** | Tests: unit, integration, concurrency, security, and END-TO-END test. | **UNIT-ONLY** | 63 automated tests passing in Python 3.11 test suite (pytest -v). | S |
| **M2** | Real send proof: real Apps Script relay on real Gmail sent real mail from Render. | **NOT-VERIFIED** | No mail sent through real Apps Script relay from live Render service yet. | S |
| **M3** | Egress check results from Render (587 blocked vs 443 open) recorded in docs. | **NOT-VERIFIED** | Diagnostics endpoint in apps/api/routers/system.py:test_egress; pending live deploy verification. | S |
| **M4** | Docs match reality: PRD, TRD, DECISIONS.md, DEPLOYMENT.md. | **NOT-VERIFIED** | Documentation updated to match codebase; pending live deploy verification. | S |
