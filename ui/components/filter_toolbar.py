"""
ui/components/filter_toolbar.py
Filter & Export toolbar matching the clean white UI:
- Filter: [All Statuses ▾] dropdown combobox
- Search IP, Store, or Device...
- Right buttons: [Clear Results] [Export CSV] [Export Excel (5 Sheets)]
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import ui.theme as theme

class FilterToolbar(tk.Frame):
    def __init__(
        self,
        parent,
        on_filter_changed: Optional[Callable[[str], None]] = None,
        on_search_changed: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_export_csv: Optional[Callable[[], None]] = None,
        on_export_excel: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, bg=theme.COLOR_BG, pady=6)
        self.on_filter_changed = on_filter_changed
        self.on_search_changed = on_search_changed
        self.on_clear = on_clear
        self.on_export_csv = on_export_csv
        self.on_export_excel = on_export_excel

        self._build_widgets()

    def _build_widgets(self):
        # Left Side: Filter Dropdown + Search Input
        left = tk.Frame(self, bg=theme.COLOR_BG)
        left.pack(side=tk.LEFT)

        tk.Label(left, text="Filter:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_BG).pack(side=tk.LEFT, padx=(0, 6))

        self.cbo_filter = ttk.Combobox(
            left, values=["All Statuses", "Success", "Offline", "Mismatch", "Miss", "Blocked"],
            state="readonly", width=14, font=theme.FONT_BODY
        )
        self.cbo_filter.set("All Statuses")
        self.cbo_filter.pack(side=tk.LEFT, padx=(0, 14))
        self.cbo_filter.bind("<<ComboboxSelected>>", self._on_filter_select)

        # Search Bar
        tk.Label(left, text="🔍", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_BG).pack(side=tk.LEFT, padx=(0, 4))
        self.ent_search = tk.Entry(
            left, font=theme.FONT_BODY, bg=theme.COLOR_CARD_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=26
        )
        self.ent_search.pack(side=tk.LEFT)
        self.ent_search.bind("<KeyRelease>", lambda e: self._on_search_type())

        # Right Side: Export & Clear Actions
        right = tk.Frame(self, bg=theme.COLOR_BG)
        right.pack(side=tk.RIGHT)

        if self.on_clear:
            tk.Button(
                right, text="Clear Results", font=theme.FONT_BODY,
                bg="#FFFFFF", fg=theme.COLOR_TEXT_SECONDARY, activebackground="#E2E8F0", activeforeground=theme.COLOR_TEXT_PRIMARY,
                relief="flat", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=10, pady=3, cursor="hand2", command=self.on_clear
            ).pack(side=tk.LEFT, padx=(0, 6))

        if self.on_export_csv:
            tk.Button(
                right, text="Export CSV", font=theme.FONT_BODY,
                bg="#FFFFFF", fg=theme.COLOR_TEXT_SECONDARY, activebackground="#E2E8F0", activeforeground=theme.COLOR_TEXT_PRIMARY,
                relief="flat", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=10, pady=3, cursor="hand2", command=self.on_export_csv
            ).pack(side=tk.LEFT, padx=(0, 6))

        if self.on_export_excel:
            tk.Button(
                right, text="Export Excel", font=theme.FONT_BODY,
                bg="#FFFFFF", fg=theme.COLOR_TEXT_PRIMARY, activebackground="#E2E8F0", activeforeground=theme.COLOR_TEXT_PRIMARY,
                relief="flat", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=10, pady=3, cursor="hand2", command=self.on_export_excel
            ).pack(side=tk.LEFT)

    def _on_filter_select(self, event=None):
        val = self.cbo_filter.get()
        if self.on_filter_changed:
            self.on_filter_changed(val)

    def _on_search_type(self):
        query = self.ent_search.get().strip()
        if self.on_search_changed:
            self.on_search_changed(query)
