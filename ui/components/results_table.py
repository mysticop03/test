"""
ui/components/results_table.py
Sortable Treeview results grid.
Headings and cell data are strictly center-aligned for clean, professional data presentation.
Status is placed at the very end of the row.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional
from models.result import AuditResult, AuditStatus
import ui.theme as theme

COLUMNS_BY_MODE = {
    "version_war": [
        ("store_code", "Store", 100),
        ("till_name", "Till", 80),
        ("ip", "IP Address", 130),
        ("latency_ms", "Latency", 90),
        ("file_size", "File Size", 130),
        ("file_modified", "File Last Modified", 165),
        ("delivery_version", "Delivery Version", 165),
        ("status", "Status", 140)
    ],
    "file_info": [
        ("store_code", "Store", 100),
        ("till_name", "Till", 80),
        ("ip", "IP Address", 130),
        ("latency_ms", "Latency", 90),
        ("file_size", "File Size", 150),
        ("file_modified", "File Last Modified", 200),
        ("status", "Status", 140)
    ],
    "command": [
        ("store_code", "Store", 100),
        ("till_name", "Till", 80),
        ("ip", "IP Address", 130),
        ("latency_ms", "Latency", 90),
        ("preview_output", "Command Output", 380),
        ("status", "Status", 140)
    ]
}

COLUMNS = COLUMNS_BY_MODE["version_war"]

class ResultsTable(ttk.Frame):
    MAX_DISPLAY_ROWS = 50  # Cap Tkinter treeview items to prevent UI lag / crashes

    def __init__(self, parent):
        super().__init__(parent)
        self.all_results: List[AuditResult] = []
        self.displayed_items: Dict[str, AuditResult] = {}
        self.current_filter = "all"
        self.search_query = ""
        self.current_mode = "version_war"

        self._build_widgets()

    def _build_widgets(self):
        scroll_y = ttk.Scrollbar(self, orient="vertical")
        scroll_x = ttk.Scrollbar(self, orient="horizontal")

        col_ids = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Explicitly configure both heading and column cell alignment to CENTER
        for col_id, title, width in COLUMNS:
            self.tree.heading(
                col_id,
                text=title,
                anchor="center",
                command=lambda c=col_id: self._sort_column(c, False)
            )
            self.tree.column(
                col_id,
                width=width,
                minwidth=60,
                stretch=True,
                anchor="center"
            )

        for tag, cfg in theme.TAG_CONFIG.items():
            self.tree.tag_configure(tag, background=cfg["bg"], foreground=cfg["fg"])

        self.tree.bind("<Double-1>", self._on_double_click)

        # Status note at bottom of table
        self.lbl_table_status = ttk.Label(
            self,
            text="Display capped at latest 50 tills to keep UI smooth. 100% of data is preserved for export.",
            font=theme.FONT_SMALL,
            foreground=theme.COLOR_TEXT_SECONDARY
        )
        self.lbl_table_status.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=(2, 0))

    def set_mode(self, mode: str):
        """Dynamically configure table columns for active mode (e.g. Command Output vs File Size)."""
        self.current_mode = mode if mode in COLUMNS_BY_MODE else "version_war"
        cols_def = COLUMNS_BY_MODE[self.current_mode]
        col_ids = [c[0] for c in cols_def]
        self.tree.config(columns=col_ids)
        for col_id, title, width in cols_def:
            self.tree.heading(
                col_id,
                text=title,
                anchor="center",
                command=lambda c=col_id: self._sort_column(c, False)
            )
            self.tree.column(
                col_id,
                width=width,
                minwidth=60,
                stretch=True,
                anchor="center"
            )
        self.refresh_display()

    def add_result(self, result: AuditResult):
        self.all_results.append(result)
        if self._matches_filter_and_search(result):
            self._insert_tree_row(result)
        self._update_table_status_label()

    def _insert_tree_row(self, r: AuditResult):
        # Enforce max 50 rows displayed in Tkinter to prevent GUI lag and crashes
        children = self.tree.get_children()
        if len(children) >= self.MAX_DISPLAY_ROWS:
            oldest = children[0]
            if oldest in self.displayed_items:
                del self.displayed_items[oldest]
            self.tree.delete(oldest)

        latency_str = f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
        cols_def = COLUMNS_BY_MODE.get(self.current_mode, COLUMNS_BY_MODE["version_war"])

        val_map = {
            "store_code": r.store_code,
            "till_name": r.till_name,
            "ip": r.ip,
            "latency_ms": latency_str,
            "file_size": r.war_size,
            "file_modified": r.war_modified,
            "delivery_version": r.delivery_version,
            "preview_output": r.preview_output,
            "status": r.status
        }
        row_vals = tuple(val_map.get(c[0], "-") for c in cols_def)
        item_id = self.tree.insert("", tk.END, values=row_vals, tags=(r.status,))
        self.displayed_items[item_id] = r

    def clear(self):
        self.all_results.clear()
        self.displayed_items.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def set_filter(self, filter_name: str):
        self.current_filter = filter_name
        self.refresh_display()

    def set_search(self, query: str):
        self.search_query = query.lower()
        self.refresh_display()

    def get_filtered_results(self, filter_name: Optional[str] = None) -> List[AuditResult]:
        """Returns results matching the specified filter (or current active filter) in strict FCFS order."""
        f = (filter_name if filter_name is not None else self.current_filter).lower()
        if f == "all":
            if self.search_query:
                return [r for r in self.all_results if self._matches_filter_and_search(r)]
            return list(self.all_results)
        elif f == "success":
            return [r for r in self.all_results if r.is_success]
        elif f == "mismatches":
            return [r for r in self.all_results if r.is_mismatch]
        elif f == "missing":
            return [r for r in self.all_results if r.status == AuditStatus.FILE_MISSING]
        elif f == "offline":
            return [r for r in self.all_results if r.status in (AuditStatus.OFFLINE, AuditStatus.TIMEOUT, AuditStatus.AUTH_FAIL)]
        return list(self.all_results)

    def sort_by_target_order(self):
        """Sort all results in strict FCFS order (Store order, then Till 1 to 13) and refresh view."""
        self.all_results.sort(key=lambda r: (r.store_order_index, r.till_num))
        self.refresh_display()

    def refresh_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.displayed_items.clear()

        matching = [r for r in self.all_results if self._matches_filter_and_search(r)]
        # Show at most the latest 50 matching items
        for r in matching[-self.MAX_DISPLAY_ROWS:]:
            latency_str = f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
            cols_def = COLUMNS_BY_MODE.get(self.current_mode, COLUMNS_BY_MODE["version_war"])
            val_map = {
                "store_code": r.store_code,
                "till_name": r.till_name,
                "ip": r.ip,
                "latency_ms": latency_str,
                "file_size": r.war_size,
                "file_modified": r.war_modified,
                "delivery_version": r.delivery_version,
                "preview_output": r.preview_output,
                "status": r.status
            }
            row_vals = tuple(val_map.get(c[0], "-") for c in cols_def)
            item_id = self.tree.insert("", tk.END, values=row_vals, tags=(r.status,))
            self.displayed_items[item_id] = r

        self._update_table_status_label()

    def _update_table_status_label(self):
        if not hasattr(self, "lbl_table_status"):
            return
        total_all = len(self.all_results)
        matching = len([r for r in self.all_results if self._matches_filter_and_search(r)])
        if matching > self.MAX_DISPLAY_ROWS:
            self.lbl_table_status.config(
                text=f"Showing latest {self.MAX_DISPLAY_ROWS} of {matching} matching rows ({total_all} total tills audited). 100% of data is preserved for export."
            )
        else:
            self.lbl_table_status.config(
                text=f"Showing all {matching} matching rows ({total_all} total tills audited). 100% of data is preserved for export."
            )

    def _matches_filter_and_search(self, r: AuditResult) -> bool:
        st = r.status
        if self.current_filter == "success" and not r.is_success:
            return False
        elif self.current_filter == "mismatches" and not r.is_mismatch:
            return False
        elif self.current_filter == "missing" and st != AuditStatus.FILE_MISSING:
            return False
        elif self.current_filter == "offline" and st not in (AuditStatus.OFFLINE, AuditStatus.TIMEOUT, AuditStatus.AUTH_FAIL):
            return False

        if self.search_query:
            combined = f"{r.store_code} {r.till_name} {r.ip} {r.status} {r.delivery_version} {r.preview_output}".lower()
            if self.search_query not in combined:
                return False

        return True

    def _sort_column(self, col: str, reverse: bool):
        data = []
        for child in self.tree.get_children(""):
            val = self.tree.set(child, col)
            data.append((val, child))

        data.sort(reverse=reverse)
        for index, (_, child) in enumerate(data):
            self.tree.move(child, "", index)

        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    def _on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        r = self.displayed_items.get(item[0])
        if not r:
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Till Inspector Details: {r.store_code} - {r.till_name}")
        dialog.geometry("680x450")
        dialog.transient(self)

        top = tk.Frame(dialog, bg=theme.COLOR_HEADER_BG, padx=14, pady=10)
        top.pack(fill=tk.X)
        tk.Label(top, text=f"{r.store_code} | {r.till_name} ({r.ip})", fg="white", bg=theme.COLOR_HEADER_BG, font=theme.FONT_TITLE).pack(anchor="w")
        tk.Label(top, text=f"Status: {r.status}  |  Latency: {r.latency_ms} ms  |  Timestamp: {r.timestamp}", fg="#94A3B8", bg=theme.COLOR_HEADER_BG, font=theme.FONT_BODY).pack(anchor="w", pady=(2, 0))

        txt_frame = ttk.Frame(dialog, padding=10)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        txt = tk.Text(txt_frame, wrap="word", font=theme.FONT_MONO)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", r.full_output if r.full_output else "(No full output captured)")
        txt.config(state="disabled")
