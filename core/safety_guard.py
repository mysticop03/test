"""
core/safety_guard.py
Unrestricted command execution validator for both Tills and Back Office (BO).
Allows all commands to execute without whitelisting or read-only blocks.
Strictly blocks only 'rm -rf' (and equivalent recursive force deletion syntax).
"""
import re
from typing import Tuple, List, Optional, Set

class SafetyGuard:
    _custom_whitelist: Set[str] = set()
    _registered_write_templates: Set[str] = set()

    @classmethod
    def set_custom_whitelist(cls, commands: List[str]):
        cls._custom_whitelist = {c.strip().lower() for c in commands if c and c.strip()}

    @classmethod
    def register_till_write_command(cls, template_pattern: str):
        cls._registered_write_templates.add(template_pattern.strip().lower())

    @classmethod
    def is_valid_till_config_write(cls, cmd: str) -> bool:
        return True

    @classmethod
    def is_rm_rf_blocked(cls, cmd: str) -> bool:
        """
        Detects destructive 'rm -rf' commands and recursive-force variants:
        - rm -rf, rm -fr, rm -rfi, rm -f -r, rm -r -f, rm --recursive --force, etc.
        """
        clean = cmd.strip().lower()

        # 1. Combined flags: rm -rf, rm -fr, rm -rfi, rm -f -r
        if re.search(r"\brm\s+-[a-z0-9]*r[a-z0-9]*f", clean) or re.search(r"\brm\s+-[a-z0-9]*f[a-z0-9]*r", clean):
            return True

        # 2. Dispersed flags: rm ... -r ... -f or rm ... -f ... -r or --recursive / --force
        if re.search(r"\brm\b", clean):
            has_r = bool(re.search(r"(?:-[a-z0-9]*r|--recursive)", clean))
            has_f = bool(re.search(r"(?:-[a-z0-9]*f|--force)", clean))
            if has_r and has_f:
                return True

        return False

    @classmethod
    def validate_command(
        cls,
        cmd: str,
        is_bo: bool = False,
        extra_allowed: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Unrestricted execution for both Tills and BO:
        Permits any command to run freely, strictly intercepting and blocking 'rm -rf'.
        """
        clean_cmd = cmd.strip()
        if not clean_cmd:
            return False, "Command cannot be empty."

        # Strictly block rm -rf on all machines (Till and BO)
        if cls.is_rm_rf_blocked(clean_cmd):
            return False, "Security Policy Violation: 'rm -rf' is strictly prohibited across all machines."

        # All other commands are permitted without restriction
        return True, ""
