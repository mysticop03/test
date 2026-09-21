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

COLUMNS = [
    ("store_code", "Store", 100),
    ("till_name", "Till", 80),
    ("ip", "IP Address", 130),
    ("latency_ms", "Latency", 90),
    ("war_size", "WAR Size", 130),
    ("war_modified", "WAR Last Modified", 165),
    ("delivery_version", "Delivery Version", 165),
    ("status", "Status", 140)
]

class ResultsTable(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.all_results: List[AuditResult] = []
        self.displayed_items: Dict[str, AuditResult] = {}
        self.current_filter = "all"
        self.search_query = ""

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

    def add_result(self, result: AuditResult):
        self.all_results.append(result)
        if self._matches_filter_and_search(result):
            self._insert_tree_row(result)

    def _insert_tree_row(self, r: AuditResult):
        latency_str = f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
        item_id = self.tree.insert("", tk.END, values=(
            r.store_code,
            r.till_name,
            r.ip,
            latency_str,
            r.war_size,
            r.war_modified,
            r.delivery_version,
            r.status
        ), tags=(r.status,))
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

        for r in self.all_results:
            if self._matches_filter_and_search(r):
                self._insert_tree_row(r)

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
