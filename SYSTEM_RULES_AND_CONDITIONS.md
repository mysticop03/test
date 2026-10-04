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
    > You can pass multiple URLs separated by commas (e.g. `wget https://www.google.com/, https://www.youtube.com/` or `https://google.com, https://youtube.com`). The engine probes all specified URLs over the same SSH connection and renders a dedicated result row for each URL per machine in the table:
    > - `Till 1` $\rightarrow$ `URL 1` (`200 OK`)
    > - `Till 1` $\rightarrow$ `URL 2` (`200 OK`)
    > - `Till 2` $\rightarrow$ `URL 1` ...
    > - `Till 2` $\rightarrow$ `URL 2` ...
    > 
    > `wget` and `curl` are permitted on both Tills and Back Office. Writing arbitrary downloaded files to disk on Back Office (via `-O <file>` or `-o <file>`) is blocked, keeping Back Office strictly read-only.
33. **`curl`**
    - **What it does**: Client tool for transferring data with URLs using HTTP/HTTPS/FTP.
    - **Daily Store Use Case**: Queries local or remote health check microservices, tests API endpoints, and inspects HTTP status codes.
    - **Usage Examples**:
      ```bash
      curl -s http://localhost:8080/actuator/health
      curl -I http://localhost:8080/pos/
      curl https://www.google.com/, https://www.youtube.com/
      ```
34. **`ss`**
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
  * Completely **ignores the Number of Tills** count.

### 6.5 Network CIDR Validation
Target IPs are validated against approved private enterprise ranges:
* Store Subnets: `10.0.0.0/8`
* Testing Subnets: `192.168.0.0/16`
* Local Loopback: `127.0.0.0/8`

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
* Configurable from **1 to 5** in the UI (default: 1).
* Governs how many store subnets are processed simultaneously.

### 8.2 Global Sliding Window Ceiling (Max 100 Connections)
* Maintains a dynamic sliding window across store worker threads.
* Enforces a hard global ceiling of **100 concurrent SSH connections** across all stores.
* Prevents socket exhaustion, router lockups, and POS switchboard overloads.

### 8.3 Socket Timeout
* Taken directly from the UI `Timeout` input (default: 5 seconds, min 1s, max 30s).
* Fast socket-level pre-check drops offline machines without hanging background threads.

---

## 9. Dynamic Results Table & Row Inspection

### 9.1 Dynamic Column Presentation
The Results Table automatically configures visible columns based on user configuration:
* **File Size Only Audited**: Shows `Store`, `Device`, `IP Address`, `Latency`, `File Size`, `Last Modified`, `Status`. (Hides `Variable` & `Value`).
* **Variable / Value Only Audited**: Shows `Store`, `Device`, `IP Address`, `Latency`, `Variable`, `Value`, `Last Modified`, `Status`. (Hides `File Size`).
* **Both Audited**: Shows full columns (`File Size`, `Variable`, `Value`, `Last Modified`).
* **Terminal Mode**: Switches to `Store`, `Device`, `IP Address`, `Latency`, `Command Output`, `Status`.
* **Auth User Column Removed**: Redundant user column eliminated to maximize screen real estate.

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
