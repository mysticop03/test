"""
ui/components/filter_toolbar.py
Filter pills ([All], [Success], [Mismatches], [Missing], [Offline]), live search, and export actions.
Clean, intuitive: CSV button dynamically exports the currently active section.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import ui.theme as theme

class FilterToolbar(ttk.Frame):
    def __init__(
        self,
        parent,
        on_filter_changed: Optional[Callable[[str], None]] = None,
        on_search_changed: Optional[Callable[[str], None]] = None,
        on_export_excel: Optional[Callable[[], None]] = None,
        on_export_csv: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, padding=(0, 6))
        self.on_filter_changed = on_filter_changed
        self.on_search_changed = on_search_changed
        self.on_export_excel = on_export_excel
        self.on_export_csv = on_export_csv
        self.on_clear = on_clear

        self.current_filter = "all"
        self._build_widgets()

    def _build_widgets(self):
        # Filter buttons on left
        ttk.Label(self, text="Filter:").pack(side=tk.LEFT, padx=(0, 6))

        self.btn_f_all = ttk.Button(self, text="[ All ]", width=9, command=lambda: self._set_filter("all"))
        self.btn_f_all.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_f_success = ttk.Button(self, text="✓ Success", width=11, command=lambda: self._set_filter("success"))
        self.btn_f_success.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_f_mismatches = ttk.Button(self, text="⚠️ Mismatches", width=14, command=lambda: self._set_filter("mismatches"))
        self.btn_f_mismatches.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_f_missing = ttk.Button(self, text="✕ Missing", width=11, command=lambda: self._set_filter("missing"))
        self.btn_f_missing.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_f_offline = ttk.Button(self, text="🔌 Offline", width=11, command=lambda: self._set_filter("offline"))
        self.btn_f_offline.pack(side=tk.LEFT, padx=(0, 16))

        # Search entry
        ttk.Label(self, text="🔍").pack(side=tk.LEFT)
        self.ent_search = ttk.Entry(self, width=18)
        self.ent_search.pack(side=tk.LEFT, padx=(4, 16))
        self.ent_search.bind("<KeyRelease>", lambda e: self._on_search_change())

        # Clear table button
        if self.on_clear:
            ttk.Button(self, text="🗑 Clear Table", command=self.on_clear).pack(side=tk.LEFT, padx=(0, 16))

        # Export buttons on right (Clean: Excel and Context-aware CSV only)
        if self.on_export_excel:
            ttk.Button(self, text="📊 Excel (.xlsx)", command=self.on_export_excel).pack(side=tk.RIGHT)

        if self.on_export_csv:
            self.btn_csv = ttk.Button(self, text="📄 Export CSV", command=self.on_export_csv)
            self.btn_csv.pack(side=tk.RIGHT, padx=6)

    def _set_filter(self, filter_name: str):
        self.current_filter = filter_name
        self._update_button_labels()
        if self.on_filter_changed:
            self.on_filter_changed(filter_name)

    def _update_button_labels(self):
        f = self.current_filter
        self.btn_f_all.config(text="[ All ]" if f == "all" else "All")
        self.btn_f_success.config(text="[ ✓ Success ]" if f == "success" else "✓ Success")
        self.btn_f_mismatches.config(text="[ ⚠️ Mismatches ]" if f == "mismatches" else "⚠️ Mismatches")
        self.btn_f_missing.config(text="[ ✕ Missing ]" if f == "missing" else "✕ Missing")
        self.btn_f_offline.config(text="[ 🔌 Offline ]" if f == "offline" else "🔌 Offline")

        # Contextual label for CSV export button
        if hasattr(self, "btn_csv"):
            if f == "success":
                self.btn_csv.config(text="📄 Export Success CSV")
            elif f == "mismatches":
                self.btn_csv.config(text="📄 Export Mismatches CSV")
            elif f == "missing":
                self.btn_csv.config(text="📄 Export Missing CSV")
            elif f == "offline":
                self.btn_csv.config(text="📄 Export Offline CSV")
            else:
                self.btn_csv.config(text="📄 Export CSV")

    def _on_search_change(self):
        if self.on_search_changed:
            self.on_search_changed(self.ent_search.get().strip())
