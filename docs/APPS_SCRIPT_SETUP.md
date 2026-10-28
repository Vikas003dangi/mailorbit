# MailOrbit: Google Apps Script Relay Setup Guide

This 5-minute setup connects your personal Gmail account to MailOrbit without revealing your Gmail password or paying for third-party email APIs.

---

### Step 1: Open Google Apps Script
1. Open your browser and navigate to: **[script.google.com](https://script.google.com)**.
2. Sign in with the **Gmail account** you want to send cold emails from.
3. Click **"+ New project"** in the top left corner.
4. Rename the project from *"Untitled project"* to **MailOrbit Relay**.

---

### Step 2: Paste the Relay Code
1. Erase all default code inside the editor (`myFunction() { ... }`).
2. Open [`scripts/mailorbit_apps_script_relay.js`](../scripts/mailorbit_apps_script_relay.js) from the MailOrbit repository.
3. Copy the entire file content and paste it into the Apps Script editor (`Code.gs`).
4. Click the **Save** icon (diskette) or press `Ctrl + S`.

---

### Step 3: Add Your Secret Auth Token (Never in Code!)
1. In the left navigation sidebar of the Apps Script editor, click the **Gear icon (Project Settings)**.
2. Scroll down to the section titled **"Script Properties"**.
3. Click **"Add script property"**.
4. In the **Property** box, type exactly:
   ```text
   RELAY_AUTH_TOKEN
   ```
5. In the **Value** box, generate or paste a random secret string (for example, `mo_relay_sec_7f9b8c2d1e0a`). You will save this same token in your MailOrbit dashboard settings.
6. Click **"Save script properties"**.

---

### Step 4: Deploy as a Web App
1. At the top right of the editor, click the blue **"Deploy"** button and choose **"New deployment"**.
2. Next to "Select type", click the gear icon and pick **"Web app"**.
3. Fill in the fields:
   - **Description**: `MailOrbit v1 Relay`
   - **Execute as**: **Me (your_email@gmail.com)** *(Crucial: must be "Me" so emails send from your inbox)*
   - **Who has access**: **Anyone** *(Crucial: MailOrbit needs to send requests to this URL; access is secured by your secret token)*
4. Click **"Deploy"**.

---

### Step 5: Authorize the App ("Google hasn't verified this app")
Google will display a permission prompt because the script sends emails on your behalf:
1. Click **"Authorize access"** in the popup window.
2. Select your Google account.
3. You will see a warning screen: **"Google hasn't verified this app"**.
   - *Why this appears*: You just authored this script yourself, so it hasn't gone through public Google verification.
4. Click the small link at the bottom: **"Advanced"**.
5. Click **"Go to MailOrbit Relay (unsafe)"**.
6. Review permissions (it will say "Send email as you") and click **"Allow"**.

---

### Step 6: Copy Web App URL to MailOrbit
1. After authorization completes, copy the **Web app URL** (starts with `https://script.google.com/macros/s/.../exec`).
2. Go to your **MailOrbit Dashboard** -> **Settings** -> **Email Relays**.
3. Paste:
   - **Script URL**: `https://script.google.com/macros/s/.../exec`
   - **Auth Token**: The exact string you saved in Step 3.
4. Click **Test Relay**. MailOrbit will verify connectivity and confirm your remaining daily sending quota.
