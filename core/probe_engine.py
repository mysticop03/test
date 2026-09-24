"""
core/probe_engine.py
Generates single-shot, enterprise-grade secure remote bash probes for Ubuntu tills.
Extracts WAR size, mtime, and parses delivery version from .properties in one round trip.
All inputs are strictly sanitized and quoted with shlex.quote() to prevent command injection (CWE-78).
Includes robust delivery version parsing for ETP Store (TS00046) and fail-safe size evaluation.
"""
import shlex
import re
from typing import Tuple, Dict, Any
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

def sanitize_keyword(kw: str) -> str:
    """Sanitize properties keyword ensuring only safe alphanumeric characters."""
    clean = str(kw).strip().replace("\r", "").replace("\n", "").replace("\0", "")
    clean = re.sub(r"[^\w.-]", "", clean)
    return clean if clean else "TS00046"

def parse_expected_size_safe(exp_input: Any) -> Tuple[int, int]:
    """
    Safely parses any size representation (str, int, float) to (dec_bytes, bin_bytes).
    Returns (0, 0) if disabled, empty, or unparseable.
    Handles '184.5 MB', '184.5', '184549376', '176M', etc.
    """
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
        # User entered MB value like 184.5 or 176
        dec_b = int(round(val * 1000 * 1000))
        bin_b = int(round(val * 1024 * 1024))
        return dec_b, bin_b
    else:
        # Raw bytes
        raw_b = int(round(val))
        return raw_b, raw_b

def evaluate_size_match(actual_bytes: int, exp_input: Any, tolerance_bytes: int = 314572) -> Tuple[bool, int]:
    """
    Evaluates whether actual file size in bytes matches expected size within tolerance.
    Supports dual decimal (MB) and binary (MiB) matching.
    Never throws TypeError regardless of input type.
    Returns: (is_match, representative_expected_bytes)
    """
    dec_exp, bin_exp = parse_expected_size_safe(exp_input)
    if dec_exp <= 0 and bin_exp <= 0:
        return True, 0  # Size check disabled

    # Direct difference
    diff_dec = abs(actual_bytes - dec_exp)
    diff_bin = abs(actual_bytes - bin_exp)
    if diff_dec <= tolerance_bytes:
        return True, dec_exp
    if diff_bin <= tolerance_bytes:
        return True, bin_exp

    # Dual unit conversions (Ubuntu stat decimal vs binary file sizes)
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

def extract_delivery_info(raw_prop_val: str) -> Tuple[str, str]:
    """
    Extracts delivery number/token and clean display version from properties value.
    E.g.: 'ETP Store V5.5 Patch 53(Delivery 81)' -> ('81', 'Delivery 81 (Patch 53)')
          'ETP Store V5.5 Patch 53(Delivery 75A)' -> ('75A', 'Delivery 75A (Patch 53)')
          'ETP Store V5.5 Patch 53(Delivery 56)' -> ('56', 'Delivery 56 (Patch 53)')
          'ETP Store V5.5 Patch 53(Delivery 56A)' -> ('56A', 'Delivery 56A (Patch 53)')
    """
    val = raw_prop_val.strip()
    if not val or val in ("MISSING", "NOT_FOUND", "-"):
        return "-", val

    m_deliv = re.search(r"(?i)delivery(?:version)?\s*[:=-]?\s*([0-9]+[a-zA-Z]*)", val)
    if m_deliv:
        deliv_num = m_deliv.group(1).strip()
        m_patch = re.search(r"(?i)patch\s*[:=-]?\s*([0-9]+[a-zA-Z]*)", val)
        if m_patch:
            display_str = f"Delivery {deliv_num} (Patch {m_patch.group(1)})"
        else:
            display_str = f"Delivery {deliv_num}"
        return deliv_num, display_str

    if re.match(r"^([0-9]+[a-zA-Z]*)$", val):
        return val, f"Delivery {val}"

    return val, val

def matches_delivery_version(actual_val: str, expected_input: str) -> bool:
    """
    Strict delivery version matcher:
    - Entering '75A' matches '75A' or 'Delivery 75A', but NOT '75' or '75B'.
    - Entering '56' matches '56' or 'Delivery 56', but NOT '56A'.
    - Entering '56A' matches '56A' or 'Delivery 56A', but NOT '56'.
    """
    exp_clean = expected_input.strip()
    if not exp_clean:
        return True  # Blank expectation = pass any valid version

    act_clean = actual_val.strip()
    if not act_clean or act_clean in ("MISSING", "NOT_FOUND", "-"):
        return False

    # 1. Exact full string match (case-insensitive)
    if exp_clean.lower() == act_clean.lower():
        return True

    # 2. Extract delivery tokens from both sides
    act_token = extract_delivery_token(act_clean)
    exp_token = extract_delivery_token(exp_clean)

    target_token = exp_token if exp_token else exp_clean.upper()

    if act_token:
        # STRICT EXACT TOKEN MATCH: '56' != '56A'
        return target_token == act_token

    # 3. If no delivery token found, use strict non-word boundary matching (never loose substring)
    pattern = r"(?i)(?<![0-9a-zA-Z])" + re.escape(exp_clean) + r"(?![0-9a-zA-Z])"
    return bool(re.search(pattern, act_clean))

class ProbeEngine:
    @staticmethod
    def build_version_war_probe(war_path: str, prop_path: str, keyword: str) -> str:
        """
        Builds a single compound bash probe executed in ONE network round trip:
        1. Checks WAR file size in bytes and last modified timestamp.
        2. Checks .properties file, greps for keyword (case-insensitive), extracts variable key and value.
        Outputs structured delimiter:
        WAR|<bytes>|<mtime>|PROP|<value>|<full_line>
        """
        safe_war = shlex.quote(sanitize_file_path(war_path))
        safe_prop = shlex.quote(sanitize_file_path(prop_path))
        safe_kw = shlex.quote(sanitize_keyword(keyword))

        probe = (
            "if [ -f " + safe_war + " ]; then "
            "W_SZ=$(stat -c '%s' " + safe_war + " 2>/dev/null || wc -c < " + safe_war + "); "
            "W_TIME=$(stat -c '%y' " + safe_war + " 2>/dev/null || date -r " + safe_war + " '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '-'); "
            "else W_SZ=MISSING; W_TIME='-'; fi; "
            "if [ -f " + safe_prop + " ]; then "
            "P_LINE=$(grep -i " + safe_kw + " " + safe_prop + " 2>/dev/null | head -n 1 | sed -e 's/^[ \t]*//' | tr -d '\r\n'); "
            'if [ -n "$P_LINE" ]; then '
            'P_VAL=$(echo "$P_LINE" | awk -F\'=\' \'{print $2}\' | sed -e \'s/^[ \t]*//\' | tr -d \'\\r\\n\'); '
            '[ -z "$P_VAL" ] && P_VAL="$P_LINE"; '
            "else P_VAL='NOT_FOUND'; fi; "
            "else P_VAL=MISSING; P_LINE='-'; fi; "
            'echo "WAR|${W_SZ:-0}|${W_TIME:--}|PROP|${P_VAL:--}|${P_LINE:--}"'
        )
        return probe

    @staticmethod
    def parse_version_war_output(
        stdout_txt: str,
        expected_size_bytes: Any,
        expected_version_str: str,
        result: AuditResult,
        tolerance_bytes: int = 314572  # 0.3 MB tolerance default
    ) -> AuditResult:
        line = stdout_txt.strip().splitlines()[-1] if stdout_txt.strip() else ""
        parts = line.split("|")

        if len(parts) >= 6 and parts[0] == "WAR":
            raw_war_sz = parts[1].strip()
            raw_war_time = parts[2].strip()
            raw_prop_val = parts[4].strip()
            raw_prop_line = parts[5].strip()

            if "." in raw_war_time:
                date_part, rest = raw_war_time.split(".", 1)
                tz_part = rest.split(" ")[-1] if " " in rest else ""
                clean_time = f"{date_part} {tz_part}".strip()
            else:
                clean_time = raw_war_time

            result.war_modified = clean_time
            deliv_num, deliv_display = extract_delivery_info(raw_prop_val)
            result.delivery_version = deliv_display
            result.prop_variable = raw_prop_line

            # Determine which checks are active based on what the user filled in
            check_size = bool(expected_size_bytes) and str(expected_size_bytes).strip() not in ("", "0", "-")
            check_version = bool(expected_version_str) and expected_version_str.strip() not in ("", "-")

            # Handle MISSING files: only fail if we actually need that file
            war_missing = (raw_war_sz == "MISSING")
            prop_missing = (raw_prop_val == "MISSING" or raw_prop_val == "NOT_FOUND")

            if war_missing and check_size:
                result.status = AuditStatus.FILE_MISSING
                result.preview_output = "WAR File Missing"
                result.full_output = f"WAR file not found on till (needed for size check)"
                if prop_missing and check_version:
                    result.preview_output = "Missing: WAR File, Properties File"
                    result.full_output = "Both WAR and Properties files missing on till"
                return result
            if prop_missing and check_version:
                result.status = AuditStatus.FILE_MISSING
                result.preview_output = "Properties File Missing"
                result.full_output = f"Properties file not found on till (needed for version check)"
                return result

            try:
                sz_bytes = int(raw_war_sz) if raw_war_sz != "MISSING" else 0
            except ValueError:
                sz_bytes = 0

            result.war_size_bytes = sz_bytes
            result.war_size = format_bytes_human(sz_bytes) if not war_missing else "-"
            result.expected_version = expected_version_str

            # Evaluate size match (skip if user didn't provide expected size)
            if check_size:
                size_matched, rep_expected_bytes = evaluate_size_match(
                    actual_bytes=sz_bytes,
                    exp_input=expected_size_bytes,
                    tolerance_bytes=tolerance_bytes
                )
                result.war_expected_bytes = rep_expected_bytes
            else:
                size_matched = True  # Don't care
                rep_expected_bytes = 0
                result.war_expected_bytes = 0

            # Evaluate version match (skip if user didn't provide expected version)
            if check_version:
                version_matched = matches_delivery_version(
                    actual_val=raw_prop_val,
                    expected_input=expected_version_str
                )
            else:
                version_matched = True  # Don't care

            exp_display_str = str(expected_size_bytes) if expected_size_bytes else "-"
            if rep_expected_bytes > 0:
                exp_display_str = format_bytes_human(rep_expected_bytes)

            # Build status based on which checks are active
            size_part = format_bytes_human(sz_bytes) if not war_missing else "(not checked)"
            ver_part = deliv_display if not prop_missing else "(not checked)"

            if size_matched and version_matched:
                result.status = AuditStatus.SUCCESS
                result.preview_output = f"Size: {size_part} | {ver_part}"
            elif (not size_matched) and (not version_matched):
                result.status = AuditStatus.BOTH_MISMATCH
                result.preview_output = f"Size: {size_part} (Exp: {exp_display_str}) | {ver_part}"
            elif not size_matched:
                result.status = AuditStatus.SIZE_MISMATCH
                result.preview_output = f"Size: {size_part} (Exp: {exp_display_str}) | {ver_part}"
            else:
                result.status = AuditStatus.VERSION_MISMATCH
                result.preview_output = f"Size: {size_part} | {ver_part} (Exp: '{expected_version_str}')"

            result.full_output = (
                f"WAR Path Checked: {result.extra.get('war_path', '-')}\n"
                f"WAR Actual Size: {format_bytes_human(sz_bytes)} ({sz_bytes:,} bytes)\n"
                f"WAR Expected Size: {exp_display_str}\n"
                f"Size Tolerance: ±0.3 MB ({tolerance_bytes} bytes)\n"
                f"WAR Last Modified: {clean_time}\n"
                f"Properties Path: {result.extra.get('prop_path', '-')}\n"
                f"Extracted Property Line: {raw_prop_line}\n"
                f"Extracted Delivery Version: {deliv_display}\n"
                f"Raw Property Value: {raw_prop_val}\n"
                f"Detected Delivery Number: {deliv_num}\n"
                f"Expected Delivery Version: {expected_version_str}\n"
                f"Overall Status: {result.status}"
            )
            return result

        result.status = AuditStatus.ERROR
        result.preview_output = "Unparseable probe response"
        result.full_output = stdout_txt
        return result

    @staticmethod
    def build_file_info_probe(file_path: str) -> str:
        """Builds probe for Mode 2: File Info."""
        safe_path = shlex.quote(sanitize_file_path(file_path))
        probe = (
            "if [ -f " + safe_path + " ]; then "
            "F_SZ=$(stat -c '%s' " + safe_path + " 2>/dev/null || wc -c < " + safe_path + "); "
            "F_TIME=$(stat -c '%y' " + safe_path + " 2>/dev/null || date -r " + safe_path + " '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '-'); "
            'echo "INFO|FOUND|${F_SZ:-0}|${F_TIME:--}"; '
            'else echo "INFO|MISSING|0|-"; fi'
        )
        return probe

    @staticmethod
    def parse_file_info_output(stdout_txt: str, file_path: str, result: AuditResult) -> AuditResult:
        line = stdout_txt.strip().splitlines()[-1] if stdout_txt.strip() else ""
        parts = line.split("|")
        if len(parts) >= 3 and parts[0] == "INFO":
            if parts[1] == "FOUND":
                try:
                    sz = int(parts[2])
                except ValueError:
                    sz = 0
                mtime = parts[3] if len(parts) > 3 else "-"
                result.status = AuditStatus.FOUND
                result.war_size_bytes = sz
                result.war_size = format_bytes_human(sz)
                result.war_modified = mtime
                result.preview_output = f"{format_bytes_human(sz)} | {mtime}"
                result.full_output = f"File: {file_path}\nSize: {format_bytes_human(sz)}\nModified: {mtime}"
                return result
            else:
                result.status = AuditStatus.FILE_MISSING
                result.preview_output = "File Missing"
                result.full_output = f"File does not exist: {file_path}"
                return result

        result.status = AuditStatus.ERROR
        result.preview_output = "Error checking file"
        result.full_output = stdout_txt
        return result
