# MailOrbit Free-Tier Deployment & Operations Guide (DEPLOYMENT.md)

This guide provides step-by-step deployment instructions for Render, Neon Serverless PostgreSQL, Cloudinary, and the Watchdog scheduler, ensuring MailOrbit runs 100% on free tiers without unexpected downtime or billing.

---

## 1. Render Deployment (Minimal M0 Setup)

Follow these exact steps in your browser:

### Step 1: Connect GitHub & Create Web Service
1. Log in to your Render dashboard at **[dashboard.render.com](https://dashboard.render.com)**.
2. Click the blue **"New +"** button in the top right corner and select **"Web Service"**.
3. Under *Connect a repository*, choose **Build and deploy from a Git repository** and click **Next**.
4. Select `Vikas003dangi/mailorbit` (if not listed, click "Configure account" to grant Render access).

### Step 2: Configure Service Details
Fill in the configuration fields:
- **Name:** `mailorbit-api`
- **Region:** `Oregon (US West)` (or `Ohio`)
- **Branch:** `main`
- **Root Directory:** *(leave blank / default root)*
- **Runtime:** **Python 3**
- **Build Command:**
  ```bash
  pip install -r apps/api/requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT
  ```
- **Instance Type:** **Free** ($0 / month)

### Step 3: Health Check Path
Click **Advanced** (at the bottom before creating):
- **Health Check Path:** `/api/v1/health`
- **Auto-Deploy:** `Yes`

### Step 4: Add Environment Variables
Under the **Environment Variables** section, add the following variable names:

| Key | Example / Instructions |
| --- | --- |
| `PYTHON_VERSION` | `3.11.9` |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `USE_FAKE_SMTP` | `false` |
| `TICK_SECRET` | Generate a random 32-character string (e.g. `sec_mo_watchdog_98234ab1c`) |
| `ENCRYPTION_MASTER_KEY` | Generate a 32-byte base64 key |
| `CORS_ORIGINS` | `["http://localhost:3000","https://vikas003dangi.github.io"]` |
| `DATABASE_URL` | *(Neon pooled connection string created in Section 2)* |

5. Click **"Create Web Service"**.

---

## 2. Neon Serverless PostgreSQL Setup

1. Open **[console.neon.tech](https://console.neon.tech)** and sign in.
2. Click **"New Project"**.
3. Name the project **`mailorbit-prod`** and select PostgreSQL 16 in the same cloud region as Render (e.g., AWS us-east-2 or us-west-2).
4. Copy the **Pooled connection string** (ends with `-pooler...` and `?sslmode=require`).
5. Ensure Neon compute auto-suspend is enabled (default is 5 minutes of idle time -> suspends to 0 Compute Units).
6. Paste the connection string into Render's `DATABASE_URL` environment variable.

---

## 3. Verifying Outbound Egress on Render

Once Render finishes deploying:
1. Open your browser or run curl to test the health check:
   ```bash
   curl https://mailorbit-api.onrender.com/api/v1/health
   ```
   *Expected response:* `{"status":"ok","app":"mailorbit-api","version":"0.1.0",...}`

2. Test the network egress diagnostic endpoint (replace with your `TICK_SECRET`):
   ```bash
   curl "https://mailorbit-api.onrender.com/api/v1/diagnostics/egress?secret=YOUR_TICK_SECRET"
   ```
3. Observe the report:
   - `smtp_587.status`: **`FAIL`** (confirms Render Free blocks port 587)
   - `script_tcp_443.status`: **`PASS`** (confirms outbound HTTPS is open)
   - `script_https_get.status`: **`PASS`** (confirms Google connection works)
   - `relay_ready`: **`true`**

---

## 4. Free-Tier Budget & Resource Monitoring

### A. Render Free Instance Hours
- **Account Limit:** Render provides 750 free instance hours shared across all web services per calendar month.
- **ABCD Smart Campus Usage:** Consumes ~46.5 hours/month.
- **MailOrbit Budget:** Cap MailOrbit at **~500 hours/month**.
- **Pinger Strategy:** Schedule cron-job.org to ping `/api/v1/tick` only during your sending window (~16 hours/day, e.g., 07:00 to 23:00 IST). 16 hours x 31 days = 496 hours. The service automatically sleeps during late night hours.
- **How to check:**
  1. Open [Render Dashboard -> Billing](https://dashboard.render.com/billing).
  2. Inspect the **"Free Instance Usage"** progress bar. Ensure the combined total stays below 700 hours.

### B. Neon Compute Units
- **Account Limit:** 100 Compute Unit (CU) hours per month free.
- When inactive, Neon compute drops to 0 CU. MailOrbit connection configuration sets `conn_max_age=0` to close idle connections immediately.
- **How to check:**
  1. Open Neon Console -> select `mailorbit-prod`.
  2. Navigate to **Usage** tab. Check that active CU hours match active ping windows.

### C. Cloudinary Storage & Bandwidth
- **Account Limit:** 25 free credits per month (approx. 25,000 transformations or 25 GB storage/bandwidth).
- MailOrbit stores lightweight PDF resumes (typically ~100 KB - 500 KB) using authenticated delivery.
- **How to check:**
  1. Open Cloudinary Console -> Dashboard.
  2. View the **Monthly Credits Usage** donut chart.
