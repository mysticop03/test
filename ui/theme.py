"""
ui/theme.py
Visual design system tokens: modern enterprise palette, typography, status badges, and styles.
"""
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 12, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 10, "bold")
FONT_BODY = (FONT_FAMILY, 9)
FONT_BODY_BOLD = (FONT_FAMILY, 9, "bold")
FONT_SMALL = (FONT_FAMILY, 8)
FONT_MONO = ("Consolas", 9)
FONT_MONO_BOLD = ("Consolas", 9, "bold")

# Palette
COLOR_BG = "#F1F5F9"          # Modern Slate 100
COLOR_CARD_BG = "#FFFFFF"     # Pure White
COLOR_BORDER = "#CBD5E1"      # Slate 300
COLOR_HEADER_BG = "#0F172A"   # Deep Navy / Slate 900
COLOR_TEXT_PRIMARY = "#0F172A"# Slate 900
COLOR_TEXT_SECONDARY = "#475569" # Slate 600
COLOR_PRIMARY = "#2563EB"     # Royal Blue 600
COLOR_PRIMARY_HOVER = "#1D4ED8"

# KPI & Status Colors
COLOR_SUCCESS = "#059669"     # Emerald 600
COLOR_SIZE_MISMATCH = "#D97706" # Amber 600
COLOR_VERSION_MISMATCH = "#EA580C" # Orange 600
COLOR_BOTH_MISMATCH = "#DC2626" # Crimson 600
COLOR_FILE_MISSING = "#7C3AED" # Purple 600
COLOR_OFFLINE = "#64748B"      # Slate 500
COLOR_ERROR = "#B91C1C"        # Dark Red

TAG_CONFIG = {
    "SUCCESS": {"bg": "#DCFCE7", "fg": "#14532D"},
    "FOUND": {"bg": "#DCFCE7", "fg": "#14532D"},
    "SIZE_MISMATCH": {"bg": "#FEF3C7", "fg": "#78350F"},
    "VERSION_MISMATCH": {"bg": "#FFEDD5", "fg": "#7C2D12"},
    "BOTH_MISMATCH": {"bg": "#FEE2E2", "fg": "#7F1D1D"},
    "FILE_MISSING": {"bg": "#F3E8FF", "fg": "#581C87"},
    "OFFLINE": {"bg": "#F1F5F9", "fg": "#334155"},
    "TIMEOUT": {"bg": "#F1F5F9", "fg": "#334155"},
    "AUTH_FAIL": {"bg": "#FEE2E2", "fg": "#7F1D1D"},
    "ERROR": {"bg": "#FEE2E2", "fg": "#7F1D1D"},
    "BLOCKED_COMMAND": {"bg": "#FFE4E6", "fg": "#881337"}
}
