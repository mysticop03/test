# Ubuntu POS Store Inspector & Version Auditor
## Master Technical Specification & Architecture Rules (Reference Document)

---

## 1. Security Architecture & Command Whitelisting

### 1.1 Command Execution Matrix & Permissions Boundary

The system operates under a strict, code-enforced security sandbox designed specifically for enterprise retail Point of Sale (POS) environments:

| Operation Category | Permitted on Tills (`🖥️ Tills`) | Permitted on Back Office (`🏢 BO`) | Permitted on Both | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Approved Read-Only Diagnostic Commands** (39 Commands) | **YES** | **YES** | **YES** | Inspection, logs, uptime, memory, storage, services, network health, processes, peripherals. |
| **Controlled In-Place Configuration Update** (`sed -i` template) | **YES** | **NO (BLOCKED)** | **Tills Only** | Property modification template strictly authorized on Tills; blocked on Back Office. |
| **Arbitrary Shell / Destructive / Privilege Escalation** | **NO (BLOCKED)** | **NO (BLOCKED)** | **NO (BLOCKED)** | `rm`, `truncate`, `dd`, `chmod 777`, `su -`, `visudo`, `nc -e`, `$()`, `` ` `` are universally blocked. |

> [!IMPORTANT]
> **Write Access Security Boundary**:
> - **Tills (`🖥️ Tills`)**: Granted controlled in-place write modification **strictly** via the verified template (`if grep -q ... sed -i ... else echo >> ... fi; grep ...`) to update POS config files safely.
> - **Back Office (`🏢 BO .12`)**: Remains **strictly 100% Read-Only**. All write vectors, disk modifications, file redirections, and package installations are intercepted and blocked with a `Blocked` status.
> - **All Other Diagnostic Commands**: All 39 approved diagnostic inspection commands are **common to both Tills and Back Office**.

---

### 1.2 Approved Commands Catalog: Purpose, Retail POS Context & Usage Guide

Below is the complete dictionary of all approved commands whitelisted in `core/safety_guard.py`, explaining what each command does, why it is essential in daily store operations, and exact real-world examples:

#### Category A: System Uptime, Boot Diagnostics & Device Identity
1. **`uptime`**
   - **What it does**: Displays how long the machine has been running, number of active users, and load averages (1, 5, 15 min).
   - **Daily Store Use Case**: Determines whether a cashier terminal has been left on continuously for weeks (causing memory leaks) or if a till recently rebooted mid-shift.
   - **Usage Example**:
     ```bash
     uptime
     ```
2. **`who`**
   - **What it does**: Displays active logged-in user sessions. With `-b`, displays the timestamp of the last system boot.
   - **Daily Store Use Case**: Verifies whether store cashiers or maintenance engineers are currently logged in, and confirms boot timestamps (`who -b`).
   - **Usage Examples**:
     ```bash
     who
     who -b
     ```
3. **`last`**
   - **What it does**: Reads `/var/log/wtmp` to show history of recent logins, reboots, and runlevel changes.
   - **Daily Store Use Case**: Crucial for investigating unexpected store power outages, accidental cashier register switch-offs, or scheduled nightly reboot audits (`last reboot`).
   - **Usage Examples**:
     ```bash
     last reboot | head -n 5
     last -n 10
     ```
   > [!NOTE]
   > `last reboot` is explicitly distinguished from the dangerous destructive command `reboot`. `last reboot` is an audit command and is 100% safe.
4. **`date`**
   - **What it does**: Prints or checks the current system date, time, and timezone.
   - **Daily Store Use Case**: Validates POS clock synchronization. Clock drift between Till and Back Office breaks tax invoice timestamps, credit card EDC tokenization, and billing batch closures.
   - **Usage Example**:
     ```bash
     date
     ```
5. **`uname`**
   - **What it does**: Displays OS kernel architecture, release, and operating system details.
   - **Daily Store Use Case**: Checks whether the POS terminal is running the standard retail Ubuntu kernel build (e.g., Ubuntu 20.04/22.04 LTS x86_64).
   - **Usage Example**:
     ```bash
     uname -a
     ```
6. **`hostname`**
   - **What it does**: Prints the network hostname of the system.
   - **Daily Store Use Case**: Confirms that store terminal network names match store numbering standards (e.g. `POS-TILL-01`, `STORE-BO-01`).
   - **Usage Example**:
     ```bash
     hostname
     ```

---

#### Category B: POS Peripherals & Hardware Verification
7. **`lsusb`**
   - **What it does**: Lists all USB buses and connected USB peripheral hardware devices.
   - **Daily Store Use Case**: Daily morning health check to verify connected retail POS hardware: barcode scanner (Honeywell/Zebra), thermal receipt printer (Epson/Star), electronic cash drawer, customer display pole, and credit card EDC swipe machine.
   - **Usage Examples**:
     ```bash
     lsusb
     lsusb | grep -i epson
     lsusb | grep -i zebra
     ```

---

#### Category C: Storage, Memory & Resource Utilization
8. **`df`**
   - **What it does**: Reports file system disk space usage in human-readable units (`-h`).
   - **Daily Store Use Case**: Detects full hard drives (`/` or `/var/log` at 100%). A full disk on a POS register freezes the billing application, preventing bill printing and offline transaction caching.
   - **Usage Examples**:
     ```bash
     df -h
     df -h /
     ```
9. **`free`**
   - **What it does**: Displays total, used, and available physical RAM and swap space (`-m` for megabytes, `-h` for human-readable).
   - **Daily Store Use Case**: Diagnoses sluggish tills and JVM memory exhaustion before cashiers report application freezing during rush hours.
   - **Usage Examples**:
     ```bash
     free -m
     free -h
     ```
10. **`top`**
    - **What it does**: Real-time snapshot of CPU and memory consumption by active processes.
    - **Daily Store Use Case**: Identifies runaway background processes or CPU spikes on tills when combined with batch flag (`top -b -n 1`).
    - **Usage Example**:
      ```bash
      top -b -n 1 | head -n 15
      ```
11. **`stat`**
    - **What it does**: Displays detailed file or filesystem status including exact byte size, inode, and last modified / access timestamps.
    - **Daily Store Use Case**: Validates deployment timestamps of billing JAR/WAR files and checks exact file attributes down to the second.
    - **Usage Example**:
      ```bash
      stat /opt/pos/billing.war
      ```
12. **`wc`**
    - **What it does**: Counts lines, words, and bytes in files (`wc -l` for line counts).
    - **Daily Store Use Case**: Checks transaction counts in offline billing queues, log volume, or row count in pricing master tables.
    - **Usage Example**:
      ```bash
      wc -l /var/log/pos/transactions.log
      ```

---

#### Category D: POS & Billing Application Processes
13. **`ps`**
    - **What it does**: Reports snapshots of current running processes.
    - **Daily Store Use Case**: Checks whether the primary POS billing engine, Tomcat container, database service, or Java daemon is active.
    - **Usage Examples**:
      ```bash
      ps -ef | grep jre
      ps -ef | grep pos
      ps aux | head -n 10
      ```
14. **`pgrep`**
    - **What it does**: Searches running processes by name and lists process IDs (PIDs).
    - **Daily Store Use Case**: Quick check to verify if a billing binary is running without piping to grep.
    - **Usage Examples**:
      ```bash
      pgrep -l java
      pgrep -l dotnet
      ```
15. **`which`**
    - **What it does**: Locates the absolute executable path of a command in `$PATH`.
    - **Daily Store Use Case**: Validates whether required runtime runtimes (e.g. Java, .NET, Python) are installed in standard system paths.
    - **Usage Example**:
      ```bash
      which java
      which dotnet
      ```
16. **`dotnet`**
    - **What it does**: .NET Core runtime and SDK driver.
    - **Daily Store Use Case**: Validates the installed .NET runtime version and hosted POS microservices.
    - **Usage Examples**:
      ```bash
      dotnet --info
      dotnet --version
      ```
17. **`java`**
    - **What it does**: Java runtime launcher.
    - **Daily Store Use Case**: Verifies JRE/JDK versions for legacy or enterprise retail billing platforms (e.g., Oracle Retail, SAP POS, customized Java POS).
    - **Usage Example**:
      ```bash
      java -version
      ```
18. **`lsof`**
    - **What it does**: Lists open files and network socket bindings held by active processes.
    - **Daily Store Use Case**: Checks which process is holding a lock on a POS configuration file or binding port 8080/8443.
    - **Usage Examples**:
      ```bash
      lsof -i :8080
      lsof /opt/pos/billing.lock
      ```

---

#### Category E: Text Processing & Configuration Inspection
19. **`cat`**
    - **What it does**: Concatenates and prints file contents to standard output.
    - **Daily Store Use Case**: Views short configuration files, release metadata, or store identifiers.
    - **Usage Example**:
      ```bash
      cat /opt/pos/version.txt
      ```
20. **`head`**
    - **What it does**: Outputs the first few lines of files (default 10).
    - **Daily Store Use Case**: Inspects file headers, version headers, or the beginning of log files without loading massive files into memory.
    - **Usage Example**:
      ```bash
      head -n 20 /opt/pos/config.properties
      ```
21. **`tail`**
    - **What it does**: Outputs the last few lines of files (default 10).
    - **Daily Store Use Case**: Inspects the newest operational logs to diagnose cashier transaction errors, barcode scanner dropouts, or sync failures.
    - **Usage Examples**:
      ```bash
      tail -n 25 /var/log/syslog
      tail -n 50 /opt/pos/logs/pos.log
      ```
22. **`ls`**
    - **What it does**: Lists directory contents with permissions, owner, size, and modification date (`ls -lh`).
    - **Daily Store Use Case**: Checks whether daily patch files, WAR files, or pricing catalog updates arrived in the staging directory.
    - **Usage Examples**:
      ```bash
      ls -lh /opt/pos/
      ls -la /opt/pos/backup/
      ```
23. **`pwd`**
    - **What it does**: Prints the current working directory path.
    - **Daily Store Use Case**: Verifies which directory the terminal session is operating in (e.g. `/home/posuser`).
    - **Usage Example**:
      ```bash
      pwd
      ```
24. **`cd`**
    - **What it does**: Changes the current directory in the execution subshell.
    - **Daily Store Use Case**: Navigates into POS application directories before executing inspection commands (`cd /opt/pos && ls -lh` or `cd Desktop && ls`).
    - **Usage Examples**:
      ```bash
      cd Desktop && ls
      cd /opt/pos && pwd
      ```
    > [!NOTE]
    > **Non-Interactive SSH Navigation**: Each command sent over SSH runs in a fresh, isolated subshell. Running standalone `cd Desktop` changes directory in that subshell and immediately terminates. To navigate and inspect files, chain the command with `&&` (e.g. `cd Desktop && ls` or `cd /opt/pos && cat config.properties`), or pass the path directly (e.g. `ls Desktop`).
23. **`find`**
    - **What it does**: Searches for files in a directory hierarchy based on name, size, or modification date.
    - **Daily Store Use Case**: Locates billing property files or checks for leftover temporary transaction files.
    - **Usage Example**:
      ```bash
      find /opt/pos/ -name "*.properties"
      ```
    > [!WARNING]
    > Dangerous modifying find flags such as `-exec`, `-delete`, and `-ok` are strictly intercepted and blocked by `SafetyGuard`.
24. **`grep` & `egrep`**
    - **What it does**: Searches text using regular expressions and prints matching lines.
    - **Daily Store Use Case**: Finds specific configuration keys, error codes, tax rates, or cashier session timeouts across large files.
    - **Usage Examples**:
      ```bash
      grep "^SessionTimeout=" /opt/pos/pos.properties
      grep -i "error" /var/log/pos/pos.log | tail -n 10
      ```
25. **`awk`**
    - **What it does**: Pattern scanning and text column processing engine.
    - **Daily Store Use Case**: Extracts property values precisely from key-value configuration files without manual parsing.
    - **Usage Example**:
      ```bash
      awk -F'=' '/^[ \t]*SessionTimeout[ \t]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' /opt/pos/pos.properties
      ```
26. **`sed`**
    - **What it does**: Stream editor for filtering and transforming text stream output.
    - **Daily Store Use Case**: Sanitizes log output, replaces patterns in read pipelines, or inspects configuration formatting.
    - **Usage Example**:
      ```bash
      sed -n '1,10p' /opt/pos/pos.properties
      ```
    > [!IMPORTANT]
    > In-place modification `sed -i` is blocked across standalone commands. It is **only** permitted inside the controlled In-Place Configuration Update template on Tills.
27. **`tr`**
    - **What it does**: Translates, squeezes, or deletes characters from standard input.
    - **Daily Store Use Case**: Strips Windows carriage return line endings (`\r\n`) from imported POS scripts.
    - **Usage Example**:
      ```bash
      cat /opt/pos/config.txt | tr -d '\r'
      ```
28. **`sort`**
    - **What it does**: Sorts lines of text files.
    - **Daily Store Use Case**: Sorts active store codes, IP lists, or error logs alphabetically or numerically.
    - **Usage Example**:
      ```bash
      cat /opt/pos/active_tills.txt | sort -n
      ```
29. **`uniq`**
    - **What it does**: Filters out duplicate adjacent lines (`uniq -c` counts occurrences).
    - **Daily Store Use Case**: Analyzes frequency of distinct billing error messages in POS logs.
    - **Usage Example**:
      ```bash
      grep "ERROR" /opt/pos/pos.log | cut -d' ' -f4- | sort | uniq -c
      ```
30. **`cut`**
    - **What it does**: Removes sections from each line of files (by byte, character, or delimiter).
    - **Daily Store Use Case**: Extracts specific fields (e.g., store ID, cashier ID) from delimited CSV/log entries.
    - **Usage Example**:
      ```bash
      cut -d',' -f1,3 /opt/pos/store_mapping.csv
      ```
31. **`echo`**
    - **What it does**: Displays a line of text.
    - **Daily Store Use Case**: Echoes diagnostic markers, tests variable expansions, or appends missing keys inside controlled write templates.
    - **Usage Example**:
      ```bash
      echo "=== System Check Complete ==="
      ```

---

#### Category F: Network Connectivity & Service Status
32. **`wget`**
    - **What it does**: Non-interactive network downloader and URL inspection client.
    - **Daily Store Use Case**: Checks whether the local POS application server, Tomcat port, or Back Office integration gateway is online and responding with HTTP 200 without creating files on disk.
    - **Usage Examples**:
      ```bash
      wget -qO- http://localhost:8080/health
      wget --spider http://10.0.0.1:8080/pos/status
      ```
    > [!NOTE]
    > **Multi-URL Health Check Support**:
    > You can pass multiple URLs separated by commas (e.g. `wget https://www.youtube.com/watch?v=8Xx2xb4ZyOM, https://www.tradingview.com/chart/LmHaKOkF/?symbol=BINANCE%3ASOLUSDT`). The engine probes all specified URLs over the same SSH connection using `wget --spider -S` and renders a dedicated result row for each URL per machine in the table:
    > - `Till 1` $\rightarrow$ `URL 1` (`200 OK`)
    > - `Till 1` $\rightarrow$ `URL 2` (`200 OK`)
    > - `Till 2` $\rightarrow$ `URL 1` ...
    > - `Till 2` $\rightarrow$ `URL 2` ...
    > `wget` is permitted on both Tills and Back Office. Writing arbitrary downloaded files to disk on Back Office (via `-O <file>` or `-o <file>`) is blocked, keeping Back Office strictly read-only.
    > 
    > **Strict Syntax & No Curl**: Command mode strictly supports `wget` followed by URL(s) separated by commas. `curl` is completely disabled.
33. **`ss`**
    - **What it does**: Modern utility to investigate listening sockets and network connections.
    - **Daily Store Use Case**: Confirms that database listener (port 3306/5432) or POS web server (port 8080/8443) is actively listening.
    - **Usage Example**:
      ```bash
      ss -tuln
      ```
35. **`netstat`**
    - **What it does**: Legacy utility for network connections, routing tables, and interface statistics.
    - **Daily Store Use Case**: Diagnoses established socket connections between Tills and Back Office database.
    - **Usage Example**:
      ```bash
      netstat -tuln
      ```
36. **`ip`**
    - **What it does**: Inspects and manages IP addresses, routing, and network devices (`ip a` or `ip addr`).
    - **Daily Store Use Case**: Verifies local network interface card (NIC) configuration, subnet mask, and link status.
    - **Usage Example**:
      ```bash
      ip a
      ip route
      ```

---

#### Category G: Service Health & Package Verification
37. **`systemctl`**
    - **What it does**: Systemd service manager control tool.
    - **Daily Store Use Case**: Checks the runtime status of the billing engine service, database, or print spooler (`systemctl status <service>`).
    - **Usage Examples**:
      ```bash
      systemctl status pos-billing
      systemctl status tomcat
      systemctl is-active pos-billing
      ```
    > [!IMPORTANT]
    > Only inspection subcommands (`status`, `is-active`, `is-enabled`) are whitelisted. Modifying subcommands (`start`, `stop`, `restart`, `disable`, `mask`) are strictly blocked on both Tills and Back Office to prevent accidental store downtime.
38. **`journalctl`**
    - **What it does**: Queries and views systemd journal logs.
    - **Daily Store Use Case**: Diagnoses why a POS service crashed or inspects system startup messages.
    - **Usage Example**:
      ```bash
      journalctl -u pos-billing -n 20 --no-pager
      ```
39. **`dpkg` & `dpkg-query`**
    - **What it does**: Debian package inspection tools.
    - **Daily Store Use Case**: Verifies installed versions of POS packages, security patches, Java packages, or thermal printer drivers.
    - **Usage Examples**:
      ```bash
      dpkg -l | grep -i pos
      dpkg-query -W -f='${Package} ${Version}\n' pos-billing
      ```
    > [!WARNING]
    > Modifying package flags (`dpkg -i`, `-r`, `-p`, `--install`, `--remove`) are strictly blocked to prevent unauthorized system alterations.

---

## 2. In-Place Configuration Update Engine (Tills Only)

### 2.1 The In-Place Modification Template
When retail store operations require updating a property across hundreds of cashier terminals (e.g. extending session timeout, updating tax rules, or changing server endpoints), the engine provides a verified, idempotent template:

```bash
FILE="/path/to/pos.properties"

if grep -q "^SessionTimeout=" "$FILE"; then
    sed -i 's/^SessionTimeout=.*/SessionTimeout=700000/' "$FILE"
else
    echo "SessionTimeout=700000" >> "$FILE"
fi

grep "^SessionTimeout=" "$FILE"
```

### 2.2 How It Works & Why It Is Safe
1. **Idempotent Existence Check (`grep -q`)**: Checks whether the target variable key already exists in `$FILE`.
2. **Update Branch (`sed -i`)**: If key exists, replaces the entire line with the new key-value pair, preserving comments and formatting elsewhere in the file.
3. **Insert Branch (`echo >>`)**: If key does not exist, appends the key-value pair cleanly at the end of the file.
4. **Immediate Verification (`grep`)**: Reads back the updated line from `$FILE` to verify that the value was written accurately.

### 2.3 Using the Template for ANY Variable or Property
The template is generic and dynamically accepts **any configuration variable and value**. To update any key:

```bash
FILE="/opt/pos/config/pos.properties"

if grep -q "^<VARIABLE_NAME>=" "$FILE"; then
    sed -i 's/^<VARIABLE_NAME>=.*/<VARIABLE_NAME>=<NEW_VALUE>/' "$FILE"
else
    echo "<VARIABLE_NAME>=<NEW_VALUE>" >> "$FILE"
fi

grep "^<VARIABLE_NAME>=" "$FILE"
```

#### Real-World Examples:
* **Updating EDC Payment IP**:
  ```bash
  FILE="/opt/pos/edc.properties"; if grep -q "^EdcServerIP=" "$FILE"; then sed -i 's/^EdcServerIP=.*/EdcServerIP=10.14.22.12/' "$FILE"; else echo "EdcServerIP=10.14.22.12" >> "$FILE"; fi; grep "^EdcServerIP=" "$FILE"
  ```
* **Setting Offline Billing Tolerance**:
  ```bash
  FILE="/opt/pos/billing.conf"; if grep -q "^OfflineMaxLimit=" "$FILE"; then sed -i 's/^OfflineMaxLimit=.*/OfflineMaxLimit=50000/' "$FILE"; else echo "OfflineMaxLimit=50000" >> "$FILE"; fi; grep "^OfflineMaxLimit=" "$FILE"
  ```

### 2.4 Strict Permissions & Validation Rules
* **Tills (`🖥️ Tills`)**: **PERMITTED**. The command is validated by `SafetyGuard.is_valid_till_config_write(cmd)` and executed over SSH.
* **Back Office (`🏢 BO .12`)**: **STRICTLY PROHIBITED**. If executed while targeting Back Office, the guard immediately returns:
  `"Security Policy Violation on Back Office: In-place configuration write commands are strictly prohibited on 100% Read-Only BO. (Permitted on Tills only)."`
* **Code Injection Protection**: Command substitutions (`$()`, `` ` ``), system tampering (`/etc/shadow`, `/etc/sudoers`), and destructive binaries (`rm`, `kill`, `reboot`, `dd`) are strictly prohibited inside the template.

---

## 3. Multi-Layer Defense on Back Office (BO Server .12)

Back Office (.12) is the store's central server and repository for transactional records. It remains **strictly 100% Read-Only**. The engine intercepts and drops every write vector through 4 inspection tiers:

1. **Tier 1: Redirection Inspection**: Blocks `>`, `>>`, `>|`, `&>`, `1>`, `2>`.
2. **Tier 2: Piped Output Writer Inspection**: Blocks `| tee`, `| dd`, etc.
3. **Tier 3: Modifying Utility Filter**: Blocks `rm`, `sed -i`, `truncate`, `touch`, `cp`, `mv`, `chmod`, `chown`, `kill`, `systemctl restart/stop`, `apt`, `wget -O <file>`, `curl -o <file>`.
4. **Tier 4: Script & Eval Filter**: Blocks scripted write handles (`python -c "open('f','w')"`), `eval`, `exec`, and subshells `bash -c`, `sh -c`.

---

## 4. Universal Attack & Tampering Defenses (Tills & BO)

The following protections are active on **all** targets regardless of device type:
1. **Reverse Shell & Network Exfiltration**: Intercepts `nc -e`, `socat`, `/dev/tcp/`, and python/perl reverse shell sockets.
2. **OS Target Tampering**: Access to `/etc/shadow`, `/etc/sudoers`, `/dev/sda`, `/dev/nvme`, `/boot/`, and modifying `/etc/passwd` is blocked.
3. **Privilege Escalation**: `su -`, `sudo su`, `sudo -i`, `visudo`, `passwd`, and `iptables -F` are prohibited.
4. **Command Substitution**: `$()` and `` ` `` syntax are prohibited to prevent nested command execution.

---

## 5. In-File Variable Extraction Logic

### 5.1 Extracting Value from `variable = value`
To extract the exact value from a properties or configuration file when the user inputs a variable (e.g., `SessionTimeout = 700000`):

#### Shell Implementation:
```bash
# Robust POSIX awk extraction (ignores leading/trailing whitespace around = and value)
awk -F'=' 'BEGIN{IGNORECASE=1} /^[ \t]*SessionTimeout[ \t]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' /path/to/file.properties
```

#### Python / Paramiko Backend Implementation:
```python
import re

def extract_variable_value(file_content: str, variable_name: str) -> str | None:
    # Matches: optional whitespace, variable_name, optional whitespace, '=', optional whitespace, capturing value
    pattern = rf'^\s*{re.escape(variable_name)}\s*=\s*(.*?)\s*$'
    match = re.search(pattern, file_content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
```
* **Input**: Variable `SessionTimeout` in file containing `SessionTimeout = 700000`
* **Output Returned**: `700000` (strictly the value after `=`, free of whitespace or key clutter).

---

## 6. IP Addressing & Subnet Offset Rules

### 6.1 Base Subnet Resolution
* IP entered: `A.B.C.D` (e.g. `192.168.29.93` or `10.14.22.50`).
* Subnet base extracted: `A.B.C.` (e.g. `192.168.29.` or `10.14.22.`).

### 6.2 Back Office (BO) IP (`.12`)
* Always mapped to **`.12`** (`A.B.C.12`).
* Back Office is audited first in the store hierarchy order.

### 6.3 Till Register IPs (`.112` Start Offset)
* POS Till 1 starts at **`.112`**.
* Formula for Till $i$:
  $$\text{IP}(\text{Till}_i) = A.B.C.(111 + i)$$
  * Till 1: `.112`
  * Till 2: `.113`
  * Till 3: `.114`
* **Number of Tills**: Configurable from 1 to 140 (default 13). Supports standard store setups as well as large terminal clusters with up to 140 tills (.112 through .251). Visible **only in Single Store Mode**; hidden in Bulk File mode.

### 6.4 UAT Mode Rule
* When **UAT** is selected:
  * Connects **exclusively to the exact IP entered in the text box** (e.g. `192.168.29.93`).
  * Completely **ignores `.112` offsets**.
  * The UI automatically **hides the `Tills:` count label and entry field** in UAT mode (since UAT targets only that single machine), cleanly restoring it when switching back to `All Tills` or `Specific`.
  * Locks `till_count = 1` for the UAT record.

### 6.5 Network CIDR Validation
Target IPs are validated against approved private enterprise ranges:
* Store Subnets: `10.0.0.0/8`
* Testing Subnets: `192.168.0.0/16`
* Local Loopback: `127.0.0.0/8`
* Enforced across Single Store audit, Bulk Ingestion, and Single-Store Terminal execution.

---

## 7. Dynamic Credential-Driven Targeting & UI States

### 7.1 Clean UI Defaults (Zero Clutter)
Upon application launch:
* All input text boxes start completely empty (`Store IP / Subnet`, `Store Code`, `File Paths`, `Sizes`, `Variables`, `Values`, `Usernames`, `Passwords`, `Custom Command`).
* Only `Timeout` starts initialized to default **`5`** seconds.
* No hardcoded sample store paths or demo credentials pollute the interface.

### 7.2 Password-Driven Status Badges (`ACTIVE` vs `IDLE`)
The credentials card dynamically monitors password entries:
* **`ACTIVE` Badge (Green `#DCFCE7` / Text `#166534`)**: Displayed when the respective password field has characters entered.
* **`IDLE` Badge (Slate Gray `#F1F5F9` / Text `#64748B`)**: Displayed when the password field is blank.

### 7.3 Credential-Driven Audit Target Selection
The audit engine automatically infers target machines based strictly on password presence:
* **Till Password Entered + BO Password Blank**:
  * Audits **Tills Only** (`.112+`).
  * Back Office subpanel dims out.
* **BO Password Entered + Till Password Blank**:
  * Audits **Back Office Only** (`.12`).
  * Till subpanel dims out.
* **Both Passwords Entered**:
  * Audits **Both Tills and Back Office**.
* **Both Blank**:
  * Audit is blocked; alerts operator to provide credentials.

---

## 8. Execution Control, Concurrency & Sliding Window

### 8.1 Batch Size (Parallel Stores)
* Configurable from **1 to 10** in the UI (default: 1).
* Governs how many store subnets are processed simultaneously.
* Strictly clamped between 1 and 10 to ensure network stability.
* Paste dialog pre-populates standard CSV/TSV headers (`Store Code,Store IP,Till Count`).

### 8.2 Global Sliding Window Ceiling (Max 100 Connections)
* Maintains a dynamic sliding window across store worker threads.
* Enforces a hard global ceiling of **100 concurrent SSH connections** across all stores.
* Allocates up to 100 workers dynamically (no static 16-worker throttle cap) while respecting the store admission budget.
* Prevents socket exhaustion, router lockups, and POS switchboard overloads.

### 8.3 Pause vs. Stop Lifecycle
* **`⏸ Pause` / `▶ Resume`**:
  * Halts new connection admissions from the scheduler queue.
  * Any SSH connection actively in-flight completes its query, but remaining pending connections wait in the queue.
  * Clicking **`▶ Resume`** picks up right where you left off with zero data loss.
* **`⏹ Stop`**:
  * Permanently aborts the audit execution.
  * Background worker pools cancel pending futures, thread execution stops, and the live timer halts.
  * Marks the session as finished; starting again requires clicking **`▶ Start Audit`** from scratch.

### 8.4 Socket Timeout
* Taken directly from the UI `Timeout` input (default: 5 seconds, min 1s, max 30s).
* Fast socket-level pre-check drops offline machines without hanging background threads.

---

## 9. Dynamic Results Table & Row Inspection

### 9.1 Dynamic Column Presentation & Display Capping
The Results Table automatically configures visible columns based on user configuration:
* **File Size Only Audited**: Shows `Store`, `Device`, `IP Address`, `Latency`, `File Size`, `Last Modified`, `Status`. (Hides `Variable` & `Value`).
* **Variable / Value Only Audited**: Shows `Store`, `Device`, `IP Address`, `Latency`, `Variable`, `Value`, `Last Modified`, `Status`. (Hides `File Size`).
* **Both Audited**: Shows full columns (`File Size`, `Variable`, `Value`, `Last Modified`).
* **Terminal Mode**: Switches to `Store`, `Device`, `IP Address`, `Latency`, `Command Output`, `Status`.
* **Auth User Column Removed**: Redundant user column eliminated to maximize screen real estate.
* **Max 50 Display Limit (First 50 Rows Only)**:
  * The interactive UI Treeview displays at most the **first 50** rows (`MAX_DISPLAY_ROWS = 50`) in natural store hierarchy order (`Till-01` through `Till-50`).
  * When auditing large stores (e.g. 60+ tills), the first 50 rows are strictly preserved and never dropped from the top. Results beyond 50 are excluded from the grid view to eliminate GUI lag.
  * **100% Data Preservation**: All results (all 60+, 500+ targets) remain stored in memory (`all_results`), guaranteeing that **`Export CSV`**, **`Export Excel`**, and the Top Metrics/KPI counters reflect 100% of all checked machines.
* **Terminal Live Stopwatch**: The elapsed time stopwatch runs live during Terminal execution as well as file/version audit modes.

### 9.2 Strict Status States (Dropdown Filter)
Standardized into **5 distinct status categories**:
1. **Success**: Binary size matches within tolerance, and/or property value matches expected string.
2. **Offline**: Machine unreachable on Port 22 within timeout (default 5s).
3. **Mismatch**: Target is online and file exists, but file size or property value differs from expected.
4. **Miss**: Specified file path or property file does not exist on the target machine.
5. **Blocked**: Write or modify operation intercepted and blocked on Back Office.

### 9.3 Embedded Linux Terminal Console & Double-Click Row Inspection
* Embedded directly into the Operations card beneath the preset chips.
* **Preset Chips Toolbar**: Instant one-click selection for:
  - `quick health`: Multi-command diagnostic bundle (`uptime; echo "--- Memory (free -h) ---"; free -h; echo "--- Boot Time (who -b) ---"; who -b; echo "--- Last Reboots ---"; last reboot | head -n 5; echo "--- Disk Space (df -h) ---"; df -h /`)
  - `uptime`: Current system uptime & 1m/5m/15m load averages
  - `free -h`: Memory & swap usage in human-readable GB/MB (`free -h`)
  - `reboot time`: Last system boot timestamp (`who -b`)
  - `last reboot`: History of past reboots (`last reboot | head -n 5`)
  - `health url`: Local service health endpoint probe (`wget http://localhost:8080/health`)
  - `ps jre`: Active Java Runtime processes (`ps -ef | grep jre`)
  - `dotnet`: Installed .NET SDK & runtime diagnostic (`dotnet --info`)
  - `logs`: System kernel & syslog review (`tail -n 20 /var/log/syslog`)
  - `date`: Current system date & time (`date`)
  - `set timeout`: In-place Till configuration template.
* **Preset Buttons & Code Location**:
  - Defined in [`ui/components/mode_card.py`](file:///c:/Users/gamin/OneDrive/Desktop/projects/tills/ui/components/mode_card.py#L179-L192) inside the `presets` list.
  - Adding or modifying presets: Simply edit or add a tuple `("Chip Label", "shell command")` to the list.
* **Multi-Command Batch & Shortcut Keywords**:
  - Defined in `SHORTCUT_KEYWORDS` inside [`ui/components/mode_card.py`](file:///c:/Users/gamin/OneDrive/Desktop/projects/tills/ui/components/mode_card.py#L22-L27).
  - Typing keywords like `quick health`, `diagnostics`, `reboot info`, or `sysinfo` into `terminal:~#` automatically expands to the chained batch commands separated by `;`.
  - SafetyGuard splits and validates every command against `DEFAULT_WHITELIST`, safely running under `bash -c`.
* **Double-Click Row Inspection & Output Window**: Double-clicking any row in the results table simultaneously updates the in-place Terminal Console screen AND opens a dedicated floating display output window (`OutputDisplayDialog`) displaying complete untruncated stdout/stderr, execution latency, target badge, status badge, command preview with copy utility, and quick Escape-to-close behavior.

---

## 10. Filtered Export Architecture & Re-Audit Ingestion

### 10.1 Active Filter Adherence
* Clicking **`Export CSV`** or **`Export Excel`** strictly exports records matching the **currently active dropdown filter**.
* If filtered to `Offline`, only unreachable machines are exported.
* If filtered to `Mismatch`, only mismatched machines are exported.
* If filtered to `All`, the entire dataset is exported.

### 10.2 Re-Audit Ingestion Compatibility
* Exported CSV and Excel reports maintain standard store columns (`Store`, `Device`, `IP Address`, etc.).
* **Re-Audit Workflow**: Operators can export offline or failed machines at 10:00 AM, and at 3:00 PM directly upload that exported file into **Bulk File** mode to re-audit only the previously failing machines without re-running thousands of already-passed stores.

### 10.3 Excel Multi-Sheet Architecture (`.xlsx`)
When exported in `All` mode, the zero-dependency Excel generator produces 5 dedicated tabs:
* **Sheet 1: `All`** — Master audit results.
* **Sheet 2: `Success`** — Compliant machines.
* **Sheet 3: `Offline`** — Unreachable machines (re-audit ready).
* **Sheet 4: `Mismatch`** — Machines with wrong file sizes or configuration values.
* **Sheet 5: `Miss`** — Machines missing the specified files.

### 10.4 Strict Store Hierarchy Order
All exports and table outputs follow natural store operational order:
$$\text{Store 1} \longrightarrow \text{Store 1 BO (.12)} \longrightarrow \text{Store 1 Till 1 (.112)} \longrightarrow \text{Till 2 (.113)} \dots \longrightarrow \text{Store 2} \longrightarrow \text{Store 2 BO (.12)} \dots$$

---

## 11. Security Defenses for Storage & Spreadsheets

1. **Zip Bomb & Memory Exhaustion Defense**: Ingestion engine limits uncompressed Excel XML size to 50 MB and zip member count to 100.
2. **Formula Injection Defense**: All exported cells beginning with `=`, `+`, `-`, or `@` are prefixed with a single quote (`'`) to neutralize malicious formula execution in Microsoft Excel.

---

## 12. KPI Stats Bar & Progress Calculation

### 12.1 Real-Time KPI Counters
* **Progress**: Real-time progress bar + fraction (`Completed / Total`).
* **Success**: Green badge count.
* **Mismatch**: Amber badge count.
* **Missing (Miss)**: Purple badge count.
* **Offline**: Red badge count.

### 12.2 Total Progress Formula
$$\text{Total Expected Audits} = \sum_{\text{stores}} \left( (\text{Tills per store}) + (\text{1 if BO targeted else 0}) \right)$$
In Bulk Mode, the progress denominator updates dynamically as the uploaded file is parsed.

---

## 13. Three Operations Modes & Dynamic Header Strictness

The operations panel provides three distinct functional buttons:

```text
[ 📁 File Check ]   [ 🏷️ Version Check ]   [ ⚡ Terminal ]
```

### 13.1 Button 1: File Check (`file_check`)
* **Primary Scope**: File existence, file size verification, last modified timestamp, and **Full Variable / Value Extraction**.
* **Variable Extraction Behavior**: Retains the **complete, unstripped raw string** (e.g. `SessionTimeout=700000`, `db.url=jdbc:...`). No token stripping is applied.
* **Strict Dynamic Column Headers**:
  * **Size Only Filled**: Displays `[Store] | [Device] | [IP Address] | [Latency] | [File Size] | [Last Modified] | [Status]`. (Hides `Variable / Value`).
  * **Variable Only Filled**: Displays `[Store] | [Device] | [IP Address] | [Latency] | [Variable / Value] | [Last Modified] | [Status]`. (Hides `File Size`).
  * **Both Filled**: Displays `[Store] | [Device] | [IP Address] | [Latency] | [File Size] | [Last Modified] | [Variable / Value] | [Status]`.

### 13.2 Button 2: Version Check (`version_check`)
* **Primary Scope**: Dedicated for Point of Sale (POS) application delivery and patch release auditing.
* **Trailing Delivery Token Stripping**:
  * POS property files frequently store values such as `ts0034 = Patch 53 Delivery No 81A` or `prop = Delivery No 79`.
  * The extraction engine ignores all preceding text (`Patch 53 Delivery No`) and extracts **strictly the trailing delivery token** (`81A` or `79`).
  * **Strict Exact Matching**: If expected delivery is `81A`, it strictly matches `81A`. Tokens such as `81`, `81B`, or `86A` are rejected as **Mismatch**.
* **Aggregated 5-Column Output Schema**:
  To prevent cluttered individual rows (`001, 81A`, `001, 81A`, `001, 86A`), results are aggregated to **1 row per store**:
  ```csv
  Store Code,IP,Mismatch Version,Offline,Status
  001,10.12.1.12,"4,6",-,Mismatch
  002,10.12.2.12,All Matched,-,Success
  003,10.12.3.12,"1,5",3,Mismatch
  004,10.12.4.12,All Matched,2,Offline
  ```
  * **`Store Code`**: Store identifier.
  * **`IP`**: Always the Back Office `.12` subnet anchor.
  * **`Mismatch Version`**: Comma-separated list of non-matching till numbers (e.g. `4,6`), or `All Matched` if all online tills matched.
  * **`Offline`**: Comma-separated list of unreachable till numbers (e.g. `2`), or `-` if all tills responded.
  * **`Status`**: `Mismatch` if any tills failed version check; `Offline` if tills were offline with no mismatches; `Success` if all matched.

### 13.3 Button 3: Terminal Console (`terminal`)
* **Primary Scope**: Direct remote diagnostic command execution and `wget` URL health checks.
* **Strict Dynamic Column Headers**:
  * Displays strictly: `[Store] | [Device] | [IP Address] | [Latency] | [Command Output] | [Status]`.
  * **Zero Column Leakage**: `File Size`, `Last Modified`, and `Variable / Value` headers are **completely omitted** from the table and exports.

---

## 14. Re-Audit Ingestion Engine for Version Reports

### 14.1 Closed-Loop Re-Audit Workflow
Operators can export the 5-column Version Check report and directly upload that file back into the application for targeted re-auditing:
1. **Header Detection**: Ingestion recognizes `Mismatch Version` and `Offline` columns.
2. **Subnet Math**: Using the store's `.12` IP, till IP addresses are automatically resolved using `112 + TillNumber - 1`:
   - Till 4 = `10.12.1.115`
   - Till 6 = `10.12.1.117`
3. **Automatic Filtering**:
   - Stores marked `All Matched` with no offline tills are **automatically bypassed** (0 scans needed).
   - Problem stores are queued strictly for their non-matching or offline till numbers.

---

## 15. Cryptographic Services & Security Sandbox

### 15.1 In-Memory Credential Encryption (`core/crypto_utils.py`)
* Leverages Python's official `cryptography` library (`cryptography.fernet.Fernet`).
* Generates an ephemeral 256-bit AES encryption key per process lifecycle.
* Passwords and sensitive authentication tokens are encrypted in memory, preventing plain-text discovery via process memory inspection or heap dumps.

### 15.2 Cryptographic Integrity & Remote SHA-256 Probes
* `compute_sha256_bytes()` and `compute_sha256_file()` provide cryptographic checksum calculation.
* `verify_hash()` uses constant-time string comparison (`hmac.compare_digest`) against timing side-channel attacks.
* `build_sha256_remote_probe()` builds non-destructive remote `sha256sum` probes for binary file validation on Ubuntu tills.

### 15.3 Network Whitelist Boundary
* Test IP `3.109.2.78/32` is completely decommissioned and removed.
* Target connections are restricted strictly to authorized private RFC subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`) with UAT test lab exception.

---

## 16. Strict Execution Timeout Enforcement & Network Buffers

### 16.1 Timeout Stacking Prevention (OS-Level `timeout`)
When executing network commands such as `wget` over SSH:
* Passing application flags `--dns-timeout=5` and `--connect-timeout=5` without an OS supervisor causes timeouts to **stack linearly** (up to 5s for DNS resolution + 5s for TCP connection = **10 seconds**).
* To enforce **strict compliance** with the user's configured timeout in the UI (e.g. 5 seconds), commands are wrapped with Linux `timeout`:
  ```bash
  timeout {timeout}s wget --spider -S -t 1 -T {timeout} --dns-timeout={timeout} --connect-timeout={timeout} ...
  ```
* If the remote target or domain fails to respond within `{timeout}` seconds, the Linux kernel terminates the process with exit code 124, returning immediately.

### 16.2 Network & Socket Buffer Reference
| Layer | Time Allocation | Description |
| :--- | :--- | :--- |
| **User Timeout** | Exactly `{timeout}s` (e.g. 5.0s) | Hard ceiling enforced by Linux `timeout` on remote machine. |
| **SSH Channel Dispatch Buffer** | `+100 ms to 300 ms` | Socket transport latency for Paramiko to open session channel, send command bytes, and receive exit signal over LAN/VPN. |
| **Reported Latency** | `~5150 ms` for a 5s timeout | Includes the 5000 ms OS execution + ~150 ms SSH socket roundtrip buffer. |

---

## 17. Wget Output Formatting & Real-Time Streaming Architecture

### 17.1 Table Display & Export: Status Code Only
* **Display & Export (`Command Output` Column)**: Strictly shows the numeric **HTTP Status Code** (e.g. `200`, `301`, `404`) or standardized failure token (`Timeout (5s)`, `DNS Failed`, `Refused`).
* **Clean Formatting**: Omit long command strings like `wget https://... - 200` from the table and CSV/Excel exports.

### 17.2 Full Output Inspection (Click / Double Click)
* Double-clicking any row in the results table or selecting a row opens the **Detail Inspector Modal** and updates the **Terminal Console Screen**.
* The inspector presents the complete diagnostic record:
  ```text
  URL: https://github.com/
  Command: wget https://github.com/
  Target Machine: Till-01 (192.168.29.93:22)
  HTTP Status Code: 200
  Latency: 183.4 ms
  ------------------------------------------------------------
  HTTP/1.1 200 OK
  Server: GitHub.com
  Date: Thu, 09 Oct 2026 01:00:00 GMT
  Content-Type: text/html; charset=utf-8
  ...
  ```

### 17.3 Real-Time Sequential Streaming (`on_sub_result`)
* When auditing multiple comma-separated URLs (e.g. `wget https://site1.com, https://site2.com, https://site3.com`):
* Results are streamed in **real-time order** via `on_sub_result` callback. As soon as URL 1 finishes, it immediately appears in the terminal log and the table. It does not wait for URL 2, 3, or 4 to complete.

---

## 18. Delivery Token Stripping: Location & Customization Guide

### 18.1 Code Location
* **File**: [`core/file_checker.py`](file:///c:/Users/gamin/OneDrive/Desktop/projects/tills/core/file_checker.py)
* **Function**: `extract_trailing_delivery_token(val: str) -> str` (around line 93)

### 18.2 How It Works
The engine cleans the input string and extracts strictly the trailing delivery number/token:
1. **Punctuation & Bracket Trimming**: Strips enclosing punctuation/brackets (`)]}"' ,;.`), allowing formats like `patch(delivery 75A)` to be sanitized to `patch(delivery 75A`.
2. **Delivery Keyword Extraction**: Regex `(?i)\bdelivery\s*(?:no|version)?\s*[:=-]?\s*([0-9]+[a-zA-Z]*)` matches:
   * `patch(delivery 75A)` -> `75A`
   * `Patch 53 Delivery No 81A` -> `81A`
   * `Delivery No 79` -> `79`
   * `delivery: 23B` -> `23B`
3. **Trailing Token Extraction**: Regex `(?:^|[\s:=-]|[\.\s(\[])([0-9]+[a-zA-Z]*)\s*$` extracts trailing tokens when no keyword is present (e.g. `Version 53.81A` -> `81A`, or bare `81A` -> `81A`).

### 18.3 Customizing for Office File Formats
If your office property file uses a different line pattern (for example: `build.delivery.tag = REL_75A` or `RELEASE=DEL-75A`), you can easily add custom regex rules directly inside `core/file_checker.py`:
```python
# Custom Office format example:
m_custom = re.search(r'(?i)\b(?:release|build|rel)[_=-]?([0-9]+[a-zA-Z]*)', clean)
if m_custom:
    return m_custom.group(1).upper()
```

---

## 19. Input File Formats & Header Specifications (CSV & Excel)

The application supports two distinct input formats:
1. **Format A: Target Scope Bulk File** (Used for standard multi-store audits)
2. **Format B: Re-Audit Version Report File** (Used to re-test only mismatched and offline tills)

---

### 19.1 Format A: Target Scope Bulk File (`.csv` or `.xlsx`)
Used in Section 1 (**Target Scope** -> **Bulk File**). Allows importing hundreds of stores at once.

#### Supported Headers (Case-Insensitive):
| Header Name | Required? | Accepted Alternates | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| **`Store Code`** | **Yes** | `Store`, `StoreCode`, `Code`, `Store_ID` | Unique identifier of the store. | `Store-001` or `101` |
| **`IP Address`** | **Yes** | `IP`, `Store IP`, `Store_IP`, `Base IP`, `Subnet` | Base IP of the store (e.g. `.12` Back Office anchor or `.1` subnet base). | `192.168.29.12` |
| **`Till Count`** | No | `Tills`, `Num Tills`, `Count`, `Max Tills` | Number of tills in the store (1 to 10). Defaults to 10 if omitted. | `5` |
| **`Till Mode`** | No | `Mode`, `Scope` | `All Tills`, `Specific`, or `UAT`. Defaults to `All Tills`. | `All Tills` |
| **`Specific Tills`**| No | `Till List`, `Include Tills` | Comma-separated till numbers when Till Mode is `Specific`. | `1,2,4` |

#### Sample Format A (CSV):
```csv
Store Code,IP Address,Till Count,Till Mode,Specific Tills
Store-001,192.168.29.12,6,All Tills,
Store-002,192.168.30.12,10,Specific,"1,3,5"
Store-003,192.168.31.12,4,All Tills,
```

#### Sample Format A (Excel - Sheet 1):
| Store Code | IP Address | Till Count | Till Mode | Specific Tills |
| :--- | :--- | :--- | :--- | :--- |
| Store-001 | 192.168.29.12 | 6 | All Tills | |
| Store-002 | 192.168.30.12 | 10 | Specific | 1, 3, 5 |
| Store-003 | 192.168.31.12 | 4 | All Tills | |

---

### 19.2 Format B: Re-Audit Version Check File (`.csv` or `.xlsx`)
Directly exported from Button 2 (**Version Check**) or created manually. When loaded into **Bulk File**, the system automatically detects this schema and audits **strictly the problem tills**.

#### Supported Headers (Case-Insensitive):
| Header Name | Required? | Description | Example Values |
| :--- | :--- | :--- | :--- |
| **`Store Code`** | **Yes** | Store identifier. | `Store-001`, `042` |
| **`IP`** | **Yes** | Back Office `.12` subnet anchor IP. | `192.168.29.12` |
| **`Mismatch Version`** | **Yes** | Comma-separated list of till numbers that failed version check, or `All Matched`. | `4,6` or `BO,2` or `All Matched` |
| **`Offline`** | **Yes** | Comma-separated list of till numbers that were unreachable, or `-` / `All Offline`. | `2` or `BO` or `-` |
| **`Status`** | No | Overall audit status (`Success`, `Mismatch`, `Offline`). | `Mismatch` |

#### Processing Behavior for Format B:
1. Stores where `Mismatch Version` is `All Matched` and `Offline` is `-` are **automatically skipped** (0 scans needed).
2. Stores with `Mismatch Version` like `4,6` or `BO` will queue **strictly Till 4, Till 6, and/or BO** for audit.
3. Till IPs are derived dynamically:
   * Till 4 = `Subnet.115` (`112 + 4 - 1`)
   * Till 6 = `Subnet.117` (`112 + 6 - 1`)
   * BO = `Subnet.15` (or subnet anchor)

#### Sample Format B (CSV):
```csv
Store Code,IP,Mismatch Version,Offline,Status
Store-001,192.168.29.12,"4,6",-,Mismatch
Store-002,192.168.30.12,All Matched,-,Success
Store-003,192.168.31.12,BO,2,Mismatch
Store-004,192.168.32.12,-,All Offline,Offline
```

#### Sample Format B (Excel - Sheet 1):
| Store Code | IP | Mismatch Version | Offline | Status |
| :--- | :--- | :--- | :--- | :--- |
| Store-001 | 192.168.29.12 | 4,6 | - | Mismatch |
| Store-002 | 192.168.30.12 | All Matched | - | Success |
| Store-003 | 192.168.31.12 | BO | 2 | Mismatch |
| Store-004 | 192.168.32.12 | - | All Offline | Offline |

