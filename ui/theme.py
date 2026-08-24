"""
Centralized dark, minimalist theme. All colors and the global
stylesheet live here so the rest of the UI code never hardcodes hex
values inline.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat

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

# -- QCalendarWidget popup helper ---------------------------------------
#
# QDateEdit's calendar popup is a QCalendarWidget whose weekday header
# row (Mon, Tue, Wed...) is painted using QTextCharFormat objects set
# via setWeekdayTextFormat(), not through the normal QSS cascade. That
# means the app-wide STYLESHEET above (and any per-widget setStyleSheet
# call) can style the calendar's grid, nav bar, and selected-day cell,
# but it can never reach that header row's text color - it stays at
# whatever the OS/Qt default is, which on a dark background often ends
# up unreadable against the row's own background.
#
# Fix: set the QTextCharFormat objects directly on the QCalendarWidget
# instance, in addition to a QSS pass for the rest of the popup.
# Call this once on every QCalendarWidget the app creates (e.g.
# `date_edit.calendarWidget()` right after constructing a QDateEdit
# with setCalendarPopup(True)).

CALENDAR_POPUP_STYLESHEET = f"""
QCalendarWidget QWidget {{
    background-color: {BG_SURFACE};
    alternate-background-color: {BG_SURFACE};
}}

QCalendarWidget QToolButton {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 13px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: {BG_SURFACE_ALT};
}}

QCalendarWidget QMenu {{
    background-color: {BG_SURFACE_ALT};
    color: {TEXT_PRIMARY};
}}

QCalendarWidget QSpinBox {{
    background-color: {BG_SURFACE_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}

QCalendarWidget QAbstractItemView:enabled {{
    color: {TEXT_PRIMARY};
    background-color: {BG_SURFACE};
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    outline: none;
}}

QCalendarWidget QAbstractItemView:disabled {{
    color: {TEXT_MUTED};
}}
"""


def style_calendar_popup(calendar_widget) -> None:
    """Apply the app's dark theme to a QCalendarWidget popup (e.g. the
    one behind a QDateEdit with setCalendarPopup(True)), including the
    weekday header row that QSS alone cannot reach.

    Usage:
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        style_calendar_popup(self.date_input.calendarWidget())
    """
    if calendar_widget is None:
        return

    weekday_format = QTextCharFormat()
    weekday_format.setForeground(QColor(TEXT_SECONDARY))
    weekday_format.setBackground(QColor(BG_SURFACE))

    weekend_format = QTextCharFormat()
    weekend_format.setForeground(QColor(TEXT_SECONDARY))
    weekend_format.setBackground(QColor(BG_SURFACE))

    for day in (
        Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday,
    ):
        calendar_widget.setWeekdayTextFormat(day, weekday_format)
    for day in (Qt.Saturday, Qt.Sunday):
        calendar_widget.setWeekdayTextFormat(day, weekend_format)

    calendar_widget.setStyleSheet(CALENDAR_POPUP_STYLESHEET)