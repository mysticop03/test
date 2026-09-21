"""
storage/csv_exporter.py
Clean UTF-8 BOM CSV generator with built-in Formula Injection / DDE Neutralization (CWE-1236).
Strictly sorted First-Come, First-Served: Store 1 (1-13), then Store 2 (1-13).
"""
import csv
from typing import List, Any
from models.result import AuditResult, AuditStatus

def sanitize_csv_cell(val: Any) -> str:
    """Neutralize potential CSV formula injection (DDE attacks) for office spreadsheets."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        # Standalone placeholder "-" is safe and preserved
        if s == "-":
            return "-"
        # Prepend a single quote so Excel/Calc treats it purely as text
        return f"'{s}"
    return s

class CsvExporter:
    @staticmethod
    def export_results(file_path: str, results: List[AuditResult], only_failures: bool = False):
        # Strict FCFS sorting
        sorted_results = sorted(results, key=lambda r: (r.store_order_index, r.till_num))

        headers = [
            "Store_Code", "Till_Name", "IP_Address", "Latency_ms",
            "WAR_Size", "WAR_Last_Modified", "Delivery_Version", "Status",
            "Expected_Version", "Variable_Details", "Timestamp"
        ]

        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in sorted_results:
                if only_failures and not AuditStatus.is_failed(r.status):
                    continue
                writer.writerow([
                    sanitize_csv_cell(r.store_code),
                    sanitize_csv_cell(r.till_name),
                    sanitize_csv_cell(r.ip),
                    sanitize_csv_cell(r.latency_ms),
                    sanitize_csv_cell(r.war_size),
                    sanitize_csv_cell(r.war_modified),
                    sanitize_csv_cell(r.delivery_version),
                    sanitize_csv_cell(r.status),
                    sanitize_csv_cell(r.expected_version),
                    sanitize_csv_cell(r.prop_variable),
                    sanitize_csv_cell(r.timestamp)
                ])
