# System Architecture & Core Logic Guide
**POS Till & Back Office Unrestricted Audit Engine**

---

## 1. The Mental Model (In Plain English)

### The Real-World Scenario
In modern retail hypermarkets and store chains:
- **1 Back Office (BO) Server:** Runs the in-store central application (`Ubuntu Linux`), fixed at IP `.12` (or `.15`).
- **POS Counters (Tills):** 10 to 100 individual cashier billing machines (`Ubuntu Linux`), starting at IP `.112` up to `.211`.

Before this software, verifying application versions, testing payment gateway URLs (PineLab, Paytm), and editing config properties required manually logging into every machine via PuTTY one by one.

### What This Software Does
This application is a **high-throughput, multi-threaded SSH automation console**:
1. You input a store IP (or upload an Excel sheet with dozens of stores).
2. It expands the store into concrete network endpoints (BO + Tills 1..N).
3. It dispatches parallel worker threads (capped at 100 concurrent SSH connections globally).
4. It runs sub-second remote checks (`stat`, `grep`, `curl`, or custom bash).
5. It streams live, sorted results to a Tkinter user interface without freezing the desktop window.

---

## 2. The Core Boundaries & Rules Matrix

| Rule / Check | Bound | File Location | Purpose & Implementation |
|---|---|---|---|
| **Max Tills Limit** | `1 .. 100` | `ui/components/target_card.py`<br>`Lines 79-95` | **IP Octet Bound:** Tills start at `.112`. With 100 tills, the 4th octet reaches `.211`. Capping at 100 guarantees the IP never overflows past `.254`. Real-time keypress validation rejects any keystroke that makes the value $>100$. |
| **Max Batch Size** | `1 .. 10 Stores` | `ui/components/target_card.py`<br>`Lines 154-180` | **Socket & Concurrency Ceiling:** In bulk mode, controls how many stores are probed simultaneously. Clamped to 10 so that active network sockets never overwhelm Windows or trigger store firewalls. |
| **SSH Timeout** | `1 .. 30 Seconds` | `ui/components/credentials_card.py`<br>`Lines 45-65` | **Anti-Hanging Protection:** Unreachable tills abort cleanly after 30s and flag as `OFFLINE`, preventing threads from getting stuck indefinitely. |
| **Strict 10. IP Check** | `ip.startswith("10.")` | `storage/store_reader.py` (L20)<br>`ui/app.py` (L219, L316) | **Enterprise Perimeter Guard:** Guarantees commands and audits execute exclusively against the internal corporate POS network (`10.0.0.0/8`). |
| **Safety Guard** | `is_rm_rf_blocked()` | `core/safety_guard.py`<br>`Lines 27-46` | **Disaster Prevention:** In unrestricted mode, all commands (systemctl, sed, kill, ps) run freely, but `rm -rf` and recursive-force variants are intercepted and blocked on the client side. |
| **Size Tolerance** | `±0.3 MB` (314 KB) | `core/file_checker.py`<br>`Lines 70-90` | **Filesystem Invariant:** Ubuntu GUI displays base-10 decimal MB, while filesystem uses base-2 binary MiB. 0.3 MB tolerance prevents false "MISMATCH" alerts due to rounding. |

---

## 3. Deep Dive into Key Components

### 3.1 Till Numbering & IP Resolution (`models/target.py`)
```
Subnet: 10.14.22.x
├── BO Server : 10.14.22.12 (Base)
├── Till 01   : 10.14.22.112 (112 + 0)
├── Till 02   : 10.14.22.113 (112 + 1)
└── Till 100  : 10.14.22.211 (112 + 99)
```
- **UAT Mode:** If "UAT" is selected or present in the store code, the app bypasses automatic `.12` and `.112` offsets and targets the exact IP provided in the UI.
- **Specific Tills:** Supports string ranges like `"1, 2, 5-8"`, resolving strictly to Tills 1, 2, 5, 6, 7, and 8.

### 3.2 Sliding-Window Concurrency (`core/parallel_runner.py`)
- **Queue-Based Admission:** Stores wait in a pending list.
- **Global SSH Budget:** Max 100 simultaneous connections. If Store A needs 50 tills and Store B needs 40 tills, both run in parallel ($50 + 40 = 90 \le 100$). A third store needing 20 tills will wait until Store A or B finishes and releases its connection quota.
- **Worker Recycling:** Completed stores are retired, freeing slots for incoming stores.

### 3.3 Safety Guard Regex Interceptor (`core/safety_guard.py`)
Intercepts destructive deletion syntax before any SSH packet is sent:
1. **Combined:** `\brm\s+-[a-z0-9]*r[a-z0-9]*f` (e.g. `rm -rf`, `rm -fr`, `rm -rfi`)
2. **Dispersed:** `\brm\b` with separate `-r` and `-f` flags (e.g. `rm -r -f`, `rm --recursive --force`)

### 3.4 Why the UI Never Freezes (`ui/app.py`)
- SSH execution runs completely in background worker threads (`daemon=True`).
- Results are posted to a thread-safe `queue.Queue`.
- The Tkinter main thread runs a recurring timer (`root.after(50, self._consume_events)`) that pops completed results and updates the canvas at 20 FPS smoothly.

### 3.5 Deterministic Store & Till Ordering
Because thread pools execute concurrently, Till 5 might finish before Till 1.
Every result object tracks:
- `store_order_index`: Sequence in which the store was entered.
- `till_num`: Numerical till index (0 for BO, 1..N for Tills).

The table renders items strictly sorted by `(store_order_index, till_num)`, ensuring output is always grouped by Store and in sequential order.

### 3.6 Reentrant Lock (`threading.RLock`) in `ConfigManager`
Standard `threading.Lock()` cannot be acquired twice by the same thread. When `reload()` acquired the lock and called `_load()`, it froze the entire application on launch.
Changing to `threading.RLock()` allows nested reentrant acquisition on the main thread, fixing the startup hang.

