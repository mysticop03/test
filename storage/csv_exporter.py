"""
storage/csv_exporter.py
Clean UTF-8 BOM CSV generator with built-in Formula Injection / DDE Neutralization (CWE-1236).
Strictly sorted Section 8.1 hierarchy: Store 1 BO -> Store 1 Tills -> Store 2 BO -> Store 2 Tills.
"""
import csv
from typing import List, Any
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
        # Strict hierarchy sorting per Section 8.1
        sorted_results = sorted(
            results,
            key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
        )

        is_terminal = any(r.operation_mode in ("command", "terminal") for r in sorted_results)
        val_header = "Command_Output" if is_terminal else "Variable_Value"

        headers = [
            "Store_Code", "Device_Name", "Device_Type", "IP_Address", "Latency_ms",
            "File_Size", "File_Last_Modified", val_header, "Status",
            "Expected_Value", "Audit_Timestamp"
        ]

        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in sorted_results:
                if only_failures and not AuditStatus.is_failed(r.status):
                    continue
                dev_type = "BO" if r.is_bo else "TILL"
                var_or_output = r.preview_output if (r.operation_mode in ("command", "terminal") or (r.delivery_version == "-" and r.prop_variable == "-")) else (r.delivery_version if r.delivery_version != "-" else r.prop_variable)
                writer.writerow([
                    sanitize_csv_cell(r.store_code),
                    sanitize_csv_cell(r.till_name),
                    sanitize_csv_cell(dev_type),
                    sanitize_csv_cell(r.ip),
                    sanitize_csv_cell(r.latency_ms),
                    sanitize_csv_cell(r.war_size),
                    sanitize_csv_cell(r.war_modified),
                    sanitize_csv_cell(var_or_output),
                    sanitize_csv_cell(r.status),
                    sanitize_csv_cell(r.expected_version),
                    sanitize_csv_cell(r.timestamp)
                ])
