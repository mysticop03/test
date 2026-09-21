"""
ui/components/metrics_bar.py
Modern KPI Dashboard card with action buttons and live progress indicators.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from models.result import AuditSummary
import ui.theme as theme

class MetricsBar(ttk.Frame):
    def __init__(
        self,
        parent,
        on_start: Optional[Callable[[], None]] = None,
        on_pause_resume: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, padding=(0, 4))
        self.on_start = on_start
        self.on_pause_resume = on_pause_resume
        self.on_stop = on_stop

        self._build_widgets()

    def _build_widgets(self):
        # Top Bar: Action Buttons, Progress, Timer
        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 4))

        self.btn_start = tk.Button(
            top, text=" ▶  Start Audit ", command=self.on_start,
            bg="#2563EB", fg="white", font=theme.FONT_BODY_BOLD,
            relief="flat", padx=14, pady=4, cursor="hand2"
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_pause = tk.Button(
            top, text=" ⏸ Pause ", command=self.on_pause_resume,
            bg="#E2E8F0", fg="#334155", font=theme.FONT_BODY_BOLD,
            relief="flat", padx=10, pady=4, state="disabled"
        )
        self.btn_pause.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = tk.Button(
            top, text=" ⏹ Stop ", command=self.on_stop,
            bg="#FEE2E2", fg="#991B1B", font=theme.FONT_BODY_BOLD,
            relief="flat", padx=10, pady=4, state="disabled"
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 12))

        self.progress_bar = ttk.Progressbar(top, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        self.lbl_clock = ttk.Label(top, text="⏱ 00:00", font=theme.FONT_MONO_BOLD)
        self.lbl_clock.pack(side=tk.RIGHT)

        # Bottom Bar: Clean KPI Badge Cards
        kpi_frame = tk.Frame(self, bg=theme.COLOR_CARD_BG, relief="solid", bd=1)
        kpi_frame.pack(fill=tk.X, pady=2)

        def make_kpi(parent, label, default_val, fg_color):
            f = tk.Frame(parent, bg=theme.COLOR_CARD_BG, padx=12, pady=4)
            f.pack(side=tk.LEFT, fill=tk.Y)
            l1 = tk.Label(f, text=label, font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG)
            l1.pack(anchor="w")
            l2 = tk.Label(f, text=default_val, font=theme.FONT_SUBTITLE, fg=fg_color, bg=theme.COLOR_CARD_BG)
            l2.pack(anchor="w")
            return l2

        self.kpi_total = make_kpi(kpi_frame, "PROGRESS", "0 / 0", theme.COLOR_TEXT_PRIMARY)
        self.kpi_success = make_kpi(kpi_frame, "SUCCESS", "0", theme.COLOR_SUCCESS)
        self.kpi_size_mismatch = make_kpi(kpi_frame, "SIZE MISMATCH", "0", theme.COLOR_SIZE_MISMATCH)
        self.kpi_ver_mismatch = make_kpi(kpi_frame, "VER MISMATCH", "0", theme.COLOR_VERSION_MISMATCH)
        self.kpi_both_mismatch = make_kpi(kpi_frame, "BOTH MISMATCH", "0", theme.COLOR_BOTH_MISMATCH)
        self.kpi_missing = make_kpi(kpi_frame, "MISSING", "0", theme.COLOR_FILE_MISSING)
        self.kpi_offline = make_kpi(kpi_frame, "OFFLINE", "0", theme.COLOR_OFFLINE)

        # Pass Rate card on right
        f_rate = tk.Frame(kpi_frame, bg=theme.COLOR_CARD_BG, padx=14, pady=4)
        f_rate.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(f_rate, text="PASS RATE", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG).pack(anchor="e")
        self.kpi_pass_rate = tk.Label(f_rate, text="0.0%", font=theme.FONT_SUBTITLE, fg=theme.COLOR_PRIMARY, bg=theme.COLOR_CARD_BG)
        self.kpi_pass_rate.pack(anchor="e")

    def update_summary(self, summary: AuditSummary):
        total = summary.total_tills
        done = summary.completed_tills

        pct = (done / total * 100) if total > 0 else 0
        self.progress_bar["value"] = pct

        self.kpi_total.config(text=f"{done} / {total}")
        self.kpi_success.config(text=str(summary.success_count))
        self.kpi_size_mismatch.config(text=str(summary.size_mismatch_count))
        self.kpi_ver_mismatch.config(text=str(summary.version_mismatch_count))
        self.kpi_both_mismatch.config(text=str(summary.both_mismatch_count))
        self.kpi_missing.config(text=str(summary.missing_count))
        self.kpi_offline.config(text=str(summary.offline_count))
        self.kpi_pass_rate.config(text=f"{summary.pass_rate_percent}%")

    def set_running_state(self, running: bool):
        if running:
            self.btn_start.config(state="disabled", bg="#94A3B8")
            self.btn_pause.config(state="normal", text=" ⏸ Pause ", bg="#E2E8F0")
            self.btn_stop.config(state="normal", bg="#FEE2E2")
        else:
            self.btn_start.config(state="normal", bg="#2563EB")
            self.btn_pause.config(state="disabled", text=" ⏸ Pause ")
            self.btn_stop.config(state="disabled")
