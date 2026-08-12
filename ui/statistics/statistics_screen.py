"""
StatisticsScreen: displays today's session statistics. All aggregation
lives in SessionRepository.today_summary() (reached via the existing
SessionManager.today_summary() wrapper) and SessionRepository.list_for_day()
for the raw session list - this screen only formats and displays that
data. It computes no new statistics of its own.
"""

from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QListWidget,
    QListWidgetItem,
)

from core.session_manager import SessionManager


class StatisticsScreen(QWidget):
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel("Statistics")
        title.setObjectName("Title")
        subtitle = QLabel(date.today().strftime("%A, %d %B"))
        subtitle.setObjectName("Subtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # -- Today's summary card ------------------------------------
        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 16, 20, 16)
        summary_layout.setSpacing(10)
        summary_layout.addWidget(self._section_header("TODAY'S SUMMARY"))

        self.focused_label = self._stat_row(summary_layout, "Focused time")
        self.total_actual_label = self._stat_row(summary_layout, "Total time logged")
        self.session_count_label = self._stat_row(summary_layout, "Sessions started")
        self.completed_label = self._stat_row(summary_layout, "Sessions completed")
        self.longest_label = self._stat_row(summary_layout, "Longest session")

        outer.addWidget(summary_card)

        # -- Today's sessions card ------------------------------------
        sessions_card = QFrame()
        sessions_card.setObjectName("Card")
        sessions_layout = QVBoxLayout(sessions_card)
        sessions_layout.setContentsMargins(20, 16, 20, 16)
        sessions_layout.setSpacing(10)
        sessions_layout.addWidget(self._section_header("TODAY'S SESSIONS"))

        self.sessions_list = QListWidget()
        self.sessions_list.setFrameShape(QFrame.NoFrame)
        sessions_layout.addWidget(self.sessions_list)

        outer.addWidget(sessions_card, 1)

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    def _stat_row(self, layout: QVBoxLayout, label_text: str) -> QLabel:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        value = QLabel("—")
        value.setStyleSheet("font-size: 13px; font-weight: 600;")
        row.addWidget(label)
        row.addStretch()
        row.addWidget(value)
        layout.addLayout(row)
        return value

    # -- Data -----------------------------------------------------------

    def refresh(self) -> None:
        self._refresh_summary()
        self._refresh_sessions_list()

    def _refresh_summary(self) -> None:
        summary = self.session_manager.today_summary()
        self.focused_label.setText(self._format_minutes(summary.get("focused_minutes", 0) or 0))
        self.total_actual_label.setText(self._format_minutes(summary.get("total_actual", 0) or 0))
        self.session_count_label.setText(str(summary.get("session_count", 0) or 0))
        self.completed_label.setText(str(summary.get("completed_count", 0) or 0))
        self.longest_label.setText(self._format_minutes(summary.get("longest_session", 0) or 0))

    def _refresh_sessions_list(self) -> None:
        self.sessions_list.clear()
        sessions = self.session_manager.session_repo.list_for_day(date.today())

        if not sessions:
            item = QListWidgetItem("No sessions recorded today yet.")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.sessions_list.addItem(item)
            return

        for session in sessions:
            started = self._format_time(session.started_at)
            task_label = f"Task #{session.task_id}" if session.task_id else "No specific task"
            actual = self._format_minutes(session.actual_minutes or 0)
            item = QListWidgetItem(
                f"{started}    {task_label}    ·  {actual} / {session.planned_minutes}m planned  ·  {session.status}"
            )
            self.sessions_list.addItem(item)

    # -- Formatting helpers -----------------------------------------------

    @staticmethod
    def _format_minutes(minutes: float) -> str:
        minutes = int(round(minutes))
        hours, mins = divmod(minutes, 60)
        if hours:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @staticmethod
    def _format_time(iso_timestamp: str) -> str:
        if not iso_timestamp:
            return "—"
        try:
            return datetime.fromisoformat(iso_timestamp).strftime("%H:%M")
        except ValueError:
            return iso_timestamp
