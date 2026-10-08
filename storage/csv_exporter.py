"""
storage/csv_exporter.py
Clean UTF-8 BOM CSV generator with built-in Formula Injection / DDE Neutralization (CWE-1236).
Implements strict dynamic column presentation matching user requirements:
1. Version Check:
   - Aggregated 5-column store report: [Store Code, IP, Mismatch Version, Offline, Status]
   - IP is always the store's .12 subnet anchor
   - Enables direct re-ingestion to audit only problem tills
2. Terminal:
   - Strictly: [Store_Code, Device_Name, IP_Address, Latency_ms, Command_Output, Status, Audit_Timestamp]
   - Omit File Size, Last Modified, Variable/Value headers
3. File Check:
   - Dynamic headers: shows File_Size, File_Last_Modified, and/or Variable_Value strictly when populated
"""
import csv
from typing import List, Any, Dict
from models.result import AuditResult, AuditStatus

def sanitize_csv_cell(val: Any) -> str:
    """Neutralize potential CSV formula injection (DDE attacks) for office spreadsheets."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        if s == "-":
            return "-"
        return f"'{s}"
    return s

class CsvExporter:
    @staticmethod
    def export_results(file_path: str, results: List[AuditResult], only_failures: bool = False):
        if not results:
            return

        is_version_check = any(r.operation_mode == "version_check" for r in results)
        is_terminal = any(r.operation_mode in ("command", "terminal") for r in results)

        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)

            # -------------------------------------------------------------
            # Case 1: Version Check (5-Column Aggregated Store Format)
            # -------------------------------------------------------------
            if is_version_check:
                headers = ["Store Code", "IP", "Mismatch Version", "Offline", "Status"]
                writer.writerow(headers)

                store_map: Dict[str, Dict[str, Any]] = {}
                for r in results:
                    code = r.store_code
                    if code not in store_map:
                        parts = r.ip.split(".")
                        base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.12" if len(parts) == 4 else r.ip
                        store_map[code] = {
                            "order": r.store_order_index,
                            "ip": base_ip,
                            "mismatches": [],
                            "offlines": [],
                            "matched": []
                        }
                    info = store_map[code]
                    if r.status == AuditStatus.SUCCESS:
                        if r.till_num:
                            info["matched"].append(r.till_num)
                    elif r.status in (AuditStatus.MISMATCH, AuditStatus.MISS):
                        if r.till_num:
                            info["mismatches"].append(r.till_num)
                    elif r.status == AuditStatus.OFFLINE:
                        if r.till_num:
                            info["offlines"].append(r.till_num)

                for code, info in sorted(store_map.items(), key=lambda x: x[1]["order"]):
                    has_mismatch = bool(info["mismatches"])
                    has_offline = bool(info["offlines"])

                    if has_mismatch:
                        m_str = ",".join(str(n) for n in sorted(set(info["mismatches"])))
                        st = AuditStatus.MISMATCH
                    elif info["matched"]:
                        m_str = "All Matched"
                        st = AuditStatus.OFFLINE if has_offline else AuditStatus.SUCCESS
                    else:
                        m_str = "-"
                        st = AuditStatus.OFFLINE

                    if has_offline:
                        if not info["matched"] and not has_mismatch:
                            o_str = "All Offline"
                        else:
                            o_str = ",".join(str(n) for n in sorted(set(info["offlines"])))
                    else:
                        o_str = "-"

                    if only_failures and st == AuditStatus.SUCCESS:
                        continue

                    writer.writerow([
                        sanitize_csv_cell(code),
                        sanitize_csv_cell(info["ip"]),
                        sanitize_csv_cell(m_str),
                        sanitize_csv_cell(o_str),
                        sanitize_csv_cell(st)
                    ])
                return

            # Strict hierarchy sorting per Section 8.1
            sorted_results = sorted(
                results,
                key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
            )

            # -------------------------------------------------------------
            # Case 2: Terminal Mode
            # -------------------------------------------------------------
            if is_terminal:
                headers = [
                    "Store_Code", "Device_Name", "IP_Address", "Latency_ms",
                    "Command_Output", "Status", "Audit_Timestamp"
                ]
                writer.writerow(headers)
                for r in sorted_results:
                    if only_failures and not AuditStatus.is_failed(r.status):
                        continue
                    writer.writerow([
                        sanitize_csv_cell(r.store_code),
                        sanitize_csv_cell(r.till_name),
                        sanitize_csv_cell(r.ip),
                        sanitize_csv_cell(r.latency_ms),
                        sanitize_csv_cell(r.preview_output),
                        sanitize_csv_cell(r.status),
                        sanitize_csv_cell(r.timestamp)
                    ])
                return

            # -------------------------------------------------------------
            # Case 3: File Check Mode (Dynamic columns)
            # -------------------------------------------------------------
            has_size = any(r.war_size != "-" for r in sorted_results)
            has_var = any((r.delivery_version != "-" or r.prop_variable != "-") for r in sorted_results)

            headers = ["Store_Code", "Device_Name", "IP_Address", "Latency_ms"]
            if has_size and not has_var:
                headers.extend(["File_Size", "File_Last_Modified"])
            elif has_var and not has_size:
                headers.extend(["Variable_Value", "File_Last_Modified"])
            else:
                headers.extend(["File_Size", "File_Last_Modified", "Variable_Value"])

            headers.extend(["Status", "Audit_Timestamp"])
            writer.writerow(headers)

            for r in sorted_results:
                if only_failures and not AuditStatus.is_failed(r.status):
                    continue

                row_data = [
                    sanitize_csv_cell(r.store_code),
                    sanitize_csv_cell(r.till_name),
                    sanitize_csv_cell(r.ip),
                    sanitize_csv_cell(r.latency_ms)
                ]

                var_val = r.delivery_version if r.delivery_version != "-" else r.prop_variable
                if has_size and not has_var:
                    row_data.extend([sanitize_csv_cell(r.war_size), sanitize_csv_cell(r.war_modified)])
                elif has_var and not has_size:
                    row_data.extend([sanitize_csv_cell(var_val), sanitize_csv_cell(r.war_modified)])
                else:
                    row_data.extend([sanitize_csv_cell(r.war_size), sanitize_csv_cell(r.war_modified), sanitize_csv_cell(var_val)])

                row_data.extend([sanitize_csv_cell(r.status), sanitize_csv_cell(r.timestamp)])
                writer.writerow(row_data)
