# Ubuntu POS Store Inspector & Version Auditor
# Master Technical Specification & Architecture Rules (Reference Manual)

================================================================================
1. SECURITY ARCHITECTURE & COMMAND WHITELISTING
================================================================================

1.1 Command Execution Matrix & Permissions Boundary

The system operates under a strict, code-enforced security sandbox designed specifically for enterprise retail Point of Sale (POS) environments:

+-------------------------------------+------------+-----------------+-------------------+
| Operation Category                  | Tills      | Back Office     | Execution Policy  |
+-------------------------------------+------------+-----------------+-------------------+
| Approved Diagnostic Commands (39)   | ALLOWED    | ALLOWED         | Common to both    |
| Controlled In-Place Config Update   | ALLOWED    | BLOCKED         | Tills Only        |
| Destructive / Privilege Escalation  | BLOCKED    | BLOCKED         | Universally blocked|
+-------------------------------------+------------+-----------------+-------------------+

Write Access Security Boundary:
- Tills: Granted controlled in-place write modification strictly via the verified template (if grep -q ... sed -i ... else echo >> ... fi; grep ...) to update POS config files safely.
- Back Office (.12): Remains strictly 100% Read-Only. All write vectors, disk modifications, file redirections, and package installations are intercepted and blocked with Blocked status.
- All Other Diagnostic Commands: All 39 approved diagnostic inspection commands are common to both Tills and Back Office.


1.2 Approved Commands Catalog (Purpose, Retail Context & Usage Guide)

Below is the complete dictionary of all approved commands whitelisted in core/safety_guard.py:

Category A: System Uptime, Boot Diagnostics & Device Identity

1. uptime
   - Purpose: Displays how long the machine has been running, active users, and load averages.
   - Retail Context: Determines whether a register has been on continuously for weeks or rebooted mid-shift.
   - Example:
       uptime

2. who
   - Purpose: Displays active user sessions. With -b, displays last boot time.
   - Retail Context: Verifies whether cashiers or engineers are logged in and confirms boot time.
   - Example:
       who
       who -b

3. last
   - Purpose: Reads /var/log/wtmp to show recent logins, reboots, and runlevel changes.
   - Retail Context: Investigates store power outages or register switch-offs (last reboot).
   - Example:
       last reboot | head -n 5
       last -n 10

4. date
   - Purpose: Checks current system date, time, and timezone.
   - Retail Context: Validates POS clock synchronization. Clock drift breaks tax invoice timestamps and card EDC tokenization.
   - Example:
       date

5. uname
   - Purpose: Displays OS kernel architecture and release details.
   - Retail Context: Checks whether the terminal is running the standard retail Ubuntu kernel build.
   - Example:
       uname -a

6. hostname
   - Purpose: Prints network hostname.
   - Retail Context: Confirms that terminal network names match store naming standards (e.g. POS-TILL-01).
   - Example:
       hostname


Category B: POS Peripherals & Hardware Verification

7. lsusb
   - Purpose: Lists USB buses and connected USB peripheral hardware devices.
   - Retail Context: Morning health check to verify connected retail POS hardware: barcode scanner (Honeywell/Zebra), receipt printer (Epson/Star), cash drawer, customer display, and card swipe EDC machine.
   - Example:
       lsusb
       lsusb | grep -i epson
       lsusb | grep -i zebra


Category C: Storage, Memory & Resource Utilization

8. df
   - Purpose: Reports file system disk space usage in human-readable units (-h).
   - Retail Context: Detects full hard drives (/ or /var/log at 100%). Full disk freezes billing applications.
   - Example:
       df -h
       df -h /

9. free
   - Purpose: Displays total, used, and available physical RAM and swap memory.
   - Retail Context: Confirms register has sufficient free memory to prevent JVM out-of-memory crashes.
   - Example:
       free -m
       free -h

10. vmstat
    - Purpose: Reports virtual memory statistics, paging, CPU activity, and system interrupts.
    - Retail Context: Analyzes register slowness caused by swapping or disk bottleneck.
    - Example:
        vmstat 1 3


Category D: System Services & Daemon Management (systemctl)

11. systemctl status
    - Purpose: Queries execution status of system services and background daemons.
    - Retail Context: Verifies core retail services: POS billing engine, database agent, sync service, or printer daemon.
    - Example:
        systemctl status pos-billing
        systemctl status cups
        systemctl is-active docker

12. service (status only)
    - Purpose: Legacy SysV-init command for checking service status.
    - Retail Context: Checks status of older legacy Ubuntu POS services.
    - Example:
        service mysql status
        service cups status


Category E: Network Connectivity, DNS & Route Diagnostics

13. ping
    - Purpose: Sends ICMP echo requests to verify network reachability and packet latency.
    - Retail Context: Checks connectivity from Till to Back Office server (.12), payment gateway, or cloud API.
    - Example:
        ping -c 3 192.168.29.12
        ping -c 2 8.8.8.8

14. ip
    - Purpose: Inspects network interfaces, IP assignments, and kernel routing tables.
    - Retail Context: Verifies that Till has correct static IP and link state is UP.
    - Example:
        ip addr show
        ip route

15. ifconfig
    - Purpose: Legacy network interface configuration and packet counter inspection tool.
    - Retail Context: Checks MAC address, assigned IP, and RX/TX packet drop errors.
    - Example:
        ifconfig eth0

16. netstat
    - Purpose: Displays active network connections and listening TCP/UDP ports.
    - Retail Context: Confirms POS database port (3306/5432) or payment EDC listening port is open.
    - Example:
        netstat -tuln
        netstat -an | grep 8080

17. ss
    - Purpose: Modern socket statistics utility.
    - Retail Context: Replaces netstat for inspecting listening sockets and established TCP connections.
    - Example:
        ss -tuln
        ss -t -a

18. wget
    - Purpose: Non-interactive network downloader. Used with --spider to probe web servers.
    - Retail Context: Checks HTTP connectivity to head office APIs, loyalty endpoints, or update servers.
    - Example:
        wget --spider -S -t 1 -T 5 https://api.retailer.com/health
        wget https://site1.com, https://site2.com

19. curl
    - Purpose: Transfers data using URL syntax; tests HTTP headers with -I.
    - Retail Context: Probes REST APIs and payment services.
    - Example:
        curl -I --connect-timeout 5 https://payment.gateway.internal/health


Category F: Process Monitoring & Thread Auditing

20. ps
    - Purpose: Reports a snapshot of currently running processes.
    - Retail Context: Verifies that POS application (Java/JRE or .NET) is running.
    - Example:
        ps -ef | grep jre
        ps aux --sort=-%mem | head -n 10


Category G: File Inspection, Property Analysis & Text Utilities

21. cat
    - Purpose: Concatenates and prints file contents.
    - Retail Context: Reads POS configuration and property files.
    - Example:
        cat /opt/pos/app.properties

22. head
    - Purpose: Displays initial lines of a file (default 10).
    - Retail Context: Inspects top configuration headers.
    - Example:
        head -n 20 /opt/pos/pos.properties

23. tail
    - Purpose: Displays last lines of a file (default 10).
    - Retail Context: Inspects newest operational logs for cashier transaction errors.
    - Example:
        tail -n 25 /var/log/syslog
        tail -n 50 /opt/pos/logs/pos.log

24. ls
    - Purpose: Lists directory contents with permissions, size, and date.
    - Retail Context: Checks whether patch files, WAR files, or pricing catalogs arrived.
    - Example:
        ls -lh /opt/pos/
        ls -la /opt/pos/backup/

25. pwd
    - Purpose: Prints current working directory.
    - Retail Context: Verifies which directory the terminal session is in.
    - Example:
        pwd

26. cd
    - Purpose: Changes directory in subshell.
    - Retail Context: Navigates before inspecting (e.g. cd Desktop && ls).
    - Example:
        cd Desktop && ls
        cd /opt/pos && pwd

27. find
    - Purpose: Searches directory trees for files by name or size.
    - Retail Context: Locates property files or temporary transaction files.
    - Example:
        find /opt/pos/ -name "*.properties"

28. grep & egrep
    - Purpose: Searches text for matching patterns.
    - Retail Context: Finds configuration keys, error codes, tax rates, or timeouts.
    - Example:
        grep "^SessionTimeout=" /opt/pos/pos.properties
        grep -i "error" /var/log/pos/pos.log | tail -n 10

29. awk
    - Purpose: Pattern scanning and column processing engine.
    - Retail Context: Extracts property values from key-value configuration files.
    - Example:
        awk -F'=' '/^[ \t]*SessionTimeout[ \t]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' /opt/pos/pos.properties

30. sed
    - Purpose: Stream editor for filtering and transforming text streams.
    - Retail Context: Filters log lines or reads configuration slices. Standalone sed -i is blocked; only controlled in-place update template is permitted.
    - Example:
        sed -n '1,10p' /opt/pos/pos.properties

31. tr, sort, uniq, cut, echo
    - Purpose: Standard POS text parsing, sorting, column extraction, and testing utilities.
    - Examples:
        cat /opt/pos/config.txt | tr -d '\r'
        cat /opt/pos/active_tills.txt | sort -n
        grep "ERROR" /opt/pos/pos.log | cut -d' ' -f4- | sort | uniq -c
        echo "=== System Check Complete ==="

32. wc
    - Purpose: Counts lines (-l), words (-w), or bytes (-c).
    - Retail Context: Counts error occurrences or active tills in registry files.
    - Example:
        grep -c "TIMEOUT" /opt/pos/logs/pos.log

33. diff
    - Purpose: Compares two files line by line.
    - Retail Context: Audits differences between current till config and standard store template.
    - Example:
        diff -u /opt/pos/config.properties /opt/pos/config.properties.bak

34. stat
    - Purpose: Displays file size in bytes, inode, permissions, and modification timestamps.
    - Retail Context: Verifies WAR/binary file sizes down to the exact byte.
    - Example:
        stat -c "%s %y" /opt/pos/billing.war

35. file
    - Purpose: Determines file type via magic numbers.
    - Retail Context: Validates whether a downloaded update file is a valid Java archive or ELF binary.
    - Example:
        file /opt/pos/billing.war

36. md5sum & sha256sum
    - Purpose: Computes cryptographic file checksums.
    - Retail Context: Verifies security integrity of billing binaries against official releases.
    - Example:
        sha256sum /opt/pos/billing.war

37. journalctl
    - Purpose: Queries systemd system and application journal logs.
    - Retail Context: Audits system boots and service crashes without touching disk.
    - Example:
        journalctl -u pos-billing -n 20 --no-pager
        journalctl -p err -n 10 --no-pager

38. dmesg
    - Purpose: Examines kernel ring buffer messages.
    - Retail Context: Diagnoses hardware faults: failing SSD, USB barcode disconnects, receipt printer power drops.
    - Example:
        dmesg -T | grep -i usb | tail -n 15

39. dotnet
    - Purpose: Executes .NET Core / .NET 6+ runtime diagnostics and inspects installed runtimes.
    - Retail Context: Verifies version and SDK info for retail POS applications built on .NET.
    - Example:
        dotnet --info
        dotnet --list-runtimes


================================================================================
2. COMMAND BLOCKING & DESTRUCTIVE PATTERN INTERCEPTION
================================================================================

2.1 Blocked Execution Patterns
The safety guard immediately intercepts and blocks any command containing:
- Shell injections: $(...), `...`, & backgrounding, sudo, su -, visudo.
- Destructive commands: rm, rmdir, truncate, shred, mkfs, dd.
- Reboot / shutdown commands: reboot, shutdown, init, poweroff, halt. (last reboot is permitted).
- Uncontrolled file writes: >, >>, tee.
- Remote shells and download-exec: nc, ncat, bash -i, curl | bash, wget | sh.


================================================================================
3. CONTROLLED IN-PLACE CONFIGURATION UPDATE TEMPLATE
================================================================================

On Tills only, property updates are strictly authorized via this verified template:
  if grep -q '^[ \t]*KEY[ \t]*=' PATH; then
    sed -i 's|^[ \t]*KEY[ \t]*=.*|KEY=VALUE|' PATH
  else
    echo 'KEY=VALUE' >> PATH
  fi; grep '^[ \t]*KEY[ \t]*=' PATH

Rules:
- Permitted strictly on Tills.
- Blocked 100% on Back Office.
- Overwrite mode: if key exists, replaces value. If missing, appends key=value.
- Returns verified updated line.


================================================================================
4. STORE TARGET RESOLUTION & SUBNET ARCHITECTURE
================================================================================

4.1 IP Addressing & Subnet Offset Formula
For standard production stores, the base IP is the store's subnet anchor (e.g. 192.168.29.12 or 10.14.22.12).
- Subnet Prefix: Derived from the first 3 octets: A.B.C. (e.g. 192.168.29.)
- Back Office (.12): Always assigned to host offset .12:
    BO IP = A.B.C.12
- Tills (.112+): Till 1 starts at .112. Calculated using:
    Till IP = A.B.C.(111 + TillNumber)
    Till 1  = A.B.C.112
    Till 2  = A.B.C.113
    Till 8  = A.B.C.119
    Till 12 = A.B.C.123

4.2 Till Count and Specific Tills Selection
- Stores support till counts from 1 up to 140 (e.g. 8 tills, 12 tills, etc.).
- When Specific Tills is empty: Audits all tills from Till 1 through Till Count.
- When Specific Tills is provided: Audits only those specific till numbers (e.g. 1,3,5 or 12).
- Supports individual numbers (1, 2, 4) or ranges (1-6).


4.3 UAT Mode Exception
In UAT test mode:
- IP address entered in the UI is taken literally without adding .12 or .112 offsets.
- Bypasses private RFC-1918 subnet restrictions to allow lab testing.


================================================================================
5. DUAL SSH CREDENTIALS & FAILOVER MECHANISM
================================================================================

Stores use distinct credentials for Tills and Back Office:
- Tills Credential: Used primarily for till targets.
- BO Credential: Used primarily for Back Office targets.
- Seamless Fallback: If primary authentication fails, automatically tries secondary credentials before marking target offline.


================================================================================
6. NETWORK SCOPE & PRIVATE SUBNET BOUNDARIES
================================================================================

All production audits are strictly confined to authorized private network ranges:
- 10.0.0.0/8
- 172.16.0.0/12
- 192.168.0.0/16
- 127.0.0.0/8 (Loopback testing)

Public internet IPs are blocked by policy (with UAT mode exception for lab environments).
Legacy test IP 3.109.2.78 has been completely decommissioned and removed.


================================================================================
7. PERFORMANCE ENGINE & STRICT RATE LIMITING
================================================================================

7.1 Strict Batch Size Cap (Max 10)
- UI Batch Size input is hard-capped at 10.
- Typing numbers greater than 10 is blocked in real-time by entry validation.
- Internal scheduler clamps store concurrency to range 1 to 10.

7.2 Strict Connection Rate Limiting (Max 100 Connections)
- Maximum concurrent SSH connections across the entire application is strictly capped at 100.
- Even if 10 stores are being audited with 12 tills each (120 targets), the thread pool enforces a hard budget ceiling of 100 simultaneous connections. Excess targets queue safely until connections free up.


================================================================================
8. THREE PRIMARY OPERATION MODES (THE 3 BUTTONS)
================================================================================

The UI features 3 dedicated operational modes:

8.1 Button 1: File Check (file_check)
- Scope: File existence, file size verification, last modified timestamp, and full variable extraction.
- Variable Value: Captures the full unstripped raw string (e.g. SessionTimeout=700000).
- Dynamic Table Headers:
  - Size Only filled: [Store, Device, IP, Latency, File Size, Last Modified, Status]
  - Variable Only filled: [Store, Device, IP, Latency, Variable / Value, Last Modified, Status]
  - Both filled: [Store, Device, IP, Latency, File Size, Last Modified, Variable / Value, Status]

8.2 Button 2: Version Check (version_check)
- Scope: Point of Sale application delivery number and patch version auditing.
- Extraction Rule: Looks for the content next to the word 'delivery' in the variable string:
  - If the variable contains 'delivery', captures whatever value comes immediately next to 'delivery':
      patch(delivery 75A)               -> 75A
      ts0034 = Patch 53 Delivery No 81A -> 81A
      Delivery No 79                    -> 79
      delivery: 23                      -> 23
  - If no 'delivery' keyword exists in the variable, takes the raw token (e.g. 23 or 81A).
- Exact Matching: If expected delivery is 23, it strictly compares against 23. Different tokens (e.g. 75A) produce Mismatch.
- Aggregated 5-Column Store Table Schema:
  To avoid cluttered individual rows, results are summarized into 1 row per store:
  [Store Code, IP, Mismatch Version, Offline, Status]
  - Store Code: Store identifier (e.g. Store-001)
  - IP: Store Back Office .12 subnet anchor IP (e.g. 192.168.29.12)
  - Mismatch Version: Comma-separated list of failed till numbers or BO (e.g. 4,6 or BO), or 'All Matched'.
  - Offline: Comma-separated list of unreachable tills or BO (e.g. 2 or BO), or '-'.
  - Status: Mismatch if any tills failed; Offline if tills unreachable with no mismatches; Success if all online tills matched.

8.3 Button 3: Terminal Console (terminal)
- Scope: Remote diagnostic commands and wget URL health checks.
- Dynamic Table Headers:
  Strictly displays: [Store, Device, IP, Latency, Command Output, Status].
  File Size, Last Modified, and Variable / Value headers are completely omitted.


================================================================================
9. TABLE PRESENTATION, WGET OUTPUT & INSPECTION
================================================================================

9.1 Wget Output Formatting
- Command Output Column (Table & CSV/Excel Export): Strictly displays the numeric HTTP status code (e.g. 200, 301, 404) or timeout token (Timeout (5s)). Long URLs and prefixes are omitted from table cells and exports.
- Row Inspection (Click / Double Click): Double-clicking any row opens the full output inspector modal and updates the terminal console screen with complete output: target URL, target machine IP, HTTP headers, latency, and raw terminal stdout.

9.2 Real-Time Sequential Streaming (Multi-URL Checks)
- When auditing multiple comma-separated URLs (e.g. wget https://site1.com, https://site2.com):
- Results stream in real-time order via callback. As soon as URL 1 finishes, it appears in the terminal and table immediately without waiting for remaining URLs.

9.3 Virtualized Table Display
- Displays up to 50 matching rows in GUI treeview to prevent UI lag.
- 100% of audit results are preserved in memory for CSV and Excel exports.


================================================================================
10. PASTE STORE LIST DIALOG & IN-MEMORY RETENTION
================================================================================

10.1 Dialog Layout & Buttons
The Paste Store List dialog features dedicated buttons at the bottom of the window:
- Clear: Clears text area and clears saved bulk stores.
- Cancel (or window close): Discards unsaved text. Re-opening dialog shows only previously saved text.
- Save: Parses store text, saves records into memory until app closure or Clear, and applies stores to target scope.

10.2 Supported Format in Dialog
  Store Code, IP, Till Count, Specific Tills
  - If Specific Tills is empty, audits all tills up to Till Count (e.g. 8 or 12).
  - If Specific Tills is specified (e.g. 1;3;5), audits only those specific tills.


================================================================================
11. INPUT FILE SPECIFICATIONS & HEADERS (CSV & EXCEL)
================================================================================

The application supports two distinct input formats:

Format A: Target Scope Bulk File (For Multi-Store Audits)
Used under Target Scope -> Bulk File (or Paste List):

Header Columns:
- Store Code (Required): Store identifier (e.g. Store-001)
- IP Address (Required): Base IP or .12 BO anchor (e.g. 192.168.29.12)
- Till Count (Optional): Number of tills in store (e.g. 8 or 12). Defaults to 10.
- Specific Tills (Optional): Specific tills to audit (e.g. 1,3,5 or 1;3;5). If empty, audits all tills.

Sample CSV (Format A):
Store Code,IP Address,Till Count,Specific Tills
Store-001,192.168.29.12,12,
Store-002,192.168.30.12,8,1;3;5
Store-003,192.168.31.12,6,

Sample Excel (Format A - Sheet 1):
Store Code   | IP Address    | Till Count | Specific Tills
Store-001    | 192.168.29.12 | 12         | 
Store-002    | 192.168.30.12 | 8          | 1, 3, 5
Store-003    | 192.168.31.12 | 6          | 


Format B: Re-Audit Version Report File (For Problem Tills Only)
Exported from Button 2 (Version Check) or prepared manually:

Header Columns:
- Store Code (Required): Store identifier
- IP (Required): Back Office .12 subnet anchor IP
- Mismatch Version (Required): List of failed tills (e.g. 4,6 or BO), or All Matched
- Offline (Required): List of offline tills (e.g. 2 or BO), or -
- Status (Optional): Overall audit status

Re-Audit Behavior:
- Stores marked 'All Matched' with no offline tills are automatically skipped.
- Problem stores audit strictly the listed failed tills.

Sample CSV (Format B):
Store Code,IP,Mismatch Version,Offline,Status
Store-001,192.168.29.12,"4,6",-,Mismatch
Store-002,192.168.30.12,All Matched,-,Success
Store-003,192.168.31.12,BO,2,Mismatch


================================================================================
12. STRICT TIMEOUT ENFORCEMENT & NETWORK BUFFERS
================================================================================

12.1 OS-Level Process Timeout Wrapper
- Wget commands are wrapped with Linux timeout to prevent timeout stacking:
    timeout {timeout}s wget --spider -S -t 1 -T {timeout} ...
- Guarantees that remote commands abort at the configured timeout (e.g. 5 seconds) instead of waiting 5s for DNS plus 5s for connect (10s total).

12.2 Network and Socket Buffer Reference
- Remote Process Timeout: Exactly {timeout}s (e.g. 5.0s).
- SSH Dispatch Buffer: +100 ms to 300 ms socket transport overhead for opening SSH channel and receiving EOF.
- Total Elapsed Time: ~5150 ms for a 5-second network timeout.


================================================================================
13. CRYPTOGRAPHY SERVICES & SECURITY POLICIES
================================================================================

- In-memory credentials encrypted using cryptography.fernet.Fernet with ephemeral keys.
- Remote binary probes use sha256sum for integrity verification.
- Passwords are never saved in cleartext or exported to log files.
- Stopping an audit immediately releases all worker threads and resets UI buttons to clickable state.
