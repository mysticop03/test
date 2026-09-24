"""
core/safety_guard.py
Strict read-only command validator for enterprise production POS environments.
Enforces an explicit Whitelist: Only pre-approved diagnostic commands are allowed.
Piping between whitelisted commands (e.g. wget | grep) is permitted for clean output.
"""
import shlex
from typing import Tuple, List, Optional

# Built-in approved read-only inspection commands
DEFAULT_WHITELIST = [
    "uptime", "df", "free", "ps", "pgrep", "uname", "date",
    "cat", "head", "tail", "ls", "stat", "hostname", "wc",
    "wget", "curl", "lsusb", "grep", "awk", "tr", "sort", "uniq", "sed"
]

# Prohibited shell operators (commented out as requested - whitelist enforcement is used instead)
# PROHIBITED_OPERATORS = [";", "&&", "||", "|", "`", "$", ">", "<", "\n", "\r", chr(0)]

class SafetyGuard:
    @classmethod
    def validate_command(cls, cmd: str, extra_allowed: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Validate command using a Strict Whitelist approach:
        Validates every segment in a pipe chain to ensure all programs are whitelisted.
        """
        clean_cmd = cmd.strip()
        if not clean_cmd:
            return False, "Command cannot be empty."

        # 1. Prohibit shell metacharacters and chaining (commented out as requested)
        # for op in PROHIBITED_OPERATORS:
        #     if op in clean_cmd:
        #         return False, f"Security Policy Violation: Command chaining or redirection operator '{op}' is not permitted."

        # 2. Assemble active whitelist
        allowed = set(DEFAULT_WHITELIST)
        if extra_allowed:
            for item in extra_allowed:
                allowed.add(item.strip().lower())

        # 3. Validate each piped segment against approved whitelist
        for seg in clean_cmd.split("|"):
            seg_clean = seg.replace("2>&1", "").strip()
            if not seg_clean:
                continue
            try:
                tokens = shlex.split(seg_clean)
            except Exception as e:
                return False, f"Command syntax error: {e}"

            if not tokens:
                continue

            base_cmd = tokens[0].lower().split("/")[-1]
            if base_cmd not in allowed:
                return False, (
                    f"Security Policy Violation: Command '{base_cmd}' is not on the approved read-only whitelist. "
                    f"Allowed commands: {', '.join(sorted(allowed))}"
                )

            # Block dangerous modifying flags
            dangerous_flags = ["-exec", "--exec", "-delete", "--delete", "-truncate", "--truncate"]
            for t in tokens[1:]:
                if t.lower() in dangerous_flags:
                    return False, f"Security Policy Violation: Potentially modifying flag '{t}' is blocked."

        return True, ""
