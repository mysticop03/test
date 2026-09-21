"""
core/probe_engine.py
Generates single-shot, enterprise-grade secure remote bash probes for Ubuntu tills.
Extracts WAR size, mtime, and parses delivery version from .properties in one round trip.
All inputs are strictly sanitized and quoted with shlex.quote() to prevent command injection (CWE-78).
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
    return clean if clean else "deliveryversion"

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
        expected_size_bytes: int,
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
            result.delivery_version = raw_prop_val
            result.prop_variable = raw_prop_line

            if raw_war_sz == "MISSING" or raw_prop_val == "MISSING":
                result.status = AuditStatus.FILE_MISSING
                missing_files = []
                if raw_war_sz == "MISSING": missing_files.append("WAR File")
                if raw_prop_val == "MISSING": missing_files.append("Properties File")
                result.preview_output = f"Missing: {', '.join(missing_files)}"
                result.full_output = f"File missing on till: {', '.join(missing_files)}"
                return result

            try:
                sz_bytes = int(raw_war_sz)
            except ValueError:
                sz_bytes = 0

            result.war_size_bytes = sz_bytes
            result.war_expected_bytes = expected_size_bytes
            result.war_size = format_bytes_human(sz_bytes)
            result.expected_version = expected_version_str

            if expected_size_bytes <= 0:
                size_matched = True
            else:
                diff_exact = abs(sz_bytes - expected_size_bytes)
                if diff_exact <= tolerance_bytes:
                    size_matched = True
                else:
                    equiv_decimal_bytes = int(round((sz_bytes / 1048576.0) * 1000000.0))
                    equiv_binary_bytes = int(round((sz_bytes / 1000000.0) * 1048576.0))
                    diff_dec = abs(equiv_decimal_bytes - expected_size_bytes)
                    diff_bin = abs(equiv_binary_bytes - expected_size_bytes)
                    size_matched = (diff_dec <= tolerance_bytes) or (diff_bin <= tolerance_bytes)

            exp_v_clean = expected_version_str.strip().lower()
            if not exp_v_clean:
                version_matched = True
            else:
                act_v_clean = raw_prop_val.strip().lower()
                version_matched = (exp_v_clean == act_v_clean) or (exp_v_clean in act_v_clean)

            if size_matched and version_matched:
                result.status = AuditStatus.SUCCESS
                result.preview_output = f"Size: {format_bytes_human(sz_bytes)} | Ver: {raw_prop_val}"
            elif (not size_matched) and (not version_matched):
                result.status = AuditStatus.BOTH_MISMATCH
                result.preview_output = f"Size: {format_bytes_human(sz_bytes)} (Exp: {format_bytes_human(expected_size_bytes)}) | Ver: {raw_prop_val}"
            elif not size_matched:
                result.status = AuditStatus.SIZE_MISMATCH
                result.preview_output = f"Size: {format_bytes_human(sz_bytes)} (Exp: {format_bytes_human(expected_size_bytes)}) | Ver: {raw_prop_val}"
            else:
                result.status = AuditStatus.VERSION_MISMATCH
                result.preview_output = f"Size: {format_bytes_human(sz_bytes)} | Ver: '{raw_prop_val}' (Exp: '{expected_version_str}')"

            result.full_output = (
                f"WAR Path Checked: {result.extra.get('war_path', '-')}\n"
                f"WAR Actual Size: {format_bytes_human(sz_bytes)}\n"
                f"WAR Expected Size: {format_bytes_human(expected_size_bytes)}\n"
                f"Size Tolerance: ±0.3 MB ({tolerance_bytes} bytes)\n"
                f"WAR Last Modified: {clean_time}\n"
                f"Properties Path: {result.extra.get('prop_path', '-')}\n"
                f"Extracted Property Line: {raw_prop_line}\n"
                f"Extracted Delivery Version: {raw_prop_val}\n"
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
