"""
OnboardingWizard: first-launch flow that collects the user's daily
routine, recurring weekly commitments, and focus preferences.

Pure UI layer - all validation of stored values and all persistence
goes through OnboardingManager. This screen never touches a
repository or SQLite directly, matching the pattern already used by
DashboardScreen/TaskDialog (business rules stay in core/, the UI only
builds widgets and calls manager methods).

Step flow:
    0. Welcome
    1. Daily routine (wake / sleep time)
    2. Weekly commitments (label + days + start/end time)
    3. Focus preferences (focus / break / min block minutes)
    4. Finish (save + complete_onboarding)
"""

from typing import Dict, List

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QStackedWidget, QLineEdit, QCheckBox, QTimeEdit, QSpinBox,
    QListWidget, QListWidgetItem, QFrame, QMessageBox,
)

from core.onboarding_manager import OnboardingManager, OnboardingPreferences


# Short/long day labels, index-aligned with WeeklyCommitment.day_of_week
# (0 = Monday ... 6 = Sunday), matching datetime.weekday() convention.
_DAY_LABELS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAY_LABELS_FULL = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# Spin box bounds mirror the ranges OnboardingManager itself enforces in
# save_preferences(). Kept as plain literals here rather than importing
# OnboardingManager's underscore-prefixed constants, consistent with how
# ScheduleScreen/DashboardScreen already duplicate the 5-240 focus-minutes
# range rather than reaching into another module's private values.
_MIN_FOCUS_MINUTES, _MAX_FOCUS_MINUTES = 5, 240
_MIN_BREAK_MINUTES, _MAX_BREAK_MINUTES = 0, 60
_MIN_BLOCK_MINUTES, _MAX_BLOCK_MINUTES = 1, 240

_STEP_COUNT = 5
_STEP_WELCOME, _STEP_ROUTINE, _STEP_COMMITMENTS, _STEP_PREFERENCES, _STEP_FINISH = range(_STEP_COUNT)


class OnboardingWizard(QDialog):
    """First-run wizard. Talks only to the OnboardingManager passed in."""

    def __init__(self, onboarding_manager: OnboardingManager, parent=None):
        super().__init__(parent)
        self.manager = onboarding_manager

        # Each entry: {"ids": [commitment_id, ...], "label": str,
        #              "days": [int, ...], "start": "HH:MM", "end": "HH:MM"}
        # One entry represents what the user perceives as a single
        # commitment even though it may back multiple WeeklyCommitment
        # rows (one per selected day).
        self._commitment_groups: List[Dict] = []

        self.setWindowTitle("Welcome to Focus")
        self.setMinimumSize(560, 520)
        self.setModal(True)

        self._build_ui()
        self._load_initial_data()

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 20)
        outer.setSpacing(16)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_welcome_step())
        self.stack.addWidget(self._build_routine_step())
        self.stack.addWidget(self._build_commitments_step())
        self.stack.addWidget(self._build_preferences_step())
        self.stack.addWidget(self._build_finish_step())
        outer.addWidget(self.stack, 1)

        nav_row = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self._go_back)
        nav_row.addWidget(self.back_button)

        nav_row.addStretch()

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("Primary")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.setMinimumWidth(100)
        self.next_button.clicked.connect(self._go_next)
        nav_row.addWidget(self.next_button)

        outer.addLayout(nav_row)

        self._update_nav_buttons()

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    def _muted_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        return label

    # -- Step 0: Welcome ---------------------------------------------------

    def _build_welcome_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        title = QLabel("Welcome to Focus")
        title.setObjectName("Title")
        layout.addWidget(title)

        body = self._muted_label(
            "Focus uses your daily routine, weekly commitments, and focus "
            "preferences to work out how much usable time you actually have "
            "each day, and to help you turn that time into realistic work "
            "sessions.\n\n"
            "This will only take a minute, and you can change any of it "
            "later in Settings."
        )
        layout.addWidget(body)
        layout.addStretch()
        return page

    # -- Step 1: Daily routine ---------------------------------------------

    def _build_routine_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        title = QLabel("Daily Routine")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(self._muted_label("When do you usually wake up and go to sleep?"))

        form = QFormLayout()
        form.setSpacing(10)

        self.wake_time_input = QTimeEdit()
        self.wake_time_input.setDisplayFormat("HH:mm")
        form.addRow("Wake time", self.wake_time_input)

        self.sleep_time_input = QTimeEdit()
        self.sleep_time_input.setDisplayFormat("HH:mm")
        form.addRow("Sleep time", self.sleep_time_input)

        layout.addLayout(form)
        layout.addStretch()
        return page

    # -- Step 2: Weekly commitments -----------------------------------------

    def _build_commitments_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        title = QLabel("Weekly Commitments")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(self._muted_label(
            "Add recurring commitments like school, work, or tuition. Focus "
            "will treat these as unavailable time when planning your day. "
            "This step is optional."
        ))

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        form_layout.addWidget(QLabel("Label"))
        self.commitment_label_input = QLineEdit()
        self.commitment_label_input.setPlaceholderText("e.g. School, Work, Tuition")
        form_layout.addWidget(self.commitment_label_input)

        form_layout.addWidget(QLabel("Days"))
        days_row = QHBoxLayout()
        days_row.setSpacing(8)
        self.day_checkboxes: List[QCheckBox] = []
        for short_label in _DAY_LABELS_SHORT:
            checkbox = QCheckBox(short_label)
            self.day_checkboxes.append(checkbox)
            days_row.addWidget(checkbox)
        days_row.addStretch()
        form_layout.addLayout(days_row)

        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        time_row.addWidget(QLabel("Start"))
        self.commitment_start_input = QTimeEdit()
        self.commitment_start_input.setDisplayFormat("HH:mm")
        self.commitment_start_input.setTime(QTime(9, 0))
        time_row.addWidget(self.commitment_start_input)

        time_row.addWidget(QLabel("End"))
        self.commitment_end_input = QTimeEdit()
        self.commitment_end_input.setDisplayFormat("HH:mm")
        self.commitment_end_input.setTime(QTime(17, 0))
        time_row.addWidget(self.commitment_end_input)
        time_row.addStretch()
        form_layout.addLayout(time_row)

        add_button = QPushButton("+ Add Commitment")
        add_button.setObjectName("Primary")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self._add_commitment)
        form_layout.addWidget(add_button)

        layout.addWidget(form_card)

        layout.addWidget(self._section_header("YOUR COMMITMENTS"))

        self.commitments_list = QListWidget()
        self.commitments_list.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.commitments_list, 1)

        remove_button = QPushButton("Remove Selected")
        remove_button.setObjectName("Danger")
        remove_button.setCursor(Qt.PointingHandCursor)
        remove_button.clicked.connect(self._remove_selected_commitment)
        layout.addWidget(remove_button)

        return page

    # -- Step 3: Focus preferences -------------------------------------------

    def _build_preferences_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        title = QLabel("Focus Preferences")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(self._muted_label(
            "These are the defaults used when planning and starting focus "
            "sessions. You can override them per-session later."
        ))

        form = QFormLayout()
        form.setSpacing(10)

        self.focus_minutes_input = QSpinBox()
        self.focus_minutes_input.setRange(_MIN_FOCUS_MINUTES, _MAX_FOCUS_MINUTES)
        self.focus_minutes_input.setSingleStep(5)
        self.focus_minutes_input.setSuffix(" min")
        form.addRow("Preferred focus duration", self.focus_minutes_input)

        self.break_minutes_input = QSpinBox()
        self.break_minutes_input.setRange(_MIN_BREAK_MINUTES, _MAX_BREAK_MINUTES)
        self.break_minutes_input.setSingleStep(5)
        self.break_minutes_input.setSuffix(" min")
        form.addRow("Preferred break duration", self.break_minutes_input)

        self.min_block_minutes_input = QSpinBox()
        self.min_block_minutes_input.setRange(_MIN_BLOCK_MINUTES, _MAX_BLOCK_MINUTES)
        self.min_block_minutes_input.setSingleStep(5)
        self.min_block_minutes_input.setSuffix(" min")
        form.addRow("Minimum useful focus block", self.min_block_minutes_input)

        layout.addLayout(form)
        layout.addWidget(self._muted_label(
            "The minimum useful focus block can't be longer than your "
            "preferred focus duration."
        ))
        layout.addStretch()
        return page

    # -- Step 4: Finish -----------------------------------------------------

    def _build_finish_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        title = QLabel("All Set")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(self._muted_label(
            "Focus will use this information to calculate your available "
            "time each day and suggest realistic work sessions. You can "
            "change any of this later in Settings."
        ))
        layout.addStretch()
        return page

    # -- Loading existing data ----------------------------------------------

    def _load_initial_data(self) -> None:
        preferences = self.manager.get_preferences()
        self.wake_time_input.setTime(self._parse_time(preferences.wake_time))
        self.sleep_time_input.setTime(self._parse_time(preferences.sleep_time))
        self.focus_minutes_input.setValue(preferences.focus_minutes)
        self.break_minutes_input.setValue(preferences.break_minutes)
        self.min_block_minutes_input.setValue(preferences.min_block_minutes)

        self._load_existing_commitments()

    def _load_existing_commitments(self) -> None:
        """Group any commitments already stored (e.g. re-opening the
        wizard) back into the multi-day entries the user perceives,
        keyed by (label, start_time, end_time)."""
        grouped: Dict[tuple, Dict] = {}
        for commitment in self.manager.get_commitments():
            key = (commitment.label, commitment.start_time, commitment.end_time)
            entry = grouped.setdefault(key, {"ids": [], "days": []})
            entry["ids"].append(commitment.id)
            entry["days"].append(commitment.day_of_week)

        self._commitment_groups = [
            {
                "ids": data["ids"],
                "label": label,
                "days": sorted(data["days"]),
                "start": start,
                "end": end,
            }
            for (label, start, end), data in grouped.items()
        ]
        self._refresh_commitments_list()

    @staticmethod
    def _parse_time(value: str) -> QTime:
        try:
            hour_str, minute_str = value.split(":")
            return QTime(int(hour_str), int(minute_str))
        except (ValueError, AttributeError):
            return QTime(7, 0)

    # -- Commitments actions --------------------------------------------------

    def _add_commitment(self) -> None:
        label = self.commitment_label_input.text().strip()
        if not label:
            QMessageBox.warning(self, "Missing label", "Please enter a label for this commitment.")
            return

        selected_days = [i for i, checkbox in enumerate(self.day_checkboxes) if checkbox.isChecked()]
        if not selected_days:
            QMessageBox.warning(self, "No days selected", "Select at least one day for this commitment.")
            return

        start_time = self.commitment_start_input.time().toString("HH:mm")
        end_time = self.commitment_end_input.time().toString("HH:mm")
        if end_time <= start_time:
            QMessageBox.warning(self, "Invalid time range", "End time must be after start time.")
            return

        created_ids = []
        try:
            for day in selected_days:
                commitment = self.manager.add_commitment(
                    day_of_week=day, start_time=start_time, end_time=end_time, label=label,
                )
                created_ids.append(commitment.id)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid commitment", str(exc))
            return

        self._commitment_groups.append({
            "ids": created_ids,
            "label": label,
            "days": selected_days,
            "start": start_time,
            "end": end_time,
        })
        self._refresh_commitments_list()

        self.commitment_label_input.clear()
        for checkbox in self.day_checkboxes:
            checkbox.setChecked(False)

    def _remove_selected_commitment(self) -> None:
        item = self.commitments_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Nothing selected", "Select a commitment to remove.")
            return

        index = item.data(Qt.UserRole)
        if index is None or not (0 <= index < len(self._commitment_groups)):
            return

        group = self._commitment_groups[index]
        for commitment_id in group["ids"]:
            self.manager.delete_commitment(commitment_id)

        del self._commitment_groups[index]
        self._refresh_commitments_list()

    def _refresh_commitments_list(self) -> None:
        self.commitments_list.clear()

        if not self._commitment_groups:
            placeholder = QListWidgetItem("No commitments added yet.")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(Qt.gray)
            self.commitments_list.addItem(placeholder)
            return

        for index, group in enumerate(self._commitment_groups):
            days_text = ", ".join(_DAY_LABELS_SHORT[d] for d in sorted(group["days"]))
            text = f"{group['label']}    ·    {days_text}    ·    {group['start']}–{group['end']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, index)
            self.commitments_list.addItem(item)

    # -- Navigation -----------------------------------------------------------

    def _update_nav_buttons(self) -> None:
        index = self.stack.currentIndex()
        self.back_button.setEnabled(index > 0)
        self.next_button.setText("Finish" if index == _STEP_FINISH else "Next")

    def _go_back(self) -> None:
        index = self.stack.currentIndex()
        if index > 0:
            self.stack.setCurrentIndex(index - 1)
            self._update_nav_buttons()

    def _go_next(self) -> None:
        index = self.stack.currentIndex()
        if not self._validate_step(index):
            return

        if index == _STEP_FINISH:
            self._finish()
            return

        self.stack.setCurrentIndex(index + 1)
        self._update_nav_buttons()

    def _validate_step(self, index: int) -> bool:
        if index == _STEP_PREFERENCES:
            focus_minutes = self.focus_minutes_input.value()
            min_block_minutes = self.min_block_minutes_input.value()
            if min_block_minutes > focus_minutes:
                QMessageBox.warning(
                    self,
                    "Invalid preferences",
                    "Minimum useful focus block cannot exceed your preferred focus duration.",
                )
                return False
        return True

    # -- Finish -----------------------------------------------------------

    def _finish(self) -> None:
        preferences = OnboardingPreferences(
            wake_time=self.wake_time_input.time().toString("HH:mm"),
            sleep_time=self.sleep_time_input.time().toString("HH:mm"),
            focus_minutes=self.focus_minutes_input.value(),
            break_minutes=self.break_minutes_input.value(),
            min_block_minutes=self.min_block_minutes_input.value(),
        )

        try:
            self.manager.save_preferences(preferences)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid preferences", str(exc))
            self.stack.setCurrentIndex(_STEP_PREFERENCES)
            self._update_nav_buttons()
            return

        self.manager.complete_onboarding()
        self.accept()
