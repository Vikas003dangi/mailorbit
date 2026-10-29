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
