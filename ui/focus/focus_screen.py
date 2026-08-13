"""
FocusScreen: the fullscreen Focus Mode window. Pure UI layer - all
session/timer business logic lives in FocusManager, SessionManager and
TimerEngine. This screen only builds widgets, reacts to the manager's
signals, and calls its existing public methods (start_focus, pause,
resume, end_early). It does not implement media controls, app
restriction, Focus Profiles, or calendar/reminder features - those are
out of scope for the MVP focus loop.
"""

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QDialog, QRadioButton, QButtonGroup, QDialogButtonBox, QFrame,
)

from core.focus_manager import FocusManager
from core.timer_engine import TimerEngine
from database.models import Task, Session


class FocusScreen(QWidget):
    """Fullscreen Focus Mode. Constructed fresh for each focus session."""

    END_REASONS = [
        "Task completed",
        "Important interruption",
        "Taking a break",
        "Other",
    ]

    def __init__(
        self,
        focus_manager: FocusManager,
        task: Optional[Task],
        duration_minutes: int,
        on_close: Callable[[], None],
    ):
        super().__init__()
        self.focus_manager = focus_manager
        self.task = task
        self.duration_minutes = duration_minutes
        self.on_close = on_close

        # True while a session is actively running or paused (i.e. not
        # yet completed/ended). Used to guard against impulsive exits.
        self._session_active = True

        # Tracks whether this screen currently holds live connections to
        # focus_manager/timer signals. FocusManager and TimerEngine are
        # long-lived singletons shared across every focus session, so
        # disconnecting must happen exactly once per FocusScreen instance -
        # otherwise a second disconnect attempt (e.g. from both
        # _show_completion() and a subsequent closeEvent()) tries to
        # disconnect a slot that's no longer connected, which is what was
        # producing the "Failed to disconnect" RuntimeWarnings.
        self._signals_connected = False

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Focus Mode")
        self.setObjectName("FocusScreen")
        self.setStyleSheet("#FocusScreen { background-color: #0d0e11; }")

        self._build_ui()
        self._connect_signals()

        self.focus_manager.start_focus(self.task, self.duration_minutes)
        self._initialize_display()

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        center = QVBoxLayout()
        center.setSpacing(14)
        center.setAlignment(Qt.AlignHCenter)

        self.mode_label = QLabel("FOCUS MODE")
        self.mode_label.setObjectName("SectionHeader")
        self.mode_label.setAlignment(Qt.AlignHCenter)
        center.addWidget(self.mode_label, alignment=Qt.AlignHCenter)

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("TimerDisplay")
        self.timer_label.setAlignment(Qt.AlignHCenter)
        center.addWidget(self.timer_label, alignment=Qt.AlignHCenter)

        task_title = self.task.title if self.task else "No specific task"
        self.task_label = QLabel(task_title)
        self.task_label.setObjectName("Title")
        self.task_label.setAlignment(Qt.AlignHCenter)
        center.addWidget(self.task_label, alignment=Qt.AlignHCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(420)
        self.progress_bar.setTextVisible(False)
        center.addWidget(self.progress_bar, alignment=Qt.AlignHCenter)

        self.state_label = QLabel("Active")
        self.state_label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        self.state_label.setAlignment(Qt.AlignHCenter)
        center.addWidget(self.state_label, alignment=Qt.AlignHCenter)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("Primary")
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.setMinimumWidth(120)
        self.pause_button.clicked.connect(self._toggle_pause)
        button_row.addWidget(self.pause_button)

        self.end_button = QPushButton("End Focus")
        self.end_button.setObjectName("Danger")
        self.end_button.setCursor(Qt.PointingHandCursor)
        self.end_button.setMinimumWidth(120)
        self.end_button.clicked.connect(self._end_focus_clicked)
        button_row.addWidget(self.end_button)

        center.addLayout(button_row)

        outer.addLayout(center)
        outer.addStretch(1)

    def _initialize_display(self) -> None:
        remaining = self.focus_manager.timer.remaining_seconds
        self.timer_label.setText(TimerEngine.format_seconds(remaining))
        self.progress_bar.setValue(0)
        self.state_label.setText("Active")

    # -- Signal wiring ------------------------------------------------

    def _connect_signals(self) -> None:
        if self._signals_connected:
            return
        self.focus_manager.timer.tick.connect(self._on_tick)
        self.focus_manager.timer.paused.connect(self._on_timer_paused)
        self.focus_manager.timer.resumed.connect(self._on_timer_resumed)
        self.focus_manager.session_finished.connect(self._on_session_finished)
        self.focus_manager.session_ended_early.connect(self._on_session_ended_early)
        self._signals_connected = True

    def _disconnect_signals(self) -> None:
        # Guard against redundant disconnects: this method can legitimately
        # be called twice in normal use (once from _show_completion() when
        # the session ends, and again from closeEvent() when the window is
        # actually closed). Only the first call should touch the signal
        # connections - the second is a no-op.
        if not self._signals_connected:
            return
        for signal, slot in (
            (self.focus_manager.timer.tick, self._on_tick),
            (self.focus_manager.timer.paused, self._on_timer_paused),
            (self.focus_manager.timer.resumed, self._on_timer_resumed),
            (self.focus_manager.session_finished, self._on_session_finished),
            (self.focus_manager.session_ended_early, self._on_session_ended_early),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._signals_connected = False

    # -- Timer/session reactions ----------------------------------------

    def _on_tick(self, remaining_seconds: int) -> None:
        self.timer_label.setText(TimerEngine.format_seconds(remaining_seconds))
        total = self.focus_manager.timer.total_seconds or 1
        elapsed = total - remaining_seconds
        self.progress_bar.setValue(int((elapsed / total) * 100))

    def _on_timer_paused(self) -> None:
        self.state_label.setText("Paused")
        self.pause_button.setText("Resume")

    def _on_timer_resumed(self) -> None:
        self.state_label.setText("Active")
        self.pause_button.setText("Pause")

    def _on_session_finished(self, session: Session) -> None:
        self._show_completion("Session complete")

    def _on_session_ended_early(self, session: Session) -> None:
        self._show_completion("Session ended")

    def _show_completion(self, message: str) -> None:
        self._session_active = False
        self._disconnect_signals()
        self.progress_bar.setValue(100)
        self.state_label.setText(message)
        self.pause_button.setEnabled(False)
        self.end_button.setText("Close")
        self.end_button.clicked.disconnect()
        self.end_button.clicked.connect(self.close)

    # -- User actions -----------------------------------------------------

    def _toggle_pause(self) -> None:
        if self.focus_manager.timer.is_paused:
            self.focus_manager.resume()
        else:
            self.focus_manager.pause()

    def _end_focus_clicked(self) -> None:
        reason = self._prompt_end_reason()
        if reason is None:
            return
        self.focus_manager.end_early(reason)

    def _prompt_end_reason(self) -> Optional[str]:
        dialog = QDialog(self)
        dialog.setWindowTitle("End Focus Session?")
        dialog.setMinimumWidth(320)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Why are you ending the session?")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        group_box = QFrame()
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(6)

        button_group = QButtonGroup(dialog)
        for i, reason_text in enumerate(self.END_REASONS):
            radio = QRadioButton(reason_text)
            if i == 0:
                radio.setChecked(True)
            button_group.addButton(radio, i)
            group_layout.addWidget(radio)
        layout.addWidget(group_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        end_btn = buttons.addButton("End Session", QDialogButtonBox.AcceptRole)
        end_btn.setObjectName("Danger")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None

        checked = button_group.checkedButton()
        return checked.text() if checked else self.END_REASONS[-1]

    # -- Window lifecycle -------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._session_active:
            # Discourage impulsive exits (e.g. Alt+F4): route the user
            # through the same confirmation flow as the End Focus button
            # instead of closing the window outright.
            event.ignore()
            self._end_focus_clicked()
            return

        self._disconnect_signals()
        event.accept()
        if self.on_close:
            self.on_close()