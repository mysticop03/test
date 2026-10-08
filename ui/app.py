"""
ui/app.py
Main Application Window & Master MVC Controller for Ubuntu POS Store Inspector & Version Auditor.
Matches the clean white/light enterprise UI layout with dynamic column configuration:
1. Target Scope (empty defaults)
2. SSH Credentials (Till + Back Office; empty defaults; timeout: 5)
3. Operations (Version & File Check + Terminal Console)
4. Action & KPI Bar
5. Filter & Export Toolbar
6. Spacious Results Grid Table (dynamically adapts columns based on size/version inputs)
"""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

import ui.theme as theme
from models.target import StoreRecord
from models.result import AuditResult, AuditSummary, AuditStatus
from core.config_manager import ConfigManager
from core.batch_orchestrator import BatchOrchestrator
from core.ssh_worker import execute_till_probe
from storage.excel_exporter import ExcelExporter
from storage.csv_exporter import CsvExporter
from storage.store_reader import is_ip_authorized

from ui.components.target_card import TargetCard
from ui.components.mode_card import ModeCard
from ui.components.credentials_card import CredentialsCard
from ui.components.metrics_bar import MetricsBar
from ui.components.filter_toolbar import FilterToolbar
from ui.components.results_table import ResultsTable
from ui.components.output_dialog import OutputDisplayDialog

# Resolve config.json sitting alongside executable or script
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

class FileCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ubuntu POS Store Inspector & Version Auditor")
        self.geometry("1280x840")
        self.minsize(1040, 720)
        self.configure(bg=theme.COLOR_BG)

        self.config_manager = ConfigManager(CONFIG_FILE)
        self.orchestrator: Optional[BatchOrchestrator] = None
        self.audit_start_time = 0.0
        import threading
        self.terminal_stop_event = threading.Event()
        self.terminal_pause_event = threading.Event()
        self.is_terminal_running = False

        self._setup_styles()
        self._build_ui()
        self._load_saved_config()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._process_events)

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=theme.COLOR_BG)
        style.configure("TLabel", background=theme.COLOR_CARD_BG, foreground=theme.COLOR_TEXT_PRIMARY, font=theme.FONT_BODY)
        style.configure("TCombobox", fieldbackground="#FFFFFF", background="#E2E8F0", foreground=theme.COLOR_TEXT_PRIMARY, arrowcolor=theme.COLOR_TEXT_SECONDARY)
        style.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")], foreground=[("readonly", theme.COLOR_TEXT_PRIMARY)])

    def _build_ui(self):
        # 1. Top Header Banner
        header = tk.Frame(self, bg=theme.COLOR_HEADER_BG, height=48, padx=14)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Left: Rounded Blue POS badge + Title
        h_left = tk.Frame(header, bg=theme.COLOR_HEADER_BG)
        h_left.pack(side=tk.LEFT, fill=tk.Y)

        lbl_badge = tk.Label(
            h_left, text="POS", fg="white", bg=theme.COLOR_PRIMARY,
            font=theme.FONT_BODY_BOLD, padx=6, pady=2
        )
        lbl_badge.pack(side=tk.LEFT, pady=10)

        lbl_title = tk.Label(
            h_left, text=" Ubuntu POS Store Inspector & Version Auditor",
            fg="white", bg=theme.COLOR_HEADER_BG, font=theme.FONT_TITLE
        )
        lbl_title.pack(side=tk.LEFT, padx=6, pady=10)

        # Main Workspace Container (Clean white/slate background)
        main_workspace = tk.Frame(self, bg=theme.COLOR_BG, padx=12, pady=6)
        main_workspace.pack(fill=tk.BOTH, expand=True)

        # 2. Row 1: Top 2-Column Split (1. Target Scope on Left, 2. SSH Credentials on Right)
        top_split = tk.Frame(main_workspace, bg=theme.COLOR_BG)
        top_split.pack(fill=tk.X, pady=(0, 8))
        top_split.columnconfigure(0, weight=6)
        top_split.columnconfigure(1, weight=5)

        self.target_card = TargetCard(top_split)
        self.target_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.creds_card = CredentialsCard(
            top_split,
            config_manager=self.config_manager,
            on_credentials_changed=self._update_table_columns
        )
        self.creds_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # 3. Row 2: Operations Section (Tabbed: Version & File Check / Terminal Console)
        self.mode_card = ModeCard(
            main_workspace,
            on_terminal_execute=self._on_terminal_execute,
            on_fields_changed=self._update_table_columns
        )
        self.mode_card.pack(fill=tk.X, pady=(0, 8))

        # 4. Row 3: Action & KPI Bar
        self.metrics_bar = MetricsBar(
            main_workspace,
            on_start=self._start_audit,
            on_pause_resume=self._toggle_pause,
            on_stop=self._stop_audit
        )
        self.metrics_bar.pack(fill=tk.X, pady=(0, 8))

        # 5. Row 4: Filter & Table Toolbar
        self.filter_bar = FilterToolbar(
            main_workspace,
            on_filter_changed=self._on_filter_changed,
            on_search_changed=self._on_search_changed,
            on_clear=self._clear_results,
            on_export_csv=self._export_csv,
            on_export_excel=self._export_excel
        )
        self.filter_bar.pack(fill=tk.X, pady=(0, 4))

        # 6. Row 5: Spacious Results Grid Table
        self.results_table = ResultsTable(main_workspace, on_row_inspect=self._on_row_inspect)
        self.results_table.pack(fill=tk.BOTH, expand=True)

    def _load_saved_config(self):
        """Loads saved values from config.json (all empty by default except timeout: 5)."""
        cfg = self.config_manager.get_all()

        # Timeout always has a default: 5 seconds (ONLY field pre-filled per user instruction)
        t_val = str(cfg.get("connection_timeout_seconds", 5))
        self.creds_card.ent_timeout.delete(0, tk.END)
        self.creds_card.ent_timeout.insert(0, t_val)

        # Per strict user requirement: DO NOT load any default paths, variables, usernames, or IPs into the UI.
        # Everything must remain completely clean and empty except for timeout.

        self._update_table_columns()

    def _update_table_columns(self):
        """Dynamically updates results grid columns based on active tab, input fields, and active credentials."""
        if not hasattr(self, "creds_card") or not hasattr(self, "mode_card") or not hasattr(self, "results_table"):
            return
        creds = self.creds_card.get_credentials()
        include_tills = creds["include_tills"]
        include_bo = creds["include_bo"]

        has_size = self.mode_card.has_size_check(include_tills=include_tills, include_bo=include_bo)
        has_version = self.mode_card.has_version_check(include_tills=include_tills, include_bo=include_bo)
        is_terminal = (self.mode_card.active_tab == "terminal")
        is_version_check = (self.mode_card.active_tab == "version_check")
        self.results_table.configure_columns(
            has_size=has_size,
            has_version=has_version,
            is_terminal=is_terminal,
            is_version_check=is_version_check
        )

    def _save_current_config(self):
        creds = self.creds_card.get_credentials()
        self.config_manager.update({
            "connection_timeout_seconds": creds["timeout"]
        })
        self.config_manager.save()

    def _start_audit(self):
        stores = self.target_card.get_configured_stores()
        if not stores or (self.target_card.target_mode == "single" and not self.target_card.ent_ip.get().strip()):
            messagebox.showwarning("No Targets", "Please enter a Store IP or select a Bulk File.")
            return

        # Security: CIDR Authorization Check for single store IP (exempt in UAT mode for test servers)
        if self.target_card.target_mode == "single" and self.target_card.till_mode != "uat":
            raw_ip = self.target_card.ent_ip.get().strip()
            allowed_cidrs = self.config_manager.get("allowed_subnets", None)
            if not is_ip_authorized(raw_ip, allowed_cidrs=allowed_cidrs):
                messagebox.showerror("Unauthorized Target", f"Security Violation: Target IP '{raw_ip}' does not belong to authorized subnets.")
                return

        creds = self.creds_card.get_credentials()
        include_tills = creds["include_tills"]
        include_bo = creds["include_bo"]

        mode_params = self.mode_card.get_mode_params()
        if mode_params.get("operation_mode") == "terminal":
            term_tgt = self.mode_card.terminal_target
            if term_tgt == "tills":
                include_bo = False
            elif term_tgt == "bo":
                include_tills = False

        # Dynamic Credential Targeting: Check if at least one device type is targeted
        if not include_tills and not include_bo:
            messagebox.showwarning(
                "Missing Credentials",
                "Please enter credentials for either Till (POS), Back Office (BO), or both to start inspection."
            )
            return

        self._save_current_config()
        self.results_table.clear()

        # Dynamic Column Presentation:
        # If size only -> show File Size and Last Modified (hide Variable/Value)
        # If version only -> show Variable, Value, and Last Modified (hide File Size)
        # If both -> show full
        self._update_table_columns()

        self.metrics_bar.set_running_state(True)
        self.audit_start_time = time.perf_counter()

        mode_params["size_tolerance_mb"] = float(self.config_manager.get("size_tolerance_mb", 0.3))
        mode_params.update(creds)

        specific_tills = self.target_card.get_specific_tills_string()
        parallel_stores = self.target_card.get_parallel_stores()

        self.orchestrator = BatchOrchestrator(
            username=creds["username"],
            password=creds["password"],
            operation_mode=mode_params["operation_mode"],
            config_params=mode_params,
            store_concurrency=parallel_stores,
            max_total_ssh_connections=100,
            timeout=creds["timeout"]
        )
        self.orchestrator.start_async(
            stores=stores,
            specific_tills_str=specific_tills,
            include_tills=include_tills,
            include_bo=include_bo
        )

    def _toggle_pause(self):
        if self.is_terminal_running:
            if self.terminal_pause_event.is_set():
                self.terminal_pause_event.clear()
                self.metrics_bar.btn_pause.config(text="⏸ Pause")
                self.mode_card.print_terminal_line("\n[RESUMED] Terminal execution resumed.")
            else:
                self.terminal_pause_event.set()
                self.metrics_bar.btn_pause.config(text="▶ Resume")
                self.mode_card.print_terminal_line("\n[PAUSED] Terminal execution paused. Click Resume to continue.")
            return

        if not self.orchestrator:
            return
        if self.orchestrator.pause_requested.is_set():
            self.orchestrator.resume()
            self.metrics_bar.btn_pause.config(text="⏸ Pause")
        else:
            self.orchestrator.pause()
            self.metrics_bar.btn_pause.config(text="▶ Resume")

    def _stop_audit(self):
        if self.is_terminal_running:
            self.terminal_stop_event.set()
            self.terminal_pause_event.clear()
            self.is_terminal_running = False
            self.metrics_bar.set_running_state(False)
            self.metrics_bar.btn_pause.config(text="⏸ Pause")
            self.mode_card.print_terminal_line("\n[STOPPED] Terminal execution aborted by user.")

        if self.orchestrator:
            self.orchestrator.stop()
            self.metrics_bar.set_running_state(False)
            self.metrics_bar.btn_pause.config(text="⏸ Pause")

    def _on_terminal_execute(self, cmd: str, target_filter: str):
        """Executes terminal command across selected targets concurrently in background, running live timer and results table."""
        stores = self.target_card.get_configured_stores()
        if not stores:
            self.mode_card.print_terminal_line("[ERROR] No target stores configured.")
            return

        if self.target_card.target_mode == "single":
            raw_ip = self.target_card.ent_ip.get().strip()
            if not raw_ip:
                self.mode_card.print_terminal_line("[ERROR] Please enter a Store IP or select a Bulk File.")
                return
            if self.target_card.till_mode != "uat":
                allowed_cidrs = self.config_manager.get("allowed_subnets", None)
                if not is_ip_authorized(raw_ip, allowed_cidrs=allowed_cidrs):
                    self.mode_card.print_terminal_line(f"[SECURITY VIOLATION] Target IP '{raw_ip}' is not an authorized store network.")
                    return

        creds = self.creds_card.get_credentials()
        include_tills = (target_filter in ("tills", "both"))
        include_bo = (target_filter in ("bo", "both"))

        targets = []
        for s in stores:
            targets.extend(s.resolve_targets(include_tills=include_tills, include_bo=include_bo))

        if not targets:
            self.mode_card.print_terminal_line(f"[INFO] No targets resolved for filter '{target_filter}'.")
            return

        self.mode_card.print_terminal_line(f"\n[RUNNING] terminal:~# {cmd}  -> Executing across {len(targets)} targets in parallel ({target_filter})...")

        params = self.mode_card.get_mode_params()
        params["custom_command"] = cmd
        params.update(creds)

        self.results_table.clear()
        self.results_table.configure_columns(has_size=False, has_version=False, is_terminal=True, is_version_check=False)
        self.terminal_stop_event.clear()
        self.terminal_pause_event.clear()
        self.is_terminal_running = True
        self.metrics_bar.set_running_state(True)
        self.audit_start_time = time.perf_counter()

        import threading
        from concurrent.futures import ThreadPoolExecutor

        def run_interactive():
            self.after(0, self._update_table_columns)

            def probe_single(t):
                if self.terminal_stop_event.is_set():
                    return None
                while self.terminal_pause_event.is_set() and not self.terminal_stop_event.is_set():
                    time.sleep(0.2)
                if self.terminal_stop_event.is_set():
                    return None

                dev_user = (creds.get("bo_username") or creds.get("username", "")) if t.is_bo else (creds.get("till_username") or creds.get("username", ""))
                dev_pass = (creds.get("bo_password") or creds.get("password", "")) if t.is_bo else (creds.get("till_password") or creds.get("password", ""))

                def _handle_sub(sub_r: AuditResult):
                    sub_r._streamed = True
                    if self.terminal_stop_event.is_set():
                        return
                    url_tag = f" {sub_r.extra.get('url')}" if sub_r.extra.get('url') else ""
                    self.mode_card.print_terminal_line(f"[{t.display_name}]{url_tag} -> {sub_r.preview_output} | Status: {sub_r.status} ({sub_r.latency_ms} ms)")
                    self.after(0, lambda r_item=sub_r: self.results_table.add_result(r_item))

                res = execute_till_probe(
                    target=t,
                    username=dev_user,
                    password=dev_pass,
                    operation_mode="terminal",
                    config_params=params,
                    timeout=creds["timeout"],
                    on_sub_result=_handle_sub
                )
                res_list = res if isinstance(res, list) else [res]
                for r in res_list:
                    if getattr(r, "_streamed", False):
                        continue
                    if self.terminal_stop_event.is_set():
                        break
                    self.mode_card.print_terminal_line(f"[{t.display_name}] {r.preview_output} | Status: {r.status} ({r.latency_ms} ms)")
                    self.after(0, lambda sub_r=r: self.results_table.add_result(sub_r))
                return res

            try:
                workers = min(100, max(1, len(targets)))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    list(executor.map(probe_single, targets))
            finally:
                self.is_terminal_running = False
                try:
                    self.after(0, self.results_table.sort_by_target_order)
                except Exception:
                    pass
                self.after(0, lambda: self.metrics_bar.set_running_state(False))

        threading.Thread(target=run_interactive, daemon=True).start()

    def _on_row_inspect(self, result: AuditResult):
        """Double-click row inspection: updates in-place Terminal Console AND opens dedicated display output window."""
        cmd_used = result.extra.get("custom_command") if result.operation_mode in ("command", "terminal") else None

        # 1. Update in-place terminal console screen
        self.mode_card.show_inspection(
            target_name=result.till_name,
            ip=result.ip,
            status=result.status,
            full_output=result.full_output or result.preview_output,
            command=cmd_used
        )

        # 2. Open dedicated floating display output window
        OutputDisplayDialog(self, result, command=cmd_used)

    def _process_events(self):
        is_running = bool((self.orchestrator and self.orchestrator.is_running()) or self.is_terminal_running)
        if is_running:
            elapsed = int(time.perf_counter() - self.audit_start_time)
            mins, secs = divmod(elapsed, 60)
            self.metrics_bar.lbl_clock.config(text=f"⏱ {mins:02d}:{secs:02d}")

        if self.orchestrator:

            while not self.orchestrator.event_queue.empty():
                try:
                    event_type, data = self.orchestrator.event_queue.get_nowait()
                    if event_type == "result":
                        self.results_table.add_result(data)
                        self.metrics_bar.update_summary(self.orchestrator.summary)
                    elif event_type == "target_summary":
                        self.metrics_bar.lbl_progress_txt.config(text=f"PROGRESS: 0 / {data.get('total_tills', 0)}")
                    elif event_type == "completed":
                        try:
                            self.results_table.sort_by_target_order()
                        except Exception:
                            pass
                        self.metrics_bar.set_running_state(False)
                        self.metrics_bar.update_summary(self.orchestrator.summary)
                        messagebox.showinfo(
                            "Audit Finished",
                            f"Audit complete!\nAudited {self.orchestrator.summary.completed_tills} targets in {self.orchestrator.summary.elapsed_seconds}s.\nPass Rate: {self.orchestrator.summary.pass_rate_percent}%"
                        )
                except Exception:
                    break

        self.after(50, self._process_events)

    def _on_filter_changed(self, filter_name: str):
        self.results_table.set_filter(filter_name)

    def _on_search_changed(self, query: str):
        self.results_table.set_search(query)

    def _clear_results(self):
        if messagebox.askyesno("Clear Results", "Clear all inspected records and reset KPIs?"):
            self.results_table.clear()
            self.metrics_bar.update_summary(AuditSummary())

    def _export_excel(self):
        if not self.results_table.all_results:
            messagebox.showwarning("No Data", "No results to export.")
            return

        filtered = self.results_table.get_filtered_results()
        if not filtered:
            messagebox.showinfo("Empty Selection", "No matching records to export for active filter.")
            return

        curr_filter = self.results_table.current_filter
        default_name = f"audit_{curr_filter}.xlsx" if curr_filter != "all" else "audit_report.xlsx"

        f_path = filedialog.asksaveasfilename(
            title=f"Export Excel ({curr_filter.capitalize()})",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel Spreadsheet", "*.xlsx")]
        )
        if f_path:
            try:
                summary = self.orchestrator.summary if self.orchestrator else AuditSummary()
                if curr_filter == "all":
                    ExcelExporter.export_audit_workbook(f_path, summary, self.results_table.all_results)
                else:
                    ExcelExporter.export_filtered_workbook(f_path, curr_filter.capitalize(), filtered)
                messagebox.showinfo("Export Successful", f"Excel report exported to:\n{f_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export Excel report: {e}")

    def _export_csv(self):
        if not self.results_table.all_results:
            messagebox.showwarning("No Data", "No results to export.")
            return

        filtered = self.results_table.get_filtered_results()
        if not filtered:
            messagebox.showinfo("Empty Selection", "No matching records to export for active filter.")
            return

        curr_filter = self.results_table.current_filter
        default_name = f"audit_{curr_filter}.csv" if curr_filter != "all" else "audit_report.csv"

        f_path = filedialog.asksaveasfilename(
            title=f"Export CSV ({curr_filter.capitalize()})",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")]
        )
        if f_path:
            try:
                CsvExporter.export_results(f_path, filtered)
                messagebox.showinfo("Export Successful", f"Exported {len(filtered)} rows to:\n{f_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export CSV: {e}")

    def _on_close(self):
        if self.orchestrator and self.orchestrator.is_running():
            if messagebox.askyesno("Exit Confirmation", "An audit is currently running. Stop audit and exit?"):
                self.orchestrator.stop()
                self.destroy()
        else:
            self._save_current_config()
            self.destroy()

def main():
    app = FileCheckerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
