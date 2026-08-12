"""
Centralized dark, minimalist theme. All colors and the global
stylesheet live here so the rest of the UI code never hardcodes hex
values inline.
"""

# -- Palette -----------------------------------------------------------
BG_BASE = "#0d0e11"          # app background
BG_SURFACE = "#15171b"       # cards / panels
BG_SURFACE_ALT = "#1b1e23"   # hovered / secondary panels
BORDER = "#262a31"
TEXT_PRIMARY = "#eceef0"
TEXT_SECONDARY = "#9aa0aa"
TEXT_MUTED = "#5d636e"
ACCENT = "#5b8def"           # single accent color, used sparingly
ACCENT_HOVER = "#4a76d1"
ACCENT_MUTED = "#243352"
DANGER = "#e06c75"
SUCCESS = "#7cc48f"
WARNING = "#e0b96c"

FONT_FAMILY = "Segoe UI, -apple-system, sans-serif"

STYLESHEET = f"""
* {{
    font-family: {FONT_FAMILY};
    color: {TEXT_PRIMARY};
    outline: none;
}}

QWidget {{
    background-color: {BG_BASE};
}}

QWidget#Sidebar {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER};
}}

QWidget#Card, QFrame#Card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLabel {{
    background: transparent;
}}

QLabel#Title {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel#Subtitle {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QLabel#SectionHeader {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
}}

QLabel#TimerDisplay {{
    font-size: 96px;
    font-weight: 200;
    color: {TEXT_PRIMARY};
}}

QLabel#StatValue {{
    font-size: 26px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel#StatLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
}}

QPushButton {{
    background-color: {BG_SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QPushButton:hover {{
    background-color: #21252c;
    border: 1px solid #33383f;
}}

QPushButton:pressed {{
    background-color: #191c21;
}}

QPushButton#Primary {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}

QPushButton#Primary:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#Danger {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}

QPushButton#Danger:hover {{
    background-color: rgba(224, 108, 117, 0.12);
}}

QPushButton#NavButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QPushButton#NavButton:hover {{
    background-color: {BG_SURFACE_ALT};
    color: {TEXT_PRIMARY};
}}

QPushButton#NavButtonActive {{
    background-color: {ACCENT_MUTED};
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    color: {ACCENT};
}}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{
    background-color: {BG_SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QListWidget, QTreeWidget, QTableWidget {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QProgressBar {{
    background-color: {BG_SURFACE_ALT};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}

QCheckBox {{
    font-size: 13px;
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QDialog {{
    background-color: {BG_SURFACE};
}}
"""
