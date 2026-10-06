"""
ui/components/results_table.py
White / Light Mode Treeview Results Grid.
Implements dynamic column presentation matching user requirements & Section 7.1:
- If user fills File Size only -> Shows File Size and Last Modified (Hides Variable/Value)
- If user fills Version only -> Shows Variable, Value, and Last Modified (Hides File Size)
- If both -> Shows full (File Size, Last Modified, Variable/Value)
- Strictly centered headings and cell data
- Status badges: Success, Mismatch, Miss, Offline, Blocked
- Double-clicking switches to the in-place Terminal Console (no popups)
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable
from models.result import AuditResult, AuditStatus
import ui.theme as theme

class ResultsTable(tk.Frame):
    MAX_DISPLAY_ROWS = 50

    def __init__(self, parent, on_row_inspect: Optional[Callable[[AuditResult], None]] = None):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        self.on_row_inspect = on_row_inspect
        self.all_results: List[AuditResult] = []
        self.displayed_items: Dict[str, AuditResult] = {}
        self.current_filter = "all"
        self.search_query = ""

        # Default full columns
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
            rowheight=26,
            font=theme.FONT_MONO
        )
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

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")

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

    def configure_columns(self, has_size: bool, has_version: bool, is_terminal: bool = False):
        """
        Dynamically adjusts table columns based on user input:
        - If size only -> shows File Size and Last Modified (hides Variable/Value)
        - If version only -> shows Variable/Value and Last Modified (hides File Size)
        - If both -> shows full columns
        - If terminal mode -> shows Command Output
        """
        if is_terminal:
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
                # Both or default
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

        if self._matches_filter_and_search(result):
            self._insert_tree_row(result)

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
        
        # Real-time natural sorting: Store 1 BO -> Till 01..n -> Store 2 BO -> Till 01..n
        new_key = (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
        insert_idx = tk.END
        for idx, child_id in enumerate(children):
            existing_res = self.displayed_items.get(child_id)
            if existing_res:
                exist_key = (existing_res.store_order_index, 0 if existing_res.is_bo else (existing_res.till_num or 1))
                if new_key < exist_key:
                    insert_idx = idx
                    break

        # Only display the first MAX_DISPLAY_ROWS (50) in natural sorted order
        if len(children) >= self.MAX_DISPLAY_ROWS:
            if insert_idx == tk.END:
                # Belongs beyond the first 50 rows -> do not display in grid (retained in all_results for export)
                return
            # Remove the last item (50th) from the bottom so the first 50 are preserved
            last_item = children[-1]
            if last_item in self.displayed_items:
                del self.displayed_items[last_item]
            self.tree.delete(last_item)

        item_id = self.tree.insert("", insert_idx, values=row_vals, tags=(r.status,))
        self.displayed_items[item_id] = r

    def clear(self):
        self.all_results.clear()
        self.displayed_items.clear()
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

    def sort_by_target_order(self):
        # Strict Store Hierarchy: Store 1 -> BO -> Tills -> Store 2 -> BO -> Tills
        self.all_results.sort(key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1)))
        self.refresh_display()

    def refresh_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.displayed_items.clear()

        matching = [r for r in self.all_results if self._matches_filter_and_search(r)]
        matching.sort(key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1)))
        if not matching:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            if self.lbl_empty.winfo_ismapped():
                self.lbl_empty.place_forget()

        for r in matching[:self.MAX_DISPLAY_ROWS]:
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

        if self.on_row_inspect:
            self.on_row_inspect(r)
