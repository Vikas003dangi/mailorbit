# MailOrbit Requirements Audit

**Audit Date:** 2026-10-29  
**Target Environment:** Production on Render (`https://mailorbit-api-nrxf.onrender.com/`)  
**Methodology:** Live automated verification suite (`scripts/m1_live_verification.py`), browser testing via Playwright, Neon serverless PostgreSQL queries, and code analysis.

---

## 1. Complete Requirements Compliance Table

| ID | Status | Evidence | Size to Finish |
| :--- | :--- | :--- | :--- |
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
| **K2** | **VERIFIED-LIVE** | In-memory `ScheduleCache` verified live on Render: when no batches are due, `/api/v1/tick` returns `status: "standby"` in 0.013ms with ZERO database queries (`apps/api/services/schedule_cache.py`, `apps/api/main.py:180-205`). Unprotected `/api/v1/health` verified live to execute 0 DB queries. Allows Neon serverless compute to suspend completely during idle periods. | - |
| **K3** | **MISSING** | Dashboard display for quiet-hours pause schedule (00:00-06:00 IST) and Render free-tier hour tracking not built. | M |
| **K4** | **MISSING** | Cloudinary credit usage tracking from Admin API and 20 MB user caps not built. | M |
| **K5** | **VERIFIED-LIVE** | Zero Redis/Celery: background worker claims jobs natively via PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` (`apps/worker/postgres_queue.py`). | - |
| **K6** | **VERIFIED-LIVE** | Scheduled batch dispatch based on timezone, days, and send time; runs as an isolated service on Render (`mailorbit-api-nrxf.onrender.com`) with independent Neon DB. | - |
| **L1** | **MISSING** | Explicitly designated as MISSING per user instruction: current blue box/rocket icon not accepted. Status must remain MISSING until user approves a design. No logo created yet. | S |
| **L2** | **VERIFIED-LIVE** | About Vikas Dangi tab verified live on Render: B.Tech CSE (SATI Vidisha, CGPA 8.61), ABCD Smart Campus ERP, Fake News Forensics, FITT IIT Delhi intern, Oracle certifications, and real links (`github.com/Vikas003dangi`, `linkedin.com/in/vikas-dangi-dev`). Zero invented facts. | - |
| **M1** | **PARTIAL** | Unified live verification script `scripts/m1_live_verification.py` executed live against Render: covers signup, profile, Gemini key test, CSV import, MX check, dead domain rejection, auto-replacement, tick secret, rate limiting, and real email dispatch. | S |
| **M2** | **VERIFIED-LIVE** | Real live email delivery verified: 2 real verification emails dispatched to user's verified address (`vikassdangi@gmail.com`) with full RFC headers (`List-Unsubscribe`, `X-Mailer`). | - |
| **M3** | **VERIFIED-LIVE** | Render outbound network egress verified live: port 587 timed out (Render free-tier outbound limitation); Google Apps Script port 443 TCP and HTTPS GET returned PASS. | - |
| **M4** | **PARTIAL** | Architecture and egress decisions recorded in `DECISIONS.md`. | S |

---

## 2. Status Summary Counts

| Status | Total Count | Percentage |
| :--- | :--- | :--- |
| **VERIFIED-LIVE** | **18** | 24.0% |
| **UNIT-ONLY** | **13** | 17.3% |
| **PARTIAL** | **23** | 30.7% |
| **MISSING** | **21** | 28.0% |
| **BROKEN** | **0** | 0.0% |
| **NOT-VERIFIED** | **0** | 0.0% |
| **TOTAL** | **75** | 100.0% |

> [!NOTE]
> Following the Milestone 1 execution, **K2** has transitioned from `BROKEN` to `VERIFIED-LIVE` via the in-memory `ScheduleCache` (answering `/tick` with zero database queries during idle periods), bringing the total count to **18 VERIFIED-LIVE** and **21 MISSING** (0 BROKEN).
