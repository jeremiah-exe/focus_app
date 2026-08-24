"""
SettingsScreen: a single scrollable Normal Mode page for editing the
preferences the onboarding flow originally collected - focus/break
lengths, minimum useful focus block, wake/sleep time, and recurring
weekly commitments.

This screen is a pure UI layer, matching the pattern already used by
DashboardScreen/ScheduleScreen/OnboardingWizard: all validation and
persistence goes through the existing OnboardingManager (which itself
wraps SettingsRepository + CommitmentRepository). No repository or
SQLite access happens here, and no new persistence system is created -
this is only a second entry point onto the same manager the onboarding
wizard already uses.

Saving behaviour:
- Focus Preferences + Daily Routine share one "Save Changes" action,
  since they persist together as a single OnboardingPreferences object
  (OnboardingManager.save_preferences). Nothing is written to storage
  until that button is clicked, so navigating away or reopening the
  app before saving simply discards in-progress edits - refresh()
  always reloads the last *saved* state.
- Weekly Commitments save immediately per action (add/edit/remove),
  same as the onboarding wizard, since each is already a discrete,
  reversible operation with its own list to reflect the result in.
"""

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QSpinBox, QTimeEdit, QLineEdit, QCheckBox, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QMessageBox,
)

from core.onboarding_manager import OnboardingManager, OnboardingPreferences


# Index-aligned with WeeklyCommitment.day_of_week (0 = Monday ... 6 =
# Sunday), matching datetime.weekday() convention - same labels the
# onboarding wizard uses, kept local here rather than imported since
# they're simple display constants, not shared business logic.
_DAY_LABELS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Spin box bounds mirror what OnboardingManager.save_preferences()
# itself enforces, same as ScheduleScreen/DashboardScreen/
# OnboardingWizard already duplicate rather than importing the
# manager's underscore-prefixed constants.
_MIN_FOCUS_MINUTES, _MAX_FOCUS_MINUTES = 5, 240
_MIN_BREAK_MINUTES, _MAX_BREAK_MINUTES = 0, 60
_MIN_BLOCK_MINUTES, _MAX_BLOCK_MINUTES = 1, 240


class SettingsScreen(QWidget):
    def __init__(self, onboarding_manager: OnboardingManager):
        super().__init__()
        self.onboarding_manager = onboarding_manager

        # Grouped commitment display state, same shape/approach as
        # OnboardingWizard._commitment_groups: one entry represents
        # what the user perceives as a single commitment even though
        # it may back multiple WeeklyCommitment rows (one per day).
        self._commitment_groups: List[Dict] = []

        # Index into _commitment_groups currently loaded into the
        # add/edit form, or None when the form is in "add new" mode.
        self._editing_group_index: Optional[int] = None

        self._build_ui()
        self.refresh()

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("Title")
        subtitle = QLabel("Update the preferences and commitments onboarding collected.")
        subtitle.setObjectName("Subtitle")
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        content_layout.addWidget(self._build_focus_preferences_card())
        content_layout.addWidget(self._build_daily_routine_card())

        save_row = QHBoxLayout()
        self.save_button = QPushButton("Save Changes")
        self.save_button.setObjectName("Primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setMinimumHeight(38)
        self.save_button.clicked.connect(self._save_preferences)
        save_row.addWidget(self.save_button)

        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet("color: #7cc48f; font-size: 12px;")
        save_row.addWidget(self.save_status_label)
        save_row.addStretch()
        content_layout.addLayout(save_row)

        content_layout.addWidget(self._build_commitments_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    def _muted_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        return label

    # -- Focus Preferences card --------------------------------------------

    def _build_focus_preferences_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(self._section_header("FOCUS PREFERENCES"))

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
        return card

    # -- Daily Routine card -------------------------------------------------

    def _build_daily_routine_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(self._section_header("DAILY ROUTINE"))

        form = QFormLayout()
        form.setSpacing(10)

        self.wake_time_input = QTimeEdit()
        self.wake_time_input.setDisplayFormat("HH:mm")
        form.addRow("Typical wake time", self.wake_time_input)

        self.sleep_time_input = QTimeEdit()
        self.sleep_time_input.setDisplayFormat("HH:mm")
        form.addRow("Typical sleep time", self.sleep_time_input)

        layout.addLayout(form)
        return card

    # -- Weekly Commitments card --------------------------------------------

    def _build_commitments_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(self._section_header("WEEKLY COMMITMENTS"))
        layout.addWidget(self._muted_label(
            "Recurring unavailable periods such as school, work, or tuition. "
            "Focus treats these as busy time when planning your day."
        ))

        form_card = QFrame()
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(0, 0, 0, 0)
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

        form_buttons_row = QHBoxLayout()
        form_buttons_row.setSpacing(10)

        self.commit_form_button = QPushButton("+ Add Commitment")
        self.commit_form_button.setObjectName("Primary")
        self.commit_form_button.setCursor(Qt.PointingHandCursor)
        self.commit_form_button.clicked.connect(self._submit_commitment_form)
        form_buttons_row.addWidget(self.commit_form_button)

        self.cancel_edit_button = QPushButton("Cancel Edit")
        self.cancel_edit_button.setCursor(Qt.PointingHandCursor)
        self.cancel_edit_button.clicked.connect(self._cancel_commitment_edit)
        self.cancel_edit_button.setVisible(False)
        form_buttons_row.addWidget(self.cancel_edit_button)

        form_buttons_row.addStretch()
        form_layout.addLayout(form_buttons_row)

        layout.addWidget(form_card)

        layout.addWidget(self._section_header("YOUR COMMITMENTS"))

        self.commitments_list = QListWidget()
        self.commitments_list.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.commitments_list)

        list_buttons_row = QHBoxLayout()
        list_buttons_row.setSpacing(10)

        edit_button = QPushButton("Edit Selected")
        edit_button.setCursor(Qt.PointingHandCursor)
        edit_button.clicked.connect(self._edit_selected_commitment)
        list_buttons_row.addWidget(edit_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.setObjectName("Danger")
        remove_button.setCursor(Qt.PointingHandCursor)
        remove_button.clicked.connect(self._remove_selected_commitment)
        list_buttons_row.addWidget(remove_button)

        list_buttons_row.addStretch()
        layout.addLayout(list_buttons_row)

        return card

    # -- Loading / refresh --------------------------------------------------

    def refresh(self) -> None:
        """Called on construction and whenever MainWindow navigates here.
        Reloads the last *saved* preferences and commitments from
        OnboardingManager - any not-yet-saved edits in the preference
        form are intentionally discarded, since this screen only ever
        writes to storage via the explicit Save Changes / commitment
        actions below, never implicitly."""
        self._load_preferences()
        self._reload_commitments()
        self._cancel_commitment_edit()
        self.save_status_label.setText("")

    def _load_preferences(self) -> None:
        preferences = self.onboarding_manager.get_preferences()
        self.focus_minutes_input.setValue(preferences.focus_minutes)
        self.break_minutes_input.setValue(preferences.break_minutes)
        self.min_block_minutes_input.setValue(preferences.min_block_minutes)
        self.wake_time_input.setTime(self._parse_time(preferences.wake_time))
        self.sleep_time_input.setTime(self._parse_time(preferences.sleep_time))

    def _reload_commitments(self) -> None:
        """Re-fetch every WeeklyCommitment from OnboardingManager and
        re-group them for display, so the list always reflects exactly
        what's persisted rather than UI-side bookkeeping that could
        drift from it."""
        grouped: Dict[tuple, Dict] = {}
        for commitment in self.onboarding_manager.get_commitments():
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

    @staticmethod
    def _parse_time(value: str) -> QTime:
        try:
            hour_str, minute_str = value.split(":")
            return QTime(int(hour_str), int(minute_str))
        except (ValueError, AttributeError):
            return QTime(7, 0)

    # -- Saving preferences ---------------------------------------------------

    def _save_preferences(self) -> None:
        preferences = OnboardingPreferences(
            wake_time=self.wake_time_input.time().toString("HH:mm"),
            sleep_time=self.sleep_time_input.time().toString("HH:mm"),
            focus_minutes=self.focus_minutes_input.value(),
            break_minutes=self.break_minutes_input.value(),
            min_block_minutes=self.min_block_minutes_input.value(),
        )
        try:
            self.onboarding_manager.save_preferences(preferences)
        except ValueError as exc:
            self.save_status_label.setText("")
            QMessageBox.warning(self, "Invalid preferences", str(exc))
            return

        self.save_status_label.setText("Saved.")

    # -- Commitment form actions -----------------------------------------------

    def _submit_commitment_form(self) -> None:
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

        if self._editing_group_index is None:
            self._create_commitment_group(label, selected_days, start_time, end_time)
        else:
            self._replace_commitment_group(
                self._editing_group_index, label, selected_days, start_time, end_time
            )

    def _create_commitment_group(self, label: str, days: List[int], start_time: str, end_time: str) -> None:
        try:
            for day in days:
                self.onboarding_manager.add_commitment(
                    day_of_week=day, start_time=start_time, end_time=end_time, label=label,
                )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid commitment", str(exc))
            return

        self._reload_commitments()
        self._cancel_commitment_edit()

    def _replace_commitment_group(
        self, group_index: int, label: str, days: List[int], start_time: str, end_time: str
    ) -> None:
        """Editing a grouped commitment (which may back several
        WeeklyCommitment rows, one per day) is implemented as: remove
        every underlying record the displayed group currently owns,
        then recreate one record per newly selected day. This keeps
        editing correct even when the user adds/removes days, renames
        the label, or changes the time range in the same edit, since
        the resulting set of records is always rebuilt from the form's
        current values rather than patched field-by-field."""
        if not (0 <= group_index < len(self._commitment_groups)):
            self._cancel_commitment_edit()
            return

        group = self._commitment_groups[group_index]

        # Create the replacement records first and only remove the old
        # ones once every new record has been validated and persisted
        # successfully - if add_commitment() raises partway through
        # (e.g. a bad value slipped past the client-side checks above),
        # the original group is left intact instead of being deleted
        # with nothing valid to replace it.
        created_ids: List[int] = []
        try:
            for day in days:
                commitment = self.onboarding_manager.add_commitment(
                    day_of_week=day, start_time=start_time, end_time=end_time, label=label,
                )
                created_ids.append(commitment.id)
        except ValueError as exc:
            for commitment_id in created_ids:
                self.onboarding_manager.delete_commitment(commitment_id)
            QMessageBox.warning(self, "Invalid commitment", str(exc))
            return

        for commitment_id in group["ids"]:
            self.onboarding_manager.delete_commitment(commitment_id)

        self._reload_commitments()
        self._cancel_commitment_edit()

    def _edit_selected_commitment(self) -> None:
        item = self.commitments_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Nothing selected", "Select a commitment to edit.")
            return

        index = item.data(Qt.UserRole)
        if index is None or not (0 <= index < len(self._commitment_groups)):
            return

        group = self._commitment_groups[index]
        self._editing_group_index = index

        self.commitment_label_input.setText(group["label"])
        for i, checkbox in enumerate(self.day_checkboxes):
            checkbox.setChecked(i in group["days"])
        self.commitment_start_input.setTime(self._parse_time(group["start"]))
        self.commitment_end_input.setTime(self._parse_time(group["end"]))

        self.commit_form_button.setText("Update Commitment")
        self.cancel_edit_button.setVisible(True)

    def _cancel_commitment_edit(self) -> None:
        self._editing_group_index = None
        self.commit_form_button.setText("+ Add Commitment")
        self.cancel_edit_button.setVisible(False)

        self.commitment_label_input.clear()
        for checkbox in self.day_checkboxes:
            checkbox.setChecked(False)
        self.commitment_start_input.setTime(QTime(9, 0))
        self.commitment_end_input.setTime(QTime(17, 0))

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
            self.onboarding_manager.delete_commitment(commitment_id)

        if self._editing_group_index == index:
            self._cancel_commitment_edit()

        self._reload_commitments()
