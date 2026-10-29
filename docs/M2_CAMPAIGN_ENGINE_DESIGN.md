# MailOrbit Milestone 2: Campaign Engine Redesign
## Technical Architecture & Implementation Specification (PLAN ONLY)

**Date:** 2026-10-29  
**Target Delivery:** Milestone 2  
**Status:** DESIGN / PLAN ONLY (Pending User Approval to Build)  
**Compatibility:** 100% backward-compatible with existing Auth, Encryption, Senders/Relays, Postgres Queue, and DB records. Zero data loss via non-destructive Alembic migration.

---

## 1. Executive Summary & Core Objectives

Milestone 2 re-architects MailOrbit's execution engine from static, one-shot batches into an elastic, multi-account **Campaign Engine**. 

A **Campaign** serves as the master outreach container (e.g., *"Q4 Senior Product Designer Outreach"*). It controls:
1. **Dynamic Mid-Run Lead Ingestion:** Contacts added mid-flight queue smoothly without resetting progress or disturbing active workers.
2. **Fair-Share Multi-Account Budget Auto-Balancing:** Distributes daily sending workload across 1..N active sender relays (e.g., 10/10/10 across 3 accounts, or weighted allocations like 4/13/13), enforcing strict per-account quotas and deliverability safety warnings (>50/day on personal Gmail).
3. **Calendar Scheduling & Repeat Rounds:** Configures launch date/time, active weekdays (e.g. Mon–Fri), holiday skip dates, and automated repeat follow-up rounds with strict suppression guardrails (never re-email replies, bounces, or opt-outs; minimum 7-day cooldown gap; max rounds cap).
4. **"Not Working" Quarantine & 1-Click Replacement Audit Trail:** Automatically segregates bad-syntax, dead-DNS, and hard-bounced contacts into a dedicated folder with 1-click replacement that inherits sequence position and tracks who replaced whom, when, and why.
5. **Size 1..N Unified Execution Path:** Executes ad-hoc single sends (size 1) or full-scale runs using the exact same pacing, encryption, template/AI personalization, and 10% safety pause circuit breaker.

---

## 2. Relational Schema & Zero-Data-Loss Migration

### 2.1 Database Entities (`packages/shared/schema.py`)

```
+-----------------------------------------------------------------------------------------+
|                                        CAMPAIGN                                         |
|-----------------------------------------------------------------------------------------|
| id (UUID, PK)                                                                           |
| user_id (UUID, FK -> users.id, indexed)                                                 |
| purpose_id (UUID, FK -> purposes.id, nullable)                                          |
| name (VARCHAR(120), e.g. "Q4 Product Designer")                                          |
| status (VARCHAR(30): DRAFT, ACTIVE, PAUSED, COMPLETED, CANCELLED)                       |
| daily_budget_total (INTEGER, default 30)                                                |
| schedule_start_date (DATE, nullable)                                                    |
| schedule_start_time (VARCHAR(5), e.g. "09:30")                                          |
| timezone (VARCHAR(50), default "Asia/Kolkata")                                          |
| active_days (JSON, e.g. ["mon", "tue", "wed", "thu", "fri"])                            |
| skip_dates (JSON, e.g. ["2026-11-01", "2026-12-25"])                                   |
| stop_date (DATE, nullable)                                                              |
| repeat_rounds (INTEGER, default 1, max 3)                                               |
| current_round (INTEGER, default 1)                                                      |
| min_round_gap_days (INTEGER, default 7)                                                 |
| last_round_completed_at (TIMESTAMPTZ, nullable)                                         |
| created_at / updated_at (TIMESTAMPTZ)                                                   |
+-----------------------------------------------------------------------------------------+
       | 1                                               | 1
       | has many                                        | has many
       v N                                               v N
+-----------------------------------------------+ +-----------------------------------------------+
|                  SUB_BATCH                    | |                    CONTACT                    |
|-----------------------------------------------| |-----------------------------------------------|
| id (UUID, PK)                                 | | id (UUID, PK)                                 |
| campaign_id (UUID, FK -> campaigns.id, idx)   | | campaign_id (UUID, FK -> campaigns.id, idx)   |
| user_id (UUID, FK -> users.id)                | | purpose_id (UUID, FK -> purposes.id)          |
| sender_relay_id (UUID, FK -> relays.id, idx)  | | sub_batch_id (UUID, FK -> sub_batches.id, idx)|
| name (VARCHAR(120), e.g. "Batch 1 - Relay A") | | email (VARCHAR(255))                          |
| size (INTEGER)                                | | name, company, role (VARCHAR)                 |
| position (INTEGER)                            | | sequence_position (INTEGER, indexed)          |
| status (PENDING, RUNNING, COMPLETED, PAUSED)  | | status (PENDING, SENT, BOUNCED, INACTIVE...)  |
| round_number (INTEGER, default 1)             | | status_reason (TEXT)                          |
| scheduled_date (DATE)                         | | is_not_working (BOOLEAN, default FALSE, idx)  |
| sent_count, failed_count (INTEGER)            | | replaced_by_contact_id (UUID, FK -> self.id)  |
| created_at, completed_at (TIMESTAMPTZ)        | | sent_at (TIMESTAMPTZ)                         |
+-----------------------------------------------+ +-----------------------------------------------+
                                                                 | 1
                                                                 | has substitution audit
                                                                 v N
                                                  +-----------------------------------------------+
                                                  |              CONTACT_REPLACEMENT              |
                                                  |-----------------------------------------------|
                                                  | id (UUID, PK)                                 |
                                                  | campaign_id (UUID, FK -> campaigns.id, idx)   |
                                                  | user_id (UUID, FK -> users.id)                |
                                                  | original_contact_id (UUID, FK -> contacts.id) |
                                                  | replaced_by_contact_id (UUID, FK -> contacts) |
                                                  | original_email (VARCHAR(255))                 |
                                                  | replacement_email (VARCHAR(255))              |
                                                  | reason (VARCHAR(255))                         |
                                                  | replaced_at (TIMESTAMPTZ, default UTC now)    |
                                                  +-----------------------------------------------+
```

### 2.2 Sender Relay Quota & Budget Schema Extension

In `SenderRelay`:
- `daily_budget_limit`: User-configured daily target for this specific account (default: `30`).
- `daily_sent_count`: Tracked count for current calendar date in user's timezone.
- `last_reset_date`: Date when `daily_sent_count` was last zeroed out.
- `is_personal_account`: Boolean flag. If `TRUE` and `daily_budget_limit > 50`, system flags deliverability risk.

### 2.3 Non-Destructive Alembic Migration Plan

1. **Step 1 (Add Tables):** Create `campaigns` and `contact_replacements` tables with proper foreign keys and indices.
2. **Step 2 (Backfill Default Campaign):** For existing users with existing `batches` and `contacts`, automatically generate a default `Campaign(name="Primary Outreach", status="ACTIVE")` per user and assign existing records to it.
3. **Step 3 (Alter Existing Tables):**
   - Add `campaign_id` (nullable initially, backfilled, then foreign key) to `batches` and `contacts`.
   - Add `sequence_position`, `is_not_working`, `replaced_by_contact_id` to `contacts`.
   - Add `daily_budget_limit`, `daily_sent_count`, `last_reset_date` to `sender_relays`.
4. **Step 4 (Zero-Downtime Guarantee):** All existing queries referencing `batches` remain operational. `Batch` model aliases to `SubBatch` seamlessly.

---

## 3. Core Engine Algorithms

### 3.1 Dynamic Mid-Run Lead Ingestion

When a user imports a CSV or pastes 50 new contacts while a campaign is actively running:

```text
Algorithm: AppendLeadsToActiveCampaign(campaign_id, new_contacts)
1. Lock campaign row (SELECT FOR UPDATE) to prevent race conditions with the scheduler tick.
2. Query max(sequence_position) for campaign: current_max_pos.
3. For each lead in new_contacts:
     pos = current_max_pos + 1
     current_max_pos = pos
     insert Contact(
       campaign_id=campaign_id,
       sequence_position=pos,
       status="PENDING",
       is_not_working=FALSE
     )
4. Recalculate campaign statistics:
     total_contacts += len(new_contacts)
     pending_contacts += len(new_contacts)
     estimated_days_remaining = ceil(pending_contacts / daily_budget_total)
5. Refresh schedule_cache in memory:
     schedule_cache.record_schedule_change(earliest_due_time)
6. Commit transaction. Active dispatch worker picks up new contacts immediately once current sub-batch completes.
```

### 3.2 Fair-Share Daily Budget Auto-Balancer

Calculates the daily dispatch allowance across multiple sender accounts.

```text
Algorithm: BalanceDailySendingQuota(campaign_id, active_relays, target_daily_total)
Input:
  - active_relays: List of verified relays for user with status="ACTIVE".
  - target_daily_total: Campaign total target (e.g., 30).

Steps:
1. Filter relays that have not yet breached their daily cap:
     available_relays = [r for r in active_relays if r.daily_sent_today < r.daily_budget_limit]
2. If available_relays is empty:
     Log "All sender relays have exhausted daily quota. Standing by until tomorrow's send window."
     Return []
3. Calculate target allocation per relay:
     total_capacity = sum(r.daily_budget_limit - r.daily_sent_today for r in available_relays)
     daily_needed = min(target_daily_total, total_capacity)
     
     # Proportionally distribute daily_needed across available relays
     allocations = {}
     remaining_to_allocate = daily_needed
     
     # Equal share division with integer remainder distribution
     base_share = daily_needed // len(available_relays)
     remainder = daily_needed % len(available_relays)
     
     for idx, relay in enumerate(available_relays):
       quota = base_share + (1 if idx < remainder else 0)
       # Clamp to relay's individual remaining daily cap
       clamped_quota = min(quota, relay.daily_budget_limit - relay.daily_sent_today)
       allocations[relay.id] = clamped_quota

4. For each relay with allocation > 0:
     Slice next PENDING contacts from campaign (ORDER BY sequence_position ASC)
     Create SubBatch(size=allocation, sender_relay_id=relay.id)
     Enqueue dispatch job in Postgres queue
5. Return generated sub-batches.
```

### 3.3 Calendar Scheduler & Repeat Rounds Guardrails

```text
Algorithm: EvaluateCampaignRepeatRounds(campaign_id)
1. Check if all contacts in Round R have reached terminal state (SENT, BOUNCED, INACTIVE, REPLIED, UNSUBSCRIBED).
2. If PENDING contacts remain: Continue current round.
3. If Round R is finished:
     a. If current_round >= repeat_rounds:
          Mark campaign.status = "COMPLETED"
          Generate in-app notification & system email: "Campaign 'X' has completed all R rounds."
          Return
     b. Check cooldown gap:
          days_since_last_round = (now() - campaign.last_round_completed_at).days
          if days_since_last_round < campaign.min_round_gap_days:
              Log "Round cooldown in effect. Next round due on {due_date}."
              Return (Standby)
     c. Initialize Round R + 1:
          # Query eligible contacts for re-engagement
          eligible_contacts = SELECT * FROM contacts WHERE campaign_id = campaign_id
            AND status = "SENT"
            AND is_not_working = FALSE
            AND email NOT IN (SELECT email FROM do_not_contact WHERE user_id = user_id)
            AND status NOT IN ("REPLIED", "BOUNCED", "UNSUBSCRIBED")
          
          # Mark all non-eligible as excluded
          For contact in eligible_contacts:
              Reset contact.status = "PENDING"
              Increment contact.round_count += 1
          
          campaign.current_round += 1
          campaign.last_round_completed_at = now()
          Commit & notify user that Round R + 1 has commenced.
```

### 3.4 "Not Working" Lead Quarantine & 1-Click Replacement

When an address fails pre-send DNS (NXDOMAIN, no MX/A) or returns a 5xx fatal delivery rejection:

```text
Algorithm: QuarantineAndReplaceLead(contact_id, failure_reason)
1. Mark contact:
     contact.status = "INACTIVE"
     contact.status_reason = failure_reason
     contact.is_not_working = TRUE
2. Add contact to Campaign "Not Working" section.
3. Decrement campaign.delivered_count and leave open slot in sub-batch.
4. Auto-topup check:
     If standby pending leads exist in campaign:
       Fetch next pending lead (ORDER BY sequence_position ASC)
       Assign to current sub-batch to maintain targeted send quota.
5. User 1-Click Replacement Action (from UI):
     User opens "Not Working" tab -> clicks "Replace" on contact_id.
     Inputs: new_email, new_name, new_company, reason (e.g., "Updated email found on LinkedIn").
     
     Transaction:
       new_contact = Contact(
         campaign_id=contact.campaign_id,
         email=new_email,
         name=new_name,
         company=new_company,
         sequence_position=contact.sequence_position, # Inherits exact position
         status="PENDING",
         is_not_working=FALSE
       )
       session.add(new_contact)
       session.flush()
       
       contact.replaced_by_contact_id = new_contact.id
       
       audit_entry = ContactReplacement(
         campaign_id=contact.campaign_id,
         original_contact_id=contact.id,
         replaced_by_contact_id=new_contact.id,
         original_email=contact.email,
         replacement_email=new_contact.email,
         reason=reason,
         replaced_at=now()
       )
       session.add(audit_entry)
       session.commit()
```

### 3.5 Ad-Hoc Size 1..N Sends

Single sends reuse 100% of the production pipeline:
- Input: `POST /api/v1/campaigns/quick-send` with `{to_email, name, company, role, template_or_ai, relay_id}`.
- Generates an ephemeral `Campaign(is_ad_hoc=True, size=1)` and executes immediately via `dispatch_batch()`.
- Guarantees AES-256-GCM secret decryption in memory, DNS domain validation, Gemini BYOK personalization, 25-40s pacing if $N > 1$, and circuit breaker checks.

---

## 4. Seven Worked Numerical Examples

### Example 1: Standard Multi-Account Fair-Share Auto-Balancing
* **Setup:** 120 contacts in campaign, 3 active sender relays (A, B, C). Daily budget set to 30/day total.
* **Math:**
  * Day 1: Target 30 emails. $30 / 3 = 10$ emails per account.
    * Relay A sends contacts #1–#10.
    * Relay B sends contacts #11–#20.
    * Relay C sends contacts #21–#30.
  * Day 2: Target 30 emails. Relays A, B, C send contacts #31–#40, #41–#50, #51–#60.
  * Day 3: Relays A, B, C send contacts #61–#70, #71–#80, #81–#90.
  * Day 4: Relays A, B, C send contacts #91–#100, #101–#110, #111–#120.
* **Outcome:** Exactly 4 calendar days. Each account sends 40 emails total across 4 days (10/day), maintaining pristine sender reputation well below the 50/day personal Gmail safety threshold.

---

### Example 2: Weighted Multi-Account Allocation (4 / 13 / 13)
* **Setup:** User has 3 relays:
  * Relay 1: New Gmail account (warm-up phase), user manually caps at 4/day.
  * Relay 2: Established Gmail account, cap set at 13/day.
  * Relay 3: Established Gmail account, cap set at 13/day.
  * Total daily budget: $4 + 13 + 13 = 30\text{/day}$. Campaign has 150 contacts.
* **Math:**
  * Day 1: Relay 1 sends 4 contacts (#1–#4). Relay 2 sends 13 contacts (#5–#17). Relay 3 sends 13 contacts (#18–#30). Total sent: 30.
  * Duration: $150 / 30 = 5$ days.
* **Outcome:** Relay 1 never exceeds 4 sends/day. Relays 2 & 3 share the heavier load safely without triggering Google spam filters.

---

### Example 3: Mid-Flight Relay Quota Depletion & Dynamic Redistribution
* **Setup:** 2 relays (A and B). Daily budget target: 30 emails (15 each).
* **Execution:**
  * Relay A dispatches 15 emails successfully.
  * Relay B dispatches 8 emails, then Google Apps Script returns `429 Daily User Sending Quota Exceeded`.
  * Relay B status transitions to `QUOTA_EXCEEDED` for the day. 7 leads from Relay B's sub-batch remain pending.
* **Engine Decision:**
  * Relay A already met its 15 daily budget cap. If Relay A's max cap allows, it can absorb up to its limit. If Relay A's cap is hard 15, the remaining 7 leads pause cleanly.
  * Next morning at 06:00 IST (quota reset), Relay B is reset to `ACTIVE`. The 7 remaining leads are dispatched first, followed by the standard Day 2 allocation. Zero dropped leads.

---

### Example 4: Dynamic Lead Addition Mid-Campaign
* **Setup:** Campaign of 60 leads running over 2 days (30/day).
* **Execution:**
  * On Day 1 at 14:00 (after 20 emails have dispatched), the user uploads 40 new leads from a conference CSV.
* **Engine Decision:**
  * Existing dispatch worker continues uninterrupted.
  * New leads are assigned `sequence_position` 61 through 100.
  * Campaign total updates to 100 leads.
  * Day 1 finishes its scheduled 30 sends (leads #1–#30).
  * Day 2 sends leads #31–#60.
  * Day 3 sends leads #61–#90.
  * Day 4 sends leads #91–#100 (10 emails).
* **Outcome:** Zero race conditions, zero duplicate emails, smooth schedule recalculation from 2 days to 3.3 days.

---

### Example 5: "Not Working" Quarantine & 1-Click Sequence Replacement
* **Setup:** Batch of 30 leads.
  * Lead #14 (`cto@deadstartup.invalid`) fails DNS MX lookup (`NXDOMAIN`).
  * Lead #22 (`vp@oldcorp.com`) returns SMTP `550 5.1.1 User unknown`.
* **Engine Decision:**
  * Leads #14 and #22 are immediately tagged `is_not_working = TRUE`, `status = "INACTIVE"` and moved to "Not Working" folder.
  * Immediate auto-topup pulls Lead #31 and Lead #32 from the pending pool so the day's quota of 30 successful deliveries is met.
  * Later, user clicks "Replace" on Lead #14 in the Not Working folder and enters `cto_new@realcompany.com`.
  * `cto_new@realcompany.com` is inserted with `sequence_position = 14`, inheriting priority.
  * Audit row created in `contact_replacements`: `original: cto@deadstartup.invalid -> replaced_by: cto_new@realcompany.com | reason: Replaced bad domain`.

---

### Example 6: Multi-Round Follow-up Campaign with Response Suppression
* **Setup:** 100 contacts, `repeat_rounds = 3`, `min_round_gap_days = 7`.
* **Execution:**
  * **Round 1:** 100 emails sent.
    * 5 recipients reply.
    * 3 recipients click unsubscribe (`UNSUBSCRIBED`).
    * 2 emails hard bounce (`BOUNCED`).
    * 90 recipients do not reply.
  * **Cooldown Period:** Engine enters 7-day standby window. Zero emails sent for this campaign during the 7 days.
  * **Round 2 (Day 8):**
    * Suppression filter runs: 5 replies + 3 unsubscribed + 2 bounced = 10 permanently suppressed.
    * Round 2 queues exactly 90 contacts with Follow-up Subject & Template ("Following up on my previous note...").
    * 4 recipients reply, 1 unsubscribes.
  * **Cooldown Period:** Another 7-day cooldown.
  * **Round 3 (Day 16):**
    * Suppression filter runs: 85 eligible contacts queued for final round.
  * **Finish (Day 19):** All 3 rounds complete. Campaign status transitions to `COMPLETED`. User receives final report email summarizing 100 initial leads, 9 total replies (9% reply rate), and 0 spam complaints.

---

### Example 7: Ad-Hoc Size 1 Single Send
* **Setup:** User discovers a high-priority recruiter on LinkedIn and wants to send one email immediately without adding them to a bulk batch.
* **Execution:**
  * User opens "Quick Send", enters Recruiter email, name, and JD snippet, and clicks "Send Now".
  * Engine creates ephemeral ad-hoc send job ($N = 1$).
  * Pre-send check resolves MX records in 45ms.
  * AI Personalizer calls Gemini with user's BYOK key to generate tailored pitch in 1.2s.
  * Dispatches via user's primary Apps Script relay over HTTPS:443.
  * Audit log recorded in `messages` and `send_events`.
* **Outcome:** Delivered in under 3 seconds with identical encryption, logging, and security as a 300-lead enterprise batch.

---

## 5. Deliverability Safety Risk Matrix

| Configuration | Risk Level | Engine Action / Warning |
| :--- | :--- | :--- |
| $\le 30$ emails/day per personal account | **SAFE** | Green status. Optimal delivery rate and Gmail inbox placement. |
| $31 - 50$ emails/day per personal account | **MODERATE** | Informational notice: Recommended only for accounts aged $>3$ months. |
| $> 50$ emails/day per personal account | **HIGH RISK** | Prominent warning modal required before saving: *"High Deliverability Risk: Google strictly monitors personal accounts sending >50/day. High velocity risks spam flagging, temporary rate limits, or account suspension. Consider connecting an additional relay."* |
| $> 100$ emails/day total without warm-up | **CRITICAL** | Enforces gradual warm-up ramp (Day 1: 20, Day 2: 30, Day 3: 45...). |

---

## 6. M2 Test Plan (To Be Executed After User Approval)

1. **Test M2-T1 (Campaign Model & Migration):** Verify Alembic migration creates `campaigns`, `contact_replacements`, adds new columns to `contacts` and `sender_relays`, and backfills existing data with zero data loss.
2. **Test M2-T2 (Fair-Share Budget Balancer):** Unit test distributing 30 emails across 3 relays with equal caps (10/10/10) and custom caps (4/13/13).
3. **Test M2-T3 (Dynamic Mid-Run Addition):** Add 20 contacts to an active campaign; assert sequence order is preserved and worker dispatches all 20 after current batch.
4. **Test M2-T4 (Repeat Rounds Suppression):** Simulate 10 contacts with 1 reply and 1 bounce; verify Round 2 queues exactly 8 contacts.
5. **Test M2-T5 (Not Working Quarantine & Replacement):** Mock DNS NXDOMAIN failure; assert contact moves to Not Working; trigger replacement API; assert replacement inherits sequence position and audit trail is recorded.
6. **Test M2-T6 (Size 1 Ad-Hoc Send):** Execute single send endpoint; verify end-to-end delivery through mock relay with AI personalization.
7. **Test M2-T7 (Personal Account Cap Warning):** Test that updating sender relay budget to $>50$ returns validation warning response.

---
**END OF SPECIFICATION — WAITING FOR USER "GO" BEFORE COMMENCING CODE IMPLEMENTATION**
