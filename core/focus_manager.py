"""
FocusManager: coordinates the TimerEngine and SessionManager to run
a focus session end-to-end. This is the orchestrator described in the
project spec - it does not implement timer or persistence details itself.
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.timer_engine import TimerEngine
from core.session_manager import SessionManager
from database.models import Task


class FocusManager(QObject):
    session_started = Signal()
    session_finished = Signal(object)   # Session
    session_ended_early = Signal(object)  # Session

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        self.timer = TimerEngine()
        self.current_task: Optional[Task] = None

        self.timer.finished.connect(self._on_timer_finished)

    def start_focus(self, task: Optional[Task], duration_minutes: int) -> None:
        self.current_task = task
        task_id = task.id if task else None
        self.session_manager.start_session(task_id, duration_minutes)
        self.timer.start(duration_minutes)
        self.session_started.emit()

    def pause(self) -> None:
        self.timer.pause()
        self.session_manager.pause_session()

    def resume(self) -> None:
        self.timer.resume()
        self.session_manager.resume_session()

    def end_early(self, reason: str) -> None:
        elapsed = self.timer.elapsed_seconds()
        self.timer.stop()
        session = self.session_manager.end_early(elapsed, reason)
        self.current_task = None
        self.session_ended_early.emit(session)

    def _on_timer_finished(self) -> None:
        elapsed = self.timer.total_seconds
        session = self.session_manager.complete_session(elapsed)
        self.current_task = None
        self.session_finished.emit(session)
