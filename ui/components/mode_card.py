"""
ui/components/mode_card.py
Operations card matching the clean white UI:
Tab 1: Version & File Check
  - Side-by-side subpanels:
    1. Till Config (Offset .112+) [Cyan accent]
       All fields empty by default
    2. Back Office Config (Offset .12) [Purple accent]
       All fields empty by default
Tab 2: Terminal Console
  - Header: terminal:~# with [Tills] [BO] [Both] target selectors
  - Preset chips: uptime, reboot time, health url, logs, ps jre, dotnet, modify config
  - In-place dark Linux terminal screen (#0A0E17)
  - show_inspection() method for double-click row inspection without popups
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
import ui.theme as theme

# Quick shortcut aliases: mapping keyword triggers to multi-command batch sequences
SHORTCUT_KEYWORDS = {
    "quick health": 'uptime; echo "--- Memory (free -h) ---"; free -h; echo "--- Boot Time (who -b) ---"; who -b; echo "--- Last Reboots ---"; last reboot | head -n 5; echo "--- Disk Space (df -h) ---"; df -h /',
    "diagnostics": 'uptime; echo "--- Memory (free -h) ---"; free -h; echo "--- Boot Time (who -b) ---"; who -b; echo "--- Last Reboots ---"; last reboot | head -n 5; echo "--- Disk Space (df -h) ---"; df -h /',
    "reboot info": "uptime; who -b; last reboot | head -n 5",
    "sysinfo": "uname -a; uptime; free -h; df -h /",
}


class ModeCard(tk.Frame):
    def __init__(
        self,
        parent,
        on_terminal_execute: Optional[Callable[[str, str], None]] = None,
        on_fields_changed: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=12, pady=10)
        self.on_terminal_execute = on_terminal_execute
        self.on_fields_changed = on_fields_changed
        self.active_tab = "version_war"
        self.terminal_target = "tills"  # "tills", "bo", or "both"

        self._build_widgets()

    def _build_widgets(self):
        # Tab Header Bar
        tab_bar = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        tab_bar.pack(fill=tk.X, pady=(0, 8))

        self.btn_tab_vcheck = tk.Button(
            tab_bar, text="Version & File Check", font=theme.FONT_BODY_BOLD,
            bg=theme.COLOR_PRIMARY, fg="white", activebackground=theme.COLOR_PRIMARY_HOVER, activeforeground="white",
            relief="flat", padx=14, pady=4, cursor="hand2", command=lambda: self._select_tab("version_war")
        )
        self.btn_tab_vcheck.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_tab_term = tk.Button(
            tab_bar, text="Terminal Console", font=theme.FONT_BODY_BOLD,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, activebackground="#E2E8F0", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=14, pady=4, cursor="hand2", command=lambda: self._select_tab("terminal")
        )
        self.btn_tab_term.pack(side=tk.LEFT)

        # Content Containers
        self.container_vcheck = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        self.container_vcheck.pack(fill=tk.BOTH, expand=True)

        self.container_term = tk.Frame(self, bg=theme.COLOR_CARD_BG)

        # ====================================================================
        # Tab 1: Version & File Check Subpanels
        # ====================================================================
        grid_v = tk.Frame(self.container_vcheck, bg=theme.COLOR_CARD_BG)
        grid_v.pack(fill=tk.BOTH, expand=True)
        grid_v.columnconfigure(0, weight=1)
        grid_v.columnconfigure(1, weight=1)

        # Left Subpanel: Tills
        till_box = tk.Frame(grid_v, bg=theme.COLOR_SUBPANEL_BG, highlightbackground="#BAE6FD", highlightthickness=1, padx=10, pady=8)
        till_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tk.Label(till_box, text="Tills", font=theme.FONT_BODY_BOLD, fg=theme.COLOR_CYAN, bg=theme.COLOR_SUBPANEL_BG).pack(anchor="w", pady=(0, 6))

        tb_r1 = tk.Frame(till_box, bg=theme.COLOR_SUBPANEL_BG)
        tb_r1.pack(fill=tk.X, pady=2)
        tk.Label(tb_r1, text="File Path:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=7, anchor="w").pack(side=tk.LEFT)
        self.ent_till_war = tk.Entry(tb_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat")
        self.ent_till_war.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 6))

        tk.Label(tb_r1, text="Size:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_till_size = tk.Entry(tb_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=10)
        self.ent_till_size.pack(side=tk.LEFT, padx=(4, 0))

        tb_r2 = tk.Frame(till_box, bg=theme.COLOR_SUBPANEL_BG)
        tb_r2.pack(fill=tk.X, pady=2)
        tk.Label(tb_r2, text="Prop Path:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=7, anchor="w").pack(side=tk.LEFT)
        self.ent_till_prop = tk.Entry(tb_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat")
        self.ent_till_prop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 6))

        tk.Label(tb_r2, text="Variable:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_till_var = tk.Entry(tb_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=9)
        self.ent_till_var.pack(side=tk.LEFT, padx=(4, 6))

        tk.Label(tb_r2, text="Value:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_till_val = tk.Entry(tb_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=8)
        self.ent_till_val.pack(side=tk.LEFT, padx=(4, 0))

        # Right Subpanel: BO
        bo_box = tk.Frame(grid_v, bg=theme.COLOR_SUBPANEL_BG, highlightbackground="#E9D5FF", highlightthickness=1, padx=10, pady=8)
        bo_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        tk.Label(bo_box, text="BO", font=theme.FONT_BODY_BOLD, fg=theme.COLOR_PURPLE, bg=theme.COLOR_SUBPANEL_BG).pack(anchor="w", pady=(0, 6))

        bo_r1 = tk.Frame(bo_box, bg=theme.COLOR_SUBPANEL_BG)
        bo_r1.pack(fill=tk.X, pady=2)
        tk.Label(bo_r1, text="File Path:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=7, anchor="w").pack(side=tk.LEFT)
        self.ent_bo_war = tk.Entry(bo_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat")
        self.ent_bo_war.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 6))

        tk.Label(bo_r1, text="Size:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_bo_size = tk.Entry(bo_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=10)
        self.ent_bo_size.pack(side=tk.LEFT, padx=(4, 0))

        bo_r2 = tk.Frame(bo_box, bg=theme.COLOR_SUBPANEL_BG)
        bo_r2.pack(fill=tk.X, pady=2)
        tk.Label(bo_r2, text="Prop Path:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=7, anchor="w").pack(side=tk.LEFT)
        self.ent_bo_prop = tk.Entry(bo_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat")
        self.ent_bo_prop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 6))

        tk.Label(bo_r2, text="Variable:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_bo_var = tk.Entry(bo_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=9)
        self.ent_bo_var.pack(side=tk.LEFT, padx=(4, 6))

        tk.Label(bo_r2, text="Value:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.ent_bo_val = tk.Entry(bo_r2, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY, insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=8)
        self.ent_bo_val.pack(side=tk.LEFT, padx=(4, 0))

        for entry in [
            self.ent_till_war, self.ent_till_size, self.ent_till_prop, self.ent_till_var, self.ent_till_val,
            self.ent_bo_war, self.ent_bo_size, self.ent_bo_prop, self.ent_bo_var, self.ent_bo_val
        ]:
            entry.bind("<KeyRelease>", self._notify_fields_changed)
            entry.bind("<FocusOut>", self._notify_fields_changed)

        # ====================================================================
        # Tab 2: Terminal Console
        # ====================================================================
        term_hdr = tk.Frame(self.container_term, bg=theme.COLOR_CARD_BG)
        term_hdr.pack(fill=tk.X, pady=(0, 4))

        tk.Label(term_hdr, text="terminal:~#", font=theme.FONT_MONO_BOLD, fg=theme.COLOR_TERMINAL_PROMPT, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT, padx=(0, 10))

        # Target Selector Pills [Tills] [BO] [Both]
        tgt_grp = tk.Frame(term_hdr, bg="#F1F5F9", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1)
        tgt_grp.pack(side=tk.LEFT)

        self.btn_tgt_tills = tk.Button(
            tgt_grp, text="🖥️ Tills", font=theme.FONT_SMALL,
            bg=theme.COLOR_PRIMARY, fg="white", relief="flat", padx=8, pady=2, cursor="hand2", command=lambda: self._set_terminal_target("tills")
        )
        self.btn_tgt_tills.pack(side=tk.LEFT)

        self.btn_tgt_bo = tk.Button(
            tgt_grp, text="🏢 BO", font=theme.FONT_SMALL,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, relief="flat", padx=8, pady=2, cursor="hand2", command=lambda: self._set_terminal_target("bo")
        )
        self.btn_tgt_bo.pack(side=tk.LEFT)

        self.btn_tgt_both = tk.Button(
            tgt_grp, text="Both", font=theme.FONT_SMALL,
            bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY, relief="flat", padx=8, pady=2, cursor="hand2", command=lambda: self._set_terminal_target("both")
        )
        self.btn_tgt_both.pack(side=tk.LEFT)

        # Preset Chips: uptime, reboot time, health url, logs, ps jre, dotnet, system info
        chips_frame = tk.Frame(term_hdr, bg=theme.COLOR_CARD_BG)
        chips_frame.pack(side=tk.RIGHT)

        presets = [
            ("quick health", 'uptime; echo "--- Memory (free -h) ---"; free -h; echo "--- Boot Time (who -b) ---"; who -b; echo "--- Last Reboots ---"; last reboot | head -n 5; echo "--- Disk Space (df -h) ---"; df -h /'),
            ("uptime", "uptime"),
            ("free -h", "free -h"),
            #("reboot time", "who -b"),
            #("last reboot", "last reboot | head -n 5"),
            #("health url", "wget http://localhost:8080/health"),
            ("ps jre", "ps -ef | grep jre"),
            #("dotnet", "dotnet --info"),
            #("logs", "tail -n 20 /var/log/syslog"),
            ("date", "date"),
            ("set timeout", 'FILE=""; if grep -q "^SessionTimeout=" "$FILE"; then sed -i \'s/^SessionTimeout=.*/SessionTimeout=700000/\' "$FILE"; else echo "SessionTimeout=700000" >> "$FILE"; fi; grep "^SessionTimeout=" "$FILE"')
        ]
        for label, cmd_str in presets:
            b = tk.Button(
                chips_frame, text=label, font=theme.FONT_SMALL,
                bg="#E2E8F0", fg="#475569", activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
                relief="flat", padx=6, pady=1, cursor="hand2",
                command=lambda c=cmd_str: self._insert_preset_command(c)
            )
            b.pack(side=tk.LEFT, padx=2)

        # Command Input Bar
        c_bar = tk.Frame(self.container_term, bg=theme.COLOR_CARD_BG)
        c_bar.pack(fill=tk.X, pady=(2, 4))

        tk.Label(c_bar, text="terminal:~#", font=theme.FONT_MONO_BOLD, fg=theme.COLOR_TERMINAL_PROMPT, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT, padx=(0, 6))

        self.ent_cmd = tk.Entry(
            c_bar, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat"
        )
        self.ent_cmd.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.ent_cmd.bind("<Return>", lambda e: self._on_execute())

        self.btn_exec = tk.Button(
            c_bar, text="▶ Execute", font=theme.FONT_BODY_BOLD,
            bg=theme.COLOR_PRIMARY, fg="white", activebackground=theme.COLOR_PRIMARY_HOVER, activeforeground="white",
            relief="flat", padx=12, pady=2, cursor="hand2", command=self._on_execute
        )
        self.btn_exec.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear_term = tk.Button(
            c_bar, text="🗑 Clear", font=theme.FONT_BODY,
            bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY, activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=8, pady=2, cursor="hand2", command=self.clear_console
        )
        self.btn_clear_term.pack(side=tk.LEFT)

        # Linux Terminal Console Screen
        self.txt_term = tk.Text(
            self.container_term, height=6, bg=theme.COLOR_TERMINAL_BG, fg=theme.COLOR_TERMINAL_FG,
            font=theme.FONT_MONO, insertbackground="white", relief="flat", highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1
        )
        self.txt_term.pack(fill=tk.BOTH, expand=True)
        self.txt_term.insert("1.0", "[terminal:~#] Linux in-place inspection console ready. Double-click any result row to view output.\n")
        self.txt_term.config(state="disabled")

    def _select_tab(self, tab_id: str):
        self.active_tab = tab_id
        if tab_id == "version_war":
            self.btn_tab_vcheck.config(bg=theme.COLOR_PRIMARY, fg="white")
            self.btn_tab_term.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)
            self.container_term.pack_forget()
            self.container_vcheck.pack(fill=tk.BOTH, expand=True)
        else:
            self.btn_tab_term.config(bg=theme.COLOR_PRIMARY, fg="white")
            self.btn_tab_vcheck.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)
            self.container_vcheck.pack_forget()
            self.container_term.pack(fill=tk.BOTH, expand=True)
        self._notify_fields_changed()

    def _notify_fields_changed(self, event=None):
        if self.on_fields_changed:
            self.on_fields_changed()

    def _set_terminal_target(self, tgt: str):
        self.terminal_target = tgt
        btns = [("tills", self.btn_tgt_tills), ("bo", self.btn_tgt_bo), ("both", self.btn_tgt_both)]
        for t, btn in btns:
            if t == tgt:
                btn.config(bg=theme.COLOR_PRIMARY, fg="white")
            else:
                btn.config(bg="#F1F5F9", fg=theme.COLOR_TEXT_SECONDARY)

    def _insert_preset_command(self, cmd_str: str):
        self.ent_cmd.delete(0, tk.END)
        self.ent_cmd.insert(0, cmd_str)

    def _on_execute(self):
        raw_cmd = self.ent_cmd.get().strip()
        if not raw_cmd:
            return
        cmd = SHORTCUT_KEYWORDS.get(raw_cmd.lower(), raw_cmd)
        if self.on_terminal_execute:
            self.on_terminal_execute(cmd, self.terminal_target)

    def show_inspection(self, target_name: str, ip: str, status: str, full_output: str, command: Optional[str] = None):
        """Switches to Terminal Console tab and prints the double-clicked row details without popups (Section 7.3)."""
        def _do_inspect():
            self._select_tab("terminal")
            self.txt_term.config(state="normal")
            self.txt_term.insert(tk.END, f"\n{'='*75}\n")
            self.txt_term.insert(tk.END, f"[INSPECTION] Target: {target_name} ({ip})  |  Status: {status}\n")
            if command:
                self.txt_term.insert(tk.END, f"[COMMAND] terminal:~# {command}\n")
            self.txt_term.insert(tk.END, f"{'-'*75}\n")
            self.txt_term.insert(tk.END, f"{full_output.strip()}\n")
            self.txt_term.see(tk.END)
            self.txt_term.config(state="disabled")
        try:
            self.after(0, _do_inspect)
        except Exception:
            _do_inspect()

    def print_terminal_line(self, line: str):
        def _do_print():
            self.txt_term.config(state="normal")
            self.txt_term.insert(tk.END, f"{line}\n")
            self.txt_term.see(tk.END)
            self.txt_term.config(state="disabled")
        try:
            self.after(0, _do_print)
        except Exception:
            _do_print()

    def clear_console(self):
        def _do_clear():
            self.txt_term.config(state="normal")
            self.txt_term.delete("1.0", tk.END)
            self.txt_term.insert("1.0", "[terminal:~#] Console cleared.\n")
            self.txt_term.config(state="disabled")
        try:
            self.after(0, _do_clear)
        except Exception:
            _do_clear()

    def has_size_check(self, include_tills: Optional[bool] = None, include_bo: Optional[bool] = None) -> bool:
        """True if user filled expected size or file path in active target config (Till or BO)."""
        check_tills = include_tills if include_tills is not None else True
        check_bo = include_bo if include_bo is not None else True

        if not check_tills and not check_bo:
            check_tills = True
            check_bo = True

        s1 = bool(self.ent_till_size.get().strip() or self.ent_till_war.get().strip()) if check_tills else False
        s2 = bool(self.ent_bo_size.get().strip() or self.ent_bo_war.get().strip()) if check_bo else False
        return bool(s1 or s2)

    def has_version_check(self, include_tills: Optional[bool] = None, include_bo: Optional[bool] = None) -> bool:
        """True if user filled variable, value, or prop path in active target config."""
        check_tills = include_tills if include_tills is not None else True
        check_bo = include_bo if include_bo is not None else True

        if not check_tills and not check_bo:
            check_tills = True
            check_bo = True

        v1 = bool(self.ent_till_val.get().strip() or self.ent_till_var.get().strip() or self.ent_till_prop.get().strip()) if check_tills else False
        v2 = bool(self.ent_bo_val.get().strip() or self.ent_bo_var.get().strip() or self.ent_bo_prop.get().strip()) if check_bo else False
        return bool(v1 or v2)

    def get_mode_params(self) -> dict:
        return {
            "operation_mode": self.active_tab,
            "till_war_path": self.ent_till_war.get().strip(),
            "till_war_expected_size": self.ent_till_size.get().strip(),
            "till_prop_path": self.ent_till_prop.get().strip(),
            "till_prop_variable": self.ent_till_var.get().strip(),
            "till_expected_val": self.ent_till_val.get().strip(),
            "bo_war_path": self.ent_bo_war.get().strip(),
            "bo_war_expected_size": self.ent_bo_size.get().strip(),
            "bo_prop_path": self.ent_bo_prop.get().strip(),
            "bo_prop_variable": self.ent_bo_var.get().strip(),
            "bo_expected_val": self.ent_bo_val.get().strip(),
            "custom_command": self.ent_cmd.get().strip(),
            "cmd_expected_output": ""
        }
