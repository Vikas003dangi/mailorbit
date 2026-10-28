# PRD — AI Cold-Email Outreach Platform (MailOrbit)

Oct 28, 2026 · @vd

## 1. Vision and summary

A web platform where a non-coder uploads a bulk list of contacts, picks a resume and a purpose, and sends personalised, safely paced emails from their own Gmail, with an AI layer (the user's own Gemini key) that writes the mails, scans resumes and tailors them to a job description.

Product name: **MailOrbit**. It turns what Vikas does today with Antigravity, Python scripts and a JSON file into an autonomous product anyone can use without code or an agent running in the background.

- **One sentence:** bulk, personalised, safe-paced outreach campaigns, with AI, for people who cannot code.
- **Core promise:** upload 350 contacts, and the platform sends 30 a day, each mail different, with the right attachment, and replaces any address that fails immediately.
- **Audience:** job seekers, professionals requesting referrals, freelancers pitching clients, and individuals running outreach campaigns.
- **General Purpose:** The platform is not only for HR job applications. "Purpose" is a general campaign type (job application, referral, freelance pitch, reminder, custom outreach). Each purpose has its own template, AI prompt, and attachments.

## 2. Problem and current state

Today the system works, but only because Antigravity and Vikas are in the loop every day. The as-built audit shows 360 leads, 8 daily batches of 30, and a working send, bounce and tracker pipeline built on local scripts and one JSON file.

| Area | Today (as built) | What the platform must do |
| --- | --- | --- |
| Trigger | User tells Antigravity "send next batch" or runs a script | Automatic daily sending, no agent or terminal |
| Login to Gmail | Hardcoded app password in scripts | Per-user Google Apps Script relay with secret token (or encrypted app password) |
| Data store | One flat JSON file (360 leads), corrupts on parallel writes | Relational database (Neon Serverless PostgreSQL), one workspace per user |
| Batches | Not stored; derived from send dates and slices of the pending list | Auto-created batches from rules (N per day, time T, days D), named, with zero manual steps |
| Mail content | Fixed Python templates, 4 categories, plus hand-injected custom pitches | AI-written unique mails, templates, or manual writing per purpose |
| Resume & Files | One master PDF, fallback folders, hardcoded paths | Multiple attachments/resumes per user, mapped to purposes, roles, and groups |
| Scheduling | None; manual only | Schedule any batch or single mail for a future date and time |
| Failures | Bounces found by IMAP scraping; replacement done by asking the agent | Pre-send domain check, immediate replacement from the same group to maintain daily target |
| Replies | Logged by hand in a markdown file | Reply detection and a simple response pipeline |
| AI | None at send time | User's own Gemini key powers writing, resume scan and JD tailoring |

## 3. Target users and personas

The primary user is a job seeker or professional who sends outreach emails.

| Persona | Goal | Main pain today |
| --- | --- | --- |
| Fresher / job seeker (primary) | Reach 300+ HRs with the right resume, without being marked spam | Writes the same mail by hand, loses track of who got what |
| Referral seeker | Target engineers/leads at specific companies with tailored pitches | Needs a tailored portfolio link and referral pitch |
| Freelancer / agency seeker | Pitch services to small businesses | Needs batches by industry and follow-ups |
| Professional / consultant | Reach niche contacts on custom schedules | Needs flexible scheduling and custom attachments |

## 4. Goals and non-goals

The v1 goal is that a new user sends their first safe batch within 15 minutes of signing up, with no code and no agent.

**Goals**
- Bulk import contacts, group them into named batches, and auto-dispatch on a safe daily schedule (N per day, time T, days D).
- Support any purpose (job application, referral, pitch) with its own templates, prompts, and attachments.
- Schedule any single email for a future date/time (manually written, templated, or AI-generated).
- Auto-detect failed addresses before/during send, mark inactive, and immediately pick the next pending contact so daily target is reached.
- Free tier deployment: Static frontend on GitHub Pages, FastAPI backend on Render, Neon PostgreSQL, Cloudinary storage, per-user Apps Script relay.
- Bring-your-own-key AI layer: mail writing, resume scan, JD match.
- Envelope encryption of credentials at rest using environment master key.

**Non-goals for v1**
- Open/click tracking pixels (hurts deliverability).
- Native desktop/mobile app (responsive web app on mobile browsers).
- List scraping/purchasing.

## 5. Core features

| ID | Feature | Requirement | Priority |
| --- | --- | --- | --- |
| F1 | Sign-up and profile | Email sign-in with short-lived access tokens and HttpOnly refresh cookies. Profile with links, skills, experience. | P0 |
| F2 | Connect sender Gmail | Connect via per-user Google Apps Script relay (zero password shared) or encrypted credentials. | P0 |
| F3 | Contact import | Upload CSV/Excel. Column mapping (email, name, company, role). Deduplication on import. | P0 |
| F4 | Batches and groups | Auto-split contacts into batches of size N, scheduled for time T on days D. Zero manual steps. | P0 |
| F5 | Document library | Upload resumes/portfolios/proposals (PDF/DOCX) to Cloudinary authenticated storage. | P0 |
| F6 | Purpose and role profiles | Save general purpose profiles (job application, referral, freelance pitch). Map templates and attachments. | P0 |
| F7 | Mail content modes | AI-written (unique), template with variables, or manual composition. | P0 |
| F8 | Daily send engine | Sends batch at safe daily cap (default 30) with 25-40s gaps in allowed windows. Pause/resume/stop. | P0 |
| F9 | Send now or by name | "Send now", "send next batch", or test-send to self. | P0 |
| F10 | Single & batch scheduling | Schedule any single mail or batch for future timestamp in user time zone. | P0 |
| F11 | Failure handling | Domain MX/A pre-check; immediate inactive flagging on bounce/rejection. | P0 |
| F12 | Immediate auto-replacement | Immediate top-up from pending queue when a lead fails before or during sending. | P0 |
| F13 | Inactive mails list | Filter, export, and inspect inactive/bounced leads with failure reason. | P0 |
| F14 | Dashboard | Delivered today, pending, failed, replaced, schedule queue, next run time. | P0 |
| F15 | Reply inbox | Track replies and halt automated follow-ups. | P1 |
| F16 | Follow-ups | Automated 1-2 sequence follow-ups if no response after N days. | P1 |
| F17 | Unsubscribe & DNC | Opt-out footer, List-Unsubscribe header, user-level do-not-contact list. | P0 |

## 6. AI layer
- Bring-your-own-key (BYOK) for Gemini API.
- Mail writer, subject variants, resume scanner, and JD matching.
- Human review sample preview before dispatch.

## 7. Safety & Deliverability
- Hard cap of 30-50 emails/day per sender account.
- 25-40s randomized delay between dispatches.
- Bounce threshold safeguard (>10% pauses sender).
- Zero secret logging.

