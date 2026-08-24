"""
ScheduleScreen: lets the user define a manual availability window and
see the Scheduler's suggested work/break blocks for it. All scheduling
logic (chunking tasks, inserting breaks, computing leftover buffer)
lives in core.scheduler.Scheduler - this screen only collects input
(window + focus/break lengths), calls Scheduler.generate(), and renders
the resulting ScheduleBlock list. No calendar integration and no new
scheduling algorithm are implemented here.
"""

from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QSpinBox, QTimeEdit, QDateEdit,
)

from core.task_manager import TaskManager
from core.onboarding_manager import OnboardingManager
from core.scheduler import Scheduler, SchedulerInput, SchedulerResult, BusyInterval
from ui.theme import style_calendar_popup


_KIND_STYLE = {
    "TASK": ("Focus", "#5b8def"),
    "BREAK": ("Break", "#e0b96c"),
    "BUFFER": ("Free / unscheduled", "#5d636e"),
    "BUSY": ("Unavailable", "#e06c75"),
}


class ScheduleScreen(QWidget):
    def __init__(self, task_manager: TaskManager, scheduler: Scheduler, onboarding_manager: OnboardingManager):
        super().__init__()
        self.task_manager = task_manager
        self.scheduler = scheduler
        self.onboarding_manager = onboarding_manager
        self.last_result: SchedulerResult | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel("Schedule")
        title.setObjectName("Title")
        subtitle = QLabel("Plan today's available time into work and break blocks.")
        subtitle.setObjectName("Subtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # Read the saved onboarding preferences once, at construction
        # time, to seed the availability window (wake/sleep time) and
        # focus/break length defaults below. This is a one-shot read
        # for initial values only - nothing in this screen ever writes
        # back to OnboardingManager, so a user changing these controls
        # for one generated schedule never touches the saved preference.
        preferences = self.onboarding_manager.get_preferences()

        input_card = QFrame()
        input_card.setObjectName("Card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 16, 20, 16)
        input_layout.setSpacing(12)
        input_layout.addWidget(self._section_header("AVAILABILITY"))

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_row.addWidget(QLabel("Date"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dddd, d MMMM yyyy")
        self.date_input.setDate(QDate.currentDate())
        # The calendar popup's weekday header row (Mon/Tue/...) is
        # painted via QTextCharFormat, not QSS, so it doesn't pick up
        # the app-wide stylesheet on its own - style it explicitly.
        style_calendar_popup(self.date_input.calendarWidget())
        date_row.addWidget(self.date_input)
        date_row.addStretch()
        input_layout.addLayout(date_row)

        window_row = QHBoxLayout()
        window_row.setSpacing(10)

        window_row.addWidget(QLabel("From"))
        self.start_input = QTimeEdit()
        self.start_input.setDisplayFormat("HH:mm")
        # Defaults to the wake time collected during onboarding rather
        # than the current clock time, since "availability window"
        # means the user's usual day, not "right now".
        self.start_input.setTime(self._parse_time(preferences.wake_time))
        window_row.addWidget(self.start_input)

        window_row.addWidget(QLabel("To"))
        self.end_input = QTimeEdit()
        self.end_input.setDisplayFormat("HH:mm")
        # Defaults to the sleep time collected during onboarding, for
        # the same reason.
        self.end_input.setTime(self._parse_time(preferences.sleep_time))
        window_row.addWidget(self.end_input)

        window_row.addStretch()
        input_layout.addLayout(window_row)

        durations_row = QHBoxLayout()
        durations_row.setSpacing(10)

        durations_row.addWidget(QLabel("Focus length"))
        self.focus_minutes_input = QSpinBox()
        self.focus_minutes_input.setRange(5, 240)
        self.focus_minutes_input.setSingleStep(5)
        self.focus_minutes_input.setValue(preferences.focus_minutes)
        self.focus_minutes_input.setSuffix(" min")
        durations_row.addWidget(self.focus_minutes_input)

        durations_row.addWidget(QLabel("Break length"))
        self.break_minutes_input = QSpinBox()
        self.break_minutes_input.setRange(0, 60)
        self.break_minutes_input.setSingleStep(5)
        self.break_minutes_input.setValue(preferences.break_minutes)
        self.break_minutes_input.setSuffix(" min")
        durations_row.addWidget(self.break_minutes_input)

        durations_row.addStretch()
        input_layout.addLayout(durations_row)

        self.pending_tasks_label = QLabel("—")
        self.pending_tasks_label.setStyleSheet("color: #9aa0aa; font-size: 12px;")
        input_layout.addWidget(self.pending_tasks_label)

        self.generate_button = QPushButton("Generate Schedule")
        self.generate_button.setObjectName("Primary")
        self.generate_button.setCursor(Qt.PointingHandCursor)
        self.generate_button.setMinimumHeight(38)
        self.generate_button.clicked.connect(self._generate_schedule)
        input_layout.addWidget(self.generate_button)

        outer.addWidget(input_card)

        results_card = QFrame()
        results_card.setObjectName("Card")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(20, 16, 20, 16)
        results_layout.setSpacing(10)
        results_layout.addWidget(self._section_header("SUGGESTED SCHEDULE"))

        self.summary_label = QLabel("Generate a schedule to see suggested blocks.")
        self.summary_label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        results_layout.addWidget(self.summary_label)

        self.blocks_list = QListWidget()
        self.blocks_list.setFrameShape(QFrame.NoFrame)
        results_layout.addWidget(self.blocks_list)

        self.unscheduled_label = QLabel("")
        self.unscheduled_label.setWordWrap(True)
        self.unscheduled_label.setStyleSheet("color: #e0b96c; font-size: 12px;")
        results_layout.addWidget(self.unscheduled_label)

        outer.addWidget(results_card, 1)

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    def refresh(self) -> None:
        """Called when the user navigates to this screen. Refreshes the
        pending-task count only; does not re-run the scheduler (that
        depends on the user's chosen window) and deliberately does not
        touch focus_minutes_input/break_minutes_input - those are seeded
        once from saved preferences in _build_ui() and are otherwise
        fully user-controlled, so repeated navigation must not reset
        them back to the saved defaults."""
        pending = self.task_manager.list_active_tasks()
        count = len(pending)
        if count == 0:
            self.pending_tasks_label.setText("No active tasks to schedule.")
        elif count == 1:
            self.pending_tasks_label.setText("1 active task ready to schedule.")
        else:
            self.pending_tasks_label.setText(f"{count} active tasks ready to schedule.")

    def _generate_schedule(self) -> None:
        tasks = self.task_manager.list_active_tasks()

        # selected date -> Python weekday() (Monday=0 ... Sunday=6) ->
        # that day's recurring commitments, via the shared OnboardingManager
        # only. No repository/SQLite access happens here.
        weekday = self.date_input.date().toPython().weekday()
        commitments = self.onboarding_manager.get_commitments_for_day(weekday)
        busy_intervals = [
            BusyInterval(start=commitment.start_time, end=commitment.end_time, label=commitment.label)
            for commitment in commitments
        ]

        scheduler_input = SchedulerInput(
            tasks=tasks,
            window_start=self.start_input.time().toString("HH:mm"),
            window_end=self.end_input.time().toString("HH:mm"),
            focus_minutes=self.focus_minutes_input.value(),
            break_minutes=self.break_minutes_input.value(),
            busy_intervals=busy_intervals,
        )
        try:
            result = self.scheduler.generate(scheduler_input)
        except ValueError as exc:
            self.blocks_list.clear()
            self.summary_label.setText(f"Could not generate schedule: {exc}")
            self.unscheduled_label.setText("")
            return

        self.last_result = result
        self._render_result(result)

    def _render_result(self, result: SchedulerResult) -> None:
        self.blocks_list.clear()

        if not result.blocks:
            self.summary_label.setText(
                "No blocks generated - check that the end time is after the start time."
            )
            self.unscheduled_label.setText("")
            return

        for block in result.blocks:
            kind_text, color = _KIND_STYLE.get(block.kind, (block.kind, "#eceef0"))
            item = QListWidgetItem(
                f"{block.start} – {block.end}    {block.label}    "
                f"·  {block.duration_minutes}m  ·  {kind_text}"
            )
            item.setForeground(self._qcolor(color))
            self.blocks_list.addItem(item)

        available = self._format_minutes(result.total_available_minutes)
        planned = self._format_minutes(result.total_planned_minutes)
        self.summary_label.setText(f"Available: {available}    ·    Planned focus time: {planned}")

        if result.unscheduled_tasks:
            titles = ", ".join(t.title for t in result.unscheduled_tasks)
            self.unscheduled_label.setText(f"Didn't fit in this window: {titles}")
        else:
            self.unscheduled_label.setText("")

    @staticmethod
    def _qcolor(hex_value: str) -> QColor:
        return QColor(hex_value)

    @staticmethod
    def _format_minutes(minutes: float) -> str:
        minutes = int(round(minutes))
        hours, mins = divmod(minutes, 60)
        if hours:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @staticmethod
    def _parse_time(value: str) -> QTime:
        try:
            hour_str, minute_str = value.split(":")
            return QTime(int(hour_str), int(minute_str))
        except (ValueError, AttributeError):
            return QTime(7, 0)