# Operations Standard Operating Procedure (SOP) & Task Management

## 1. Purpose
This procedure defines standard protocols for monitoring cross-departmental operations, identifying execution delays, tracking budget allocations, and producing executive operational status reports.

## 2. Task Tracking & Delay Criteria
All enterprise operations are recorded in the central task ledger (`workspace/operations_tasks.csv`).
- **On Schedule:** `Days_Delayed == 0` and task is progressing towards its scheduled `Due_Date`.
- **Minor Delay (Watchlist):** `1 <= Days_Delayed < 5`. Monitored internally by the project manager.
- **Critical Delay (Action Required):** `Days_Delayed >= 5` or `Priority == "Critical"` when `Status != "Completed"`. Must be highlighted in executive reviews.
- **Blocked State:** Any task with `Status == "Blocked"` requires an immediate mitigation plan and assigned executive sponsor within 24 hours.

## 3. Operations Review Framework
When tasked with reviewing operations or project task ledgers:
1. **Data Inspection:** Inspect `operations_tasks.csv` using analytical tools to extract total tasks, status breakdowns, and delayed task metrics.
2. **Delay Calculation:** Compute total delayed tasks, average delay in days, and sum of affected task budgets.
3. **Blocker Analysis:** Identify dependencies (e.g., procurement delays, security audit prerequisites, external supplier bottlenecks).
4. **Reporting Structure:**
   - **Executive Summary:** Overall operational health, active vs delayed task counts, total budget at risk.
   - **Action Item Table:** Task ID, Task Name, Department, Assignee, Days Delayed, and Current Status.
   - **Remediation Plan:** Immediate next steps, resource reallocations, and required approvals.
