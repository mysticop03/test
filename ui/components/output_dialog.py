"""
ui/components/output_dialog.py
Dedicated floating inspection output window for Ubuntu POS Store Inspector.
Triggered on double-clicking any result row in the audit results grid.
Displays complete, untruncated output, device metadata, status badge, and copy utilities.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional
import ui.theme as theme
from models.result import AuditResult


class OutputDisplayDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, result: AuditResult, command: Optional[str] = None):
        super().__init__(parent)
        self.parent = parent
        self.result = result
        self.command = command or result.extra.get("custom_command") or result.extra.get("url")

        # Window Setup
        dev_title = result.till_name if result.till_name.startswith(("BO", "Till")) else f"{'BO' if result.is_bo else 'Till'} {result.till_name}"
        self.title(f"Inspection Output — {dev_title} ({result.ip})")
        self.geometry("820x600")
        self.minsize(640, 420)
        self.configure(bg=theme.COLOR_BG)

        # Center over parent
        self._center_window(820, 600)

        # Keep on top of main window & bind Escape to close
        self.transient(parent)
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        self.focus_set()

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = max(10, px + (pw - width) // 2)
            y = max(10, py + (ph - height) // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            self.geometry(f"{width}x{height}")

    def _build_ui(self):
        # 1. Top Header Banner (Deep Slate / Navy)
        hdr = tk.Frame(self, bg=theme.COLOR_HEADER_BG, padx=16, pady=12)
        hdr.pack(fill=tk.X)

        # Left Header: Target Details
        left_box = tk.Frame(hdr, bg=theme.COLOR_HEADER_BG)
        left_box.pack(side=tk.LEFT, fill=tk.Y)

        dev_prefix = "BO: " if self.result.is_bo else "Till: "
        title_lbl = tk.Label(
            left_box,
            text=f"{dev_prefix}{self.result.till_name}",
            font=(theme.FONT_FAMILY, 13, "bold"),
            fg="#FFFFFF",
            bg=theme.COLOR_HEADER_BG
        )
        title_lbl.pack(anchor="w")

        meta_line = tk.Frame(left_box, bg=theme.COLOR_HEADER_BG)
        meta_line.pack(anchor="w", pady=(3, 0))

        # Store badge
        tk.Label(
            meta_line,
            text=f"Store: {self.result.store_code}",
            font=theme.FONT_SMALL,
            fg="#94A3B8",
            bg=theme.COLOR_HEADER_BG
        ).pack(side=tk.LEFT, padx=(0, 10))

        # IP badge
        tk.Label(
            meta_line,
            text=f"IP: {self.result.ip}",
            font=(theme.FONT_FAMILY, 8, "bold"),
            fg="#E2E8F0",
            bg=theme.COLOR_HEADER_BG
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Latency badge
        lat_text = f"⏱ {self.result.latency_ms} ms" if self.result.latency_ms > 0 else "⏱ Offline"
        tk.Label(
            meta_line,
            text=lat_text,
            font=theme.FONT_SMALL,
            fg="#38BDF8",
            bg=theme.COLOR_HEADER_BG
        ).pack(side=tk.LEFT)

        # Right Header: Status Pill
        right_box = tk.Frame(hdr, bg=theme.COLOR_HEADER_BG)
        right_box.pack(side=tk.RIGHT, fill=tk.Y)

        cfg = theme.TAG_CONFIG.get(self.result.status, {"bg": "#E2E8F0", "fg": "#0F172A"})
        status_pill = tk.Label(
            right_box,
            text=f"  {self.result.status.upper()}  ",
            font=(theme.FONT_FAMILY, 10, "bold"),
            bg=cfg["bg"],
            fg=cfg["fg"],
            padx=10,
            pady=4,
            relief="flat"
        )
        status_pill.pack(anchor="e")

        # 2. Command / Mode Info Bar
        info_bar = tk.Frame(self, bg="#FFFFFF", padx=16, pady=8, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        info_bar.pack(fill=tk.X)

        if self.command:
            tk.Label(info_bar, text="terminal:~#", font=theme.FONT_MONO_BOLD, fg=theme.COLOR_TERMINAL_PROMPT, bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 6))
            cmd_ent = tk.Entry(info_bar, font=theme.FONT_MONO, fg=theme.COLOR_TEXT_PRIMARY, bg="#F8FAFC", relief="flat", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1)
            cmd_ent.insert(0, str(self.command))
            cmd_ent.config(state="readonly")
            cmd_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

            btn_copy_cmd = tk.Button(
                info_bar,
                text="Copy Cmd",
                font=theme.FONT_SMALL,
                bg="#F1F5F9",
                fg=theme.COLOR_TEXT_SECONDARY,
                relief="flat",
                padx=6,
                pady=1,
                cursor="hand2",
                command=lambda: self._copy_to_clipboard(str(self.command), btn_copy_cmd, "Copy Cmd")
            )
            btn_copy_cmd.pack(side=tk.LEFT)
        else:
            # Mode 1: WAR / Version check summary
            parts = []
            if self.result.war_size and self.result.war_size != "-":
                parts.append(f"Size: {self.result.war_size}")
            if self.result.war_modified and self.result.war_modified != "-":
                parts.append(f"Modified: {self.result.war_modified}")
            if self.result.delivery_version and self.result.delivery_version != "-":
                parts.append(f"Version: {self.result.delivery_version}")
            elif self.result.prop_variable and self.result.prop_variable != "-":
                parts.append(f"Variable: {self.result.prop_variable}")

            summary_text = " | ".join(parts) if parts else "Audit inspection details"
            tk.Label(
                info_bar,
                text=summary_text,
                font=theme.FONT_BODY,
                fg=theme.COLOR_TEXT_SECONDARY,
                bg="#FFFFFF"
            ).pack(side=tk.LEFT)

        # 3. Main Console Output Screen
        content_frame = tk.Frame(self, bg=theme.COLOR_BG, padx=16, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Header above console
        screen_hdr = tk.Frame(content_frame, bg=theme.COLOR_BG)
        screen_hdr.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            screen_hdr,
            text="COMMAND / PROBE OUTPUT",
            font=(theme.FONT_FAMILY, 8, "bold"),
            fg=theme.COLOR_TEXT_SECONDARY,
            bg=theme.COLOR_BG
        ).pack(side=tk.LEFT)

        full_txt = (self.result.full_output or self.result.preview_output or "(Empty Output)").strip()
        lines_count = len(full_txt.splitlines())
        chars_count = len(full_txt)

        tk.Label(
            screen_hdr,
            text=f"{lines_count} lines  •  {chars_count} chars",
            font=theme.FONT_SMALL,
            fg=theme.COLOR_TEXT_MUTED,
            bg=theme.COLOR_BG
        ).pack(side=tk.RIGHT)

        # Console Text Box with Scrollbars
        txt_box_frame = tk.Frame(content_frame, bg=theme.COLOR_TERMINAL_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        txt_box_frame.pack(fill=tk.BOTH, expand=True)

        v_scroll = tk.Scrollbar(txt_box_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(txt_box_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.txt_output = tk.Text(
            txt_box_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            bg=theme.COLOR_TERMINAL_BG,
            fg="#E2E8F0",
            insertbackground="#FFFFFF",
            selectbackground="#2563EB",
            selectforeground="#FFFFFF",
            relief="flat",
            padx=10,
            pady=8,
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True)
        v_scroll.config(command=self.txt_output.yview)
        h_scroll.config(command=self.txt_output.xview)

        # Populate output
        self.txt_output.insert("1.0", full_txt)
        self.txt_output.config(state="disabled")

        # 4. Bottom Footer Toolbar
        footer = tk.Frame(self, bg="#FFFFFF", padx=16, pady=10, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        footer.pack(fill=tk.X)

        tk.Label(
            footer,
            text="Press Esc to close window",
            font=theme.FONT_SMALL,
            fg=theme.COLOR_TEXT_MUTED,
            bg="#FFFFFF"
        ).pack(side=tk.LEFT)

        btn_close = tk.Button(
            footer,
            text="✕ Close",
            font=theme.FONT_BODY,
            bg="#E2E8F0",
            fg=theme.COLOR_TEXT_PRIMARY,
            activebackground="#CBD5E1",
            activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(side=tk.RIGHT, padx=(8, 0))

        self.btn_copy_all = tk.Button(
            footer,
            text="📋 Copy Output",
            font=theme.FONT_BODY_BOLD,
            bg=theme.COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=theme.COLOR_PRIMARY_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=lambda: self._copy_to_clipboard(full_txt, self.btn_copy_all, "📋 Copy Output")
        )
        self.btn_copy_all.pack(side=tk.RIGHT)

    def _copy_to_clipboard(self, text: str, btn: tk.Button, orig_text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        btn.config(text="✓ Copied!")
        self.after(1800, lambda: btn.config(text=orig_text))
