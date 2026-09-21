"""
core/safety_guard.py
Strict read-only command validator for enterprise production POS environments.
Enforces an explicit Whitelist: Only pre-approved diagnostic commands are allowed.
Blocks command chaining, subshells, reverse shells, code execution, and unauthorized utilities.
"""
import shlex
from typing import Tuple, List, Optional

GLOBAL_BYPASS_SAFETY = False

# Built-in approved read-only inspection commands
DEFAULT_WHITELIST = [
    "uptime", "df", "free", "ps", "pgrep", "uname", "date",
    "cat", "head", "tail", "ls", "stat", "hostname", "wc"
]

# Prohibited shell operators that enable command chaining or file redirection
PROHIBITED_OPERATORS = [";", "&&", "||", "|", "`", "$", ">", "<", "\n", "\r", chr(0)]

class SafetyGuard:
    @classmethod
    def validate_command(cls, cmd: str, extra_allowed: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Validate command using a Strict Whitelist approach:
        1. Check for command chaining and redirection operators.
        2. Extract the base executable / program name.
        3. Ensure the base executable is on the approved whitelist.
        """
        if GLOBAL_BYPASS_SAFETY:
            return True, ""

        clean_cmd = cmd.strip()
        if not clean_cmd:
            return False, "Command cannot be empty."

        # 1. Prohibit shell metacharacters and chaining
        for op in PROHIBITED_OPERATORS:
            if op in clean_cmd:
                return False, f"Security Policy Violation: Command chaining or redirection operator '{op}' is not permitted."

        # 2. Parse base command token safely
        try:
            tokens = shlex.split(clean_cmd)
        except Exception as e:
            return False, f"Command syntax error: {e}"

        if not tokens:
            return False, "Command cannot be empty."

        base_cmd = tokens[0].lower().split("/")[-1]  # Handles /bin/df or /usr/bin/uptime

        # 3. Assemble active whitelist
        allowed = set(DEFAULT_WHITELIST)
        if extra_allowed:
            for item in extra_allowed:
                allowed.add(item.strip().lower())

        if base_cmd not in allowed:
            return False, (
                f"Security Policy Violation: Command '{base_cmd}' is not on the approved read-only whitelist. "
                f"Allowed commands: {', '.join(sorted(allowed))}"
            )

        # 4. Block dangerous flags on otherwise safe commands (e.g. sed -i, find -exec, cat > file)
        dangerous_flags = ["-exec", "--exec", "-delete", "--delete", "-truncate", "--truncate"]
        for t in tokens[1:]:
            if t.lower() in dangerous_flags:
                return False, f"Security Policy Violation: Potentially modifying flag '{t}' is blocked."

        return True, ""
