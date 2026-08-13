"""
Persistence layer for recurring weekly commitments (fixed unavailable
periods such as school, work, or tuition that repeat every week).
Contains only CRUD/query logic and basic data-shape validation - no
scheduling logic. This repository does not depend on, and is not used
by, core.scheduler.Scheduler.
"""

from typing import List, Optional

from database.database import Database
from database.models import WeeklyCommitment


class CommitmentRepository:
    def __init__(self, database: Database):
        self.db = database

    def add(self, commitment: WeeklyCommitment) -> WeeklyCommitment:
        self._validate(commitment)
        cursor = self.db.connection.execute(
            """
            INSERT INTO weekly_commitments (day_of_week, start_time, end_time, label, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                commitment.day_of_week, commitment.start_time, commitment.end_time,
                commitment.label, commitment.created_at,
            ),
        )
        self.db.connection.commit()
        commitment.id = cursor.lastrowid
        return commitment

    def update(self, commitment: WeeklyCommitment) -> None:
        self._validate(commitment)
        self.db.connection.execute(
            """
            UPDATE weekly_commitments
            SET day_of_week = ?, start_time = ?, end_time = ?, label = ?
            WHERE id = ?
            """,
            (
                commitment.day_of_week, commitment.start_time, commitment.end_time,
                commitment.label, commitment.id,
            ),
        )
        self.db.connection.commit()

    def delete(self, commitment_id: int) -> None:
        self.db.connection.execute(
            "DELETE FROM weekly_commitments WHERE id = ?", (commitment_id,)
        )
        self.db.connection.commit()

    def list_all(self) -> List[WeeklyCommitment]:
        rows = self.db.connection.execute(
            "SELECT * FROM weekly_commitments ORDER BY day_of_week ASC, start_time ASC"
        ).fetchall()
        return [self._row_to_commitment(r) for r in rows]

    def list_for_day(self, day_of_week: int) -> List[WeeklyCommitment]:
        self._validate_day(day_of_week)
        rows = self.db.connection.execute(
            "SELECT * FROM weekly_commitments WHERE day_of_week = ? ORDER BY start_time ASC",
            (day_of_week,),
        ).fetchall()
        return [self._row_to_commitment(r) for r in rows]

    # -- Validation -----------------------------------------------------
    # No OnboardingManager/business-logic layer exists yet for this
    # feature, so the minimum data-shape validation needed to keep the
    # table consistent lives here, at the same level TaskManager would
    # normally own it once that layer exists.

    @staticmethod
    def _validate(commitment: WeeklyCommitment) -> None:
        CommitmentRepository._validate_day(commitment.day_of_week)
        CommitmentRepository._validate_time(commitment.start_time, "start_time")
        CommitmentRepository._validate_time(commitment.end_time, "end_time")
        if commitment.end_time <= commitment.start_time:
            raise ValueError(
                f"end_time ({commitment.end_time!r}) must be after "
                f"start_time ({commitment.start_time!r})"
            )

    @staticmethod
    def _validate_day(day_of_week: int) -> None:
        if not isinstance(day_of_week, int) or isinstance(day_of_week, bool) or not (0 <= day_of_week <= 6):
            raise ValueError(f"day_of_week must be an int 0-6, got {day_of_week!r}")

    @staticmethod
    def _validate_time(value: str, field_name: str) -> None:
        try:
            hour_str, minute_str = value.split(":")
            hour, minute = int(hour_str), int(minute_str)
            if not (len(hour_str) == 2 and len(minute_str) == 2 and 0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"{field_name} must be in 'HH:MM' 24-hour format, got {value!r}")

    @staticmethod
    def _row_to_commitment(row) -> WeeklyCommitment:
        return WeeklyCommitment(
            id=row["id"],
            day_of_week=row["day_of_week"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            label=row["label"],
            created_at=row["created_at"],
        )
