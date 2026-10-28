# MailOrbit Architectural Decisions & Deviations Log (DECISIONS.md)

This document records all deviations from the initial draft specifications, architecture decisions driven by free-tier hosting realities, and benchmark diagnostic results.

---

## 1. Free-Tier Overrides & TRD Section Mapping

The following sections of the Technical Requirements Document (TRD) were updated to accommodate free-tier operations without recurring infrastructure costs:

| TRD Section | Original Specification | Free-Tier Override Decision | Technical Rationale |
| --- | --- | --- | --- |
| **Section 1 (Architecture)** | Separate worker containers and Redis instance. | In-process worker module (`apps/worker`) executed inside the FastAPI service behind a `JobQueue` interface. | Render Free Tier allows only one web service container. Running Redis or separate worker containers exceeds the 750-hour free allowance. |
| **Section 2 (Tech Stack - Queue)** | Redis + Celery / Arq. | PostgreSQL row-level leasing (`FOR UPDATE SKIP LOCKED`) managed by the in-process worker. | Eliminates Redis memory cost and broker operational complexity. PostgreSQL handles batch leasing reliably with zero extra processes. |
| **Section 2 (Tech Stack - Mail)** | Direct SMTP via `smtplib` on `smtp.gmail.com:587`. | Per-user Google Apps Script relay over HTTPS (`script.google.com:443`). Local dev uses Axllent Mailpit on port 1025. | Render Free Tier blocks outbound TCP on port 587 (silent timeout). Sending via Google Apps Script Web App over HTTPS:443 bypasses the port block and sends directly from the user's Gmail. |
| **Section 2 (Tech Stack - Storage)**| AWS S3-compatible bucket. | Cloudinary Authenticated Storage. | Free tier offers 25 monthly credits, built-in image/PDF processing, and signed temporary URLs without AWS billing setup. |
| **Section 2 (Tech Stack - Frontend)**| Server-side rendered Next.js app. | Next.js Static Export (`output: 'export'`) hosted on GitHub Pages. | Static frontend costs $0, has zero sleep latency, and avoids consuming Render runtime hours. |
| **Section 7 (Secrets & KMS)** | Cloud Key Management Service (AWS/GCP KMS). | Environment Variable Master Key (`ENCRYPTION_MASTER_KEY`) with AES-256-GCM envelope encryption interface. | Cloud KMS has no free tier and requires billing activation. The encryption module is designed as an interchangeable adapter so cloud KMS can be swapped in later without modifying caller code. |
| **Section 9 (Deployment & Budgets)**| 24/7 worker uptime. | Watchdog schedule (~16h/day active, ~500h/month total) triggered via cron-job.org pings to `/api/v1/tick`. | Vikas's Render account has a shared 750 free instance hours limit. ABCD smart campus uses ~46.5 hours; capping MailOrbit to ~500 hours leaves comfortable buffer to prevent service suspension. |

---

## 2. In-Process Worker Architecture

Rather than merging worker code into the API endpoints, the worker is encapsulated in its own package:
- **Location:** `apps/worker`
- **Contract:** Defined by `JobQueue(ABC)` protocol (`enqueue`, `claim_batch`, `complete`, `fail`, `heartbeat`).
- **Runner:** `WorkerRunner` executes batch claims and dispatches to registered handler callbacks.
- **Triggering:** Can be ticked synchronously by the watchdog endpoint (`POST /api/v1/tick`) or run as an in-process background daemon thread (`start_background()`).

---

## 3. Network Egress Diagnostics (Local vs. Render Free)

### Check Specification:
1. TCP `smtp.gmail.com:587` (standard SMTP submission port)
2. TCP `script.google.com:443` (Google Apps Script HTTPS port)
3. HTTPS GET `https://script.google.com` (TLS handshake & HTTP layer validation)

### Diagnostic Results:

#### A. Local Development Machine (Windows 11):
- **Command:** `python scripts/check_smtp_egress.py`
- **Executed at:** 2026-10-28 14:42:02 IST
- **Results:**
  - 1. TCP `smtp.gmail.com:587`: **`[PASS]`** - Connected successfully
  - 2. TCP `script.google.com:443`: **`[PASS]`** - Connected successfully
  - 3. HTTPS GET `script.google.com`: **`[PASS]`** - HTTP 200 (OK)
- **Conclusion:** Local dev environment has uninhibited outbound egress. Local testing of the Google Apps Script relay and Mailpit will succeed.

#### B. Render Free Tier Web Service:
- **Service Name:** `mailorbit-api` (`srv-dbgsb8ks728c73c96fe0`)
- **Live URL:** `https://mailorbit-api-nrxf.onrender.com`
- **Endpoint:** `GET /api/v1/diagnostics/egress?secret=sec_orbit_test_7f21a`
- **Measured at:** 2026-10-28 15:37:29 IST (`2026-10-28T10:07:29.221994Z`)
- **Actual Measured Results:**
  - 1. TCP `smtp.gmail.com:587`: **`[FAIL]`** - `Connection timed out (5.0s)`
  - 2. TCP `script.google.com:443`: **`[PASS]`** - `Connected successfully`
  - 3. HTTPS GET `script.google.com`: **`[PASS]`** - `HTTP 200 (OK)`
- **`relay_ready`:** **`true`**
- **Conclusion:** Empirically proves that direct outbound SMTP is blocked on Render Free Tier, whereas outbound HTTPS to `script.google.com:443` is fully operational. This confirms that the per-user Google Apps Script relay is the verified, working architecture for free-tier email dispatch.

---

## 4. Apps Script Relay Security Architecture

- **Token Storage:** Token is stored inside Google Apps Script `PropertiesService.getScriptProperties().getProperty("RELAY_AUTH_TOKEN")`, **never** in script text or repository code.
- **Quota Safeguard:** Checks `MailApp.getRemainingDailyQuota()` on every call; returns `QUOTA_EXCEEDED` if 0.
- **Idempotency:** Cached via `CacheService` for 6 hours using `idem_<key>` to prevent duplicate sends on network retries.
- **Attachment Guard:** Strict 25 MB payload threshold enforced before calling `MailApp.sendEmail()`.
- **Zero Secret Logging:** Neither the token nor request authorization headers are logged to Cloud Logging or execution transcripts.

