"""
ui/app.py
Main Application Window & MVC Controller for file_checker.
Clean layout:
  1. Store IP
  2. Credentials
  3. Operations
Tolerance is configured via config.json alongside the executable.
"""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

import ui.theme as theme
from models.target import StoreRecord
from models.result import AuditResult, AuditSummary
from core.config_manager import ConfigManager
from core.batch_orchestrator import BatchOrchestrator
from storage.excel_exporter import ExcelExporter
from storage.csv_exporter import CsvExporter

from ui.components.target_card import TargetCard
from ui.components.mode_card import ModeCard
from ui.components.credentials_card import CredentialsCard
from ui.components.metrics_bar import MetricsBar
from ui.components.filter_toolbar import FilterToolbar
from ui.components.results_table import ResultsTable

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
        self.geometry("1220x800")
        self.minsize(1020, 680)

        self.config_manager = ConfigManager(CONFIG_FILE)
        self.orchestrator: Optional[BatchOrchestrator] = None
        self.audit_start_time = 0.0

        self._setup_styles()
        self._build_ui()
        self._load_saved_config()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._process_events)

    def _setup_styles(self):
        self.configure(bg=theme.COLOR_BG)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=theme.COLOR_BG)
        style.configure("TLabelframe", background=theme.COLOR_CARD_BG, relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=theme.COLOR_CARD_BG, foreground=theme.COLOR_TEXT_PRIMARY, font=theme.FONT_SUBTITLE)
        style.configure("TLabel", background=theme.COLOR_CARD_BG, font=theme.FONT_BODY)
        style.configure("TRadiobutton", background=theme.COLOR_CARD_BG, font=theme.FONT_BODY)
        style.configure("TNotebook", background=theme.COLOR_BG, tabmargins=[2, 4, 2, 0])
        style.configure("TNotebook.Tab", font=theme.FONT_BODY_BOLD, padding=[12, 4])
        style.configure("Treeview.Heading", font=theme.FONT_BODY_BOLD, relief="flat")
        style.configure("Treeview", font=theme.FONT_MONO, rowheight=26, fieldbackground="#FFFFFF")

    def _build_ui(self):
        # 1. Header Banner (Clean title, blue marked subtitle removed)
        header = tk.Frame(self, bg=theme.COLOR_HEADER_BG, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        lbl_title = tk.Label(
            header, text="  Ubuntu POS Store Inspector & Version Auditor",
            fg="white", bg=theme.COLOR_HEADER_BG, font=theme.FONT_TITLE
        )
        lbl_title.pack(side=tk.LEFT, padx=12)

        # Main Workspace Container
        main_workspace = tk.Frame(self, bg=theme.COLOR_BG, padx=10, pady=8)
        main_workspace.pack(fill=tk.BOTH, expand=True)

        # 2. Top 2-Column Section (1. Store IP on Left, 2. Credentials on Right)
        top_split = tk.Frame(main_workspace, bg=theme.COLOR_BG)
        top_split.pack(fill=tk.X, pady=(0, 6))

        top_split.columnconfigure(0, weight=6)
        top_split.columnconfigure(1, weight=5)

        self.target_card = TargetCard(top_split)
        self.target_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.creds_card = CredentialsCard(top_split)
        self.creds_card.grid(row=0, column=1, sticky="nsew", padx=(0, 0))

        # 3. Operations Mode Selector
        self.mode_card = ModeCard(main_workspace)
        self.mode_card.pack(fill=tk.X, pady=(0, 6))

        # 4. KPI Metrics & Execution Action Bar
        self.metrics_bar = MetricsBar(
            main_workspace,
            on_start=self._start_audit,
            on_pause_resume=self._toggle_pause,
            on_stop=self._stop_audit
        )
        self.metrics_bar.pack(fill=tk.X, pady=(0, 6))

        # 5. Filter Toolbar & Search Bar
        self.filter_bar = FilterToolbar(
            main_workspace,
            on_filter_changed=self._on_filter_changed,
            on_search_changed=self._on_search_changed,
            on_export_excel=self._export_excel,
            on_export_csv=self._export_csv,
                        on_clear=self._clear_table
        )
        self.filter_bar.pack(fill=tk.X, pady=(0, 4))

        # 6. Spacious Results Grid Table
        self.results_table = ResultsTable(main_workspace)
        self.results_table.pack(fill=tk.BOTH, expand=True)

    def _load_saved_config(self):
        cfg = self.config_manager.get_all()
        if "default_username" in cfg:
            self.creds_card.ent_user.delete(0, tk.END)
            self.creds_card.ent_user.insert(0, cfg["default_username"])
        if "last_ip_or_subnet" in cfg:
            self.target_card.ent_ip.delete(0, tk.END)
            self.target_card.ent_ip.insert(0, cfg["last_ip_or_subnet"])
        if "last_specific_tills" in cfg:
            self.target_card.ent_specific_tills.delete(0, tk.END)
            self.target_card.ent_specific_tills.insert(0, cfg["last_specific_tills"])
        if "war_path" in cfg:
            self.mode_card.ent_war_path.delete(0, tk.END)
            self.mode_card.ent_war_path.insert(0, cfg["war_path"])
        if "war_expected_size_bytes" in cfg and cfg["war_expected_size_bytes"]:
            self.mode_card.ent_war_bytes.delete(0, tk.END)
            self.mode_card.ent_war_bytes.insert(0, str(cfg["war_expected_size_bytes"]))
        if "properties_path" in cfg:
            self.mode_card.ent_prop_path.delete(0, tk.END)
            self.mode_card.ent_prop_path.insert(0, cfg["properties_path"])
        if "expected_delivery_version" in cfg:
            self.mode_card.ent_exp_version.delete(0, tk.END)
            self.mode_card.ent_exp_version.insert(0, cfg["expected_delivery_version"])

    def _save_current_config(self):
        creds = self.creds_card.get_credentials()
        mode_params = self.mode_card.get_mode_params()
        self.config_manager.update({
            "default_username": creds["username"],
            "last_ip_or_subnet": self.target_card.ent_ip.get().strip(),
            "last_specific_tills": self.target_card.ent_specific_tills.get().strip(),
            "war_path": mode_params["war_path"],
            "war_expected_size_bytes": mode_params["war_expected_size_bytes"],
            "properties_path": mode_params["properties_path"],
            "properties_keyword": mode_params["properties_keyword"],
            "expected_delivery_version": mode_params["expected_delivery_version"]
        })
        self.config_manager.save()

    def _start_audit(self):
        stores = self.target_card.get_configured_stores()
        if not stores:
            messagebox.showwarning("No Targets", "Please specify a store IP or load a bulk stores file.")
            return

        creds = self.creds_card.get_credentials()
        if not creds["password"]:
            if not messagebox.askyesno("Empty Password", "Password field is empty. Proceed with empty posuser password?"):
                return

        self._save_current_config()
        self.results_table.clear()
        self.metrics_bar.set_running_state(True)
        self.audit_start_time = time.perf_counter()

        mode_params = self.mode_card.get_mode_params()
        # Read tolerance from backend config.json
        mode_params["size_tolerance_mb"] = float(self.config_manager.get("size_tolerance_mb", 0.3))

        specific_tills = self.target_card.get_specific_tills_string()

        self.orchestrator = BatchOrchestrator(
            username=creds["username"],
            password=creds["password"],
            operation_mode=mode_params["operation_mode"],
            config_params=mode_params,
            store_concurrency=creds["store_concurrency"],
            timeout=creds["timeout"]
        )
        self.orchestrator.start_async(stores, specific_tills)

    def _toggle_pause(self):
        if not self.orchestrator:
            return
        if self.orchestrator.pause_requested.is_set():
            self.orchestrator.resume()
            self.metrics_bar.btn_pause.config(text=" ⏸ Pause ")
        else:
            self.orchestrator.pause()
            self.metrics_bar.btn_pause.config(text=" ▶ Resume ")

    def _stop_audit(self):
        if self.orchestrator:
            self.orchestrator.stop()
            self.metrics_bar.set_running_state(False)

    def _process_events(self):
        if self.orchestrator:
            if self.orchestrator.is_running():
                elapsed = int(time.perf_counter() - self.audit_start_time)
                mins, secs = divmod(elapsed, 60)
                self.metrics_bar.lbl_clock.config(text=f"⏱ {mins:02d}:{secs:02d}")

            while not self.orchestrator.event_queue.empty():
                try:
                    event_type, data = self.orchestrator.event_queue.get_nowait()
                    if event_type == "result":
                        self.results_table.add_result(data)
                        self.metrics_bar.update_summary(self.orchestrator.summary)
                    elif event_type == "target_summary":
                        self.metrics_bar.kpi_total.config(text=f"0 / {data.get('total_tills', 0)}")
                    elif event_type == "completed":
                        self.results_table.sort_by_target_order()
                        self.metrics_bar.set_running_state(False)
                        self.metrics_bar.update_summary(self.orchestrator.summary)
                        messagebox.showinfo(
                            "Audit Finished",
                            f"Audit complete!\nProcessed {self.orchestrator.summary.completed_tills} tills in {self.orchestrator.summary.elapsed_seconds}s.\nPass Rate: {self.orchestrator.summary.pass_rate_percent}%"
                        )
                except Exception:
                    break

        self.after(50, self._process_events)

    def _on_filter_changed(self, filter_name: str):
        self.results_table.set_filter(filter_name)

    def _on_search_changed(self, query: str):
        self.results_table.set_search(query)

    def _clear_table(self):
        if messagebox.askyesno("Clear Table", "Clear all records from table?"):
            self.results_table.clear()
            self.metrics_bar.update_summary(AuditSummary())

    def _export_excel(self):
        if not self.results_table.all_results:
            messagebox.showwarning("No Data", "No results to export.")
            return

        f_path = filedialog.asksaveasfilename(
            title="Export Excel Audit Report",
            defaultextension=".xlsx",
            filetypes=[("Excel Spreadsheet", "*.xlsx")]
        )
        if f_path:
            try:
                summary = self.orchestrator.summary if self.orchestrator else AuditSummary()
                ExcelExporter.export_audit_workbook(f_path, summary, self.results_table.all_results)
                messagebox.showinfo("Export Successful", f"Excel report exported to:\n{f_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export Excel file: {e}")

    def _export_csv(self):
        if not self.results_table.all_results:
            messagebox.showwarning("No Data", "No results to export.")
            return

        cur_f = self.results_table.current_filter
        filtered = self.results_table.get_filtered_results()

        if not filtered:
            messagebox.showinfo("Empty Section", f"There are no till records in the '{cur_f.title()}' section to export.")
            return

        # Context-aware default filenames and titles
        if cur_f == "success":
            def_name = "audit_success_tills.csv"
            dlg_title = "Export Success Tills CSV"
        elif cur_f == "mismatches":
            def_name = "audit_mismatched_tills.csv"
            dlg_title = "Export Mismatches CSV (Re-Audit Ready)"
        elif cur_f == "missing":
            def_name = "audit_missing_tills.csv"
            dlg_title = "Export Missing Tills CSV (Re-Audit Ready)"
        elif cur_f == "offline":
            def_name = "audit_offline_tills.csv"
            dlg_title = "Export Offline Tills CSV (Re-Audit Ready)"
        else:
            def_name = "audit_all_tills.csv"
            dlg_title = "Export All Tills CSV"

        f_path = filedialog.asksaveasfilename(
            title=dlg_title,
            initialfile=def_name,
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")]
        )
        if f_path:
            try:
                CsvExporter.export_results(f_path, filtered, only_failures=False)
                messagebox.showinfo("Export Successful", f"Exported {len(filtered)} tills to:\n{f_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export CSV: {e}")

    def _export_action_list(self):
        if not self.results_table.all_results:
            messagebox.showwarning("No Data", "No results to export.")
            return

        failures = [r for r in self.results_table.all_results if AuditStatus.is_failed(r.status)]
        if not failures:
            messagebox.showinfo("No Failures", "All tills passed successfully! There are no action items or failed tills to export.")
            return

        f_path = filedialog.asksaveasfilename(
            title="Export Failed Tills Action List (Re-Audit Ready)",
            initialfile="audit_failed_action_list.csv",
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")]
        )
        if f_path:
            try:
                CsvExporter.export_results(f_path, self.results_table.all_results, only_failures=True)
                messagebox.showinfo("Export Successful", f"Action list with {len(failures)} failed tills exported to:\n{f_path}\n\nTip: You can directly load this file next time to scan ONLY these failed tills!")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export action list: {e}")

    def _on_close(self):
        if self.orchestrator and self.orchestrator.is_running():
            if messagebox.askyesno("Exit", "Audit is currently running. Stop audit and exit?"):
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
