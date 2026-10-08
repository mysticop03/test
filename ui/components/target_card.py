"""
ui/components/target_card.py
1. Target Scope card matching the clean white UI:
- Segmented toggle buttons [Single Store] [Bulk File]
- Line 1: Store IP [ ]  Code: [ ]  Tills: [ ] (all empty by default)
- Line 2: Till Mode: [All Tills] [Specific] [UAT (Direct IP)]
- Bulk view: File browse, paste dialog, Parallel Stores (1-10)
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Callable, Optional
from models.target import StoreRecord
from storage.store_reader import load_stores_from_file, parse_stores_from_text
import ui.theme as theme

class TargetCard(tk.Frame):
    def __init__(self, parent, on_stores_changed: Optional[Callable[[List[StoreRecord]], None]] = None):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        self.on_stores_changed = on_stores_changed
        self.bulk_stores: List[StoreRecord] = []
        self.pasted_raw_text: str = ""
        self.target_mode = "single"  # "single" or "bulk"
        self.till_mode = "all"       # "all", "specific", or "uat"

        self._build_widgets()

    def _build_widgets(self):
        # Header Row
        hdr_row = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        hdr_row.pack(fill=tk.X, pady=(0, 8))

        lbl_title = tk.Label(hdr_row, text="1. Target Scope", font=theme.FONT_SUBTITLE, fg=theme.COLOR_TEXT_PRIMARY, bg=theme.COLOR_CARD_BG)
        lbl_title.pack(side=tk.LEFT)

        # Segmented Toggle [Single Store] [Bulk File] on right
        btn_grp = tk.Frame(hdr_row, bg="#F1F5F9", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        btn_grp.pack(side=tk.RIGHT)

        self.btn_single = tk.Button(
            btn_grp, text="Single Store", font=theme.FONT_SMALL,
            bg=theme.COLOR_PRIMARY, fg="white", activebackground=theme.COLOR_PRIMARY_HOVER, activeforeground="white",
            relief="flat", padx=10, pady=2, cursor="hand2", command=lambda: self._set_target_mode("single")
        )
        self.btn_single.pack(side=tk.LEFT)

        self.btn_bulk = tk.Button(
            btn_grp, text="Bulk File", font=theme.FONT_SMALL,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, activebackground="#E2E8F0", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=10, pady=2, cursor="hand2", command=lambda: self._set_target_mode("bulk")
        )
        self.btn_bulk.pack(side=tk.LEFT)

        # Container for Single Store
        self.single_container = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        self.single_container.pack(fill=tk.X)

        # Line 1: Store IP | Code | Tills (All initialized completely empty)
        r1 = tk.Frame(self.single_container, bg=theme.COLOR_CARD_BG)
        r1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(r1, text="Store IP:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT)
        self.ent_ip = tk.Entry(r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
                               insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=17)
        self.ent_ip.pack(side=tk.LEFT, padx=(6, 14))

        tk.Label(r1, text="Code:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT)
        self.ent_store_code = tk.Entry(r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
                                       insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=11)
        self.ent_store_code.pack(side=tk.LEFT, padx=(6, 14))

        # Tills count box (hidden in UAT mode since UAT targets a single machine)
        self.tills_box = tk.Frame(r1, bg=theme.COLOR_CARD_BG)
        self.tills_box.pack(side=tk.LEFT)

        self.lbl_tills = tk.Label(self.tills_box, text="Tills:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG)
        self.lbl_tills.pack(side=tk.LEFT)
        self.ent_tills = tk.Entry(self.tills_box, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
                                  insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=5)
        self.ent_tills.pack(side=tk.LEFT, padx=(6, 0))

        def validate_till_count(event=None):
            val = self.ent_tills.get().strip()
            if val:
                if not val.isdigit() or int(val) < 1:
                    self.ent_tills.delete(0, tk.END)
                    self.ent_tills.insert(0, "1")
                elif int(val) > 10:
                    self.ent_tills.delete(0, tk.END)
                    self.ent_tills.insert(0, "10")

        self.ent_tills.bind("<FocusOut>", validate_till_count)

        # Line 2: Till Mode: [All Tills] [Specific] [UAT (Direct IP)]
        r2 = tk.Frame(self.single_container, bg=theme.COLOR_CARD_BG)
        r2.pack(fill=tk.X)

        tk.Label(r2, text="Till Mode:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT, padx=(0, 6))

        mode_grp = tk.Frame(r2, bg="#F1F5F9", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        mode_grp.pack(side=tk.LEFT)

        self.btn_tm_all = tk.Button(
            mode_grp, text="All Tills", font=theme.FONT_SMALL,
            bg=theme.COLOR_PRIMARY, fg="white", relief="flat", padx=10, pady=3, cursor="hand2",
            command=lambda: self._set_till_mode("all")
        )
        self.btn_tm_all.pack(side=tk.LEFT)

        self.btn_tm_spec = tk.Button(
            mode_grp, text="Specific", font=theme.FONT_SMALL,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, relief="flat", padx=10, pady=3, cursor="hand2",
            command=lambda: self._set_till_mode("specific")
        )
        self.btn_tm_spec.pack(side=tk.LEFT)

        self.btn_tm_uat = tk.Button(
            mode_grp, text="UAT", font=theme.FONT_SMALL,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, relief="flat", padx=10, pady=3, cursor="hand2",
            command=lambda: self._set_till_mode("uat")
        )
        self.btn_tm_uat.pack(side=tk.LEFT)

        # Specific Tills Input (empty by default)
        self.ent_specific_tills = tk.Entry(
            r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=12
        )

        # Container for Bulk File
        self.bulk_container = tk.Frame(self, bg=theme.COLOR_CARD_BG)

        b_r1 = tk.Frame(self.bulk_container, bg=theme.COLOR_CARD_BG)
        b_r1.pack(fill=tk.X, pady=(0, 6))

        self.btn_browse = tk.Button(
            b_r1, text="📂 Browse File (.csv, .xlsx)", font=theme.FONT_BODY,
            bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY, activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=12, pady=4, cursor="hand2", command=self._browse_bulk_file
        )
        self.btn_browse.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_paste = tk.Button(
            b_r1, text="📋 Paste List", font=theme.FONT_BODY,
            bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY, activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=12, pady=4, cursor="hand2", command=self._open_paste_dialog
        )
        self.btn_paste.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear_bulk = tk.Button(
            b_r1, text="🗑️ Clear", font=theme.FONT_BODY,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, activebackground="#FEE2E2", activeforeground="#DC2626",
            relief="flat", padx=10, pady=4, cursor="hand2", command=self._clear_bulk_stores
        )
        self.btn_clear_bulk.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(b_r1, text="Batch Size:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT)
        self.ent_parallel = tk.Entry(
            b_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=4
        )
        self.ent_parallel.insert(0, "1")
        self.ent_parallel.pack(side=tk.LEFT, padx=(6, 0))

        def _validate_batch_input(proposed):
            if proposed == "":
                return True
            if proposed.isdigit():
                val = int(proposed)
                return 1 <= val <= 10
            return False

        vcmd = (b_r1.register(_validate_batch_input), "%P")
        self.ent_parallel = tk.Entry(
            b_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=4,
            validate="key", validatecommand=vcmd
        )
        self.ent_parallel.insert(0, "1")
        self.ent_parallel.pack(side=tk.LEFT, padx=(6, 0))

        def _clamp_batch_on_focus_out(event=None):
            val = self.ent_parallel.get().strip()
            if not val.isdigit() or int(val) < 1:
                self.ent_parallel.delete(0, tk.END)
                self.ent_parallel.insert(0, "1")
            elif int(val) > 10:
                self.ent_parallel.delete(0, tk.END)
                self.ent_parallel.insert(0, "10")

        self.ent_parallel.bind("<FocusOut>", _clamp_batch_on_focus_out)

        self.lbl_bulk_status = tk.Label(
            self.bulk_container, text="",
            font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_MUTED, bg=theme.COLOR_CARD_BG
        )
        self.lbl_bulk_status.pack(anchor="w")

    def _clear_bulk_stores(self):
        """Clears loaded bulk stores and in-memory paste list."""
        self.bulk_stores = []
        self.pasted_raw_text = ""
        self.lbl_bulk_status.config(text="")
        if self.on_stores_changed:
            self.on_stores_changed([])

    def _set_target_mode(self, mode: str):
        self.target_mode = mode
        if mode == "single":
            self.btn_single.config(bg=theme.COLOR_PRIMARY, fg="white")
            self.btn_bulk.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)
            self.bulk_container.pack_forget()
            self.single_container.pack(fill=tk.X)
        else:
            self.btn_bulk.config(bg=theme.COLOR_PRIMARY, fg="white")
            self.btn_single.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)
            self.single_container.pack_forget()
            self.bulk_container.pack(fill=tk.X)

    def _set_till_mode(self, mode: str):
        self.till_mode = mode
        btns = [
            ("all", self.btn_tm_all),
            ("specific", self.btn_tm_spec),
            ("uat", self.btn_tm_uat)
        ]
        for m, btn in btns:
            if m == mode:
                btn.config(bg=theme.COLOR_PRIMARY, fg="white")
            else:
                btn.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)

        if mode == "uat":
            self.tills_box.pack_forget()
            self.ent_specific_tills.pack_forget()
        elif mode == "specific":
            self.tills_box.pack_forget()
            self.ent_specific_tills.pack(side=tk.LEFT, padx=(8, 0))
        else:  # "all"
            if not self.tills_box.winfo_ismapped():
                self.tills_box.pack(side=tk.LEFT)
            self.ent_specific_tills.pack_forget()

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
                    fg=theme.COLOR_SUCCESS
                )
                if self.on_stores_changed:
                    self.on_stores_changed(self.bulk_stores)
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to load file: {e}")

    def _open_paste_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Paste Store List")
        dialog.geometry("620x420")
        dialog.configure(bg=theme.COLOR_BG)
        dialog.transient(self)

        top_info = tk.Frame(dialog, bg=theme.COLOR_BG)
        top_info.pack(fill=tk.X, padx=14, pady=(8, 4))
        tk.Label(
            top_info, text="Paste Store IP, Till Count & Specific Tills (CSV/TSV):",
            font=theme.FONT_SUBTITLE, fg=theme.COLOR_TEXT_PRIMARY, bg=theme.COLOR_BG
        ).pack(anchor="w")
        tk.Label(
            top_info,
            text="Standard format: Store Code, IP, Till Count, Specific Tills\n"
                 "• If Specific Tills is empty, checks all tills (e.g. 8 or 12 tills).\n"
                 "• If Specific Tills is given (e.g. 1;3;5), checks only those specific tills.",
            font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_BG, justify="left"
        ).pack(anchor="w", pady=(2, 0))

        # Bottom Button Bar packed FIRST with side=tk.BOTTOM so it is ALWAYS visible inside the box
        btn_row = tk.Frame(dialog, bg=theme.COLOR_BG)
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=10)

        txt = tk.Text(
            dialog, wrap="none", font=theme.FONT_MONO,
            bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", relief="flat",
            highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 4))

        # Only saved text persists in self.pasted_raw_text until closure of app or Clear is clicked
        if self.pasted_raw_text:
            txt.insert("1.0", self.pasted_raw_text)
        else:
            template_text = (
                "Store Code,IP,Till Count,Specific Tills\n"
                "Store-001,10.14.22.12,12,\n"
                "Store-002,10.14.23.12,8,1;3;5\n"
            )
            txt.insert("1.0", template_text)
            txt.tag_add("sel", "2.0", "end")

        def save_paste():
            """Saves pasted stores into memory until app closure or Clear is clicked."""
            content = txt.get("1.0", tk.END).strip()
            if not content:
                self._clear_bulk_stores()
                dialog.destroy()
                return

            try:
                stores = parse_stores_from_text(content)
                if stores:
                    self.bulk_stores = stores
                    self.pasted_raw_text = content  # Persists until closure or clear
                    self.lbl_bulk_status.config(
                        text=f"✓ Loaded {len(stores)} pasted stores",
                        fg=theme.COLOR_SUCCESS
                    )
                    dialog.destroy()
                    if self.on_stores_changed:
                        self.on_stores_changed(self.bulk_stores)
                else:
                    messagebox.showwarning("Parse Error", "Could not parse store records. Please check the format.")
            except Exception as e:
                messagebox.showerror("Parse Error", f"Error parsing store list: {e}")

        def cancel_paste():
            """Cancels dialog without saving changes. Unsaved text is discarded."""
            dialog.destroy()

        def clear_paste_dialog():
            """Clears both text area and saved store list."""
            txt.delete("1.0", tk.END)
            self._clear_bulk_stores()

        # Buttons packed directly in the bottom box:
        tk.Button(
            btn_row, text="💾 Save", bg=theme.COLOR_PRIMARY, fg="white",
            activebackground=theme.COLOR_PRIMARY_HOVER, activeforeground="white",
            relief="flat", padx=16, pady=6, font=theme.FONT_BUTTON, cursor="hand2", command=save_paste
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            btn_row, text="Cancel", bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY,
            activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=14, pady=6, font=theme.FONT_BODY, cursor="hand2", command=cancel_paste
        ).pack(side=tk.RIGHT)

        tk.Button(
            btn_row, text="🗑️ Clear", bg="#FEE2E2", fg="#DC2626",
            activebackground="#FECACA", activeforeground="#DC2626",
            relief="flat", padx=14, pady=6, font=theme.FONT_BODY, cursor="hand2", command=clear_paste_dialog
        ).pack(side=tk.LEFT)

    def get_configured_stores(self) -> List[StoreRecord]:
        if self.target_mode == "bulk" and self.bulk_stores:
            return list(self.bulk_stores)

        code = self.ent_store_code.get().strip() or "Store-001"
        ip = self.ent_ip.get().strip()
        tills_str = self.ent_tills.get().strip()
        till_count = int(tills_str) if tills_str.isdigit() else 10
        till_count = max(1, min(10, till_count))
        is_uat = (self.till_mode == "uat")
        if is_uat:
            till_count = 1
        spec_str = self.ent_specific_tills.get().strip() if self.till_mode == "specific" else ""

        return [StoreRecord(
            store_code=code,
            subnet_or_ip=ip,
            till_count=till_count,
            specific_tills=spec_str,
            is_uat=is_uat
        )]

    def get_parallel_stores(self) -> int:
        if self.target_mode == "bulk":
            val = self.ent_parallel.get().strip()
            if val.isdigit():
                return max(1, min(10, int(val)))
            return 1
        return 1

    get_batch_size = get_parallel_stores

    def get_specific_tills_string(self) -> str:
        if self.till_mode == "specific":
            return self.ent_specific_tills.get().strip()
        return ""
