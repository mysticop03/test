"""
ui/components/metrics_bar.py
Modern White / Light Mode KPI Action & Stats Bar:
- Left: [▶ Start Audit] [⏸ Pause] [⏹ Stop]
- Middle: PROGRESS: 0 / 0 + progress bar underneath
- Right: TIME ⏱ 00:00 | SUCCESS 0 | MISMATCH 0 | MISSING 0 | OFFLINE 0 | PASS RATE 0.0%
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from models.result import AuditSummary
import ui.theme as theme

class MetricsBar(tk.Frame):
    def __init__(
        self,
        parent,
        on_start: Optional[Callable[[], None]] = None,
        on_pause_resume: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, bg=theme.COLOR_CARD_BG, highlightbackground=theme.COLOR_CARD_BORDER, highlightthickness=1, padx=14, pady=8)
        self.on_start = on_start
        self.on_pause_resume = on_pause_resume
        self.on_stop = on_stop

        self._build_widgets()

    def _build_widgets(self):
        # Left Side: Action Buttons
        left_grp = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        left_grp.pack(side=tk.LEFT, padx=(0, 16))

        self.btn_start = tk.Button(
            left_grp, text="▶ Start Audit", font=theme.FONT_BODY_BOLD,
            bg=theme.COLOR_PRIMARY, fg="white", activebackground=theme.COLOR_PRIMARY_HOVER, activeforeground="white",
            relief="flat", padx=14, pady=5, cursor="hand2", command=self.on_start
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_pause = tk.Button(
            left_grp, text="⏸ Pause", font=theme.FONT_BODY_BOLD,
            bg="#E2E8F0", fg="#475569", activebackground="#CBD5E1", activeforeground=theme.COLOR_TEXT_PRIMARY,
            relief="flat", padx=10, pady=5, state="disabled", command=self.on_pause_resume
        )
        self.btn_pause.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = tk.Button(
            left_grp, text="⏹ Stop", font=theme.FONT_BODY_BOLD,
            bg="#FEE2E2", fg="#991B1B", activebackground="#FECACA", activeforeground="#991B1B",
            relief="flat", padx=10, pady=5, state="disabled", command=self.on_stop
        )
        self.btn_stop.pack(side=tk.LEFT)

        # Middle: Progress Label + Progress Bar
        mid_grp = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        mid_grp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))

        self.lbl_progress_txt = tk.Label(
            mid_grp, text="PROGRESS: 0 / 0", font=theme.FONT_SMALL,
            fg=theme.COLOR_TEXT_SECONDARY, bg=theme.COLOR_CARD_BG, anchor="w"
        )
        self.lbl_progress_txt.pack(fill=tk.X)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Light.Horizontal.TProgressbar", background=theme.COLOR_PRIMARY, troughcolor="#E2E8F0", bordercolor="#CBD5E1", lightcolor=theme.COLOR_PRIMARY, darkcolor=theme.COLOR_PRIMARY)

        self.progress_bar = ttk.Progressbar(mid_grp, orient="horizontal", mode="determinate", style="Light.Horizontal.TProgressbar", length=140)
        self.progress_bar.pack(fill=tk.X, pady=(2, 0))

        # Right Side: KPI Counters
        kpi_grp = tk.Frame(self, bg=theme.COLOR_CARD_BG)
        kpi_grp.pack(side=tk.RIGHT)

        def make_kpi(parent, title, fg_val):
            col = tk.Frame(parent, bg=theme.COLOR_CARD_BG, padx=8)
            col.pack(side=tk.LEFT)
            tk.Label(col, text=title, font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_MUTED, bg=theme.COLOR_CARD_BG).pack(anchor="center")
            lbl_val = tk.Label(col, text="0", font=theme.FONT_BODY_BOLD, fg=fg_val, bg=theme.COLOR_CARD_BG)
            lbl_val.pack(anchor="center")
            return lbl_val

        # Clock
        col_clk = tk.Frame(kpi_grp, bg=theme.COLOR_CARD_BG, padx=8)
        col_clk.pack(side=tk.LEFT)
        tk.Label(col_clk, text="TIME", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_MUTED, bg=theme.COLOR_CARD_BG).pack(anchor="center")
        self.lbl_clock = tk.Label(col_clk, text="⏱ 00:00", font=theme.FONT_MONO_BOLD, fg=theme.COLOR_TEXT_PRIMARY, bg=theme.COLOR_CARD_BG)
        self.lbl_clock.pack(anchor="center")

        self.kpi_success = make_kpi(kpi_grp, "SUCCESS", theme.COLOR_SUCCESS)
        self.kpi_mismatch = make_kpi(kpi_grp, "MISMATCH", theme.COLOR_MISMATCH)
        self.kpi_missing = make_kpi(kpi_grp, "MISSING", theme.COLOR_MISS)
        self.kpi_offline = make_kpi(kpi_grp, "OFFLINE", theme.COLOR_OFFLINE)

        # Pass Rate
        col_pr = tk.Frame(kpi_grp, bg=theme.COLOR_CARD_BG, padx=8)
        col_pr.pack(side=tk.LEFT)
        tk.Label(col_pr, text="PASS RATE", font=theme.FONT_SMALL, fg=theme.COLOR_TEXT_MUTED, bg=theme.COLOR_CARD_BG).pack(anchor="center")
        self.kpi_pass_rate = tk.Label(col_pr, text="0.0%", font=theme.FONT_BODY_BOLD, fg=theme.COLOR_PRIMARY, bg=theme.COLOR_CARD_BG)
        self.kpi_pass_rate.pack(anchor="center")

    def set_running_state(self, is_running: bool):
        if is_running:
            self.btn_start.config(state="disabled", bg="#E2E8F0", fg="#94A3B8")
            self.btn_pause.config(state="normal", bg="#E2E8F0", fg="#0F172A", cursor="hand2")
            self.btn_stop.config(state="normal", bg="#FEE2E2", fg="#991B1B", cursor="hand2")
        else:
            self.btn_start.config(state="normal", bg=theme.COLOR_PRIMARY, fg="white", cursor="hand2")
            self.btn_pause.config(state="disabled", bg="#E2E8F0", fg="#94A3B8", text="⏸ Pause", cursor="arrow")
            self.btn_stop.config(state="disabled", bg="#FEE2E2", fg="#991B1B", cursor="arrow")

    def update_summary(self, summary: AuditSummary):
        total = summary.total_tills
        done = summary.completed_tills
        pct = (done / total * 100) if total > 0 else 0
        self.progress_bar["value"] = pct

        self.lbl_progress_txt.config(text=f"PROGRESS: {done} / {total}")
        self.kpi_success.config(text=str(summary.success_count))
        self.kpi_mismatch.config(text=str(summary.mismatch_count))
        self.kpi_missing.config(text=str(summary.missing_count))
        self.kpi_offline.config(text=str(summary.offline_count))
        self.kpi_pass_rate.config(text=f"{summary.pass_rate_percent}%")
