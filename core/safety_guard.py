"""
core/safety_guard.py
Strict command validator for enterprise production POS environments.
Implements Section 1.1 and 1.2 of SYSTEM_RULES_AND_CONDITIONS.md:
1. Back Office (.15): Strictly 100% Read-Only through 4 inspection tiers.
2. Tills (.112+): Whitelisted read-only inspection + controlled in-place write hook.
Supports diagnostic commands including 'ps -ef | grep jre' and 'dotnet'.
"""
import shlex
import re
from typing import Tuple, List, Optional, Set

# Built-in approved read-only inspection commands
DEFAULT_WHITELIST = [
    "uptime", "who", "last", "df", "free", "ps", "pgrep", "uname", "date",
    "cat", "head", "tail", "ls", "stat", "hostname", "wc", "pwd", "cd",
    "wget", "lsusb", "grep", "egrep", "awk", "tr", "sort", "uniq", "sed",
    "cut", "which", "dotnet", "java", "find", "netstat", "ss", "ip",
    "systemctl", "journalctl", "dpkg", "dpkg-query", "echo", "top", "lsof"
]

# Prohibited on Back Office (.15) - 4 Inspection Tiers
BO_PROHIBITED_REDIRECTIONS = [">", ">>", ">|", "&>", "1>", "2>"]
BO_PROHIBITED_PIPE_WRITERS = ["tee", "dd"]
BO_PROHIBITED_MODIFYING_UTILITIES = [
    "rm", "truncate", "touch", "cp", "mv", "chmod", "chown",
    "kill", "pkill", "killall", "apt", "apt-get", "dpkg -i",
    "useradd", "userdel", "usermod", "reboot", "shutdown", "init"
]

class SafetyGuard:
    _registered_write_templates: Set[str] = set()

    @classmethod
    def register_till_write_command(cls, template_pattern: str):
        """Register a verified in-place config modification template for Tills."""
        cls._registered_write_templates.add(template_pattern.strip().lower())

    @classmethod
    def is_valid_till_config_write(cls, cmd: str) -> bool:
        """
        Validates controlled in-place config modification template on Tills per Section 1.1:
        FILE="..."
        if grep -q "^<key>=" "$FILE"; then
            sed -i 's/^<key>=.*/<key>=<val>/' "$FILE"
        else
            echo "<key>=<val>" >> "$FILE"
        fi
        grep "^<key>=" "$FILE"
        """
        clean = cmd.strip()
        cmd_lower = clean.lower()

        # Must contain essential components of in-place config update
        has_grep = "grep -q" in cmd_lower or "grep " in cmd_lower
        has_sed = "sed -i" in cmd_lower
        has_echo = any(h in cmd_lower for h in ["echo ", "echo\t", "echo\"", "echo'"])
        has_append = ">>" in cmd_lower
        has_conditional = "if " in cmd_lower and "then" in cmd_lower and "fi" in cmd_lower

        if not (has_grep and has_sed and has_echo and has_append and has_conditional):
            return False

        # Must NOT contain forbidden dangerous binaries, tampering, or privilege escalation
        forbidden = [
            "rm ", "rm\t", "rmdir", "truncate", "kill", "pkill", "killall",
            "apt", "dpkg -i", "reboot", "shutdown", "init", "mkfs", "dd ",
            "useradd", "userdel", "usermod", "passwd", "sudo", "su -",
            "/etc/shadow", "/etc/sudoers", "/boot/", "/dev/sda", "/dev/nvme",
            "/dev/tcp", "nc -e", "socat"
        ]
        for f in forbidden:
            if f in cmd_lower:
                return False

        # Check for command substitution
        if "$(" in clean or "`" in clean:
            return False

        # Check that sed command is strictly a substitution: s/.../.../ (or s#...#...# or s|...|...|)
        if not re.search(r"sed\s+-i\s+['\"][sS][/#|]", clean):
            return False

        return True

    @classmethod
    def validate_command(
        cls,
        cmd: str,
        is_bo: bool = False,
        extra_allowed: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Validate command per Section 1.1 & 1.2 rules.
        Strictly enforces that ONLY approved whitelisted commands can ever execute.
        """
        clean_cmd = cmd.strip()
        if not clean_cmd:
            return False, "Command cannot be empty."

        cmd_lower = clean_cmd.lower()

        # Check if this matches authorized In-Place Config Update template on Tills (Section 1.1)
        if cls.is_valid_till_config_write(clean_cmd):
            if is_bo:
                return False, "Security Policy Violation on Back Office: In-place configuration write commands are strictly prohibited on 100% Read-Only BO. (Permitted on Tills only)."
            return True, ""

        # ====================================================================
        # Universal Attack & Tampering Defenses (Active on both Tills and BO)
        # ====================================================================
        # 1. Reverse shell & network exfiltration blocked
        rev_shell_patterns = [r"\bnc\s+-e\b", r"\bsocat\b", r"/dev/tcp/", r"\bpython.*-c.*socket\b", r"\bperl.*-e.*socket\b"]
        for pat in rev_shell_patterns:
            if re.search(pat, cmd_lower):
                return False, "Security Violation: Reverse shell or network socket exfiltration blocked."

        # 2. OS tampering and protected target access blocked
        os_protected_targets = ["/etc/shadow", "/etc/sudoers", "/dev/sda", "/dev/nvme", "/boot/"]
        for target in os_protected_targets:
            if target in cmd_lower:
                return False, f"Security Violation: Access to critical system target '{target}' is blocked."

        # Modifying /etc/passwd
        if "/etc/passwd" in cmd_lower and any(op in cmd_lower for op in [">", "rm", "chmod", "chown", "mv", "cp", "dd", "sed"]):
            return False, "Security Violation: Tampering with '/etc/passwd' is blocked."

        # 3. Privilege escalation blocked
        priv_escalation = [r"\bsu\s+-", r"\bsudo\s+su\b", r"\bsudo\s+-i\b", r"\bvisudo\b", r"\bpasswd\b", r"\biptables\s+-f\b"]
        for pat in priv_escalation:
            if re.search(pat, cmd_lower):
                return False, "Security Violation: Privilege escalation attempt blocked."

        # 4. Command substitution injection blocked ($() and backticks)
        if "$(" in clean_cmd or "`" in clean_cmd:
            return False, "Security Violation: Command substitution ($() or backticks) is strictly prohibited."

        # ====================================================================
        # Multi-Layer Defense on Back Office (BO Server .15) - 100% Read-Only
        # ====================================================================
        if is_bo:
            # Tier 1: Redirection Inspection
            clean_for_redirs = clean_cmd.replace("2>&1", "")
            for op in BO_PROHIBITED_REDIRECTIONS:
                if op in clean_for_redirs and not (clean_for_redirs.startswith('"') and clean_for_redirs.endswith('"')):
                    return False, f"Security Policy Violation on Back Office: Redirection operator '{op}' is prohibited on 100% Read-Only BO."

            # Tier 2: Piped Output Writer Inspection
            for seg in clean_cmd.split("|"):
                seg_tokens = seg.strip().split()
                if seg_tokens and seg_tokens[0].lower() in BO_PROHIBITED_PIPE_WRITERS:
                    return False, f"Security Policy Violation on Back Office: Output stream writer '{seg_tokens[0]}' blocked."

            # Tier 3: Modifying Utility Filter
            for util in BO_PROHIBITED_MODIFYING_UTILITIES:
                if util == "reboot" and re.search(r"\blast\s+.*reboot\b", cmd_lower):
                    continue  # 'last reboot' is an audit of past reboots, not a system reboot
                if re.search(rf"\b{re.escape(util)}\b", cmd_lower):
                    return False, f"Security Policy Violation on Back Office: Modifying utility '{util}' blocked."

            if "sed -i" in cmd_lower:
                return False, "Security Policy Violation on Back Office: In-place sed editing blocked."
            if "systemctl" in cmd_lower and any(act in cmd_lower for act in ["restart", "stop", "disable", "reload"]):
                return False, "Security Policy Violation on Back Office: Service modification blocked (use 'systemctl status')."
            if "wget" in cmd_lower:
                # Only block writing to disk (e.g. -O file or -o file, but allow -O - or spider or standard URL checks)
                if re.search(r"(?:-O\s+(?!-|/dev/null)|-o\s+(?!/dev/null)|--output(?:-document)?\s+(?!-|/dev/null))", clean_cmd):
                    return False, "Security Policy Violation on Back Office: Writing downloaded files to disk is blocked (URL inspection and stdout allowed)."

            # Tier 4: Script & Eval Filter
            if any(h in cmd_lower for h in ["python -c", "python3 -c", "eval ", "exec "]):
                return False, "Security Policy Violation on Back Office: Arbitrary script execution / eval blocked."

        # ====================================================================
        # HTTP / HTTPS URL Inspection Handling (Strictly wget with comma-separated URLs)
        # ====================================================================
        # Strictly supports 'wget <url>' or multiple comma-separated URLs e.g. "wget https://a.com, https://b.com"
        urls = re.findall(r'https?://[^\s,;"\'<>]+', clean_cmd)
        first_word = clean_cmd.split()[0].rstrip(",;").lower() if clean_cmd.split() else ""
        if urls and first_word == "wget":
            # On Back Office: Block writing downloaded files to disk (allow stdout - or /dev/null or spider inspection)
            if is_bo and "wget" in cmd_lower:
                if re.search(r'(?:-O\s+(?!-|/dev/null)|-o\s+(?!/dev/null)|--output(?:-document)?\s+(?!-|/dev/null))', clean_cmd):
                    return False, "Security Policy Violation on Back Office: Writing downloaded files to disk is blocked (URL inspection and stdout allowed)."

            # Protect against destructive/prohibited binaries chained with URL commands
            destructive_commands = [
                "rm", "reboot", "shutdown", "init", "mkfs", "truncate", "kill", "pkill", "killall",
                "su", "sudo", "useradd", "userdel", "usermod", "passwd", "chmod", "chown", "dd",
                "bash", "sh", "zsh", "python", "perl"
            ]
            scrubbed = re.sub(r'https?://[^\s,;"\'<>]+', '', clean_cmd)
            words = [w.strip(';,&|()[]{}"\' \t').lower() for w in re.split(r'[\s;,&|]+', scrubbed) if w.strip(';,&|()[]{}"\' \t')]
            for w in words:
                if w in destructive_commands:
                    return False, f"Security Violation: Prohibited command '{w}' blocked."
            return True, ""

        allowed = set(DEFAULT_WHITELIST)
        if extra_allowed:
            for item in extra_allowed:
                allowed.add(item.strip().lower())

        # Split statements by statement delimiters (;, &&, ||, \n) while preserving 2>&1
        scrubbed = clean_cmd.replace("2>&1", "")
        # Split on statements
        statements = re.split(r"(?:&&|\|\||[;\n])", scrubbed)

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            # Split statement into piped segments
            segments = stmt.split("|")
            for seg in segments:
                seg_clean = seg.strip()
                if not seg_clean:
                    continue

                try:
                    tokens = shlex.split(seg_clean)
                except Exception:
                    tokens = seg_clean.split()

                if not tokens:
                    continue

                base_cmd = tokens[0].lower().split("/")[-1]
                if base_cmd not in allowed:
                    # Check if it matches any registered in-place write templates on Tills
                    is_registered = any(t in cmd_lower for t in cls._registered_write_templates)
                    if not is_registered:
                        return False, (
                            f"Security Policy Violation: Command '{base_cmd}' is NOT permitted. "
                            f"Execution is strictly restricted to approved commands: {', '.join(sorted(DEFAULT_WHITELIST[:15]))}..."
                        )

                # Block dangerous modifying flags
                dangerous_flags = [
                    "-exec", "--exec", "-delete", "--delete", "-truncate", "--truncate",
                    "-ok", "--ok", "-i", "--in-place"
                ]
                for t in tokens[1:]:
                    tl = t.lower()
                    if tl in dangerous_flags and base_cmd in ("find", "sed"):
                        return False, f"Security Policy Violation: Dangerous modifying flag '{t}' is blocked on '{base_cmd}'."

                # If systemctl, strictly allow only status and queries
                if base_cmd == "systemctl":
                    disallowed_verbs = ["start", "stop", "restart", "reload", "disable", "enable", "mask", "unmask"]
                    for t in tokens[1:]:
                        if t.lower() in disallowed_verbs:
                            return False, f"Security Policy Violation: 'systemctl {t}' is prohibited. Only inspection commands like 'systemctl status' are allowed."

                # If dpkg, block installation or removal
                if base_cmd == "dpkg":
                    for t in tokens[1:]:
                        if t.lower() in ["-i", "-r", "-p", "--install", "--remove", "--purge"]:
                            return False, f"Security Policy Violation: Package modification flag '{t}' on 'dpkg' is blocked."

        return True, ""
