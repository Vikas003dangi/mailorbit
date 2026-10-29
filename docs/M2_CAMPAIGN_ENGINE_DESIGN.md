# MailOrbit Milestone 2: Campaign Engine Redesign
## Revised Technical Architecture & Implementation Specification (PLAN ONLY)

**Date:** 2026-10-29  
**Revision:** v2.0 (Single Sender Account Fair-Share Model)  
**Status:** DESIGN / PLAN ONLY (Awaiting User Approval; No M2 Code Written)  
**Compatibility:** 100% backward-compatible with existing Auth, Encryption, Senders/Relays, and Postgres Queue. Zero data loss via non-destructive Alembic migration.

---

## 1. Core Architecture: Single Sender Account Model

In this model, **the daily budget belongs strictly to ONE SENDER ACCOUNT (one Gmail/relay)**, defaulting to **30 emails/day**. Multi-sender rotation is deferred to a future phase.

```
+-----------------------------------------------------------------------------------------+
|                                ONE SENDER RELAY ACCOUNT                                 |
|                               (e.g., you@gmail.com)                                     |
|                                                                                         |
|  - Configurable Daily Limit: default 30/day (warning modal if > 30, ceiling = quota)    |
|  - Real-time Rolling Quota: reads MailApp.getRemainingDailyQuota()                      |
+-----------------------------------------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          | hosts                                             | hosts
          v                                                   v
+-------------------------------+                   +-------------------------------+
|     CAMPAIGN A ("Designers")  |                   |     CAMPAIGN B ("Engineers")  |
+-------------------------------+                   +-------------------------------+
          |                                                   |
    +-----+-----+                                       +-----+-----+
    |           |                                       |           |
    v           v                                       v           v
[Sub-Batch 1] [Sub-Batch 2]                       [Sub-Batch 1] [Sub-Batch 2]
```

### 1.1 Water-Filling Fair-Share Balancing Algorithm
1. **Scope:** The sender account's daily allowance (default 30/day, clamped to `MailApp.getRemainingDailyQuota()`) is distributed across all **active sub-batches** across all active campaigns attached to that sender using **water-filling**:
   - Each active sub-batch is assigned an equal base share $\lfloor \text{budget} / N \rfloor$.
   - Each sub-batch's allocation is capped at its current `pending_count`.
   - Any leftover unallocated units from capped sub-batches are pooled and redistributed equally among the remaining unsatisfied sub-batches.
   - The process repeats until the daily budget is fully allocated or all active sub-batches have zero pending leads.
   - Any remaining integer units ($< \text{active count}$) are distributed 1-by-1 in priority/creation order.

```python
def water_fill_fair_share(sub_batches: List[SubBatch], daily_budget: int) -> Dict[uuid.UUID, int]:
    allocations = {sb.id: 0 for sb in sub_batches}
    pending = {sb.id: sb.pending_count for sb in sub_batches}
    active_pool = [sb.id for sb in sub_batches if sb.pending_count > 0]
    remaining_budget = daily_budget

    while remaining_budget > 0 and active_pool:
        equal_share = remaining_budget // len(active_pool)
        if equal_share == 0:
            for sb_id in list(active_pool):
                if remaining_budget == 0:
                    break
                if pending[sb_id] > allocations[sb_id]:
                    allocations[sb_id] += 1
                    remaining_budget -= 1
            break

        progress_made = False
        for sb_id in list(active_pool):
            needed = pending[sb_id] - allocations[sb_id]
            grant = min(needed, equal_share)
            if grant > 0:
                allocations[sb_id] += grant
                remaining_budget -= grant
                progress_made = True
            if allocations[sb_id] >= pending[sb_id]:
                active_pool.remove(sb_id)

        if not progress_made:
            break

    return allocations
```
3. **Ceiling:** The absolute ceiling is the sender relay's real rolling 24-hour remaining quota returned by `MailApp.getRemainingDailyQuota()`. If remaining quota $< 30$, sending stops at the real quota.
4. **Safety Risk Warning:** If a user configures a daily budget $>30$ on a personal Gmail account, the UI displays a warning modal requiring explicit acknowledgement:
   > *"Deliverability Notice: Setting a daily limit above 30 on a personal Gmail account increases the risk of Google spam filtering or temporary account limits. Real remaining quota is [X]. Do you wish to proceed?"*

---

## 2. Google Apps Script Rolling 24-Hour Quota Handling

### 2.1 Quota Reset Mechanics
* Google Apps Script quotas operate on a **rolling 24-hour window** calculated from the time each email is dispatched, **not a fixed wall-clock time like 06:00 IST**.
* Consumer `@gmail.com` accounts have a base quota of 100 emails/rolling 24h. Google Workspace accounts have 1,500/rolling 24h.

### 2.2 Relay Protocol & Failure Manifestation
1. **Telemetry in Ping/Send:** In every response from the Google Apps Script Web App relay (`doPost`), the relay includes:
   ```json
   {
     "status": "SENT",
     "remaining_daily_quota": 68
   }
   ```
   Obtained in Apps Script via `MailApp.getRemainingDailyQuota()`.
2. **How Quota Exhaustion Arrives:**
   * When Google's quota is exhausted, Apps Script does *not* throw an HTTP 429.
   * Google Apps Script runtime halts execution with an uncatchable runtime exception:
     `Exception: Service invoked too many times for one day: email.`
   * The Apps Script Web App wrapper catches or returns this as:
     `HTTP 200 OK` with JSON body:
     ```json
     {
       "status": "ERROR",
       "error": "Exception: Service invoked too many times for one day: email.",
       "remaining_daily_quota": 0
     }
     ```
3. **Engine Action:**
   * The engine inspects `remaining_daily_quota`. If $0$ or if the error contains `"Service invoked too many times"`, the engine:
     a) Immediately pauses active sub-batches on that sender relay.
     b) Sets relay status to `QUOTA_EXCEEDED`.
     c) Records `quota_exhausted_at = now()`.
     d) Does not attempt further sends until the rolling window clears (probed via test ping without sending).

---

## 3. Campaign & Batch Management Features

### 3.1 Batch Creation: Manual or Automatic
* **Automatic:** User imports leads and sets a batch size (e.g., 10 or 30). The engine automatically partitions leads into `SubBatch 1`, `SubBatch 2`, etc.
* **Manual:** User creates named sub-batches manually and moves selected contacts between them.

### 3.2 Moving Contacts Between Sub-Batches
* Users can select contacts via checkboxes in the UI and click **"Move to Sub-Batch..."** to reassign them to another sub-batch within the same campaign.
* Sequence positions within the destination sub-batch are appended sequentially.

### 3.3 Flexible Contact Input
* **CSV / Excel:** File upload with fuzzy column mapping.
* **Direct Paste Box:** Text area accepting emails separated by **commas or newlines** (e.g. `alice@co.com, bob@co.com` or line-delimited lists), with automatic whitespace trimming and format validation.

### 3.4 Calendar Scheduling
* **Start Date Picker:** Includes quick shortcuts: **"Today"** and **"Tomorrow"**.
* **Start Time & Timezone:** User-specified send time (e.g., 09:30 AM) in user's timezone.
* **Skip Dates:** Date picker allowing users to select company holidays or dates to pause (e.g., `["2026-11-26", "2026-12-25"]`).
* **Stop Date:** Optional calendar date after which all campaign dispatches automatically halt.

### 3.5 One-Click Auto-Balance
* Clicking **"Auto-Balance"** on a sender account recalculates the target daily allocation across all active sub-batches and campaigns, displaying the expected days to completion.

### 3.6 Dynamic Mid-Run Ingestion & New Campaigns Joining
* **Adding Leads Mid-Run:** Contacts added to a running campaign append at `sequence_position = current_max + 1`. Active workers continue dispatching without interruption; stats auto-recalculate.
* **New Campaign Joining a Running Sender:** When Campaign 2 is activated on a sender already running Campaign 1, the fair-share engine automatically adjusts the next day's allocation (e.g. from 30/0 to 15/15), sharing the sender's budget without exceeding 30/day.

---

## 4. Quarantine, Replacement & Repeat Round Guardrails

### 4.1 "Not Working" Folder & Automatic Cascade Replacement
* **Trigger:** Contacts failing pre-send verification (bad format, NXDOMAIN, no MX/A) or returning permanent fatal rejections (5xx user unknown) are tagged `is_not_working = TRUE`, `status = "INACTIVE"` and moved to the campaign's **"Not Working"** section.
* **Automatic Replacement:** The engine immediately draws the next `PENDING` contact from the **SAME campaign**.
* **Cascade Replacement:** If the replacement contact *also* fails DNS or bounces, it is *also* quarantined, and the engine draws the next pending contact until a valid contact is delivered or the pending pool is exhausted.
* **Audit Trail:** Every replacement writes to `contact_replacements`:
  `original_contact_id -> replaced_by_contact_id | timestamp | reason`.
* **Budget Safety on Manual Replacement:** If a user manually replaces a failed contact via the "Not Working" screen, the replacement inherits the sequence position, but **cannot be dispatched today if the sender has already delivered its daily limit (30)**. It dispatches in the next available scheduled send window.

### 4.2 Repeat Rounds with Message Variation
* **Cooldown Period:** Cooldown begins strictly **from the timestamp the previous round completed**, not when it started (e.g., exactly 7 full days from Round 1 completion).
* **Permanent Suppression Filter:** The engine permanently excludes any contact who:
  1. Replied to a previous round (`status == "REPLIED"`).
  2. Unsubscribed or clicked List-Unsubscribe (`status == "UNSUBSCRIBED"`).
  3. Bounced or was marked inactive (`status in ["BOUNCED", "INACTIVE"]` or `is_not_working == True`).
  4. Is on the global `do_not_contact` table.
* **Message Variation:** Each subsequent round MUST vary the outreach copy:
  * **AI Variation:** Gemini rewrites the angle with a follow-up directive (*"Follow up conversationally referencing my earlier email, highlighting a different skill from my profile"*).
  * **Template Variation:** User selects a dedicated Round 2 / Round 3 follow-up template.

---

## 5. Seven Worked Numerical Examples (Single Sender Model)

*Assumptions: All examples assume 1 personal Gmail sender account with a user-configured daily budget of 30 emails/day, operating within Google's rolling quota.*

### Example 1: Standard Fair-Share Split Across 3 Sub-Batches on One Sender
* **Setup:** 1 Sender (budget: 30/day). Campaign has 90 contacts divided into 3 sub-batches (30 each).
* **Math:**
  * Day 1: 3 active sub-batches share 30 budget equally ($30 / 3 = 10$ each):
    * Sub-batch 1 sends contacts #1–#10 (20 remain).
    * Sub-batch 2 sends contacts #31–#40 (20 remain).
    * Sub-batch 3 sends contacts #61–#70 (20 remain).
    * Sender total today: $10 + 10 + 10 = 30$. Sender cap reached.
  * Day 2: Each sends 10 contacts (#11–#20, #41–#50, #71–#80). Total sent: 30.
  * Day 3: Each sends 10 contacts (#21–#30, #51–#60, #81–#90). Total sent: 30.
* **Outcome:** Exactly 3 calendar days. Daily volume never exceeds 30.

---

### Example 2: Two Campaigns Sharing One Sender Account
* **Setup:** 1 Sender (budget: 30/day).
  * Campaign A ("Designers"): 40 contacts in 2 sub-batches (A1: 20, A2: 20).
  * Campaign B ("Engineers"): 40 contacts in 2 sub-batches (B1: 20, B2: 20).
* **Math:**
  * Total active sub-batches across sender: 4.
  * Fair share: $30 / 4 = 7$ with remainder 2.
    * Sub-batch A1 gets 8 emails.
    * Sub-batch A2 gets 8 emails. (Campaign A total: 16).
    * Sub-batch B1 gets 7 emails.
    * Sub-batch B2 gets 7 emails. (Campaign B total: 14).
    * Sender total today: $8 + 8 + 7 + 7 = 30$.
* **Outcome:** Both campaigns make balanced progress concurrently without exceeding the sender's 30/day limit.

---

### Example 3: Two Sub-Batches with Small Pending Queues (10 Pending Each)
* **Setup:** 1 Sender (budget: 30/day).
  * Sub-batch A has 10 pending contacts.
  * Sub-batch B has 10 pending contacts.
* **Water-Filling Execution:**
  * Active sub-batches: 2.
  * Total pending across sender: $10 + 10 = 20 \le 30$.
  * Base equal share: $30 / 2 = 15$.
  * Sub-batch A caps at its pending count: $10$ (cannot send 15).
  * Sub-batch B caps at its pending count: $10$ (cannot send 15).
  * Leftover budget: $30 - 20 = 10$ unused (no pending leads remain to consume it).
* **Final Numbers:**
  * Sub-batch A sends: **10** (completes).
  * Sub-batch B sends: **10** (completes).
  * Unused daily budget: **10**.
  * Total dispatched today: **20**.

---

### Example 4: Asymmetric Sub-Batches (Redistribution of Leftover Share)
* **Setup:** 1 Sender (budget: 30/day).
  * Sub-batch 1 has 4 pending contacts.
  * Sub-batch 2 has 30 pending contacts.
* **Water-Filling Execution:**
  * Active candidates: 2.
  * Iteration 1: Base share $= 30 / 2 = 15$.
    * Sub-batch 1 needs $4 \le 15 \to$ allocated **4** (Sub-batch 1 completes; removed from active pool).
    * Sub-batch 2 allocated initial share of **15**.
    * Unallocated leftover: $30 - 4 - 15 = 11$.
  * Iteration 2: 1 active candidate (Sub-batch 2).
    * Sub-batch 2 needs $30 - 15 = 15 > 11$.
    * Entire leftover 11 is granted to Sub-batch 2: $15 + 11 = \mathbf{26}$.
* **Final Numbers:**
  * Sub-batch 1 sends: **4** (0 remain pending; completed).
  * Sub-batch 2 sends: **26** (4 remain pending for tomorrow).
  * Total dispatched today: **30** ($4 + 26 = 30$).
  *(Note: If Sub-batch 2 only had 20 pending leads, it would cap at 20, yielding $4 + 20 = 24$ sent and 6 unused).*

---

### Example 5: Automatic Cascade Replacement & Manual Replacement Budget Safety
* **Setup:** 1 Sender (budget: 30/day). Sub-batch of 30 leads is actively dispatching.
* **Cascade Replacement Execution:**
  * Lead #12 fails DNS MX check (`NXDOMAIN`). Quarantined to "Not Working".
  * Engine automatically draws next pending contact (#31) from SAME campaign.
  * Lead #31 has a malformed syntax error. Quarantined to "Not Working" as well.
  * Engine automatically draws next pending contact (#32). Lead #32 is valid and delivers.
  * Day finishes: exactly 30 valid emails sent.
* **Manual Replacement Action:**
  * User opens "Not Working" section and enters a new valid email for Lead #12.
  * Lead #12's replacement is saved and inherits sequence position 12.
  * **Budget Safety Check:** Since the sender already dispatched 30 emails today, the replacement is **held for tomorrow's send window**. It cannot push today's total to 31.
* **Audit Trail:**
  * `#12 (bad domain)` $\to$ auto-replaced by `#31 (syntax error)` $\to$ auto-replaced by `#32 (delivered)`.
  * `#12` $\to$ manual replacement queued for next day.

---

### Example 6: Apps Script Rolling 24-Hour Quota Ceiling
* **Setup:** Sender daily limit set to 30. Personal Gmail account (base 100 rolling quota).
* **Execution:**
  * On Monday at 11:00 AM, first email dispatches. Rolling 24-hour window opens.
  * Relay reports `MailApp.getRemainingDailyQuota() = 100`.
  * Day 1 sends 30 emails. Relay quota drops to 70.
  * On Tuesday at 09:00 AM (22 hours later), scheduled window opens.
  * Relay reports remaining quota: `70`.
  * Engine calculates: $\min(\text{budget}=30, \text{remaining}=70) = 30$. Dispatches 30.
* **Quota Exhaustion Scenario:**
  * Suppose the user sent 65 emails outside MailOrbit via their personal Gmail.
  * Relay reports `MailApp.getRemainingDailyQuota() = 12`.
  * Engine clamps send: $\min(30, 12) = 12$.
  * Sends 12 emails, then pauses cleanly with status `QUOTA_EXCEEDED` and alerts user:
    `"Relay rolling quota reached. 18 emails postponed until Google rolling quota replenishes."`
  * Avoids runtime exception crash.

---

### Example 7: Repeat Rounds with Message Variation & Cooldown
* **Setup:** 1 Sender (budget: 30/day). Campaign of 90 contacts, 3 repeat rounds, 7-day cooldown.
* **Round 1:**
  * Days 1–3: 90 emails sent (30/day).
  * Completed on Day 3 at 11:30 AM.
  * Outcomes: 6 replied, 2 opted out, 2 bounced. 10 permanently suppressed.
  * 80 contacts eligible for Round 2.
* **Cooldown:** Exactly 7 days from Round 1 completion (Day 3, 11:30 AM to Day 10, 11:30 AM). Zero emails sent.
* **Round 2 (Day 11):**
  * Uses Round 2 Follow-up Template / AI follow-up prompt.
  * Days 11–13: 80 contacts sent (Day 11: 30, Day 12: 30, Day 13: 20).
  * Completed on Day 13 at 10:15 AM.
  * 4 replied, 1 opted out. 75 contacts eligible for Round 3.
* **Cooldown:** Exactly 7 days from Day 13 completion.
* **Round 3 (Final Round):**
  * Uses Round 3 Breakup Template.
  * Days 21–23: 75 contacts sent.
  * Campaign marks `COMPLETED`. Notification email sent to user.

---

## 6. Milestone Split: M2a vs M2b

To ensure zero downtime, thorough test verification, and clean delivery, Milestone 2 is split into two phases:

### Phase M2a: Backend Engine, Data Models, Scheduler & Migration
* **Scope:**
  1. Alembic migration adding `campaigns` and `contact_replacements` tables, and adding `campaign_id`, `sequence_position`, `is_not_working`, `replaced_by_contact_id` to existing tables.
  2. Non-destructive backfill: Existing batches/contacts assigned to a default Campaign.
  3. Single-sender fair-share auto-balancer algorithm.
  4. Apps Script rolling quota reader (`getRemainingDailyQuota`) and pause handler.
  5. Schedule cache & calendar engine (active days, skip dates, stop date, Today/Tomorrow).
  6. "Not Working" auto-cascade replacement logic and audit trail.
  7. Repeat rounds cooldown and suppression filter.
  8. Size 1..N ad-hoc send path.
* **Test Plan List (M2a):**
  * `test_m2a_alembic_migration_zero_data_loss`: Verifies schema updates without dropping existing data.
  * `test_m2a_fair_share_sub_batch_balancer`: Tests 30 budget split across 3 sub-batches (10/10/10) and uneven sub-batches.
  * `test_m2a_two_campaigns_sharing_one_sender`: Tests budget division across multiple campaigns on one sender.
  * `test_m2a_apps_script_rolling_quota_clamp`: Verifies engine clamps sending when remaining quota $< 30$.
  * `test_m2a_dynamic_lead_ingestion`: Verifies mid-run appended contacts receive incremented sequence numbers.
  * `test_m2a_cascade_replacement`: Verifies a failed replacement draws the next candidate and writes audit rows.
  * `test_m2a_manual_replacement_respects_daily_budget`: Verifies manual replacement cannot exceed 30/day limit.
  * `test_m2a_repeat_rounds_suppression`: Verifies replies, bounces, and unsubscribes are excluded from Round 2.
  * `test_m2a_repeat_rounds_cooldown`: Verifies round cannot fire before 7-day cooldown from previous completion.
  * `test_m2a_size_1_adhoc_send`: Verifies single send executes through standard pipeline.
* **Live Site Checks (M2a):**
  * Database schema verified in Neon Console with zero broken tables.
  * API endpoints operational: `POST /api/v1/campaigns`, `POST /api/v1/campaigns/{id}/auto-balance`, `GET /api/v1/campaigns/{id}/not-working`.
  * `/tick` answers `"standby"` with zero database queries when nothing is due.

### Phase M2b: User Interface, Screens & Workflows
* **Scope:**
  1. **Campaign Overview & Creation Modal:** Start date picker with "Today" and "Tomorrow" shortcuts, skip dates multi-select, stop date, daily budget input with $>30$ warning modal.
  2. **Sub-Batch Manager:** Toggle between Auto-partition and Manual creation. Drag/move contacts between sub-batches.
  3. **Direct Paste Area:** Text box for comma- or newline-separated email lists.
  4. **One-Click Auto-Balance Button:** Visual preview of daily distribution across sub-batches.
  5. **"Not Working" Quarantine Section:** Table of failed leads showing failure reason (NXDOMAIN, syntax, bounce), replacement history pill, and "Replace" modal.
  6. **Repeat Rounds Configuration Tab:** Cooldown gap selector, max rounds cap, and Round 2/3 message angle selector.
  7. **Enhanced Dashboard Metrics Strip:** Scheduled, Running, Completed, Failed/Paused counts.
* **Test Plan List (M2b):**
  * Unit tests for frontend state transitions and date helpers.
  * Playwright E2E browser tests:
    * Create a campaign with Today shortcut $\to$ paste 5 contacts $\to$ click Auto-Balance.
    * Move a contact from Sub-batch 1 to Sub-batch 2.
    * Trigger replacement on a quarantined lead in "Not Working" tab.
    * Configure budget $>30$ and verify safety warning modal displays.
* **Live Site Checks (M2b):**
  * Live navigation in browser at `/`.
  * Smooth UI with zero hydration errors or console warnings.
  * Visual inspection of "Not Working" tab and replacement audit modal.

---

**END OF REVISED SPECIFICATION — STOPPED AND WAITING FOR USER APPROVAL BEFORE COMMENCING M2a CODE**
