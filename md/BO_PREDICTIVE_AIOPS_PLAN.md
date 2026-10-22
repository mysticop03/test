# Predictive Server Maintenance & AIOps Architecture Plan
## Autonomous BO Server Lockup & Deadlock Prevention Engine

> **Document Status:** Future Architectural Roadmap  
> **Target Domain:** Data Science, AIOps, Predictive Maintenance, Distributed Telemetry  
> **Environment:** Air-gapped / Restricted Enterprise Retail Network (Zero Cloud Leaks)

---

## 1. Executive Summary & Vision

In high-volume enterprise retail environments, the Back Office (BO) server at `.12` is the central brain of every branch. It hosts critical transaction databases (Microsoft SQL Server / Linux SQL engine), pricing catalogs, and inventory synchronization services.

When a BO server freezes or becomes unresponsive, hundreds of checkout tills timeout, halting customer billing. Currently, failures are addressed **reactively** after store managers report that "the BO server is stuck."

**The Objective:**  
Upgrade the existing auditing infrastructure into a **Predictive AIOps Engine** that continuously ingests OS telemetry (`uptime`, `free`, `df`, `vmstat`) and database concurrency state (`sp_who2`), models degradation patterns, and forecasts lockups **1 to 4 hours before they happen**.

```
┌────────────────────────────────────────────────────────┐
│             BO Server Telemetry Ingestion              │
├───────────────────────────┬────────────────────────────┤
│   OS Kernel Metrics       │    Database Lock State     │
│  (uptime, free, df, vm)   │   (EXEC sp_who2 via sqlcmd)│
└─────────────┬─────────────┴──────────────┬─────────────┘
              │                            │
              ▼                            ▼
┌───────────────────────────┐┌───────────────────────────┐
│ Feature Engineering (OS)  ││ Graph Lock Engine (DB)    │
│  - Available RAM Ratio    ││  - Blocked Sessions Count │
│  - Swap Thrashing Pct     ││  - Head Blocker SPID      │
│  - Load-to-Core Ratio     ││  - Directed Cycle (Dead)  │
│  - I/O Wait Bottleneck    ││  - Lock Cascade Depth     │
└─────────────┬─────────────┘└─────────────┬─────────────┘
              │                            │
              └──────────────┬─────────────┘
                             ▼
┌────────────────────────────────────────────────────────┐
│           Predictive Data Science Pipeline             │
│   • Isolation Forest (Unsupervised Anomaly Detection)  │
│   • Random Forest / Logistic Risk Scorer (0 - 100%)    │
│   • Root-Cause Attribution & Early-Warning Advisory    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Why BO Servers Get "Stuck": The 4 Critical Failure Modes

### Mode 1: Swap Thrashing (The Slow Memory Bleed)
* **Mechanism:** Java POS services or database connection pools experience gradual memory leaks over weeks of uptime.
* **Tipping Point:** When physical available RAM drops below 5–8%, the Linux kernel aggressively pages memory to disk via `kswapd0`, pegging CPU cores at 100% and freezing user-space processes.

### Mode 2: Storage Exhaustion (Write Failures)
* **Mechanism:** Transaction logs (`.ldf` or MySQL binary logs) or unrotated debug logs fill the root `/` partition.
* **Tipping Point:** At 98–100% disk utilization, write operations fail immediately, causing database engines to lock up to prevent database corruption.

### Mode 3: Database Deadlocks & Lock Cascades (`sp_who2`)
* **Mechanism:** A background batch query (e.g. daily inventory sync or pricing update) takes exclusive table locks. Tills attempting to record customer bills get queued behind this lock.
* **Tipping Point:** 50+ tills queue behind a single **Head Blocker SPID**. SQL Server exhausts its worker thread pool, causing all tills to report connection timeouts (`Socket Error 10054`). If two SPIDs wait on each other's resources, a **Circular Deadlock** freezes both transactions.

### Mode 4: I/O Queue Congestion (Hardware Bottleneck)
* **Mechanism:** Failing SSDs, disk controllers, or saturated SATA buses cause processes to enter the uninterruptible sleep state (`D` state in Linux, `b` column in `vmstat`).

---

## 3. Telemetry Ingestion Architecture (100% Read-Only)

All data collection adheres to the existing `safety_guard.py` 100% read-only policy on the BO server:

### A. OS Telemetry Probe (Single Compound Bash Execution)
```bash
uptime; echo "---MEM---"; free -m; echo "---DISK---"; df -m /; echo "---VMSTAT---"; vmstat 1 2 | tail -n 1
```

### B. Database Concurrency Probe (`sp_who2`)
Executed using local read-only database authentication:
```bash
sqlcmd -S localhost -E -Q "EXEC sp_who2" -s"," -W
```
Or via Dynamic Management Views (DMVs):
```sql
SELECT 
    r.session_id AS spid,
    r.blocking_session_id AS blkby,
    r.status,
    r.wait_type,
    r.wait_time,
    r.cpu_time,
    r.total_elapsed_time,
    t.text AS sql_text
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0;
```

---

## 4. Feature Engineering Pipeline (Mathematical & Graph Theory)

The raw telemetry strings are converted into a structured feature vector $X$:

### 4.1 Continuous Numerical Features (OS)
* `ram_available_pct` $= \frac{\text{MemAvailable}}{\text{MemTotal}} \times 100$
* `swap_used_pct` $= \frac{\text{SwapUsed}}{\text{SwapTotal}} \times 100$
* `disk_used_pct` $= \frac{\text{DiskUsed}}{\text{DiskTotal}} \times 100$
* `load_to_core_ratio` $= \frac{\text{15min Load Average}}{\text{CPU Core Count}}$
* `io_wait_processes` $=$ Value of column `b` from `vmstat` (processes in uninterruptible disk I/O)
* `uptime_days` $=$ Total days without a system reboot

### 4.2 Graph-Theoretic Concurrency Features (`sp_who2`)
In `sp_who2`, the relationship between `SPID` (Process ID) and `BlkBy` (Blocked By) forms a **Directed Graph** $G = (V, E)$:
* **Directed Edge:** An edge exists $A \rightarrow B$ if session $A$ is waiting for session $B$ to release a lock.
* `blocked_sessions_count`: Total nodes where in-degree $> 0$ (number of tills currently frozen).
* `head_blocker_spid`: The root node in the lock tree with out-degree $> 0$ and in-degree $= 0$.
* `blocking_depth`: The maximum path length from any blocked till to the head blocker.
* `is_circular_deadlock`: Boolean flag determined using cycle-detection algorithms (DFS / Tarjan's algorithm). A cycle ($A \rightarrow B \rightarrow A$) indicates an unresolvable deadlock.

---

## 5. Machine Learning & Predictive Modeling Strategy

### Layer 1: Unsupervised Anomaly Detection (`IsolationForest`)
* **Algorithm:** Scikit-Learn `IsolationForest`
* **Purpose:** Detects unusual multi-metric degradation states that do not trigger static threshold alerts (e.g. a 20% drop in available memory accompanied by an unexpected rise in I/O wait).
* **Output:** Anomaly Score $\in [-1, 1]$.

### Layer 2: Supervised Risk Classifier (`RandomForestClassifier`)
* **Target Variable:** `freeze_risk` $\in [0, 1]$
* **Predicted Probability:** Calibrated probability score ($0\%$ to $100\%$).
* **Threshold Stratification:**
  * **0% – 35% [Healthy / Green]:** Stable resources, no blocking locks.
  * **36% – 70% [Warning / Amber]:** Chronic resource degradation or lock queues forming ($12$–$24$h estimated window).
  * **71% – 100% [Critical / Red Alert]:** Severe swap thrashing, disk $>95\%$, or active deadlocks; freeze imminent within $1$–$2$ hours.

### Layer 3: Model Explainability & Root-Cause Attribution
The model computes feature contributions (via Tree SHAP or feature weightings) to explain *why* the server is at risk:
```text
Primary Driver: Database Lock Cascade (SPID 54 holding exclusive lock on 'BILL_HEADER')
Secondary Driver: Swap Thrashing (Available RAM at 6.2%, Swap at 88%)
```

---

## 6. Implementation Architecture & Module Plan

```
tills/
├── core/
│   ├── bo_telemetry_collector.py   # Extracts uptime, free, df, vmstat, and sp_who2
│   ├── sp_who2_parser.py           # Parses BlkBy, builds graph, detects deadlocks
│   ├── feature_pipeline.py         # Transforms raw telemetry into numerical feature arrays
│   ├── predictive_model.py         # Isolation Forest & Risk Scorer inference engine
│   └── safety_guard.py             # Existing 100% read-only verification
├── models/
│   └── bo_health.py                # Data classes: BOHealthRecord, ConcurrencyGraph, RiskReport
└── ui/components/
    └── bo_health_card.py           # Clean UI display card with radar gauges and alerts
```

---

## 7. Sample UI / Terminal Output Format

```text
================================================================================
   BO PREDICTIVE HEALTH & CONCURRENCY MONITOR: Store-001 (192.168.29.12)
================================================================================
Overall Health Score:       [CRITICAL RISK: 91%]
Estimated Time to Freeze:   ~45 to 90 minutes if transaction load persists

1. OS & HARDWARE HEALTH LAYER
   - RAM Available:         5.8% (360 MB remaining of 8.0 GB)  [CRITICAL]
   - Swap Utilization:      84.2% (Active thrashing detected)  [CRITICAL]
   - Root Disk Space (/):   72.1% (28 GB free)                 [HEALTHY]
   - 15-Min Load Average:   3.6x physical CPU capacity         [WARNING]
   - Disk I/O Wait Procs:   4 processes blocked in 'D' state   [WARNING]

2. DATABASE CONCURRENCY LAYER (sp_who2)
   - Active Sessions:       62 connected
   - Blocked Tills:         14 tills waiting on locks          [CRITICAL]
   - Head Blocker:          SPID 54 (User: 'sa', Program: 'Daily_Sync_Task')
   - Lock State:            Lock Cascade (Chain Depth: 4)
   - Deadlock Status:       Circular Dependency Warning on Table 'TRAN_HEADER'

3. ROOT CAUSE & ACTIONABLE REMEDIATION
   - Primary Bottleneck:    SPID 54 is executing a long table scan without NOLOCK,
                            causing a lock queue that exhausted database worker threads.
   - Recommended Action:    1. Terminate blocker: KILL 54;
                            2. Schedule pos-backend memory clean before peak shift.
================================================================================
```

---

## 8. Career & Resumé Framing Guide (For Data Science Roles)

When presenting this project in Data Science and Machine Learning interviews, frame the work as **Enterprise Applied Machine Learning for Infrastructure Resilience**:

### Highlight Points for Interviews:
1. **Real-World Telemetry Ingestion:** Emphasize that data was extracted directly from live Linux servers and SQL databases over restricted enterprise networks, not downloaded from synthetic CSV benchmarks.
2. **Feature Engineering:** Discuss the normalization of load averages by CPU core counts, swap thrashing rates, and the transformation of `sp_who2` blocked sessions into directed graph metrics.
3. **Graph Theory Algorithms:** Explain how you detected circular deadlocks using directed graph cycle detection algorithms.
4. **Offline Compliance:** Highlight that the entire ML inference engine runs 100% offline inside enterprise firewalls using pure Scikit-Learn without cloud API dependencies.
5. **Business Impact:** Preventing retail store database lockups protects thousands of dollars per hour in interrupted retail billing.

---
*Created as an architectural blueprint for future implementation.*
