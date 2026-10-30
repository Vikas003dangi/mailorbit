# MailOrbit Platform System Relay Setup Guide

**Target Audience:** Workspace Owner / System Administrator (Non-technical guide)  
**Purpose:** Deploy the platform-owned Google Apps Script email relay to send transactional system emails (OTPs, Account Activation, Password Resets, Security Notices) reliably from Render without hitting SMTP port blocks.

---

## 1. Why is this needed?

- Cloud hosts like Render block outbound SMTP (port 587 / 465) on free-tier instances to prevent spam.
- Third-party transactional mailers (like Brevo) fail SPF/DKIM authentication when sending from Gmail addresses.
- MailOrbit uses a dedicated platform Google Apps Script relay executing inside Google's infrastructure via HTTPS POST on port 443.
- No passwords are ever stored or transmitted. The platform authenticates with a secret random token stored in Google Script Properties.

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Create a Dedicated Platform Gmail Account
1. Open an incognito browser window and navigate to [https://accounts.google.com/signup](https://accounts.google.com/signup).
2. Create a new Google account for the platform (e.g., `mailorbit.system@gmail.com` or `mailorbit.auth@gmail.com`).
3. Set a strong password and complete recovery email/phone setup.
4. Go to [Google Account Security](https://myaccount.google.com/security) and **Turn on 2-Step Verification**.

---

### Step 2: Create the Apps Script Project
1. Log into your new platform Gmail account.
2. In your browser, open [https://script.google.com/home/start](https://script.google.com/home/start).
3. Click the **+ New project** button at the top left.
4. Rename the project from "Untitled project" to **`MailOrbit System Relay`** (click on the title at the top).

---

### Step 3: Paste the System Relay Code
1. In the Apps Script code editor, delete any boilerplate code (`function myFunction() { ... }`).
2. Open the file [`scripts/mailorbit_system_relay.js`](../scripts/mailorbit_system_relay.js) in your local MailOrbit repository.
3. Copy the entire file contents and paste them into the Apps Script `Code.gs` editor window.
4. Click the **Save** icon (diskette icon) or press `Ctrl + S` (`Cmd + S` on Mac).

---

### Step 4: Configure the Secret Auth Token
1. In the left navigation panel of Apps Script, click the **Project Settings** (gear icon ⚙️).
2. Scroll down to the **Script Properties** section.
3. Click **Add script property**.
4. Set Property: `RELAY_AUTH_TOKEN`
5. Set Value: A strong, random 32-character secret string (e.g. run `openssl rand -hex 16` or generate a random password).
6. Click **Save script properties**.
   > [!IMPORTANT]
   > Keep this token secret. Never paste it in public forums, tickets, or chat messages.

---

### Step 5: Deploy the Web App
1. At the top right of the Apps Script window, click the blue **Deploy** button and choose **New deployment**.
2. Next to "Select type", click the gear icon ⚙️ and select **Web app**.
3. Fill in the deployment details:
   - **Description:** `MailOrbit System Relay v1`
   - **Execute as:** `Me (your-system-email@gmail.com)`
   - **Who has access:** `Anyone` (authentication is handled securely inside the script via your `RELAY_AUTH_TOKEN`)
4. Click **Deploy**.
5. Google will display an **Authorization Required** dialog:
   - Click **Authorize access**.
   - Select your platform Gmail account.
   - If you see "Google hasn't verified this app", click **Advanced** at the bottom left, then click **Go to MailOrbit System Relay (unsafe)**.
   - Click **Allow** to grant Gmail permissions (`MailApp.sendEmail`).
6. Once deployed, Google will display your **Web App URL**:
   - `https://script.google.com/macros/s/AKfycb.../exec`
   - Copy this URL.

---

### Step 6: Configure Render Environment Variables
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Select your `mailorbit-api` Web Service.
3. In the left menu, select **Environment**.
4. Add or update the following environment variables:
   - `SYSTEM_RELAY_URL` = `https://script.google.com/macros/s/AKfycb.../exec` (your copied Web App URL)
   - `SYSTEM_RELAY_TOKEN` = `<the exact RELAY_AUTH_TOKEN you set in Script Properties>`
   - `ADMIN_EMAILS` = `["vikassdangi@gmail.com"]`
5. Click **Save Changes**. Render will automatically restart the service with the new configuration.

---

## 3. Operational Guarantees & Safeguards

- **Daily Platform Cap:** 90 system emails per rolling day (safely below Gmail's 100/day consumer quota).
- **Idempotency:** Cached for 6 hours; identical requests with the same key are not resent.
- **Fail-Safe Behavior:** If the relay is unavailable or quota is exceeded, signup/verification displays clear, honest error status (`QUOTA_EXCEEDED` or `RELAY_UNAVAILABLE`).
- **No Auto-Verification:** Accounts are **never** auto-verified under any failure or grace condition.
