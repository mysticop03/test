#!/usr/bin/env python3
"""
cli.py
Headless CLI runner for automated batch audits of store POS tills.
Secure: Password is never passed on command line flags, preventing telemetry leakage.
"""
import sys
import os
import argparse
import getpass
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.target import StoreRecord
from models.result import AuditStatus
from core.batch_orchestrator import BatchOrchestrator
from core.config_manager import ConfigManager
from storage.store_reader import load_stores_from_file
from storage.excel_exporter import ExcelExporter
from storage.csv_exporter import CsvExporter

def main():
    parser = argparse.ArgumentParser(description="Secure Headless Ubuntu POS Till Inspector")
    parser.add_argument("--stores", required=True, help="Path to CSV or Excel (.xlsx) file containing stores")
    parser.add_argument("--user", default="posuser", help="SSH username (default: posuser)")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--timeout", type=int, default=5, help="Socket timeout seconds (default: 5)")
    parser.add_argument("--tills", default="", help="Specific tills e.g. '1, 2, 5' (default: all)")

    # Mode selection
    parser.add_argument("--mode", choices=["version_war", "file_info", "command"], default="version_war")
    parser.add_argument("--war-path", default="/opt/pos/app.war", help="WAR file path on till")
    parser.add_argument("--war-bytes", type=int, default=0, help="Expected WAR file exact bytes")
    parser.add_argument("--prop-path", default="/opt/pos/config/app.properties", help="Properties file path on till")
    parser.add_argument("--keyword", default="deliveryversion", help="Keyword to search in properties file")
    parser.add_argument("--expected-version", default="", help="Expected delivery version string")
    parser.add_argument("--command", default="uptime", help="Read-only command for Mode 3")
    parser.add_argument("--cmd-expected", default="", help="Expected command output substring")

    # Reporting
    parser.add_argument("--export-xlsx", help="Path to export multi-sheet Excel (.xlsx) report")
    parser.add_argument("--export-csv", help="Path to export CSV report")

    args = parser.parse_args()

    # Security: Read password securely via environment variable or interactive masked prompt
    password = os.environ.get("POS_SSH_PASSWORD")
    if not password:
        password = getpass.getpass(f"Enter SSH password for {args.user}: ")

    cfg_file = os.path.join(BASE_DIR, "config.json")
    cfg_mgr = ConfigManager(cfg_file)
    allowed_cidrs = cfg_mgr.get("allowed_subnets", ["10.0.0.0/8", "192.168.0.0/16", "127.0.0.1/32"])

    print(f"[*] Loading stores from: {args.stores}")
    stores = load_stores_from_file(args.stores, allowed_cidrs=allowed_cidrs)
    print(f"[*] Loaded {len(stores)} authorized store records.")

    concurrency = int(cfg_mgr.get("store_concurrency", 2))
    tolerance_mb = float(cfg_mgr.get("size_tolerance_mb", 0.3))
    tolerance_bytes = int(tolerance_mb * 1048576)

    config_params = {
        "operation_mode": args.mode,
        "war_path": args.war_path,
        "war_expected_size_bytes": args.war_bytes,
        "properties_path": args.prop_path,
        "properties_keyword": args.keyword,
        "expected_delivery_version": args.expected_version,
        "file_info_path": args.war_path,
        "custom_command": args.command,
        "cmd_expected_output": args.cmd_expected,
        "size_tolerance_bytes": tolerance_bytes
    }

    orchestrator = BatchOrchestrator(
        username=args.user,
        password=password,
        operation_mode=args.mode,
        config_params=config_params,
        store_concurrency=concurrency,
        timeout=args.timeout
    )

    print(f"[*] Starting audit (Mode: {args.mode}, Concurrency: {concurrency} stores)...")
    orchestrator.start_async(stores, args.tills)

    while orchestrator.is_running() or not orchestrator.event_queue.empty():
        while not orchestrator.event_queue.empty():
            try:
                etype, data = orchestrator.event_queue.get_nowait()
                if etype == "result":
                    print(f"[{data.status:14}] {data.store_code} {data.till_name} ({data.ip}) | {data.preview_output}")
                elif etype == "store_batch_start":
                    print(f"--> Batch {data['batch_index']}: Auditing stores: {', '.join(data['stores'])} ({data['till_count']} tills)")
            except Exception:
                break
        time.sleep(0.1)

    s = orchestrator.summary
    print("\n================ AUDIT SUMMARY ================")
    print(f"Total Tills:        {s.total_tills}")
    print(f"Completed Tills:    {s.completed_tills}")
    print(f"Success Count:      {s.success_count}")
    print(f"Size Mismatches:    {s.size_mismatch_count}")
    print(f"Version Mismatches: {s.version_mismatch_count}")
    print(f"Both Mismatch:      {s.both_mismatch_count}")
    print(f"File Missing:       {s.missing_count}")
    print(f"Offline / Timeout:  {s.offline_count}")
    print(f"Pass Rate:          {s.pass_rate_percent}%")
    print(f"Elapsed Time:       {s.elapsed_seconds}s")
    print("================================================")

    if args.export_xlsx:
        ExcelExporter.export_audit_workbook(args.export_xlsx, s, orchestrator.all_results)
        print(f"[+] Multi-sheet Excel report exported to: {args.export_xlsx}")

    if args.export_csv:
        CsvExporter.export_results(args.export_csv, orchestrator.all_results)
        print(f"[+] CSV report exported to: {args.export_csv}")

if __name__ == "__main__":
    main()
