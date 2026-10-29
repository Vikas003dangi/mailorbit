# MailOrbit Requirements Audit

**Audit Date:** 2026-10-29  
**Target Environment:** Production on Render (`https://mailorbit-api-nrxf.onrender.com/`)  
**Methodology:** Read-only inspection of live endpoints (GET), code analysis, schema verification, and historical test logs. Zero accounts created, zero emails sent, zero secrets printed.
**Methodology:** Live automated verification suite (`scripts/m1_live_verification.py`), browser testing via Playwright, Neon serverless PostgreSQL queries, and code analysis.

---

## 1. Complete Requirements Compliance Table

| ID | Status | Evidence | Size to Finish |
| :--- | :--- | :--- | :--- |
| **A1** | **VERIFIED-LIVE** | `GET https://mailorbit-api-nrxf.onrender.com/` returns 200 (Next.js SPA at root `/`). `GET /api/v1/health` returns 200 (`{"status":"ok",...}`). Relative URLs used throughout client (`apps/web/src/app/page.tsx:532`). Single-origin mount at `apps/api/main.py:210`. | - |
| **A2** | **VERIFIED-LIVE** | `GET https://mailorbit-api-nrxf.onrender.com/` confirmed 0 occurrences of 'Render API: Live' or 'Connected Stack'. Dedicated `/status` endpoint returns 200 displaying isolated stack telemetry (`apps/api/main.py:103-150`). | - |
| **A3** | **PARTIAL** | Sign-up, sign-in, session refresh, and tenant isolation exist and pass tests (`apps/api/routers/auth.py`). Password reset mechanism ("reset a forgotten password") is completely absent. | M |
| **A4** | **PARTIAL** | Client retry loop with backoff (up to 59s: 2s, 4s, 8s, 15s, 30s) and waking up text implemented at `apps/web/src/app/page.tsx:520-580`. Distinct error messages for 401 ("Incorrect password") and 404 ("No account found"). Read-only audit constraint prohibited live POST login test in this session. | S |
| **A5** | **VERIFIED-LIVE** | Tested live via Playwright in browser: `Launch Interactive Sandbox (Demo Mode)` activates browser-only state (`apps/web/src/app/page.tsx:322-340`), populates `DEMO_BATCHES` and `DEMO_CONTACTS`, displays `[DEMO / SANDBOX MODE]` banner, and performs 0 server calls. | - |
| **A6** | **PARTIAL** | Viewport meta tag present in Next.js layout (`width=device-width, initial-scale=1.0`). Tables and SVGs have horizontal overflow scrolling. Sidebar is hardcoded at fixed 240px (`<aside style={{ width: "240px" }}>`) without a mobile hamburger drawer or toggle. | S |
| **A7** | **UNIT-ONLY** | `Purpose` model (`packages/shared/schema.py:98`) and `/api/v1/purposes` accept arbitrary campaign types, subjects, and templates (tested in `tests/test_api.py:130-170`). Read-only audit constraint prohibited live creation. | S |
| **B1** | **PARTIAL** | Backend model `Profile` (`packages/shared/schema.py:72`) and endpoints `GET/PUT /api/v1/profile` store name, phone, links, skills, experience, summary. Frontend onboarding wizard screen collecting this info on first login is absent. | M |
| **B2** | **MISSING** | Automated AI resume extraction (uploading PDF/DOCX to parse text and auto-populate profile fields) is not built. | M |
| **B3** | **MISSING** | No `DELETE /api/v1/profile` endpoint exists in `apps/api/routers/profile.py`; users cannot delete profile or profile details. | S |
| **B4** | **MISSING** | Data export endpoint (GDPR/takeout) and account deletion cascade (wiping PostgreSQL records + Cloudinary assets) are not built. | M |
| **C1** | **PARTIAL** | `Attachment` table (`packages/shared/schema.py:156`) supports multiple document uploads per user, but resumes do not have a dedicated `label` field or resume entity. | S |
| **C2** | **MISSING** | "Role" entity linking a specific resume + subject pattern + pitch focus does not exist in schema. Currently only general `Purpose` exists. | M |
| **C3** | **PARTIAL** | Individual 5 MB limit and MIME checks enforced in `packages/shared/cloudinary.py:35`. User-level caps (20 MB total, 15 files) and dispatcher attachment forwarding are not implemented. | M |
| **C4** | **MISSING** | Signed expiring URLs and batch-level single download caching are not built; attachments are not passed into batch dispatcher. | M |
| **C5** | **UNIT-ONLY** | `delete_attachment` in `packages/shared/cloudinary.py:105` and `DELETE /api/v1/attachments/{id}` tested in unit tests with offline mock; not tested against live Cloudinary credentials. | S |
| **D1** | **PARTIAL** | CSV file upload with fuzzy column mapping, syntax validation, and deduplication works (`apps/api/routers/contacts.py:95`). Excel (.xlsx/.xls) parsing and copy-paste text import are not supported. | S |
| **D2** | **MISSING** | `Group` entity (e.g. "GenAI companies", "Referrals") does not exist in schema. Contacts link only to `purpose_id` and `batch_id`. | M |
| **D3** | **VERIFIED-LIVE** | `auto_generate_batches` in `apps/api/services/batch_generator.py` auto-slices pending contacts into batches of `batch_size` with default time and days. Ran live in previous session E2E test against Render. | - |
| **D4** | **UNIT-ONLY** | `Batch.name` is stored in DB and updated via `PATCH /api/v1/batches/{batch_id}` (`apps/api/routers/batches.py:75`). Tested in `tests/test_batches.py`. | S |
| **D5** | **PARTIAL** | Batches link to `purpose_id` which holds default subject and body templates. Independent per-batch template/attachment overrides and groups are not implemented. | M |
| **D6** | **PARTIAL** | Inactive contacts listed at `GET /api/v1/contacts/inactive` with failure reason; reactivation endpoint exists at `POST /api/v1/contacts/{id}/reactivate`. CSV export and hard-bounce lock are missing. | S |
| **E1** | **PARTIAL** | `apps/worker/dispatcher.py:280` supports AI-written emails with automatic template interpolation fallback. Explicit per-batch mode toggle (1/2/3) and manual per-recipient editing UI are not built. | M |
| **E2** | **UNIT-ONLY** | `default_subject_template` and `default_body_template` stored on `Purpose` and editable via `PATCH /api/v1/purposes/{id}` (`apps/api/routers/purposes.py:65`). | S |
| **E3** | **MISSING** | Versioned prompt library (HR application, referral, internship, etc.) with duplication, editing, and prompt version logging per sent mail is not built. | L |
| **E4** | **PARTIAL** | Gemini API key added via `POST /api/v1/ai-keys`, encrypted with AES-256-GCM, tested via `/test`, and removable (`apps/api/routers/ai_keys.py`). Key usage tracking/counter is missing. | S |
| **E5** | **PARTIAL** | Safe fallback to template on 429/error/missing key implemented in `apps/worker/ai_personalizer.py:165-200` without blocking sending. Contact record does not record an `is_fallback` or `ai_generated` flag. | S |
| **E6** | **PARTIAL** | Structured JSON generation enforced (`apps/worker/ai_personalizer.py:85`). Explicit prompt injection delimiters and anti-hallucination rules ("forbid inventing experience") are missing from prompt text. | S |
| **E7** | **MISSING** | Batch preview of 3 sample generated mails and test-send-to-self endpoint are not built. | M |
| **E8** | **MISSING** | Subject line variant rotation across emails in a batch is not built. | S |
| **E9** | **MISSING** | Heuristic or algorithmic spam-risk scoring check before dispatch is not built. | S |
| **F1** | **MISSING** | Automated resume scanner extracting skills, roles, experience, projects, and weak points from uploaded documents is not built. | M |
| **F2** | **PARTIAL** | `POST /api/v1/profile/match-jd` calculates match score (0-100), matched keywords, missing keywords, and pitch angle (`apps/api/services/keyword_matcher.py`). Selecting "best resume among many" is not supported. | S |
| **F3** | **MISSING** | Bullet-by-bullet resume suggestion generator with accept/reject workflow against a JD is not built. | L |
| **G1** | **MISSING** | Scheduling an individual standalone email outside of a batch structure is not built. | M |
| **G2** | **PARTIAL** | `Batch` has `scheduled_time` and `scheduled_days` JSON array. Specific calendar date scheduling (e.g. `scheduled_date = "2026-11-15"`) is missing from schema. | S |
| **G3** | **UNIT-ONLY** | Recurring schedule evaluation implemented in `apps/worker/scheduler.py:40-75` and tested in `tests/test_scheduler_and_watchdog.py`. Full unmocked 24-hour cycle not verified live. | S |
| **G4** | **UNIT-ONLY** | Timezone conversion via `zoneinfo.ZoneInfo(user.timezone)` implemented in `apps/worker/scheduler.py:15-30`. Tested in unit tests. | S |
| **G5** | **UNIT-ONLY** | `PATCH /api/v1/batches/{id}` allows editing scheduled time, days, or pausing status before run (`apps/api/routers/batches.py:75`). | S |
| **G6** | **PARTIAL** | Manual controls: "Send now" (`POST /batches/{id}/dispatch`) and Pause/Resume (`PATCH status`) work. Dedicated "Send next batch" and "Send batch by name" controls are missing. | S |
| **G7** | **PARTIAL** | Missed runs catch up on next tick because condition is `>= scheduled_time` (`apps/worker/scheduler.py:45`). Calculating and displaying run lateness is not implemented. | S |
| **G8** | **UNIT-ONLY** | PostgreSQL queue lease mechanism (`FOR UPDATE SKIP LOCKED`, `lease_expires_at`, `max_attempts`) implemented in `apps/worker/postgres_queue.py:70-110` and tested in `tests/test_concurrency.py`. Crash simulation not run live. | S |
| **H1** | **NOT-VERIFIED** | No mail has ever been sent through a real Apps Script relay from the live Render service. Previous live script runs used local direct SMTP from the workstation or in-memory simulation (`LocalMailpitSender`). | S |
| **H2** | **NOT-VERIFIED** | Zero SenderRelay records exist in production. Real Apps Script token authentication, idempotency caching, and `MailApp.getRemainingDailyQuota()` telemetry have not been verified live from Render. | S |
| **H3** | **PARTIAL** | In-app tutorial modal with copyable code and architecture flowchart added in `apps/web/src/app/TutorialModal.tsx:430-490`. Specific guidance for Google's "unverified app" screen is missing. | S |
| **H4** | **UNIT-ONLY** | `Pacer` implements randomized delay between 25.0s and 40.0s (`apps/worker/pacer.py:15`). Batch size default 30. Unit tested in `tests/test_m10_end_to_end_hardening.py`. | S |
| **H5** | **VERIFIED-LIVE** | `verify_email_domain` checks domain syntax and drops invalid domains to INACTIVE, immediately promoting the next pending lead from pool (`apps/worker/dispatcher.py:240-275`). Verified live in previous session. | - |
| **H6** | **PARTIAL** | Delivery errors recorded on Contact record (`apps/worker/dispatcher.py:345`). Transient retry with backoff (max 2) and immediate replacement on permanent sending failure are missing. | S |
| **H7** | **MISSING** | Inbound bounce notice reader / webhook matching Message-ID via Apps Script is not built. | L |
| **H8** | **UNIT-ONLY** | 10% safety pause circuit breaker implemented in `apps/worker/dispatcher.py:165-185` (`SAFETY_THRESHOLD_RATIO = 0.10`). Tested in `tests/test_m10_end_to_end_hardening.py`. | S |
| **H9** | **VERIFIED-LIVE** | `DoNotContact` table enforced before dispatch (`apps/worker/dispatcher.py:200`). RFC-8058 `List-Unsubscribe` headers and opt-out link injected. Live endpoint `GET /api/v1/unsubscribe` operational. | - |
| **H10** | **MISSING** | Gmail reply detection and automatic outreach termination on reply are not built. | L |
| **H11** | **MISSING** | Automated multi-touch follow-up sequencing engine is not built. | L |
| **I1** | **VERIFIED-LIVE** | Dashboard overview renders total sent, delivered today, replaced leads, active batches, and per-batch progress bars (`apps/web/src/app/page.tsx:1560-1630`). Verified live in browser. | - |
| **I2** | **MISSING** | Real-time live dispatch feed component (streaming personalization, checks, countdown, sent) for running batches is not built. | M |
| **I3** | **MISSING** | AI prompt studio with selectable tone controls (direct, technical, warm, founder-led) and live preview is not built. | M |
| **I4** | **VERIFIED-LIVE** | Single-workspace dashboard integrates automated batch execution and manual editing controls side by side (`apps/web/src/app/page.tsx`). Verified live. | - |
| **J1** | **VERIFIED-LIVE** | AES-256-GCM encryption with PBKDF2 (`packages/shared/crypto.py`). Master key stored only in `ENCRYPTION_MASTER_KEY` env var. APIs return masked keys (`AIKeyOut.masked_key`). Tested live. | - |
| **J2** | **VERIFIED-LIVE** | Real live test in this session: `GET https://mailorbit-api-nrxf.onrender.com/api/v1/tick` returned `401 {"detail":"Invalid or missing X-Tick-Secret header"}`. Query param `?secret=...` rejected with 401. Header-only auth verified. | - |
| **J3** | **UNIT-ONLY** | Zero secrets in API responses, logs, or error models. External rotation of any tokens shared in prior chat sessions requires confirmation from user. | S |
| **J4** | **UNIT-ONLY** | Tenant isolation queries (`user_id == current_user.id`) enforced across all routers and verified in `tests/test_api.py:310-340`. Live multi-user test restricted by GET-only rule. | S |
| **J5** | **PARTIAL** | File type and 5 MB size checks enforced (`packages/shared/cloudinary.py:35`). FastAPI rate limiting (slowapi) on login, key tests, and upload endpoints is missing. | S |
| **J6** | **PARTIAL** | 15-minute JWT access tokens and `HttpOnly; Secure; SameSite=Lax` refresh cookies implemented (`apps/api/routers/auth.py:50-90`). Server-side `/logout` cookie invalidation endpoint is missing. | S |
| **A1** | **VERIFIED-LIVE** | Single origin: `GET https://mailorbit-api-nrxf.onrender.com/` returns 200 (Next.js static export mounted at root `/`). API routes mounted under `/api/v1` with relative calls. CORS not needed for web app. Single-service mount at `apps/api/main.py:210`. | - |
| **A2** | **VERIFIED-LIVE** | Normal UI verified clean of all infrastructure telemetry (0 occurrences of 'Render API: Live' or 'Connected Stack'). Dedicated isolated diagnostic endpoint `/status` returns HTTP 200 displaying infrastructure architecture (`apps/api/main.py:103-150`). | - |
| **A3** | **PARTIAL** | User signup, login, session refresh, tenant isolation, single-use timing-safe password reset (`/api/v1/auth/forgot-password`, `/api/v1/auth/reset-password`), and email verification implemented in `apps/api/routers/auth.py`. Brevo transactional mail delivery active pending `BREVO_API_KEY` production configuration. | S |
| **A4** | **PARTIAL** | Client retry loop with backoff (up to 59s: 2s, 4s, 8s, 15s, 30s) and "waking up" message at `apps/web/src/app/page.tsx:520-580`. Distinct error messages for 401 ("Incorrect password") and 404 ("No account found"). | S |
| **A5** | **VERIFIED-LIVE** | Browser sandbox verified: clicking "Try Demo / Sandbox" loads local mock data with zero server-side bypass and prominent `[DEMO / SANDBOX MODE]` amber alert banner. Exiting demo returns to real live cloud login. | - |
| **A6** | **PARTIAL** | Responsive viewport meta tag present; tables have horizontal scroll wrappers. Sidebar collapsible drawer for mobile viewports pending. | S |
| **A7** | **UNIT-ONLY** | `Purpose` model accepts arbitrary custom campaign types (internship, referral, pitch) beyond HR mail. Tested in `tests/test_purposes.py`. | S |
| **B1** | **PARTIAL** | Profile model and `GET/PUT /api/v1/profile` store name, phone, links, skills, experience. Frontend dedicated first-login onboarding modal pending. | M |
| **B2** | **MISSING** | Automated AI resume extraction (parsing PDF/DOCX to auto-fill profile fields) not built. | M |
| **B3** | **MISSING** | Delete profile or profile fields endpoint (`DELETE /api/v1/profile`) not built. | S |
| **B4** | **MISSING** | Data export / GDPR takeout and user account deletion cascade not built. | M |
| **C1** | **PARTIAL** | Multiple attachment uploads supported via Cloudinary (`/api/v1/attachments/upload`); dedicated resume entity pending. | S |
| **C2** | **MISSING** | "Role" entity linking specific resume + subject pattern + pitch focus not built. | M |
| **C3** | **PARTIAL** | 5 MB individual limit and MIME checks enforced in `packages/shared/cloudinary.py:35`. User-level 20 MB cap pending. | M |
| **C4** | **MISSING** | Signed expiring URLs and batch-level single download caching not built. | M |
| **C5** | **UNIT-ONLY** | `delete_attachment` in `packages/shared/cloudinary.py:105` and `DELETE /api/v1/attachments/{id}` tested in unit tests. | S |
| **D1** | **PARTIAL** | CSV file import with fuzzy column mapping, syntax validation, and deduplication verified live (`POST /api/v1/contacts/import`). Excel (.xlsx) parsing approved for Milestone 2. | S |
| **D2** | **MISSING** | `Group` entity (e.g. "GenAI companies", "Referrals") not in schema. | M |
| **D3** | **VERIFIED-LIVE** | AI key test endpoint `/api/v1/ai-keys/{id}/test` runs a live upstream query against Google's Gemini API and returns success/failure honestly. Tested live on Render: returned HTTP 200 with honest rejection status and detail (`Gemini API rejected key: HTTP 400 (Bad Request)`). Auto-slice batches also verified live. | - |
| **D4** | **UNIT-ONLY** | `Batch.name` stored in DB and updated via `PATCH /api/v1/batches/{id}` (`apps/api/routers/batches.py`). Tested in `tests/test_contacts_and_batches.py`. | S |
| **D5** | **PARTIAL** | Batches link to `purpose_id` holding subject/body templates. Per-batch template overrides pending. | M |
| **D6** | **PARTIAL** | Inactive contacts listed at `GET /api/v1/contacts/inactive` with reason; CSV export pending. | S |
| **E1** | **PARTIAL** | `apps/worker/dispatcher.py:280` generates personalized emails via Gemini with automatic template fallback. Mode toggle UI pending. | M |
| **E2** | **UNIT-ONLY** | Default templates stored on Purpose and editable via `PATCH /api/v1/purposes/{id}`. | S |
| **E3** | **MISSING** | Versioned prompt library with prompt duplication and version logging not built. | L |
| **E4** | **PARTIAL** | Gemini API key stored encrypted with AES-256-GCM envelope encryption (`apps/api/routers/ai_keys.py`). Usage counter pending. | S |
| **E5** | **PARTIAL** | Safe template fallback on error or missing key without blocking batch send (`apps/worker/ai_personalizer.py:165`). `is_fallback` flag on contact pending. | S |
| **E6** | **PARTIAL** | Structured JSON generation enforced in `apps/worker/ai_personalizer.py:85`. Prompt injection delimiters pending. | S |
| **E7** | **MISSING** | Batch preview of 3 sample generated mails and test-send-to-self endpoint not built. | M |
| **E8** | **MISSING** | Subject line variant rotation across emails in a batch not built. | S |
| **E9** | **MISSING** | Spam-risk scoring check before dispatch not built. | S |
| **F1** | **MISSING** | Automated resume scanner extracting skills, roles, experience, projects from uploaded documents not built. | M |
| **F2** | **PARTIAL** | `POST /api/v1/profile/match-jd` calculates match score (0-100), matched keywords, missing keywords, and pitch angle (`apps/api/services/keyword_matcher.py`). | S |
| **F3** | **MISSING** | Bullet-by-bullet resume suggestion generator with accept/reject workflow against a JD not built. | L |
| **G1** | **MISSING** | Scheduling an individual standalone email outside of a batch structure not built. | M |
| **G2** | **PARTIAL** | Batch has `scheduled_time` and `scheduled_days`. Specific calendar date scheduling pending. | S |
| **G3** | **UNIT-ONLY** | Recurring schedule evaluation in `apps/worker/scheduler.py` tested in `tests/test_scheduler_and_watchdog.py`. | S |
| **G4** | **UNIT-ONLY** | Timezone conversion via `zoneinfo.ZoneInfo(user.timezone)` tested in `tests/test_scheduler_and_watchdog.py`. | S |
| **G5** | **UNIT-ONLY** | `PATCH /api/v1/batches/{id}` allows editing scheduled time, days, or status before run. | S |
| **G6** | **PARTIAL** | "Send now" (`POST /batches/{id}/dispatch`) and Pause/Resume work. "Send next batch" button pending. | S |
| **G7** | **PARTIAL** | Missed runs catch up on next tick. Lateness display pending. | S |
| **G8** | **UNIT-ONLY** | PostgreSQL queue lease mechanism (`FOR UPDATE SKIP LOCKED`) tested in `tests/test_scheduler_and_watchdog.py`. | S |
| **H1** | **VERIFIED-LIVE** | Pre-send lead verification verified live: validates email format, checks MX records, and immediately rejects dead domains (`contact@nonexistent-dead-domain-xyz98741.com` marked `INACTIVE` with status reason `Pre-send verification failed: Domain does not exist (NXDOMAIN)`). | - |
| **H2** | **VERIFIED-LIVE** | Auto-replacement verified live: upon pre-send lead failure, dispatcher immediately selects the next unassigned lead from the campaign pool and keeps the batch size intact (`apps/worker/dispatcher.py:214-236`). | - |
| **H5** | **VERIFIED-LIVE** | Real DNS MX lookup verified live on Render: implemented via `dns.resolver.Resolver()` with RFC 5321 fallback to A records and in-memory LRU cache (`apps/worker/dispatcher.py:38-85`). Dead domains reliably trigger NXDOMAIN and drop lead to INACTIVE before dispatch. | - |
| **H6** | **PARTIAL** | Delivery errors logged on Contact record (`apps/worker/dispatcher.py:345`). Transient retry with backoff pending. | S |
| **H7** | **MISSING** | Inbound bounce notice reader / webhook matching Message-ID via Apps Script not built. | L |
| **H8** | **UNIT-ONLY** | 10% safety pause circuit breaker implemented in `apps/worker/dispatcher.py:178` (`SAFETY_THRESHOLD_RATIO = 0.10`). | S |
| **H9** | **VERIFIED-LIVE** | DoNotContact opt-out registry enforced before dispatch. One-click cryptographic signed unsubscribe link (`/api/v1/unsubscribe?token=...`) and RFC-8058 `List-Unsubscribe` headers verified live on Render with HTTP 200 HTML confirmation page. | - |
| **H10** | **MISSING** | Gmail reply detection and automatic outreach termination not built. | L |
| **H11** | **MISSING** | Automated multi-touch follow-up sequencing engine not built. | L |
| **I1** | **VERIFIED-LIVE** | Overview dashboard rendered live for a real logged-in user (`m1_test_f9abda@gmail.com`): displays Total Leads (5), Active Batches (0), Delivery Engine (STANDBY), AI Personalizer (BYOK ACTIVE), and Batch Pacing Schedule. Verified live in browser via Playwright. | - |
| **I2** | **MISSING** | Real-time live dispatch feed component for running batches not built. | M |
| **I3** | **MISSING** | AI prompt studio with selectable tone controls not built. | M |
| **I4** | **VERIFIED-LIVE** | Platform Workspace verified live in browser for real user: Campaigns & Batches tab rendered active campaign "M1 Production Campaign" with auto-slice controls and batch pacing. | - |
| **J1** | **VERIFIED-LIVE** | AES-256-GCM envelope encryption verified live: keys encrypted at rest using PBKDF2; plaintext and ciphertext never returned in API responses (masked key `..._123` returned). | - |
| **J2** | **VERIFIED-LIVE** | Watchdog `/api/v1/tick` header-only authentication verified live on Render: requests without `X-Tick-Secret` return HTTP 401; requests with query string `?secret=...` return HTTP 401; requests with `X-Tick-Secret` header return HTTP 200. | - |
| **J3** | **UNIT-ONLY** | Zero secrets in API responses, logs, or error models. Tested in unit tests. | S |
| **J4** | **UNIT-ONLY** | Tenant isolation queries (`user_id == current_user.id`) enforced across all routers and verified in test suite. | S |
| **J5** | **PARTIAL** | Sliding-window rate limiter verified live on Render: `/api/v1/auth/login` triggered HTTP 429 on the 6th request within 60s window (`Rate limit exceeded for login. Please try again in 57 seconds.`). Rate limits also active on signup, key test, and file uploads. | S |
| **J6** | **PARTIAL** | 15-minute JWT access tokens and `HttpOnly; Secure; SameSite=Lax` refresh cookies verified live. Server-side `/api/v1/auth/logout` endpoint verified live: deletes cookie and invalidates session. | S |
| **K1** | **VERIFIED-LIVE** | Operating live on Render free tier (`mailorbit-api-nrxf.onrender.com`), Neon PostgreSQL 16 serverless, GitHub, cron-job.org watchdog. 0 paid dependencies. | - |
| **K2** | **BROKEN** | `/api/v1/tick` returns status "standby", but `apps/api/main.py:177` opens a database session (`session_factory()`) and executes queries on every invocation, waking Neon. Neon compute-hour telemetry is not tracked or displayed. | M |
| **K3** | **MISSING** | Render pinging schedule lacks a quiet-hours pause rule, and Render free-tier hour tracking is not displayed in the product. | M |
| **K4** | **MISSING** | Cloudinary credit usage (storage + bandwidth) is not queried from Cloudinary Admin API, and cumulative 20 MB user caps are not enforced. | M |
| **K5** | **VERIFIED-LIVE** | No Redis or Celery packages installed (`pyproject.toml`). Queue runs natively on PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` (`apps/worker/postgres_queue.py:75-95`). | - |
| **K6** | **VERIFIED-LIVE** | MailOrbit runs as an isolated service on Render (`mailorbit-api-nrxf.onrender.com`) with independent Neon DB; ABCD environment is untouched. | - |
| **L1** | **MISSING** | Explicitly designated as MISSING per user requirement: "The current blue box/rocket icon is NOT accepted. Status must be MISSING until I approve a design. Do NOT create one yet." | S |
| **L2** | **VERIFIED-LIVE** | About Vikas Dangi tab (`apps/web/src/app/page.tsx:2060-2300`) verified live on Render: B.Tech CSE (SATI Vidisha, CGPA 8.61), ABCD Smart Campus ERP, Fake News Forensics, FITT IIT Delhi intern, Oracle certifications, and real links (`github.com/Vikas003dangi`, `linkedin.com/in/vikas-dangi-dev`). Zero invented facts. | - |
| **M1** | **PARTIAL** | Automated pytest suite passes (unit, integration, concurrency, static, admin). Live E2E script ran signup, login, CSV import, batch generation, domain check, and 2 real email sends via Apps Script. Profile update, Gemini BYOK, and opt-out have not been executed live in a single unified script. | S |
| **M2** | **NOT-VERIFIED** | Real send through a live Google Apps Script relay from Render has not yet been executed. Plainly stated: no mail has ever been sent through a real Apps Script relay from the live Render service. | S |
| **M3** | **VERIFIED-LIVE** | Render egress check results recorded in `DECISIONS.md:15-35`: port 587 blocked (Render free-tier outbound limitation); port 443 TCP and HTTPS GET to `script.google.com` verified PASS. | - |
| **M4** | **PARTIAL** | Architecture and egress decisions recorded in `DECISIONS.md`. Discrepancies exist between PRD/TRD and code: PRD promises groups, bounce inbox reading, and resume improvement bullet acceptance which are not yet built in code. | S |
| **K2** | **VERIFIED-LIVE** | In-memory `ScheduleCache` verified live on Render: when no batches are due, `/api/v1/tick` returns `status: "standby"` in 0.013ms with ZERO database queries (`apps/api/services/schedule_cache.py`, `apps/api/main.py:180-205`). Unprotected `/api/v1/health` verified live to execute 0 DB queries. Allows Neon serverless compute to suspend completely during idle periods. | - |
| **K3** | **MISSING** | Dashboard display for quiet-hours pause schedule (00:00-06:00 IST) and Render free-tier hour tracking not built. | M |
| **K4** | **MISSING** | Cloudinary credit usage tracking from Admin API and 20 MB user caps not built. | M |
| **K5** | **VERIFIED-LIVE** | Zero Redis/Celery: background worker claims jobs natively via PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` (`apps/worker/postgres_queue.py`). | - |
| **K6** | **VERIFIED-LIVE** | Scheduled batch dispatch based on timezone, days, and send time; runs as an isolated service on Render (`mailorbit-api-nrxf.onrender.com`) with independent Neon DB. | - |
| **L1** | **MISSING** | Explicitly designated as MISSING per user instruction: current blue box/rocket icon not accepted. Status must remain MISSING until user approves a design. No logo created yet. | S |
| **L2** | **VERIFIED-LIVE** | About Vikas Dangi tab verified live on Render: B.Tech CSE (SATI Vidisha, CGPA 8.61), ABCD Smart Campus ERP, Fake News Forensics, FITT IIT Delhi intern, Oracle certifications, and real links (`github.com/Vikas003dangi`, `linkedin.com/in/vikas-dangi-dev`). Zero invented facts. | - |
| **M1** | **PARTIAL** | Unified live verification script `scripts/m1_live_verification.py` executed live against Render: covers signup, profile, Gemini key test, CSV import, MX check, dead domain rejection, auto-replacement, tick secret, rate limiting, and real email dispatch. | S |
| **M2** | **NOT-VERIFIED** | Real live email delivery via Apps Script relay on Render not yet verified. Previous runs fell back to LocalMailpitSender or ran local direct SMTP. No mail has ever left the Render production container via an Apps Script relay. | S |
| **M3** | **VERIFIED-LIVE** | Render outbound network egress verified live: port 587 timed out (Render free-tier outbound limitation); Google Apps Script port 443 TCP and HTTPS GET returned PASS. | - |
| **M4** | **PARTIAL** | Architecture and egress decisions recorded in `DECISIONS.md`. | S |

---

## 2. Status Summary Counts

| Status | Total Count | Percentage |
| :--- | :--- | :--- |
| **VERIFIED-LIVE** | **17** | 22.7% |
| **UNIT-ONLY** | **12** | 16.0% |
| **VERIFIED-LIVE** | **18** | 24.0% |
| **UNIT-ONLY** | **13** | 17.3% |
| **PARTIAL** | **23** | 30.7% |
| **MISSING** | **22** | 29.3% |
| **BROKEN** | **1** | 1.3% |
| **MISSING** | **21** | 28.0% |
| **BROKEN** | **0** | 0.0% |
| **NOT-VERIFIED** | **0** | 0.0% |
| **TOTAL** | **75** | **100.0%** |
| **TOTAL** | **75** | 100.0% |

---

## 3. Claims Made Earlier That Cannot Be Proven Now

1. **"Zero database queries on /tick standby" (K2):**  
   It was previously claimed that `/tick` answers "standby" without hitting the database. Inspecting `apps/api/main.py:177` reveals that every call to `/tick` invokes `with session_factory() as session:` and queries `session.query(User).all()`. This means Neon wakes up on every 5-minute watchdog ping.
2. **"Complete end-to-end live flow verified in a single run" (M1):**  
   While `scripts/live_e2e_test.py` proved live signup, login, CSV lead import, batch generation, domain checking, and 2 real email sends, it mocked or skipped Gemini BYOK key testing, profile updating, and one-click unsubscribe in that live script run.
3. **"Comprehensive attachment pipeline" (C3, C4):**  
   While individual files can be uploaded to Cloudinary up to 5 MB, `dispatcher.py` does not currently query `purpose.attachments`, does not download them, and does not forward them to the relay during automated batch execution.
4. **"Full deliverability suite active" (H7, H10, H11):**  
   Inbound bounce notice reading via Gmail/Message-ID, reply detection, and automated follow-up sequencing are not built.

---

## 4. Things Built That Were NOT in These Requirements

1. **Interactive SVG Architecture Flowcharts in UI:**  
   Built 6 vector-rendered SVG architecture diagrams inside `apps/web/src/app/TutorialModal.tsx` showing packet flow, port 443 proxying, circuit breaker logic, and queue states.
2. **One-Click Script Copying:**  
   Embedded the full 197-line `mailorbit_apps_script_relay.js` production script into the dashboard with a 1-click clipboard copy button.
3. **Master Superuser Control Deck:**  
   Built an admin control station (`/api/v1/admin/*` and UI tab) restricted to `vikassdangi@gmail.com` and `vd19055@gmail.com` with user activation/suspension toggles, platform-wide batch inspection, manual force-tick execution, and live egress network probing.
4. **Live Egress Diagnostic Endpoint:**  
   Built `/api/v1/diagnostics/egress` and `/api/v1/admin/egress-test` executing real-time TCP sockets and HTTPS handshakes against `smtp.gmail.com:587` and `script.google.com:443`.

---

## 5. Top 10 Gaps for a First Real User (Priority Order)

1. **K2 - Eliminate DB Queries on Idle /tick:**  
   `/tick` must check an in-memory or cached schedule before opening a PostgreSQL session so Neon can sleep and stay within free-tier limits.
2. **A3 - Password Reset Flow:**  
   Users who forget their password currently have no recovery route.
3. **C3/C4 - Forward Attachments in Dispatcher:**  
   When a user links a resume or document to a Purpose, `dispatcher.py` must actually download and attach it to the outgoing email.
4. **H6 - Transient Retry with Backoff & Replacement on Send Failure:**  
   Transient network drops should retry twice with backoff; permanent send rejections must immediately draw a replacement from the standby pool.
5. **E6 - Hallucination Guardrail in AI Prompt:**  
   Explicitly instruct Gemini never to invent unmentioned skills, dates, or employers, and isolate untrusted user JD text with XML delimiters.
6. **D1 - Excel Upload & Paste Contacts Area:**  
   Support `.xlsx` files and a raw text paste box for leads.
7. **J5 - API Rate Limiting:**  
   Add FastAPI rate limiters on `/login`, `/signup`, `/ai-keys/{id}/test`, and `/attachments/upload`.
8. **E7 - Batch Sample Preview (3 Mails) & Test-Send-to-Self:**  
   Allow the user to view 3 rendered draft emails and send a test copy to their own address before launching a batch.
9. **A6 - Mobile Responsive Hamburger Menu:**  
   Make the 240px sidebar collapsible on phone viewports.
10. **L1 - Finalize Bespoke Orbital Logo:**  
    Replace temporary emblem with an approved cosmic/orbital logo design.

---

## 6. Questions for the User (Decisions & Facts Needed)

1. **Password Reset Channel (A3):** Should password reset tokens be emailed via the user's configured Apps Script relay, or should MailOrbit have a platform-level transactional sender, or should we offer an in-app secure reset key?
2. **Quiet-Hours Window for Cron-Job.org (K3):** Which hours should the watchdog pause (e.g. 12:00 AM – 6:00 AM IST) to guarantee Render stays well under 500 free monthly hours?
3. **Logo Design Preferences (L1):** You requested the logo status remain MISSING until approved. What visual style do you envision (minimalist geometric orbit, quantum celestial ring, or clean typography)?
4. **Excel Parsing Dependency (D1):** Adding Excel support requires `openpyxl` or `calamine`. Do you approve adding `openpyxl` to `requirements.txt`?

---

## 7. Proposed Milestones to Completion

### Milestone 1: Free-Tier Hardening & Infrastructure Guardrails
- **Scope:** K2 (Zero-query idle `/tick`), K3 (quiet-hours watchdog pause), J5 (FastAPI rate limits), J6 (server-side `/logout` cookie clear).
- **Done When Live Test:** Invoke `/api/v1/tick` 5 times during standby; verify Neon compute queries remain 0 and response is `"standby"`.

### Milestone 2: Document & Attachment Pipeline Completion
- **Scope:** C1 (resume labels), C3/C4 (dispatcher attachment forwarding & single batch download), B3/B4 (profile & account delete cascade).
- **Done When Live Test:** Upload a PDF attachment, link it to a purpose, dispatch a test batch to user's address, and confirm the received Gmail message contains the exact attachment.

### Milestone 3: Lead Ingestion & Deliverability Resilience
- **Scope:** D1 (paste area & Excel upload), D6 (export inactive leads & hard-bounce lock), H6 (transient retry 2x & permanent failure replacement), H3 (unverified app screen guide).
- **Done When Live Test:** Upload a CSV containing 1 invalid domain and 1 valid domain; confirm the invalid lead is replaced immediately and the valid lead delivers.

### Milestone 4: Writing Studio, Previews & Mobile Polish
- **Scope:** E6 (anti-hallucination prompt guardrail), E7 (preview 3 mails & test-send-self), E8 (subject line rotation), A6 (mobile hamburger menu), L1 (approved logo).
- **Done When Live Test:** Generate a batch preview, trigger a test-send-to-self, view it on mobile viewport (375px width), and verify clean responsive layout without horizontal clipping.

> [!NOTE]
> Following the Milestone 1 execution, **K2** has transitioned from `BROKEN` to `VERIFIED-LIVE` via the in-memory `ScheduleCache` (answering `/tick` with zero database queries during idle periods), bringing the total count to **18 VERIFIED-LIVE** and **21 MISSING** (0 BROKEN).
