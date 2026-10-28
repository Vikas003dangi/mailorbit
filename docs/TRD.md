# TRD — AI Cold-Email Outreach Platform (MailOrbit)

Oct 28, 2026 · @vd

## 1. Architecture overview

The browser never sends mail directly. It communicates with the FastAPI backend, which persists data to PostgreSQL and schedules jobs. An in-process worker module (`apps/worker`) executed inside the API server claims jobs using database row locking (`SKIP LOCKED`) and processes them.

- **Web Frontend:** Next.js static export (`output: 'export'`) hosted on GitHub Pages.
- **Backend API:** FastAPI running on Render Free Tier.
- **Database:** Serverless PostgreSQL 16 on Neon (auto-suspends to 0 compute units when inactive).
- **In-Process Worker:** Python module running behind a unified `JobQueue` protocol inside the API service, triggered via watchdog ticks (`/api/v1/tick`) from cron-job.org.
- **Outbound Email:**
  - *Local Development:* Axllent Mailpit fake SMTP server (port 1025 SMTP, port 8025 Web UI).
  - *Cloud Production (Render Free Tier):* Per-user Google Apps Script relay over HTTPS (`script.google.com:443`). Render Free silently drops outbound TCP on port 587; the relay circumvents port blocking while sending directly from the user's Gmail inbox.
- **File Storage:** Cloudinary authenticated storage (free tier: 25 monthly credits) for resumes, attachments, and generated PDFs.

## 2. Tech stack

| Layer | Choice | Free-Tier Override Reason |
| --- | --- | --- |
| Web app | Next.js + TypeScript (Static Export) | Hosted on GitHub Pages with zero compute cost. Uses short-lived access tokens + HttpOnly refresh cookies. |
| API | FastAPI (Python 3.11+) | Async, lightweight, typed, running on Render Free tier. |
| Database | Neon PostgreSQL 16 | Serverless free tier; pooling with auto-suspend enabled (`conn_max_age=0`). |
| Queue & Scheduler | PostgreSQL `FOR UPDATE SKIP LOCKED` + In-process worker behind `JobQueue` | No Redis or Celery infrastructure needed in v1. Woken by cron-job.org pings to `/api/v1/tick`. |
| Storage | Cloudinary (Authenticated) | Avoids S3 costs and complex IAM setups on free tier. Resumes delivered with expiring signed URLs. |
| Email Sending | Local: Mailpit SMTP; Cloud: Per-user Google Apps Script relay | Render Free blocks outbound TCP 587. Google Apps Script over HTTPS:443 solves egress blocks with 0 server cost. |
| AI | Google Gemini API (BYOK) | User provides their own API key via dashboard. Zero platform AI compute cost. |
| Secrets | AES-256-GCM Envelope Encryption via Environment Master Key | Master key in `ENCRYPTION_MASTER_KEY` environment variable. Designed with clean interface for cloud KMS migration. |

## 3. Data model

Key relational tables in PostgreSQL:
- `users`: id, email, password_hash, timezone, created_at.
- `sender_relays`: id, user_id, email, script_url, token_ciphertext, daily_cap, remaining_quota, status.
- `ai_keys`: id, user_id, provider, api_key_ciphertext, model.
- `attachments`: id, user_id, filename, file_url, cloudinary_public_id, size_bytes.
- `purposes`: id, user_id, name (e.g. Job Application, Referral, Pitch), template, prompt_id, attachment_ids.
- `contacts`: id, user_id, email, name, company, purpose_id, batch_id, status (pending, queued, sent, bounced, inactive), reason, sent_at.
- `batches`: id, user_id, purpose_id, name, scheduled_time, target_count, status.
- `jobs`: id, job_type, payload, status (PENDING, RUNNING, COMPLETED, FAILED), lease_id, lease_expires_at, attempts, run_at.
- `send_events`: id, contact_id, batch_id, event, detail, timestamp.
- `do_not_contact`: id, user_id, email, reason, created_at.

## 4. Send engine & In-Process Worker

The in-process worker lives in `apps/worker` and is imported by `apps/api`.
- It implements the `JobQueue` interface.
- Jobs are claimed via atomic batch selection with `SELECT ... FOR UPDATE SKIP LOCKED`.
- A lease heartbeat prevents duplicate sends if a tick takes longer than the lease duration.
- Outbound sends use the Apps Script relay HTTP POST endpoint on port 443 with the user's secret token.
- Pacing: 25-40s random delay between dispatches.
- Immediate replacement: If a pre-send DNS check or relay response fails, the contact is marked `inactive` immediately and the next pending contact in the same purpose/group is claimed so the daily quota is fulfilled.

## 5. Security & Secret Management

- Master encryption key stored in `ENCRYPTION_MASTER_KEY` (AES-256-GCM).
- Apps Script relay tokens and Gemini keys encrypted at rest.
- Relay tokens stored in Google Apps Script `PropertiesService` (never hardcoded in script text).
- Zero secret logging: auth tokens, credentials, and raw script URLs are redacted from logs and exception traces.
- Strict CORS whitelist for static frontend domain.

## 6. Milestones & Build Plan

- **M0 (Current):** Repo initialization, Docker Compose (PostgreSQL 16 + Mailpit), network egress checks, Apps Script relay template, in-process worker package behind `JobQueue`, FastAPI health/tick/diagnostics endpoints, static Next.js export skeleton, documentation.
- **M1:** Database migrations (Alembic/PostgreSQL), AES-256-GCM encryption service, user auth (JWT access token + HttpOnly cookie), Relay & Gemini key connection.
- **M2:** Contact import (CSV/Excel), validation, deduplication, purpose profiles, auto-batching rules (N/day at time T on days D), inactive contact tracking.
- **M3:** Cloudinary attachment library, purpose-to-attachment linking.
- **M4:** In-process send engine with PostgreSQL leasing, Mailpit local integration, pacing, auto-topup replacement on pre-send failure.
- **M5:** Google Apps Script relay cloud dispatch, quota checks, bounce handling, 10% batch safety pause.
- **M6:** Scheduling system (single email & recurring batch), watchdog integration via cron-job.org `/api/v1/tick`.
- **M7:** Gemini BYOK AI service (mail personalization, prompt library, template fallback).
- **M8:** Resume scanning, JD keyword matching, and bullet suggestions.
- **M9:** Opt-out header/footer, do-not-contact list, account export/deletion.
- **M10:** Hardening, end-to-end integration test against Mailpit, Render staging deployment.
