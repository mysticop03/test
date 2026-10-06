"""
core/file_checker.py
Builds remote bash commands to check file size, last modified date, and property variables on Ubuntu POS tills and Back Office.
Parses delimited outputs and evaluates size tolerances and version matches.
"""
import shlex
import re
from typing import Tuple, Dict, Any, Optional
from models.result import AuditResult, AuditStatus

def format_bytes_human(num_bytes: int) -> str:
    """Format bytes into pure decimal MB (1 MB = 1,000,000 bytes) matching Ubuntu desktop display."""
    if num_bytes <= 0:
        return "-"
    mb = num_bytes / 1000000.0
    return f"{mb:.1f} MB"

def sanitize_file_path(p: str) -> str:
    """Sanitize path, preventing null-byte injection and multiline command escape."""
    clean = str(p).strip().replace("\r", "").replace("\n", "").replace("\0", "")
    return clean

def sanitize_variable_name(var: str) -> str:
    """Sanitize properties variable/keyword ensuring only safe alphanumeric characters."""
    clean = str(var).strip().replace("\r", "").replace("\n", "").replace("\0", "")
    clean = re.sub(r"[^\w.-]", "", clean)
    return clean if clean else "timeout"

def extract_variable_value(file_content: str, variable_name: str) -> Optional[str]:
    """Matches: optional whitespace, variable_name, optional whitespace, '=', optional whitespace, capturing value."""
    pattern = rf'^\s*{re.escape(variable_name)}\s*=\s*(.*?)\s*$'
    match = re.search(pattern, file_content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def parse_expected_size_safe(exp_input: Any) -> Tuple[int, int]:
    """Safely parses any size representation (str, int, float) to (dec_bytes, bin_bytes)."""
    if exp_input is None:
        return 0, 0

    s = str(exp_input).strip().lower().replace(",", "")
    if not s or s in ("0", "none", "-", ""):
        return 0, 0

    num_part = re.sub(r"[^0-9.]", "", s)
    if not num_part:
        return 0, 0

    try:
        val = float(num_part)
    except ValueError:
        return 0, 0

    if val <= 0:
        return 0, 0

    if "gb" in s or "g" in s:
        return int(val * 1000 * 1000 * 1000), int(val * 1024 * 1024 * 1024)
    elif "kb" in s or "k" in s:
        return int(val * 1000), int(val * 1024)
    elif "mb" in s or "m" in s or val < 5000:
        dec_b = int(round(val * 1000 * 1000))
        bin_b = int(round(val * 1024 * 1024))
        return dec_b, bin_b
    else:
        raw_b = int(round(val))
        return raw_b, raw_b

def evaluate_size_match(actual_bytes: int, exp_input: Any, tolerance_bytes: int = 314572) -> Tuple[bool, int]:
    """Evaluates whether actual file size matches expected size within tolerance (+-0.3 MB default)."""
    dec_exp, bin_exp = parse_expected_size_safe(exp_input)
    if dec_exp <= 0 and bin_exp <= 0:
        return True, 0

    diff_dec = abs(actual_bytes - dec_exp)
    diff_bin = abs(actual_bytes - bin_exp)
    if diff_dec <= tolerance_bytes:
        return True, dec_exp
    if diff_bin <= tolerance_bytes:
        return True, bin_exp

    equiv_decimal_bytes = int(round((actual_bytes / 1048576.0) * 1000000.0))
    equiv_binary_bytes = int(round((actual_bytes / 1000000.0) * 1048576.0))
    if abs(equiv_decimal_bytes - dec_exp) <= tolerance_bytes or abs(equiv_decimal_bytes - bin_exp) <= tolerance_bytes:
        return True, dec_exp
    if abs(equiv_binary_bytes - dec_exp) <= tolerance_bytes or abs(equiv_binary_bytes - bin_exp) <= tolerance_bytes:
        return True, bin_exp

    closest = dec_exp if diff_dec < diff_bin else bin_exp
    return False, closest

def extract_delivery_token(val: str) -> str:
    """Extract standalone delivery token, e.g. '75A', '56', '56A'."""
    s = val.strip()
    m = re.search(r"(?i)delivery(?:version)?\s*[:=-]?\s*([0-9]+[a-zA-Z]*)", s)
    if m:
        return m.group(1).upper()
    m2 = re.search(r"^([0-9]+[a-zA-Z]*)$", s)
    if m2:
        return m2.group(1).upper()
    return ""

def matches_value(actual_val: str, expected_input: str) -> bool:
    """Matches actual variable value against expected input."""
    exp_clean = expected_input.strip()
    if not exp_clean:
        return True

    act_clean = actual_val.strip()
    if not act_clean or act_clean in ("MISSING", "NOT_FOUND", "-"):
        return False

    if exp_clean.lower() == act_clean.lower():
        return True

    act_token = extract_delivery_token(act_clean)
    exp_token = extract_delivery_token(exp_clean)
    if act_token and exp_token:
        return act_token == exp_token

    pattern = r"(?i)(?<![0-9a-zA-Z])" + re.escape(exp_clean) + r"(?![0-9a-zA-Z])"
    return bool(re.search(pattern, act_clean))

class FileChecker:
    @staticmethod
    def build_version_war_probe(war_path: str, prop_path: str, variable: str) -> str:
        """Builds compound bash probe extracting file size, modified date, and property variable."""
        safe_war = shlex.quote(sanitize_file_path(war_path)) if war_path else "''"
        safe_prop = shlex.quote(sanitize_file_path(prop_path)) if prop_path else "''"
        clean_var = sanitize_variable_name(variable)

        awk_cmd = (
            "awk -F'=' 'BEGIN{IGNORECASE=1} /^[ \\t]*" + clean_var + "[ \\t]*=/ "
            "{gsub(/^[ \\t]+|[ \\t]+$/, \"\", $2); print $2; exit}' " + safe_prop + " 2>/dev/null"
        )

        probe = (
            "if [ -n " + safe_war + " ] && [ -f " + safe_war + " ]; then "
            "W_SZ=$(stat -c '%s' " + safe_war + " 2>/dev/null || wc -c < " + safe_war + "); "
            "W_TIME=$(stat -c '%y' " + safe_war + " 2>/dev/null || date -r " + safe_war + " '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '-'); "
            "else W_SZ=MISSING; W_TIME='-'; fi; "
            "if [ -n " + safe_prop + " ] && [ -f " + safe_prop + " ]; then "
            "P_VAL=$(" + awk_cmd + " | tr -d '\\r\\n'); "
            "[ -z \"$P_VAL\" ] && P_VAL='NOT_FOUND'; "
            "else P_VAL=MISSING; fi; "
            'echo "WAR|${W_SZ:-0}|${W_TIME:--}|PROP|${P_VAL:--}|' + clean_var + '"'
        )
        return probe

    @staticmethod
    def parse_version_war_output(
        stdout_txt: str,
        expected_size_bytes: Any,
        expected_val_str: str,
        result: AuditResult,
        tolerance_bytes: int = 314572
    ) -> AuditResult:
        line = stdout_txt.strip().splitlines()[-1] if stdout_txt.strip() else ""
        parts = line.split("|")

        if len(parts) >= 6 and parts[0] == "WAR":
            raw_war_sz = parts[1].strip()
            raw_war_time = parts[2].strip()
            raw_prop_val = parts[4].strip()
            var_name = parts[5].strip()

            if "." in raw_war_time:
                date_part, rest = raw_war_time.split(".", 1)
                tz_part = rest.split(" ")[-1] if " " in rest else ""
                clean_time = f"{date_part} {tz_part}".strip()
            else:
                clean_time = raw_war_time

            result.war_modified = clean_time
            result.delivery_version = raw_prop_val if raw_prop_val not in ("MISSING", "NOT_FOUND") else "-"
            result.prop_variable = f"{var_name}={raw_prop_val}" if raw_prop_val not in ("MISSING", "NOT_FOUND") else f"{var_name}=-"
            result.expected_version = str(expected_val_str) if expected_val_str else "-"

            check_size = bool(expected_size_bytes) and str(expected_size_bytes).strip() not in ("", "0", "-")
            check_val = bool(expected_val_str) and str(expected_val_str).strip() not in ("", "-")

            war_missing = (raw_war_sz == "MISSING")
            prop_missing = (raw_prop_val in ("MISSING", "NOT_FOUND"))

            if war_missing and check_size:
                result.status = AuditStatus.MISS
                result.preview_output = "WAR File Missing"
                result.full_output = "Specified WAR file does not exist on target machine."
                return result

            if prop_missing and check_val:
                result.status = AuditStatus.MISS
                result.preview_output = f"Variable '{var_name}' or Property File Missing"
                result.full_output = f"Variable '{var_name}' not found in property file on target machine."
                return result

            try:
                sz_bytes = int(raw_war_sz) if not war_missing else 0
            except ValueError:
                sz_bytes = 0

            result.war_size_bytes = sz_bytes
            result.war_size = format_bytes_human(sz_bytes) if not war_missing else "-"

            size_matches = True
            if check_size:
                size_matches, _ = evaluate_size_match(sz_bytes, expected_size_bytes, tolerance_bytes)

            val_matches = True
            if check_val:
                val_matches = matches_value(raw_prop_val, expected_val_str)

            if size_matches and val_matches:
                result.status = AuditStatus.SUCCESS
                if check_size and check_val:
                    result.preview_output = f"✓ Match ({result.war_size}, {raw_prop_val})"
                elif check_size:
                    result.preview_output = f"✓ Match ({result.war_size})"
                elif check_val:
                    result.preview_output = f"✓ Match ({raw_prop_val})"
                else:
                    result.preview_output = f"✓ OK ({result.war_size})"
                result.full_output = (
                    f"Audit Passed Successfully!\n"
                    f"Target: {result.till_name} ({result.ip})\n"
                    f"File Size: {result.war_size} ({sz_bytes} bytes)\n"
                    f"Last Modified: {clean_time}\n"
                    f"Variable: {var_name} = {raw_prop_val}\n"
                    f"Expected Size: {expected_size_bytes} | Expected Value: {expected_val_str}"
                )
            else:
                result.status = AuditStatus.MISMATCH
                reasons = []
                if not size_matches:
                    reasons.append(f"Size: actual {result.war_size} != expected {expected_size_bytes}")
                if not val_matches:
                    reasons.append(f"Value: actual '{raw_prop_val}' != expected '{expected_val_str}'")
                result.preview_output = " | ".join(reasons)
                result.full_output = (
                    f"Audit Mismatch Detected:\n"
                    f"Target: {result.till_name} ({result.ip})\n"
                    f"Details: {result.preview_output}\n"
                    f"File Size: {result.war_size} | Last Modified: {clean_time}\n"
                    f"Actual Variable Value: {raw_prop_val}"
                )

        return result

# Backward-compatibility alias
ProbeEngine = FileChecker
