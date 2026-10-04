"""
ui/components/credentials_card.py
2. SSH Credentials card matching the clean white UI:
- Timeout defaults to 5 (only field with default per user instruction)
- Till (POS) and Back Office (BO) username/password fields initialized empty
- Dynamic activation: status badge reacts to credential presence.
- Infers targeting: Till only, BO only, or Both.
"""
import tkinter as tk
from typing import Optional, Callable
import ui.theme as theme

class CredentialsCard(tk.Frame):
    def __init__(self, parent, config_manager=None, on_credentials_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=10)
        self.config_manager = config_manager
        self.on_credentials_changed = on_credentials_changed
        self._build_widgets()

    def _build_widgets(self):
        # Header Row
        hdr_row = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        hdr_row.pack(fill=tk.X, pady=(0, 8))

        lbl_title = tk.Label(hdr_row, text="2. SSH Credentials", font=theme.FONT_SUBTITLE, fg=theme.COLOR_TEXT_PRIMARY, bg=theme.COLOR_CARD_BG)
        lbl_title.pack(side=tk.LEFT)

        # Timeout on right: Timeout: [ 5 ] s
        t_frame = tk.Frame(hdr_row, bg=theme.COLOR_CARD_BG)
        t_frame.pack(side=tk.RIGHT)

        tk.Label(t_frame, text="Timeout:", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT)
        self.ent_timeout = tk.Entry(
            t_frame, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat", width=4
        )
        self.ent_timeout.insert(0, "5")
        self.ent_timeout.pack(side=tk.LEFT, padx=(4, 4))
        tk.Label(t_frame, text="s", font=theme.FONT_BODY, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(side=tk.LEFT)

        # Subcards container (Side-by-Side: Tills on Left, BO on Right)
        sub_grid = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        sub_grid.pack(fill=tk.BOTH, expand=True)
        sub_grid.columnconfigure(0, weight=1)
        sub_grid.columnconfigure(1, weight=1)

        # ----------------- Subcard 1: Tills -----------------
        self.till_frame = tk.Frame(sub_grid, bg=theme.COLOR_SUBPANEL_BG, highlightbackground="#BAE6FD", highlightthickness=1, padx=10, pady=8)
        self.till_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        t_hdr = tk.Frame(self.till_frame, bg=theme.COLOR_SUBPANEL_BG)
        t_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(t_hdr, text="Tills", font=theme.FONT_BODY_BOLD, fg=theme.COLOR_CYAN, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.badge_till = tk.Label(t_hdr, text="IDLE", font=theme.FONT_SMALL, fg="#64748B", bg="#F1F5F9", padx=6, pady=1)
        self.badge_till.pack(side=tk.RIGHT)

        t_r1 = tk.Frame(self.till_frame, bg=theme.COLOR_SUBPANEL_BG)
        t_r1.pack(fill=tk.X, pady=2)
        tk.Label(t_r1, text="User:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=5, anchor="w").pack(side=tk.LEFT)
        self.ent_till_user = tk.Entry(
            t_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat"
        )
        self.ent_till_user.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_till_user.bind("<KeyRelease>", lambda e: self._update_active_badges())

        t_r2 = tk.Frame(self.till_frame, bg=theme.COLOR_SUBPANEL_BG)
        t_r2.pack(fill=tk.X, pady=2)
        tk.Label(t_r2, text="Pass:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=5, anchor="w").pack(side=tk.LEFT)
        self.ent_till_pass = tk.Entry(
            t_r2, show="•", font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat"
        )
        self.ent_till_pass.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_till_pass.bind("<KeyRelease>", lambda e: self._update_active_badges())
        self.ent_till_pass.bind("<FocusOut>", lambda e: self._update_active_badges())

        self.btn_eye_till = tk.Button(t_r2, text="👁", font=theme.FONT_SMALL, bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY,
                                      activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY, relief="flat", padx=4, command=lambda: self._toggle_show(self.ent_till_pass))
        self.btn_eye_till.pack(side=tk.LEFT, padx=(4, 0))

        # ----------------- Subcard 2: BO -----------------
        self.bo_frame = tk.Frame(sub_grid, bg=theme.COLOR_SUBPANEL_BG, highlightbackground="#E9D5FF", highlightthickness=1, padx=10, pady=8)
        self.bo_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        bo_hdr = tk.Frame(self.bo_frame, bg=theme.COLOR_SUBPANEL_BG)
        bo_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(bo_hdr, text="BO", font=theme.FONT_BODY_BOLD, fg=theme.COLOR_PURPLE, bg=theme.COLOR_SUBPANEL_BG).pack(side=tk.LEFT)
        self.badge_bo = tk.Label(bo_hdr, text="IDLE", font=theme.FONT_SMALL, fg="#64748B", bg="#F1F5F9", padx=6, pady=1)
        self.badge_bo.pack(side=tk.RIGHT)

        bo_r1 = tk.Frame(self.bo_frame, bg=theme.COLOR_SUBPANEL_BG)
        bo_r1.pack(fill=tk.X, pady=2)
        tk.Label(bo_r1, text="User:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=5, anchor="w").pack(side=tk.LEFT)
        self.ent_bo_user = tk.Entry(
            bo_r1, font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat"
        )
        self.ent_bo_user.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_bo_user.bind("<KeyRelease>", lambda e: self._update_active_badges())

        bo_r2 = tk.Frame(self.bo_frame, bg=theme.COLOR_SUBPANEL_BG)
        bo_r2.pack(fill=tk.X, pady=2)
        tk.Label(bo_r2, text="Pass:", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_SUBPANEL_BG, width=5, anchor="w").pack(side=tk.LEFT)
        self.ent_bo_pass = tk.Entry(
            bo_r2, show="•", font=theme.FONT_MONO, bg=theme.COLOR_INPUT_BG, fg=theme.COLOR_TEXT_PRIMARY,
            insertbackground="#0F172A", highlightbackground=theme.COLOR_INPUT_BORDER, highlightthickness=1, relief="flat"
        )
        self.ent_bo_pass.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_bo_pass.bind("<KeyRelease>", lambda e: self._update_active_badges())
        self.ent_bo_pass.bind("<FocusOut>", lambda e: self._update_active_badges())

        self.btn_eye_bo = tk.Button(bo_r2, text="👁", font=theme.FONT_SMALL, bg="#E2E8F0", fg=theme.COLOR_TEXT_PRIMARY,
                                    activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY, relief="flat", padx=4, command=lambda: self._toggle_show(self.ent_bo_pass))
        self.btn_eye_bo.pack(side=tk.LEFT, padx=(4, 0))

        self._update_active_badges(notify=False)

    def _toggle_show(self, entry: tk.Entry):
        if entry.cget("show") == "":
            entry.config(show="•")
        else:
            entry.config(show="")

    def _update_active_badges(self, notify: bool = True):
        # Active ONLY when password is entered per user instruction
        till_active = bool(self.ent_till_pass.get().strip())
        bo_active = bool(self.ent_bo_pass.get().strip())

        if till_active:
            self.badge_till.config(text="ACTIVE", fg="#166534", bg="#DCFCE7")
        else:
            self.badge_till.config(text="IDLE", fg="#64748B", bg="#F1F5F9")

        if bo_active:
            self.badge_bo.config(text="ACTIVE", fg="#166534", bg="#DCFCE7")
        else:
            self.badge_bo.config(text="IDLE", fg="#64748B", bg="#F1F5F9")

        if notify and self.on_credentials_changed:
            self.on_credentials_changed()

    def get_credentials(self) -> dict:
        t_str = self.ent_timeout.get().strip()
        timeout = int(t_str) if t_str.isdigit() else 5
        timeout = max(1, min(30, timeout))

        till_user = self.ent_till_user.get().strip()
        till_pass = self.ent_till_pass.get()

        bo_user = self.ent_bo_user.get().strip()
        bo_pass = self.ent_bo_pass.get()

        # Dynamic Credential-Driven Targeting:
        # Check Tills only if Till password filled, BO only if BO password filled, both if both filled
        has_till = bool(till_pass.strip())
        has_bo = bool(bo_pass.strip())

        if has_till and not has_bo:
            include_tills = True
            include_bo = False
        elif has_bo and not has_till:
            include_tills = False
            include_bo = True
        elif has_till and has_bo:
            include_tills = True
            include_bo = True
        else:
            include_tills = False
            include_bo = False

        return {
            "till_username": till_user,
            "till_password": till_pass,
            "bo_username": bo_user,
            "bo_password": bo_pass,
            "timeout": timeout,
            "include_tills": include_tills,
            "include_bo": include_bo,
            # For backward compatibility
            "username": till_user if include_tills else bo_user,
            "password": till_pass if include_tills else bo_pass
        }
