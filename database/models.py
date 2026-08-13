"""
Typed dataclasses representing domain entities. Keeping these
separate from the sqlite rows/UI code makes the core logic testable
and independent of both the database and PySide6.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ENDED_EARLY = "ENDED_EARLY"


class RecordType(str, Enum):
    FOCUS = "FOCUS"
    BREAK = "BREAK"
    PAUSED = "PAUSED"


@dataclass
class Task:
    id: Optional[int]
    title: str
    description: str = ""
    estimated_minutes: int = 25
    priority: str = Priority.MEDIUM.value
    deadline: Optional[str] = None
    status: str = TaskStatus.TODO.value
    category: str = ""
    actual_minutes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class Session:
    id: Optional[int]
    task_id: Optional[int]
    planned_minutes: int
    actual_minutes: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    paused_seconds: int = 0
    status: str = SessionStatus.ACTIVE.value
    exit_reason: Optional[str] = None


@dataclass
class TimeRecord:
    id: Optional[int]
    session_id: int
    task_id: Optional[int]
    record_type: str
    start_at: str
    end_at: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ScheduleBlock:
    """A single suggested block of time in the day's plan."""
    label: str
    start: str          # "HH:MM"
    end: str             # "HH:MM"
    duration_minutes: int
    kind: str            # "TASK" | "BREAK" | "BUSY" | "BUFFER"
    task_id: Optional[int] = None


@dataclass
class WeeklyCommitment:
    """
    A single recurring, unavailable/busy period that repeats every week
    (e.g. school, work, tuition). day_of_week follows Python's
    datetime.weekday() convention: 0 = Monday ... 6 = Sunday.

    start_time/end_time are kept as zero-padded 24-hour "HH:MM" strings,
    matching the format already used by core.scheduler.Scheduler and
    database.models.ScheduleBlock, so they sort and compare correctly
    as plain strings and convert directly via Scheduler._parse_time-style
    parsing without any extra normalization step.
    """
    id: Optional[int]
    day_of_week: int          # 0 = Monday ... 6 = Sunday
    start_time: str            # "HH:MM"
    end_time: str               # "HH:MM"
    label: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
