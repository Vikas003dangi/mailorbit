# Architectural Decisions Record (ADR)

## ADR-001: Consolidated Single-Origin Architecture (Unified Web & API on Render)

### Status
Accepted & Implemented (Oct 29, 2026)

### Context
Previously, MailOrbit was deployed across two disconnected origins:
1. Static frontend hosted on GitHub Pages (`https://vikas003dangi.github.io/mailorbit/`)
2. Backend API hosted on Render (`https://mailorbit-api-nrxf.onrender.com/`)

This separation introduced multiple production failure modes:
- Cross-Origin Resource Sharing (CORS) preflight failures and origin header mismatches.
- Disconnected user experience where visitors perceived the backend Swagger docs and frontend as separate systems.
- Render cold-start network drops triggering client-side `Failed to fetch` errors before preflight could complete.
- Cross-origin cookie restrictions requiring `SameSite=None` with third-party cookie constraints.
- Infrastructure details (Connected Stack, Render API badges) cluttering the primary user interface.

### Decision
1. **Single-Origin Deployment**:
   - The built web application (Next.js static export) is mounted directly at root (`/`) inside FastAPI via `StaticFiles`.
   - The API is served under `/api/v1/...` on the exact same host and port.
   - The whole product is accessible via **ONE** live URL: `https://mailorbit-api-nrxf.onrender.com/`.

2. **Relative Client Routing**:
   - The browser strictly uses relative paths (`/api/v1/auth/login`, `/api/v1/health`, etc.).
   - No hardcoded origin strings, no CORS overhead, no preflight latency for same-origin requests.

3. **Same-Site Secure Cookies**:
   - Refresh tokens are delivered via `SameSite=Lax`, `HttpOnly`, `Secure` cookies scoped to `/api/v1/auth`.

4. **Infrastructure Segregation to `/status`**:
   - All infrastructure diagnostics (Render Container node, Neon PostgreSQL connection pool, UptimeRobot, cron-job.org Watchdog, Cloudinary) are removed from the normal UI.
   - A dedicated `/status` HTML endpoint is provided for operations and health monitoring.

5. **Decommission GitHub Pages**:
   - GitHub Pages deployment workflow has been removed from the user-facing pipeline. All users now access the unified Render service.

---

## 2026-10-29: Interactive Tutorial Documentation & Architecture Flowcharts Across All Modules

### Context
Users navigating MailOrbit across its various workspaces (Sender Relay & Keys, Leads & CSV Import, Campaigns & Batches, AI Personalizer & JD Matcher, Overview Command Center, and Master Admin Deck) required comprehensive, visual, and immediately actionable guidance on how each component operates under the hood, how deliverability safeguards function, and how to deploy the open-source Google Apps Script proxy.

### Decision
1. **Context-Aware Tutorial Buttons Across All Views**:
   - Every view in the platform now contains an explicit, prominent `[ 📘 Setup Guide & Flowchart ]` button in its header and contextual helper cards.
   - A persistent `[ 📘 Guides & Flowcharts ]` shortcut is embedded in the main navigation sidebar.
   - A top header `[ 📘 Tutorial Guides & Flowcharts ]` button is available even on the unauthenticated login/signup landing page.

2. **Self-Contained Interactive SVG Architectural Diagrams**:
   - Implemented 6 responsive, vector-rendered SVG flowcharts for each functional module:
     1. **Sender Relay & Apps Script**: FastAPI -> HTTPS:443 POST -> Apps Script Web App -> Quota & Idempotency Check -> Gmail MX Core -> Recipient Inbox (with Safety Circuit Breaker).
     2. **Leads & Dynamic Fallback Pool**: CSV Ingestion -> Fuzzy Column Detection -> RFC-2606 Blacklist Filter -> Active Batch (30/day) + Standby Reserve Pool with instant bounce replacement.
     3. **Campaigns & Deliverability Pacing**: Campaign Purpose -> Auto-Batch Partitioner -> Quiet Hours & Jitter (60-180s) -> RFC-8058 One-Click Unsubscribe Injection.
     4. **Gemini BYOK AI Personalizer**: Candidate Resume + Target JD -> Client-Side Encrypted Key -> Gemini 1.5 Flash -> Tailored 2-Sentence Hook Generator -> Instant Template Insertion.
     5. **Unified Host Architecture**: Next.js SPA at root `/` -> Relative calls to FastAPI `/api/v1` -> Neon Serverless PostgreSQL 16 + cron-job.org /tick Watchdog + Google Apps Script Relay.
     6. **Superuser Control Deck**: Strict JWT email whitelist -> Admin FastAPI Middleware -> Real-time Telemetry, User Status Toggles, Batch Inspection, Force-Tick Dispatcher, Egress Network Probes.

3. **1-Click Copy Snippets**:
   - Embedded complete, copyable production code directly in the tutorial modals:
     - 197-line production `mailorbit_apps_script_relay.js`
     - Validated sample CSV template with fuzzy header compatibility
     - Tested cold email outreach template
     - Gemini 1.5 Flash structured prompting template


