"""
Persistence layer for focus sessions, time records, and the
aggregate queries used by the statistics screen.
"""

from datetime import datetime, date
from typing import List, Optional

from database.database import Database
from database.models import Session, TimeRecord


class SessionRepository:
    def __init__(self, database: Database):
        self.db = database

    # -- Sessions ---------------------------------------------------

    def add(self, session: Session) -> Session:
        cursor = self.db.connection.execute(
            """
            INSERT INTO sessions (task_id, planned_minutes, actual_minutes,
                                   started_at, ended_at, paused_seconds, status, exit_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.task_id, session.planned_minutes, session.actual_minutes,
                session.started_at, session.ended_at, session.paused_seconds,
                session.status, session.exit_reason,
            ),
        )
        self.db.connection.commit()
        session.id = cursor.lastrowid
        return session

    def update(self, session: Session) -> None:
        self.db.connection.execute(
            """
            UPDATE sessions
            SET actual_minutes = ?, ended_at = ?, paused_seconds = ?,
                status = ?, exit_reason = ?
            WHERE id = ?
            """,
            (
                session.actual_minutes, session.ended_at, session.paused_seconds,
                session.status, session.exit_reason, session.id,
            ),
        )
        self.db.connection.commit()

    def list_for_day(self, day: date) -> List[Session]:
        prefix = day.isoformat()
        rows = self.db.connection.execute(
            "SELECT * FROM sessions WHERE started_at LIKE ? ORDER BY started_at ASC",
            (f"{prefix}%",),
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    # -- Time records -------------------------------------------------

    def add_record(self, record: TimeRecord) -> TimeRecord:
        cursor = self.db.connection.execute(
            """
            INSERT INTO time_records (session_id, task_id, record_type, start_at, end_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id, record.task_id, record.record_type,
                record.start_at, record.end_at, record.duration_seconds,
            ),
        )
        self.db.connection.commit()
        record.id = cursor.lastrowid
        return record

    # -- Aggregates for statistics -----------------------------------

    def today_summary(self) -> dict:
        prefix = date.today().isoformat()
        row = self.db.connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN actual_minutes ELSE 0 END), 0) AS focused_minutes,
                COALESCE(SUM(CASE WHEN status IN ('COMPLETED', 'ENDED_EARLY') THEN actual_minutes ELSE 0 END), 0) AS total_actual,
                COUNT(*) AS session_count,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0) AS completed_count,
                COALESCE(MAX(CASE WHEN status = 'COMPLETED' THEN actual_minutes ELSE 0 END), 0) AS longest_session
            FROM sessions
            WHERE started_at LIKE ?
            """,
            (f"{prefix}%",),
        ).fetchone()
        return dict(row)

    @staticmethod
    def _row_to_session(row) -> Session:
        return Session(
            id=row["id"],
            task_id=row["task_id"],
            planned_minutes=row["planned_minutes"],
            actual_minutes=row["actual_minutes"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            paused_seconds=row["paused_seconds"],
            status=row["status"],
            exit_reason=row["exit_reason"],
        )
