"""
ui/components/credentials_card.py
SSH Credentials, port, and socket timeout.
Store concurrency is maintained securely in the backend config (capped at 2 stores).
"""
import tkinter as tk
from tkinter import ttk
import ui.theme as theme
from core.config_manager import ConfigManager

class CredentialsCard(ttk.LabelFrame):
    def __init__(self, parent, config_manager=None):
        super().__init__(parent, text=" 2. SSH Settings ", padding=(12, 8))
        self.config_manager = config_manager
        self._build_widgets()

    def _build_widgets(self):
        row = ttk.Frame(self)
        row.pack(fill=tk.X)

        ttk.Label(row, text="Username:").pack(side=tk.LEFT)
        self.ent_user = ttk.Entry(row, width=12)
        def_user = self.config_manager.get("default_username", "posuser") if self.config_manager else "posuser"
        self.ent_user.insert(0, def_user)
        self.ent_user.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(row, text="Password:").pack(side=tk.LEFT)
        self.ent_pass = ttk.Entry(row, width=16, show="*")
        self.ent_pass.pack(side=tk.LEFT, padx=(4, 6))

        self.btn_toggle_pass = ttk.Button(row, text="👁", width=3, command=self._toggle_pass)
        self.btn_toggle_pass.pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(row, text="Port:").pack(side=tk.LEFT)
        self.ent_port = ttk.Entry(row, width=6)
        def_port = str(self.config_manager.get("default_port", 22)) if self.config_manager else "22"
        self.ent_port.insert(0, def_port)
        self.ent_port.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(row, text="Timeout (s):").pack(side=tk.LEFT)
        self.ent_timeout = ttk.Entry(row, width=5)
        def_tout = str(self.config_manager.get("connection_timeout_seconds", 5)) if self.config_manager else "5"
        self.ent_timeout.insert(0, def_tout)
        self.ent_timeout.pack(side=tk.LEFT, padx=(4, 16))

        # ======================================================================
        # Concurrency Spinbox: Commented out from frontend as requested.
        # Maintained securely via backend config.json ("store_concurrency": 2).
        # ======================================================================
        # ttk.Label(row, text="Store Concurrency (Batch):").pack(side=tk.LEFT)
        # self.spn_concurrency = ttk.Spinbox(row, from_=1, to=10, width=4)
        # self.spn_concurrency.set(2)
        # self.spn_concurrency.pack(side=tk.LEFT, padx=(4, 6))
        # ttk.Label(row, text="(Default: 2 stores at once = ~26 tills)", font=theme.FONT_MONO, foreground=theme.COLOR_TEXT_SECONDARY).pack(side=tk.LEFT)

    def _toggle_pass(self):
        if self.ent_pass.cget("show") == "*":
            self.ent_pass.config(show="")
        else:
            self.ent_pass.config(show="*")

    def get_credentials(self) -> dict:
        t_str = self.ent_timeout.get().strip()
        timeout = int(t_str) if t_str.isdigit() else 5
        timeout = max(1, min(30, timeout))

        p_str = self.ent_port.get().strip()
        port = int(p_str) if p_str.isdigit() else 22

        # Concurrency is retrieved from backend config (locked to 2 stores)
        concurrency = int(self.config_manager.get("store_concurrency", 2)) if self.config_manager else 2

        return {
            "username": self.ent_user.get().strip() or "posuser",
            "password": self.ent_pass.get(),
            "port": port,
            "timeout": timeout,
            "store_concurrency": concurrency
        }
