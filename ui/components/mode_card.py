"""
ui/components/mode_card.py
3. Operations tabbed selector.
Tolerance is removed from GUI and maintained cleanly in backend config.json!
"""
import tkinter as tk
from tkinter import ttk
import ui.theme as theme

class ModeCard(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text=" 3. Operations ", padding=(8, 4))
        self._build_widgets()

    def _build_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.X, expand=True)

        # Tab 1: Version & WAR Check
        self.tab1 = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab1, text="Version Check")

        t1_r1 = ttk.Frame(self.tab1)
        t1_r1.pack(fill=tk.X, pady=2)
        ttk.Label(t1_r1, text="File Path:").pack(side=tk.LEFT)
        self.ent_war_path = ttk.Entry(t1_r1, width=38)
        self.ent_war_path.insert(0, "/home/posuser/ETPSuite/ETPStoreFrontV5.5/app.war")
        self.ent_war_path.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(t1_r1, text="Expected Size:").pack(side=tk.LEFT)
        self.ent_war_bytes = ttk.Entry(t1_r1, width=16)
        self.ent_war_bytes.insert(0, "184.5 MB")
        self.ent_war_bytes.pack(side=tk.LEFT, padx=(4, 8))

        t1_r2 = ttk.Frame(self.tab1)
        t1_r2.pack(fill=tk.X, pady=2)
        ttk.Label(t1_r2, text="Prop Path:").pack(side=tk.LEFT)
        self.ent_prop_path = ttk.Entry(t1_r2, width=38)
        self.ent_prop_path.insert(0, "/home/posuser/ETPSuite/ETPStoreFrontV5.5/config/ETPLanguage_en_US.properties")
        self.ent_prop_path.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(t1_r2, text="Keyword:").pack(side=tk.LEFT)
        self.ent_keyword = ttk.Entry(t1_r2, width=14)
        self.ent_keyword.insert(0, "TS00046")
        self.ent_keyword.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(t1_r2, text="Expected Ver:").pack(side=tk.LEFT)
        self.ent_exp_version = ttk.Entry(t1_r2, width=18)
        self.ent_exp_version.insert(0, "81")
        self.ent_exp_version.pack(side=tk.LEFT, padx=(4, 0))

        # Tab 2: File Info Only
        self.tab2 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab2, text="  📄  File Info Only  ")

        t2_r = ttk.Frame(self.tab2)
        t2_r.pack(fill=tk.X, pady=4)
        ttk.Label(t2_r, text="Target File Path:").pack(side=tk.LEFT)
        self.ent_file_info_path = ttk.Entry(t2_r, width=48)
        self.ent_file_info_path.insert(0, "/home/posuser/ETPSuite/ETPStoreFrontV5.5/app.war")
        self.ent_file_info_path.pack(side=tk.LEFT, padx=(6, 12))
        ttk.Label(t2_r, text="Probes exact size in bytes, human MB, and modification timestamp.", font=theme.FONT_SMALL, foreground=theme.COLOR_TEXT_SECONDARY).pack(side=tk.LEFT)

        # Tab 3: Command Execution
        self.tab3 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab3, text="  ⚡  Execute Command  ")

        t3_r = ttk.Frame(self.tab3)
        t3_r.pack(fill=tk.X, pady=4)
        ttk.Label(t3_r, text="Command:").pack(side=tk.LEFT)
        self.ent_cmd = ttk.Entry(t3_r, width=45)
        self.ent_cmd.insert(0, "uptime")
        self.ent_cmd.pack(side=tk.LEFT, padx=(6, 16))

        ttk.Label(t3_r, text="Expected Text (Opt):").pack(side=tk.LEFT)
        self.ent_cmd_exp = ttk.Entry(t3_r, width=22)
        self.ent_cmd_exp.pack(side=tk.LEFT, padx=(6, 12))

    def get_mode_params(self) -> dict:
        selected_idx = self.notebook.index(self.notebook.select())
        mode_names = ["version_war", "file_info", "command"]
        current_mode = mode_names[selected_idx]

        war_input_str = self.ent_war_bytes.get().strip()

        return {
            "operation_mode": current_mode,
            "war_path": self.ent_war_path.get().strip(),
            "war_expected_size_input": war_input_str,
            "war_expected_size_bytes": war_input_str,
            "properties_path": self.ent_prop_path.get().strip(),
            "properties_keyword": self.ent_keyword.get().strip(),
            "expected_delivery_version": self.ent_exp_version.get().strip(),
            "file_info_path": self.ent_file_info_path.get().strip(),
            "custom_command": self.ent_cmd.get().strip(),
            "cmd_expected_output": self.ent_cmd_exp.get().strip()
        }
