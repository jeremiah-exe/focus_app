"""
TaskManager: business rules for tasks (CRUD, status transitions, timing).
The UI never talks to TaskRepository directly.
"""

from datetime import datetime
from typing import List, Optional

from database.models import Task, TaskStatus
from database.repositories.task_repository import TaskRepository


class TaskManager:
    def __init__(self, task_repository: TaskRepository):
        self.repo = task_repository

    def create_task(
        self,
        title: str,
        description: str = "",
        estimated_minutes: int = 25,
        priority: str = "MEDIUM",
        deadline: Optional[str] = None,
        category: str = "",
    ) -> Task:
        task = Task(
            id=None,
            title=title.strip(),
            description=description.strip(),
            estimated_minutes=max(1, estimated_minutes),
            priority=priority,
            deadline=deadline,
            category=category.strip(),
        )
        return self.repo.add(task)

    def update_task(self, task: Task) -> None:
        self.repo.update(task)

    def delete_task(self, task_id: int) -> None:
        self.repo.delete(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        return self.repo.get(task_id)

    def list_active_tasks(self) -> List[Task]:
        return self.repo.list_active()

    def list_all_tasks(self) -> List[Task]:
        return self.repo.list_all()

    def mark_completed(self, task_id: int) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now().isoformat()
        self.repo.update(task)

    def mark_in_progress(self, task_id: int) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        if task.status == TaskStatus.TODO.value:
            task.status = TaskStatus.IN_PROGRESS.value
            self.repo.update(task)

    def set_status(self, task_id: int, status: str) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        task.status = status
        if status == TaskStatus.COMPLETED.value:
            task.completed_at = datetime.now().isoformat()
        self.repo.update(task)

    def record_time_spent(self, task_id: int, minutes: float) -> None:
        if task_id is None or minutes <= 0:
            return
        self.repo.add_actual_minutes(task_id, minutes)
