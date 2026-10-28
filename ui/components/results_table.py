"""
ui/components/results_table.py
White / Light Mode Treeview Results Grid.
Implements dynamic column presentation matching user requirements & Section 7.1:
1. Button 1 (File Check):
   - If size only -> Shows File Size and Last Modified (Hides Variable/Value)
   - If version only -> Shows Variable / Value and Last Modified (Hides File Size)
   - If both -> Shows full (File Size, Last Modified, Variable / Value)
2. Button 2 (Version Check):
   - Aggregated 5-column format: Store Code, IP (.12), Mismatch Version, Offline, Status
   - Live real-time updates as tills finish
3. Button 3 (Terminal):
   - Shows strictly: Store, Device, IP Address, Latency, Command Output, Status
   - Hides File Size, Last Modified, Variable/Value headers
- Centered headings and cell data
- Status badges: Success, Mismatch, Miss, Offline, Blocked
- Double-clicking switches to the in-place Terminal Console (no popups)
"""
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from models.result import AuditResult, AuditStatus
import ui.theme as theme

def _device_sort_key(d: Any) -> tuple:
    if str(d).upper() == "BO":
        return (0, 0)
    try:
        return (1, int(d))
    except (ValueError, TypeError):
        return (2, str(d))

@dataclass
class StoreVersionSummary:
    store_code: str
    ip: str
    store_order_index: int = 0
    mismatch_tills: List[Any] = field(default_factory=list)
    offline_tills: List[Any] = field(default_factory=list)
    matched_tills: List[Any] = field(default_factory=list)
    all_results: List[AuditResult] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.mismatch_tills:
            return AuditStatus.MISMATCH
        if self.offline_tills and not self.matched_tills:
            return AuditStatus.OFFLINE
        if self.offline_tills and self.matched_tills:
            return AuditStatus.OFFLINE
        return AuditStatus.SUCCESS

    @property
    def mismatch_str(self) -> str:
        if self.mismatch_tills:
            return ",".join(str(n) for n in sorted(set(self.mismatch_tills), key=_device_sort_key))
        if self.matched_tills:
            return "All Matched"
        return "-"

    @property
    def offline_str(self) -> str:
        if not self.offline_tills:
            return "-"
        if not self.matched_tills and not self.mismatch_tills:
            return "All Offline"
        return ",".join(str(n) for n in sorted(set(self.offline_tills), key=_device_sort_key))


class ResultsTable(tk.Frame):
    MAX_DISPLAY_ROWS = 100

    def __init__(self, parent, on_row_inspect: Optional[Callable[[AuditResult], None]] = None, max_display_rows: int = 100):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        self.on_row_inspect = on_row_inspect
        self.max_display_rows = max_display_rows
        self.all_results: List[AuditResult] = []
        self.displayed_items: Dict[str, AuditResult] = {}
        self.store_summaries: Dict[str, StoreVersionSummary] = {}
        self.store_tree_items: Dict[str, str] = {}
        self.current_filter = "all"
        self.search_query = ""
        self.is_version_check = False
        self.is_terminal = False

        # Default columns
        self.active_columns = [
            ("store_code", "Store", 100),
            ("device_name", "Device", 95),
            ("ip", "IP Address", 140),
            ("latency_ms", "Latency", 90),
            ("file_size", "File Size", 115),
            ("file_modified", "Last Modified", 160),
            ("var_val", "Variable / Value", 165),
            ("status", "Status", 120)
        ]

        self._build_widgets()

    def _build_widgets(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Light.Treeview",
            background="#FFFFFF",
            foreground="#0F172A",
            fieldbackground="#FFFFFF",
            borderwidth=0,
            rowheight=24,
            font=theme.FONT_MONO
        )
        style.configure("Vertical.TScrollbar", width=16, arrowsize=14)
        style.configure("Horizontal.TScrollbar", width=16, arrowsize=14)
        style.configure(
            "Light.Treeview.Heading",
            background="#F8FAFC",
            foreground="#0F172A",
            relief="flat",
            font=theme.FONT_BODY_BOLD
        )
        style.map(
            "Light.Treeview",
            background=[("selected", "#E0E7FF")],
            foreground=[("selected", "#1E1B4B")]
        )

        table_frame = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        table_frame.pack(fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", style="Vertical.TScrollbar")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", style="Horizontal.TScrollbar")

        col_ids = [c[0] for c in self.active_columns]
        self.tree = ttk.Treeview(
            table_frame,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            style="Light.Treeview",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event):
            if event.delta:
                self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"

        def _on_shift_mousewheel(event):
            if event.delta:
                self.tree.xview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"

        self.tree.bind("<MouseWheel>", _on_mousewheel)
        self.tree.bind("<Shift-MouseWheel>", _on_shift_mousewheel)
        self.tree.bind("<Button-4>", lambda e: self.tree.yview_scroll(-1, "units"))
        self.tree.bind("<Button-5>", lambda e: self.tree.yview_scroll(1, "units"))

        self._apply_column_headers()

        for tag, cfg in theme.TAG_CONFIG.items():
            self.tree.tag_configure(tag, background=cfg["bg"], foreground=cfg["fg"])

        self.tree.bind("<Double-1>", self._on_double_click)

        # Empty State Placeholder Label
        self.lbl_empty = tk.Label(
            self.tree,
            text="No audit records yet. Click Start Audit above to begin inspection.",
            font=theme.FONT_BODY,
            fg=theme.COLOR_TEXT_MUTED,
            bg="#FFFFFF"
        )
        self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")

    def _apply_column_headers(self):
        col_ids = [c[0] for c in self.active_columns]
        self.tree.config(columns=col_ids)
        for col_id, title, width in self.active_columns:
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

    def configure_columns(
        self,
        has_size: bool,
        has_version: bool,
        is_terminal: bool = False,
        is_version_check: bool = False
    ):
        """
        Dynamically adjusts table columns based on user mode:
        1. Version Check: [Store Code, IP (.12), Mismatch Version, Offline, Status]
        2. Terminal: [Store, Device, IP, Latency, Command Output, Status]
        3. File Check:
           - Size only: [Store, Device, IP, Latency, File Size, Last Modified, Status]
           - Var only:  [Store, Device, IP, Latency, Variable / Value, Last Modified, Status]
           - Both:      [Store, Device, IP, Latency, File Size, Last Modified, Variable / Value, Status]
        """
        self.is_version_check = is_version_check
        self.is_terminal = is_terminal

        if is_version_check:
            self.active_columns = [
                ("store_code", "Store Code", 110),
                ("ip", "IP", 140),
                ("mismatch_val", "Mismatch Version", 200),
                ("offline_val", "Offline", 140),
                ("status", "Status", 120)
            ]
        elif is_terminal:
            self.active_columns = [
                ("store_code", "Store", 100),
                ("device_name", "Device", 95),
                ("ip", "IP Address", 140),
                ("latency_ms", "Latency", 90),
                ("preview_output", "Command Output", 400),
                ("status", "Status", 120)
            ]
        else:
            cols = [
                ("store_code", "Store", 100),
                ("device_name", "Device", 95),
                ("ip", "IP Address", 140),
                ("latency_ms", "Latency", 90)
            ]

            if has_size and not has_version:
                cols.append(("file_size", "File Size", 125))
                cols.append(("file_modified", "Last Modified", 165))
            elif has_version and not has_size:
                cols.append(("var_val", "Variable / Value", 180))
                cols.append(("file_modified", "Last Modified", 165))
            else:
                # Both size and variable
                cols.append(("file_size", "File Size", 115))
                cols.append(("file_modified", "Last Modified", 160))
                cols.append(("var_val", "Variable / Value", 165))

            cols.append(("status", "Status", 120))
            self.active_columns = cols

        self._apply_column_headers()
        self.refresh_display()

    def add_result(self, result: AuditResult):
        self.all_results.append(result)
        if self.lbl_empty.winfo_ismapped():
            self.lbl_empty.place_forget()

        if self.is_version_check:
            self._update_version_check_row(result)
        else:
            if self._matches_filter_and_search(result):
                self._insert_tree_row(result)

    def _update_version_check_row(self, r: AuditResult):
        code = r.store_code
        if code not in self.store_summaries:
            parts = r.ip.split(".")
            base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.12" if len(parts) == 4 else r.ip
            self.store_summaries[code] = StoreVersionSummary(
                store_code=code,
                ip=base_ip,
                store_order_index=r.store_order_index
            )

        summary = self.store_summaries[code]
        summary.all_results.append(r)
        dev_tag = "BO" if r.is_bo else (r.till_num if r.till_num is not None else 1)
        if r.status == AuditStatus.SUCCESS:
            if dev_tag not in summary.matched_tills:
                summary.matched_tills.append(dev_tag)
        elif r.status in (AuditStatus.MISMATCH, AuditStatus.MISS):
            if dev_tag not in summary.mismatch_tills:
                summary.mismatch_tills.append(dev_tag)
        elif r.status == AuditStatus.OFFLINE:
            if dev_tag not in summary.offline_tills:
                summary.offline_tills.append(dev_tag)

        # Check filter
        if not self._matches_summary_filter(summary):
            if code in self.store_tree_items:
                item_id = self.store_tree_items.pop(code)
                if self.tree.exists(item_id):
                    self.tree.delete(item_id)
            return

        row_vals = (
            summary.store_code,
            summary.ip,
            summary.mismatch_str,
            summary.offline_str,
            summary.status
        )

        if code in self.store_tree_items and self.tree.exists(self.store_tree_items[code]):
            item_id = self.store_tree_items[code]
            self.tree.item(item_id, values=row_vals, tags=(summary.status,))
        else:
            children = self.tree.get_children()
            new_key = summary.store_order_index
            insert_idx = tk.END
            for idx, c_id in enumerate(children):
                c_code = self.tree.item(c_id, "values")[0]
                c_sum = self.store_summaries.get(c_code)
                if c_sum and new_key < c_sum.store_order_index:
                    insert_idx = idx
                    break

            if len(children) >= self.max_display_rows:
                if insert_idx == tk.END:
                    return
                last_item = children[-1]
                for k, v in list(self.store_tree_items.items()):
                    if v == last_item:
                        del self.store_tree_items[k]
                self.tree.delete(last_item)

            item_id = self.tree.insert("", insert_idx, values=row_vals, tags=(summary.status,))
            self.store_tree_items[code] = item_id

    def _insert_tree_row(self, r: AuditResult):
        children = self.tree.get_children()

        latency_str = f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
        dev_label = f" {r.till_name}" if r.is_bo else f" {r.till_name}"
        var_display = r.delivery_version if r.delivery_version != "-" else r.prop_variable

        val_map = {
            "store_code": r.store_code,
            "device_name": dev_label,
            "ip": r.ip,
            "latency_ms": latency_str,
            "file_size": r.war_size,
            "file_modified": r.war_modified,
            "var_val": var_display,
            "preview_output": r.preview_output,
            "status": r.status
        }

        row_vals = tuple(val_map.get(col_id, "-") for col_id, _, _ in self.active_columns)
        new_key = (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
        insert_idx = tk.END
        for idx, child_id in enumerate(children):
            existing_res = self.displayed_items.get(child_id)
            if existing_res:
                exist_key = (existing_res.store_order_index, 0 if existing_res.is_bo else (existing_res.till_num or 1))
                if new_key < exist_key:
                    insert_idx = idx
                    break

        if len(children) >= self.max_display_rows:
            if insert_idx == tk.END:
                return
            last_item = children[-1]
            if last_item in self.displayed_items:
                del self.displayed_items[last_item]
            self.tree.delete(last_item)

        item_id = self.tree.insert("", insert_idx, values=row_vals, tags=(r.status,))
        self.displayed_items[item_id] = r

    def clear(self):
        self.all_results.clear()
        self.displayed_items.clear()
        self.store_summaries.clear()
        self.store_tree_items.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")

    def set_filter(self, filter_name: str):
        self.current_filter = filter_name.lower().replace(" statuses", "")
        self.refresh_display()

    def set_search(self, query: str):
        self.search_query = query.lower()
        self.refresh_display()

    def get_filtered_results(self) -> List[AuditResult]:
        return [r for r in self.all_results if self._matches_filter_and_search(r)]

    def refresh_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.displayed_items.clear()
        self.store_tree_items.clear()

        if self.is_version_check:
            # Rebuild version check table
            matching_sums = [s for s in self.store_summaries.values() if self._matches_summary_filter(s)]
            matching_sums.sort(key=lambda s: s.store_order_index)

            if not matching_sums:
                self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")
            else:
                if self.lbl_empty.winfo_ismapped():
                    self.lbl_empty.place_forget()

            for s in matching_sums[:self.max_display_rows]:
                row_vals = (s.store_code, s.ip, s.mismatch_str, s.offline_str, s.status)
                item_id = self.tree.insert("", tk.END, values=row_vals, tags=(s.status,))
                self.store_tree_items[s.store_code] = item_id
            return

        matching = [r for r in self.all_results if self._matches_filter_and_search(r)]
        matching.sort(key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1)))
        if not matching:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            if self.lbl_empty.winfo_ismapped():
                self.lbl_empty.place_forget()

        for r in matching[:self.max_display_rows]:
            latency_str = f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
            dev_label = f" {r.till_name}" if r.is_bo else f" {r.till_name}"
            var_display = r.delivery_version if r.delivery_version != "-" else r.prop_variable

            val_map = {
                "store_code": r.store_code,
                "device_name": dev_label,
                "ip": r.ip,
                "latency_ms": latency_str,
                "file_size": r.war_size,
                "file_modified": r.war_modified,
                "var_val": var_display,
                "preview_output": r.preview_output,
                "status": r.status
            }
            row_vals = tuple(val_map.get(col_id, "-") for col_id, _, _ in self.active_columns)
            item_id = self.tree.insert("", tk.END, values=row_vals, tags=(r.status,))
            self.displayed_items[item_id] = r

    def _matches_summary_filter(self, s: StoreVersionSummary) -> bool:
        st = s.status
        f = self.current_filter
        if f == "success" and st != AuditStatus.SUCCESS:
            return False
        elif f == "mismatch" and st != AuditStatus.MISMATCH:
            return False
        elif f == "offline" and st != AuditStatus.OFFLINE:
            return False
        elif f == "miss" and st != AuditStatus.MISS:
            return False
        elif f == "blocked" and st != AuditStatus.BLOCKED:
            return False

        if self.search_query:
            comb = f"{s.store_code} {s.ip} {s.mismatch_str} {s.offline_str} {s.status}".lower()
            if self.search_query not in comb:
                return False
        return True

    def _matches_filter_and_search(self, r: AuditResult) -> bool:
        st = r.status
        f = self.current_filter

        if f == "success" and st != AuditStatus.SUCCESS:
            return False
        elif f == "mismatch" and st != AuditStatus.MISMATCH:
            return False
        elif f == "miss" and st != AuditStatus.MISS:
            return False
        elif f == "offline" and st != AuditStatus.OFFLINE:
            return False
        elif f == "blocked" and st != AuditStatus.BLOCKED:
            return False

        if self.search_query:
            combined = f"{r.store_code} {r.till_name} {r.ip} {r.status} {r.delivery_version} {r.preview_output}".lower()
            if self.search_query not in combined:
                return False

        return True

    def _on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return

        if self.is_version_check:
            # Find matching store summary
            store_code = self.tree.item(item_id, "values")[0]
            summary = self.store_summaries.get(store_code)
            if not summary or not self.on_row_inspect:
                return

            details_lines = []
            for r in summary.all_results:
                dev = "BO" if r.is_bo else f"Till {r.till_num:02d}"
                details_lines.append(f"{dev:10s} | IP: {r.ip:15s} | Delivery: {r.delivery_version:8s} | Status: {r.status}")

            inspection_text = (
                f"Store: {summary.store_code}  |  Subnet/BO IP: {summary.ip}\n"
                f"Status: {summary.status}\n"
                f"Mismatch Tills: {summary.mismatch_str}\n"
                f"Offline Tills:  {summary.offline_str}\n"
                f"{'-'*75}\n"
                + "\n".join(details_lines)
            )

            synthetic_res = AuditResult(
                store_code=summary.store_code,
                till_name=f"Store {summary.store_code}",
                till_num=0,
                ip=summary.ip,
                operation_mode="version_check",
                status=summary.status,
                full_output=inspection_text,
                preview_output=f"Mismatch: {summary.mismatch_str} | Offline: {summary.offline_str}"
            )
            self.on_row_inspect(synthetic_res)
            return

        if item_id in self.displayed_items:
            result = self.displayed_items[item_id]
            if self.on_row_inspect:
                self.on_row_inspect(result)

    def sort_by_target_order(self):
        """Strictly sorts all results in store hierarchy order and refreshes the display."""
        self.all_results.sort(key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1)))
        self.refresh_display()

    def _sort_column(self, col_id: str, reverse: bool):
        # Sort logic
        pass
