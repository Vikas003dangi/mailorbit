# MailOrbit System Mail Deliverability & Warmup Guide

**System Sender Account:** `mailorbit.support@gmail.com`  
**Architecture:** Platform Google Apps Script Web App Relay (`scripts/mailorbit_system_relay.js`) executing via `MailApp.sendEmail` inside Google's native infrastructure.  
**Audience:** Platform Owner & System Administrators.

---

## 1. Executive Summary

Because MailOrbit uses a dedicated platform Gmail account (`mailorbit.support@gmail.com`) deployed through a Google Apps Script relay, all outbound system transactional emails (OTPs, Welcome notices, Security alerts) originate **directly from Google's native MX mail servers**.

### Key Advantages:
- **100% Native SPF & DKIM Alignment:** Emails pass Google's strict SPF, DKIM, and ARC authentication automatically without requiring custom DNS domain records.
- **Zero Port Blocks:** Operates via HTTPS POST over port 443; completely immune to Render/cloud host SMTP port 587 blocks.
- **Dedicated Transactional Pool:** Kept strictly separate from user outbound campaign relays.

---

## 2. 7-Day Warmup Schedule

A newly activated Google account lacks historical sender reputation. Sudden spikes from 0 to 50+ emails in a single hour can trigger Google's automated anti-abuse heuristics. 

Follow this **exact 7-day warmup schedule** by triggering verification and test transactional emails from your own accounts (`vikassdangi@gmail.com` and `vd19055@gmail.com`):

| Day | Target Volume | Target Recipient Addresses | Action Protocol on Received Email |
| :--- | :---: | :--- | :--- |
| **Day 1** | **5 emails** | `vikassdangi@gmail.com` (3), `vd19055@gmail.com` (2) | 1. Open each email immediately.<br>2. If in *Spam* or *Promotions*, click **"Report not spam"** or drag to **Primary** inbox.<br>3. Send a brief reply (e.g. *"Received OTP test"*) to 2 emails.<br>4. Add `mailorbit.support@gmail.com` to Google Contacts. |
| **Day 2** | **8 emails** | `vikassdangi@gmail.com` (4), `vd19055@gmail.com` (4) | 1. Open all emails.<br>2. Reply to at least 2 emails.<br>3. Star/flag 1 email. |
| **Day 3** | **12 emails** | Split evenly across both addresses | 1. Open all emails.<br>2. Reply to 3 emails.<br>3. Verify that all 12 land directly in Primary Inbox. |
| **Day 4** | **18 emails** | Split across both addresses + 1 secondary address | 1. Open all emails.<br>2. Reply to 4 emails.<br>3. Ensure no delay or rate-limiting warnings. |
| **Day 5** | **25 emails** | Normal test signups / OTP verifications | 1. Open and verify OTPs.<br>2. Confirm instantaneous (< 5 sec) delivery. |
| **Day 6** | **35 emails** | Realistic registration & security traffic | Open emails, verify layout rendering in dark and light modes. |
| **Day 7** | **50 emails** | Production traffic readiness | Full end-to-end confirmation. |
| **Day 8+** | **Up to 90/day** | Full production operation | Platform cap enforced at 90/day. High-priority OTPs always reserved. |

> [!TIP]
> **Why Two-Way Replies Matter:** Google's email classification algorithm places the highest positive reputation weight on **recipient replies**. When personal Gmail accounts reply to `mailorbit.support@gmail.com`, Google immediately marks the sender address as high-trust and human.

---

## 3. Checklist: What Lands in Spam and Why?

Avoid these proven deliverability pitfalls:

| Risk Factor | Why It Lands in Spam | MailOrbit Safeguard Enforced |
| :--- | :--- | :--- |
| **1. Volume Spikes** | Brand new account jumping from 0 to 50+ sends in minutes triggers anti-spam anomaly detection. | Strict 90/day platform rolling cap + 60s per-recipient OTP cooldown. |
| **2. Tracking Pixels** | Invisible 1x1 GIF tracking pixels trigger heuristic filters in Gmail and Apple Mail Privacy Protection. | **Strictly ZERO tracking pixels** in all transactional templates. |
| **3. Link Shorteners** | Links using `bit.ly`, `tinyurl`, or URL forwarding domains are blacklisted by spam filters. | **Strictly ZERO link shorteners**. Direct platform domains only or plain code. |
| **4. Unbalanced HTML** | Emails with huge HTML formatting but almost no readable text trigger spam filters. | Balanced HTML/text ratio with complete plain-text MIME alternative for every dispatch. |
| **5. Spam Trigger Words** | Aggressive words in subject lines (*"FREE", "ACT NOW", "URGENT $$$", "100% GUARANTEED"*). | Neutral, professional subjects: `[MailOrbit] Your Verification Code: 123456`. |
| **6. Sender Name Mismatch** | Inconsistent From name confuses recipient filters. | Consistent sender name **`MailOrbit`** across both Apps Script and MIME headers. |
| **7. Missing Context** | Transactional emails with no explanation trigger manual "Mark as Spam" clicks. | Clear transactional footer on every email: *"Why you received this: You are receiving this transactional notification because an action occurred on your MailOrbit account..."* |
| **8. Unhandled Bounces** | Repeatedly sending to invalid or dead addresses ruins IP/domain reputation. | Pre-send RFC 5322 regex validation and quarantine of bad addresses before sending. |

---

## 4. Troubleshooting Deliverability Issues

- **If an OTP lands in Spam during initial testing:**
  1. Open the email in Gmail web.
  2. Click **"Report not spam"** button at the top banner.
  3. Move the email to the **Primary** tab.
  4. In Google Contacts, click **Add to Contacts** &rarr; name: `MailOrbit Support`, email: `mailorbit.support@gmail.com`.
  5. Reply to the message with *"Test reply confirmed"*.
- **If Apps Script returns `QUOTA_EXCEEDED` (HTTP 429):**
  - Check `/api/v1/admin/relay-budget` in the MailOrbit admin dashboard.
  - The rolling 24-hour window will reset automatically. Non-urgent notifications will pause automatically when capacity is below 15 to reserve remaining quota for OTPs.

