"""
SessionManager: owns the lifecycle of a focus session (create, pause,
complete, end early) and writes the resulting time records. Does not
know about the UI or the timer's Qt internals - it just reacts to
events the FocusManager feeds it.
"""

from datetime import datetime
from typing import Optional

from database.models import Session, SessionStatus, TimeRecord, RecordType
from database.repositories.session_repository import SessionRepository
from database.repositories.task_repository import TaskRepository


class SessionManager:
    def __init__(self, session_repository: SessionRepository, task_repository: TaskRepository):
        self.session_repo = session_repository
        self.task_repo = task_repository
        self.current_session: Optional[Session] = None
        self._focus_record_start: Optional[datetime] = None

    def start_session(self, task_id: Optional[int], planned_minutes: int) -> Session:
        session = Session(
            id=None,
            task_id=task_id,
            planned_minutes=planned_minutes,
            started_at=datetime.now().isoformat(),
            status=SessionStatus.ACTIVE.value,
        )
        self.current_session = self.session_repo.add(session)
        self._focus_record_start = datetime.now()
        return self.current_session

    def pause_session(self) -> None:
        if not self.current_session:
            return
        self._close_focus_record()
        self.current_session.status = SessionStatus.PAUSED.value
        self.session_repo.update(self.current_session)

    def resume_session(self) -> None:
        if not self.current_session:
            return
        self.current_session.status = SessionStatus.ACTIVE.value
        self._focus_record_start = datetime.now()
        self.session_repo.update(self.current_session)

    def complete_session(self, elapsed_seconds: int) -> Session:
        return self._finish(elapsed_seconds, SessionStatus.COMPLETED.value, exit_reason=None)

    def end_early(self, elapsed_seconds: int, reason: str) -> Session:
        return self._finish(elapsed_seconds, SessionStatus.ENDED_EARLY.value, exit_reason=reason)

    # -- internals ----------------------------------------------------

    def _close_focus_record(self) -> None:
        if not self.current_session or not self._focus_record_start:
            return
        end = datetime.now()
        duration = (end - self._focus_record_start).total_seconds()
        record = TimeRecord(
            id=None,
            session_id=self.current_session.id,
            task_id=self.current_session.task_id,
            record_type=RecordType.FOCUS.value,
            start_at=self._focus_record_start.isoformat(),
            end_at=end.isoformat(),
            duration_seconds=duration,
        )
        self.session_repo.add_record(record)
        self._focus_record_start = None

    def _finish(self, elapsed_seconds: int, status: str, exit_reason: Optional[str]) -> Session:
        if not self.current_session:
            raise RuntimeError("No active session to finish.")
        self._close_focus_record()

        session = self.current_session
        session.actual_minutes = round(elapsed_seconds / 60, 2)
        session.ended_at = datetime.now().isoformat()
        session.status = status
        session.exit_reason = exit_reason
        self.session_repo.update(session)

        if session.task_id:
            self.task_repo.add_actual_minutes(session.task_id, session.actual_minutes)

        self.current_session = None
        return session

    def today_summary(self) -> dict:
        return self.session_repo.today_summary()
