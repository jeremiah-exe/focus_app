"""
Persistence layer for tasks. Contains only CRUD/query logic -
no business rules (those live in core/task_manager.py).
"""

from datetime import datetime
from typing import List, Optional

from database.database import Database
from database.models import Task


class TaskRepository:
    def __init__(self, database: Database):
        self.db = database

    def add(self, task: Task) -> Task:
        cursor = self.db.connection.execute(
            """
            INSERT INTO tasks (title, description, estimated_minutes, priority,
                                deadline, status, category, actual_minutes,
                                created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.title, task.description, task.estimated_minutes, task.priority,
                task.deadline, task.status, task.category, task.actual_minutes,
                task.created_at, task.completed_at,
            ),
        )
        self.db.connection.commit()
        task.id = cursor.lastrowid
        return task

    def update(self, task: Task) -> None:
        self.db.connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, estimated_minutes = ?, priority = ?,
                deadline = ?, status = ?, category = ?, actual_minutes = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                task.title, task.description, task.estimated_minutes, task.priority,
                task.deadline, task.status, task.category, task.actual_minutes,
                task.completed_at, task.id,
            ),
        )
        self.db.connection.commit()

    def delete(self, task_id: int) -> None:
        self.db.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.db.connection.commit()

    def get(self, task_id: int) -> Optional[Task]:
        row = self.db.connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return self._row_to_task(row) if row else None

    def list_all(self) -> List[Task]:
        rows = self.db.connection.execute(
            "SELECT * FROM tasks ORDER BY "
            "CASE status WHEN 'COMPLETED' THEN 1 WHEN 'CANCELLED' THEN 1 ELSE 0 END, "
            "CASE priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, "
            "created_at ASC"
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def list_active(self) -> List[Task]:
        rows = self.db.connection.execute(
            "SELECT * FROM tasks WHERE status NOT IN ('COMPLETED', 'CANCELLED') "
            "ORDER BY CASE priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, created_at ASC"
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def add_actual_minutes(self, task_id: int, minutes: float) -> None:
        self.db.connection.execute(
            "UPDATE tasks SET actual_minutes = actual_minutes + ? WHERE id = ?",
            (minutes, task_id),
        )
        self.db.connection.commit()

    @staticmethod
    def _row_to_task(row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            estimated_minutes=row["estimated_minutes"],
            priority=row["priority"],
            deadline=row["deadline"],
            status=row["status"],
            category=row["category"],
            actual_minutes=row["actual_minutes"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
