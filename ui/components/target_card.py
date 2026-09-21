"""
ui/components/target_card.py
1. Store IP card: Target selection (Single Store vs Bulk) and Till selection (All, Specific, UAT).
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Callable, Optional
from models.target import StoreRecord
from storage.store_reader import load_stores_from_file, parse_stores_from_text
import ui.theme as theme

class TargetCard(ttk.LabelFrame):
    def __init__(self, parent, on_stores_changed: Optional[Callable[[List[StoreRecord]], None]] = None):
        super().__init__(parent, text=" 1. Store IP ", padding=(10, 6))
        self.on_stores_changed = on_stores_changed
        self.bulk_stores: List[StoreRecord] = []

        self._build_widgets()

    def _build_widgets(self):
        # Mode Selection Toggle (Single Store vs Bulk 1500)
        top_row = ttk.Frame(self)
        top_row.pack(fill=tk.X, pady=(0, 4))

        self.target_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(
            top_row, text="Single Store", value="single",
            variable=self.target_mode_var, command=self._on_target_mode_toggle
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Radiobutton(
            top_row, text="Bulk File (1,500 Stores)", value="bulk",
            variable=self.target_mode_var, command=self._on_target_mode_toggle
        ).pack(side=tk.LEFT)

        # Single Store Controls Container
        self.single_frame = ttk.Frame(self)
        self.single_frame.pack(fill=tk.X)

        # Row 1: IP & Code
        r1 = ttk.Frame(self.single_frame)
        r1.pack(fill=tk.X, pady=2)

        ttk.Label(r1, text="IP / Subnet:").pack(side=tk.LEFT)
        self.ent_ip = ttk.Entry(r1, width=16)
        self.ent_ip.insert(0, "10.3.23.12")
        self.ent_ip.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(r1, text="Store Code:").pack(side=tk.LEFT)
        self.ent_store_code = ttk.Entry(r1, width=10)
        self.ent_store_code.insert(0, "Store-001")
        self.ent_store_code.pack(side=tk.LEFT, padx=(4, 0))

        # Row 2: Till Mode & Specific Tills
        r2 = ttk.Frame(self.single_frame)
        r2.pack(fill=tk.X, pady=(4, 2))

        self.till_sel_mode_var = tk.StringVar(value="all")

        ttk.Radiobutton(
            r2, text="All (1-13)", value="all",
            variable=self.till_sel_mode_var, command=self._on_till_mode_toggle
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Radiobutton(
            r2, text="Tills:", value="specific",
            variable=self.till_sel_mode_var, command=self._on_till_mode_toggle
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.ent_specific_tills = ttk.Entry(r2, width=10)
        self.ent_specific_tills.insert(0, "1, 2, 5")
        self.ent_specific_tills.pack(side=tk.LEFT, padx=(0, 8))

        # Changed to just "UAT" (blue mark removed)
        ttk.Radiobutton(
            r2, text="UAT", value="uat",
            variable=self.till_sel_mode_var, command=self._on_till_mode_toggle
        ).pack(side=tk.LEFT)

        # Bulk Stores Controls Container
        self.bulk_frame = ttk.Frame(self)

        b_row = ttk.Frame(self.bulk_frame)
        b_row.pack(fill=tk.X, pady=3)

        self.btn_browse = ttk.Button(b_row, text="📂 Browse File (.csv, .xlsx)", command=self._browse_bulk_file)
        self.btn_browse.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_paste = ttk.Button(b_row, text="📋 Paste List", command=self._open_paste_dialog)
        self.btn_paste.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_bulk_status = ttk.Label(self.bulk_frame, text="Select a CSV or Excel file.", font=theme.FONT_SMALL, foreground=theme.COLOR_TEXT_SECONDARY)
        self.lbl_bulk_status.pack(anchor="w", pady=(2, 0))

        self._on_till_mode_toggle()

    def _on_target_mode_toggle(self):
        if self.target_mode_var.get() == "single":
            self.bulk_frame.pack_forget()
            self.single_frame.pack(fill=tk.X)
        else:
            self.single_frame.pack_forget()
            self.bulk_frame.pack(fill=tk.X)

    def _on_till_mode_toggle(self):
        mode = self.till_sel_mode_var.get()
        if mode == "specific":
            self.ent_specific_tills.config(state="normal")
        else:
            self.ent_specific_tills.config(state="disabled")

    def _browse_bulk_file(self):
        f_path = filedialog.askopenfilename(
            title="Select Stores File",
            filetypes=[("Store Files", "*.csv *.xlsx *.tsv *.txt"), ("All Files", "*.*")]
        )
        if f_path:
            try:
                stores = load_stores_from_file(f_path)
                if not stores:
                    messagebox.showwarning("Empty File", "No valid store records found in file.")
                    return
                self.bulk_stores = stores
                fname = os.path.basename(f_path)
                self.lbl_bulk_status.config(
                    text=f"✓ Loaded {len(stores)} stores from {fname}",
                    foreground=theme.COLOR_SUCCESS
                )
                if self.on_stores_changed:
                    self.on_stores_changed(self.bulk_stores)
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to load file: {e}")

    def _open_paste_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Paste Store List")
        dialog.geometry("540x360")
        dialog.transient(self)

        ttk.Label(dialog, text="Paste Store IP & Till Count (CSV/TSV):", font=theme.FONT_SUBTITLE).pack(padx=10, pady=6, anchor="w")
        txt = tk.Text(dialog, wrap="none", font=theme.FONT_MONO, height=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        txt.insert("1.0", "Store-001, 10.3.23.12, 13\nStore-002, 10.3.24.12, 13")

        def apply_paste():
            content = txt.get("1.0", tk.END).strip()
            if content:
                stores = parse_stores_from_text(content)
                if stores:
                    self.bulk_stores = stores
                    self.lbl_bulk_status.config(
                        text=f"✓ Loaded {len(stores)} pasted stores",
                        foreground=theme.COLOR_SUCCESS
                    )
                    dialog.destroy()
                    if self.on_stores_changed:
                        self.on_stores_changed(self.bulk_stores)
                else:
                    messagebox.showwarning("Parse Error", "Could not parse store records.")

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(btn_row, text="Apply Stores", command=apply_paste).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=6)

    def get_configured_stores(self) -> List[StoreRecord]:
        if self.target_mode_var.get() == "bulk" and self.bulk_stores:
            return list(self.bulk_stores)

        code = self.ent_store_code.get().strip() or "Store-001"
        ip = self.ent_ip.get().strip()
        till_mode = self.till_sel_mode_var.get()
        till_count = 1 if till_mode == "uat" else 13

        return [StoreRecord(store_code=code, subnet_or_ip=ip, till_count=till_count)]

    def get_specific_tills_string(self) -> str:
        if self.till_sel_mode_var.get() == "specific":
            return self.ent_specific_tills.get().strip()
        return ""
