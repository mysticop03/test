"""
ui/theme.py
Clean White / Light Design System Tokens for Ubuntu POS Auditor UI.
Crisp white cards, slate backgrounds, refined borders, and clear status badges.
"""
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 12, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 10, "bold")
FONT_BODY = (FONT_FAMILY, 9)
FONT_BODY_BOLD = (FONT_FAMILY, 9, "bold")
FONT_BUTTON = (FONT_FAMILY, 9, "bold")
FONT_SMALL = (FONT_FAMILY, 8)
FONT_MONO = ("Consolas", 9)
FONT_MONO_BOLD = ("Consolas", 9, "bold")

# Clean White / Light Theme Palette
COLOR_BG = "#F1F5F9"             # Soft slate 100 canvas
COLOR_CARD_BG = "#FFFFFF"        # Pure white card containers
COLOR_CARD_BORDER = "#CBD5E1"   # Slate 300 clean border
COLOR_SUBPANEL_BG = "#F8FAFC"    # Slate 50 nested subpanels
COLOR_INPUT_BG = "#FFFFFF"       # White input background
COLOR_INPUT_BORDER = "#CBD5E1"   # Slate 300 input border
COLOR_HEADER_BG = "#0F172A"      # Deep Navy header banner

COLOR_TEXT_PRIMARY = "#0F172A"   # Deep slate 900 primary text
COLOR_TEXT_SECONDARY = "#475569" # Slate 600 secondary text
COLOR_TEXT_MUTED = "#94A3B8"     # Slate 400 hint text

COLOR_PRIMARY = "#2563EB"        # Royal Blue 600
COLOR_PRIMARY_HOVER = "#1D4ED8"
COLOR_CYAN = "#0284C7"           # Sky/Cyan 600 (Till accent)
COLOR_PURPLE = "#7E22CE"         # Purple 700 (Back Office accent)

# KPI & Status Badges
COLOR_SUCCESS = "#059669"        # Emerald 600
COLOR_MISMATCH = "#D97706"       # Amber 600
COLOR_MISS = "#7C3AED"           # Purple 600
COLOR_OFFLINE = "#DC2626"        # Red 600
COLOR_BLOCKED = "#E11D48"        # Rose 600

COLOR_TERMINAL_BG = "#0A0E17"    # Dark Linux console screen
COLOR_TERMINAL_FG = "#38BDF8"    # Sky blue text
COLOR_TERMINAL_PROMPT = "#10B981"# Green terminal prompt

TAG_CONFIG = {
    "Success": {"bg": "#DCFCE7", "fg": "#14532D"},
    "Mismatch": {"bg": "#FEF3C7", "fg": "#78350F"},
    "Miss": {"bg": "#F3E8FF", "fg": "#581C87"},
    "Offline": {"bg": "#F1F5F9", "fg": "#334155"},
    "Blocked": {"bg": "#FFE4E6", "fg": "#881337"},
    # Backward compatibility
    "SUCCESS": {"bg": "#DCFCE7", "fg": "#14532D"},
    "SIZE_MISMATCH": {"bg": "#FEF3C7", "fg": "#78350F"},
    "VERSION_MISMATCH": {"bg": "#FFEDD5", "fg": "#7C2D12"},
    "BOTH_MISMATCH": {"bg": "#FEE2E2", "fg": "#7F1D1D"},
    "FILE_MISSING": {"bg": "#F3E8FF", "fg": "#581C87"},
    "OFFLINE": {"bg": "#F1F5F9", "fg": "#334155"},
    "TIMEOUT": {"bg": "#F1F5F9", "fg": "#334155"},
    "BLOCKED_COMMAND": {"bg": "#FFE4E6", "fg": "#881337"}
}
