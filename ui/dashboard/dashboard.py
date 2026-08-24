"""
DashboardScreen: the central planning screen. Shows today's tasks,
lets the user start a focus session, and summarizes today's time.
"""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QSpinBox, QComboBox, QSizePolicy,
)

from core.task_manager import TaskManager
from core.session_manager import SessionManager
from core.onboarding_manager import OnboardingManager
from database.models import TaskStatus
from ui.tasks.task_dialog import TaskDialog


class DashboardScreen(QWidget):
    def __init__(
        self,
        task_manager: TaskManager,
        session_manager: SessionManager,
        onboarding_manager: OnboardingManager,
        on_start_focus,
    ):
        super().__init__()
        self.task_manager = task_manager
        self.session_manager = session_manager
        self.onboarding_manager = onboarding_manager
        self.on_start_focus = on_start_focus
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Focus")
        title.setObjectName("Title")
        subtitle = QLabel(date.today().strftime("%A, %d %B"))
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        add_task_btn = QPushButton("+ Add Task")
        add_task_btn.clicked.connect(self._open_add_task)
        header_row.addWidget(add_task_btn, alignment=Qt.AlignTop)
        outer.addLayout(header_row)

        # -- Task list card ------------------------------------------
        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(20, 16, 20, 16)
        list_layout.setSpacing(10)

        header_label = QLabel("TODAY")
        header_label.setObjectName("SectionHeader")
        list_layout.addWidget(header_label)

        self.task_list = QListWidget()
        self.task_list.setFrameShape(QFrame.NoFrame)
        self.task_list.itemChanged.connect(self._on_item_changed)
        self.task_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        list_layout.addWidget(self.task_list)

        outer.addWidget(list_card, 1)

        # -- Start focus + available time row -------------------------
        action_row = QHBoxLayout()
        action_row.setSpacing(16)

        start_card = QFrame()
        start_card.setObjectName("Card")
        start_layout = QVBoxLayout(start_card)
        start_layout.setContentsMargins(20, 16, 20, 16)
        start_layout.setSpacing(10)
        start_layout.addWidget(self._section_header("START FOCUS"))

        picker_row = QHBoxLayout()
        self.task_selector = QComboBox()
        self.task_selector.setMinimumWidth(180)
        picker_row.addWidget(self.task_selector, 1)

        # Default duration comes from the user's saved onboarding
        # preference (OnboardingManager.get_preferences().focus_minutes).
        # This is read once here, at widget construction time, so it
        # only ever seeds the initial value - refresh() (called on every
        # dashboard navigation) never touches this control again, which
        # is what lets a user's manual per-session change stick without
        # being reset or written back as a new saved preference.
        preferred_focus_minutes = self.onboarding_manager.get_preferences().focus_minutes

        self.duration_selector = QSpinBox()
        self.duration_selector.setRange(5, 240)
        self.duration_selector.setSingleStep(5)
        self.duration_selector.setValue(preferred_focus_minutes)
        self.duration_selector.setSuffix(" min")
        picker_row.addWidget(self.duration_selector)
        start_layout.addLayout(picker_row)

        self.start_button = QPushButton("Start Focus")
        self.start_button.setObjectName("Primary")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumHeight(42)
        self.start_button.clicked.connect(self._start_focus)
        start_layout.addWidget(self.start_button)

        action_row.addWidget(start_card, 1)

        # -- Today's time card ------------------------------------------
        time_card = QFrame()
        time_card.setObjectName("Card")
        time_layout = QVBoxLayout(time_card)
        time_layout.setContentsMargins(20, 16, 20, 16)
        time_layout.setSpacing(10)
        time_layout.addWidget(self._section_header("TODAY'S TIME"))

        self.focused_label = self._stat_row(time_layout, "Focused")
        self.sessions_label = self._stat_row(time_layout, "Sessions completed")
        self.longest_label = self._stat_row(time_layout, "Longest session")

        action_row.addWidget(time_card, 1)

        outer.addLayout(action_row)

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
        # Deliberately does NOT touch self.duration_selector: its value
        # is seeded once from the saved preference in _build_ui() and is
        # otherwise fully user-controlled. Re-reading the preference here
        # would clobber any value the user picked for their next session.
        self._refresh_task_list()
        self._refresh_task_selector()
        self._refresh_today_summary()

    def _refresh_task_list(self) -> None:
        self.task_list.blockSignals(True)
        self.task_list.clear()
        tasks = self.task_manager.list_active_tasks()
        if not tasks:
            item = QListWidgetItem("No tasks yet — add one to get started.")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.task_list.addItem(item)
        for task in tasks:
            item = QListWidgetItem(f"{task.title}    ·    {task.estimated_minutes}m")
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(
                Qt.Checked if task.status == TaskStatus.COMPLETED.value else Qt.Unchecked
            )
            item.setData(Qt.UserRole, task.id)
            self.task_list.addItem(item)
        self.task_list.blockSignals(False)

    def _refresh_task_selector(self) -> None:
        self.task_selector.clear()
        self.task_selector.addItem("No specific task", None)
        for task in self.task_manager.list_active_tasks():
            self.task_selector.addItem(task.title, task.id)

    def _refresh_today_summary(self) -> None:
        summary = self.session_manager.today_summary()
        focused_minutes = summary.get("focused_minutes", 0) or 0
        self.focused_label.setText(self._format_minutes(focused_minutes))
        self.sessions_label.setText(str(summary.get("completed_count", 0) or 0))
        longest = summary.get("longest_session", 0) or 0
        self.longest_label.setText(self._format_minutes(longest))

    @staticmethod
    def _format_minutes(minutes: float) -> str:
        minutes = int(round(minutes))
        hours, mins = divmod(minutes, 60)
        if hours:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    # -- Actions ----------------------------------------------------------

    def _open_add_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            if values["title"]:
                self.task_manager.create_task(**values)
                self.refresh()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        task_id = item.data(Qt.UserRole)
        if task_id is None:
            return
        task = self.task_manager.get_task(task_id)
        dialog = TaskDialog(self, task=task)
        if dialog.exec():
            values = dialog.get_values()
            task.title = values["title"]
            task.description = values["description"]
            task.estimated_minutes = values["estimated_minutes"]
            task.priority = values["priority"]
            task.category = values["category"]
            self.task_manager.update_task(task)
            self.refresh()

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        task_id = item.data(Qt.UserRole)
        if task_id is None:
            return
        if item.checkState() == Qt.Checked:
            self.task_manager.mark_completed(task_id)
        else:
            self.task_manager.set_status(task_id, TaskStatus.TODO.value)
        self._refresh_task_selector()
        self._refresh_today_summary()

    def _start_focus(self) -> None:
        task_id = self.task_selector.currentData()
        task = self.task_manager.get_task(task_id) if task_id else None
        duration = self.duration_selector.value()
        self.on_start_focus(task, duration)