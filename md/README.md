# Production Ubuntu POS Till Inspector & Version Auditor

Enterprise-grade, modular, and scalable inspection tool designed for auditing **1,500 retail stores (~20,000 Ubuntu POS tills)** across low-bandwidth, high-latency store WAN links.

Built with clean architecture, zero external dependencies (standard library Python + `paramiko>=2.11.0`), and enterprise-grade security hardening.

---

## Key Highlights

- **Dual-Condition Verification**: Simultaneously validates remote WAR file sizes (with intelligent Ubuntu metric decimal and binary matching within $\pm0.3\text{ MB}$) and extracts delivery versions from `.properties` files (e.g. `v0455=deliveryversion36A`).
- **Store-Wise Concurrency**: Batches execution store-by-store (default: 2 stores at a time = ~26 tills) to protect store WAN switches and office Wi-Fi routers from connection exhaustion.
- **Strict FCFS Ordering**: Guarantees deterministic First-Come, First-Served ordering across all screens, CSV reports, and Excel sheets (`Store 1 [Tills 1-13] -> Store 2 [Tills 1-13]`) irrespective of status.
- **Re-Audit / Failure Ingestion**: Exported failure lists (`audit_mismatched_tills.csv`, `audit_offline_tills.csv`, `audit_missing_tills.csv`) can be directly loaded or pasted back into the tool to audit **only those specific failed tills**, completely skipping passing tills.
- **Zero-Dependency Excel Engine**: Fully native OpenXML `.xlsx` reader and multi-sheet generator built using Python standard library `zipfile` and `xml.etree`.
- **Enterprise Security Hardened**: Protected against Command Injection (CWE-78), CSV Formula Injection (CWE-1236), Zip Bombs (CWE-409), unauthorized CIDR scanning, and memory exhaustion.

---

## Clean Architecture Overview

```text
file_checker/
├── config.json                     # Persistent user defaults & security settings
├── requirements.txt                # Single runtime dependency: paramiko>=2.11.0
├── main.py                         # Desktop GUI Entry Point
├── gui.py                          # GUI Launcher Alias
├── cli.py                          # Headless CLI Runner for automated/cron batch audits
│
├── models/                         # Pure Domain Models
│   ├── target.py                   # StoreRecord, TillTarget, FCFS tracking, specific tills
│   └── result.py                   # AuditResult, AuditSummary, AuditStatus definitions
│
├── core/                           # Networking & Execution Engine
│   ├── safety_guard.py             # Whitelist command security validator (Mode 3)
│   ├── probe_engine.py             # Single-shot bash probes, smart dual-size matching
│   ├── ssh_worker.py               # Paramiko SSH worker, 64KB buffer cap, credential scrubbing
│   ├── batch_orchestrator.py       # Store-wise concurrency orchestrator & event queue
│   └── config_manager.py           # Thread-safe configuration manager with schema validation
│
├── storage/                        # Ingestion & Zero-Dependency Exporters
│   ├── store_reader.py             # Ingests CSV, TSV, and native .xlsx with CIDR validation
│   ├── excel_exporter.py           # Multi-sheet OpenXML (.xlsx) generator
│   └── csv_exporter.py             # Clean UTF-8 BOM CSV exporter with formula injection defense
│
├── ui/                             # Decoupled Modern Tkinter GUI (MVC Pattern)
│   ├── app.py                      # Main App Window Controller
│   ├── theme.py                    # Design tokens, color badges, typography
│   └── components/
│       ├── target_card.py          # Store IP, UAT mode, Specific Tills, Bulk file loader
│       ├── mode_card.py            # 3 Operation modes with reactive dynamic inputs
│       ├── credentials_card.py     # SSH credentials, port, socket timeout
│       ├── filter_toolbar.py       # Segmented filter pills [All] [Success] [Mismatches] [Missing] [Offline] + Search
│       ├── metrics_bar.py          # Progress bar, live status pills, elapsed timer, pause/stop
│       └── results_table.py        # Centered, sortable Treeview with status tags & detail inspector
│
├── build_exe.py                    # PyInstaller standalone executable compilation script
└── build_exe.bat                   # 1-Click Windows build script
```

---

## Three Audit Operations

### Mode 1: Version & WAR (Dual Condition) — Default
Executes a single compound bash probe over SSH in **one network round trip**:
1. Checks WAR file size in bytes (`stat -c %s`) and last modified timestamp.
2. Searches the `.properties` file for the configured keyword (`deliveryversion`), extracting the variable key and value.
3. Evaluates dual condition against expected values:
   - **`SUCCESS`**: Both WAR size (within $\pm0.3\text{ MB}$) and delivery version matched.
   - **`SIZE_MISMATCH`**: Version matched, but WAR size differed.
   - **`VERSION_MISMATCH`**: Size matched, but delivery version differed.
   - **`BOTH_MISMATCH`**: Neither matched.
   - **`FILE_MISSING`**: WAR or Properties file does not exist.
   - **`OFFLINE` / `TIMEOUT`**: Till is unreachable or socket timed out.

### Mode 2: File Info
Probes the remote path for existence, exact file size in decimal MB, and last modification timestamp.

### Mode 3: Execute Command (Diagnostic)
Executes a read-only inspection command against tills. Enforces a strict security whitelist (`uptime`, `df`, `free`, `ps`, `uname`, `date`, `cat`, `head`, `tail`, `ls`, `stat`, `hostname`, `wc`).

---

## Store & Till Targeting Rules

| Input Pattern | Example | Resolved Targets | Behavior |
| :--- | :--- | :---: | :--- |
| **Production Store** | `10.14.22.12` | 13 tills | Tills expand from offset `.112`: `10.14.22.112` through `10.14.22.124` |
| **Subnet Prefix** | `10.14.22.` | 13 tills | Same as production store |
| **Specific Tills** | `1, 2, 5` | 3 tills | Targets only `.112`, `.113`, `.116` |
| **UAT 1-Till Rule** | `10.3.23.35` (count=1) | 1 till | Targets exact IP `10.3.23.35` directly without `.112` offset |
| **Loopback / Test** | `127.0.0.1` | $N$ tills | Connects to localhost targets for local testing |

---

## Enterprise Security Hardening

This application adheres to enterprise corporate security standards:

1. **CIDR & Subnet Authorization**: Restricts target IPs strictly to authorized private store subnets (`10.0.0.0/8`, `192.168.0.0/16`, and `127.0.0.1`). Public internet IPs and unauthorized networks are blocked automatically.
2. **Command Whitelist (Mode 3)**: Replaces blacklists with a strict whitelist. Blocks command chaining (`;`, `&&`, `||`), subshells (`bash`, `sh`), reverse shells (`nc`, `socat`), and redirection (`>`, `>>`).
3. **CSV Formula Injection (DDE) Neutralization (CWE-1236)**: Sanitizes exported CSV cells starting with formula triggers (`=`, `+`, `-`, `@`) by prepending `'`, preventing Microsoft Excel DDE attacks.
4. **Excel Zip Bomb Defense (CWE-409)**: Enforces a 50 MB uncompressed cap and max 100 member files on `.xlsx` files before extraction.
5. **Output Stream Capping (64 KB)**: Caps remote command stdout reading to 64 KB (`stdout.read(65536)`) to prevent workstation memory exhaustion.
6. **Zero Credential Persistence**: Passwords are never saved to `config.json` and are scrubbed from error logs and telemetry.

---

## Installation & Setup

### Prerequisites
- Python 3.8+ (Windows, Linux, or macOS)
- `paramiko>=2.11.0`

### 1. Clone & Setup Environment
```bash
git clone https://github.com/mysticop03/test.git
cd test

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\\venv\\Scripts\\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

### 1. Graphical User Interface (GUI)
```bash
python main.py
```
* **Step 1**: Choose **Single Store** or **Bulk Stores** (Browse `demo_stores.csv` or `.xlsx`).
* **Step 2**: Enter SSH credentials (`posuser` and password).
* **Step 3**: Configure expected WAR size (e.g. `184.5 MB`) and Delivery Version (e.g. `deliveryversion36A`).
* **Step 4**: Click **Start Audit**.
* **Step 5**: Filter results by `[✓ Success]`, `[⚠️ Mismatches]`, `[✕ Missing]`, `[🔌 Offline]` and click **Export CSV** or **Excel (.xlsx)**.

### 2. Headless CLI Runner (Scheduled Scans / Cron)
```bash
# Basic run with interactive password prompt:
python cli.py --stores demo_stores.csv --expected-version deliveryversion36A --export-xlsx audit_report.xlsx

# Non-interactive / CI / Cron (using environment variable):
set POS_SSH_PASSWORD=your_secure_password
python cli.py --stores demo_stores.csv --export-csv audit_report.csv
```

---

## Standalone Windows Executable Build

Compile a zero-dependency Windows executable (`dist/FileInspector.exe`):
```bash
# Using 1-click batch file:
build_exe.bat

# Or using python:
python build_exe.py
```
The compiled executable runs natively on any Windows workstation without requiring Python installed.

---

## License

Internal Enterprise Tool — All rights reserved.
