"""
TaskDialog: modal form for creating or editing a task.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QSpinBox,
    QComboBox, QDialogButtonBox, QLabel,
)

from database.models import Task, Priority


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Edit Task" if task else "New Task")
        self.setMinimumWidth(380)
        self._build_ui()
        if task:
            self._load_task(task)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("Edit Task" if self.task else "New Task")
        header.setObjectName("Title")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Mathematics — Quadratics")
        form.addRow("Title", self.title_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(70)
        form.addRow("Description", self.description_input)

        self.duration_input = QSpinBox()
        self.duration_input.setRange(5, 480)
        self.duration_input.setSingleStep(5)
        self.duration_input.setValue(30)
        self.duration_input.setSuffix(" min")
        form.addRow("Estimated duration", self.duration_input)

        self.priority_input = QComboBox()
        self.priority_input.addItems([p.value for p in Priority])
        self.priority_input.setCurrentText(Priority.MEDIUM.value)
        form.addRow("Priority", self.priority_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("e.g. School, Coding, Personal")
        form.addRow("Category", self.category_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_task(self, task: Task) -> None:
        self.title_input.setText(task.title)
        self.description_input.setPlainText(task.description)
        self.duration_input.setValue(task.estimated_minutes)
        self.priority_input.setCurrentText(task.priority)
        self.category_input.setText(task.category)

    def get_values(self) -> dict:
        return {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "estimated_minutes": self.duration_input.value(),
            "priority": self.priority_input.currentText(),
            "category": self.category_input.text().strip(),
        }
