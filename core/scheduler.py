"""
Scheduler: turns a manual availability window + a list of tasks into
a suggested sequence of work/break blocks. Pure logic, no PySide6,
no database - fully unit-testable in isolation.

MVP scope: manual availability only (no calendar busy-periods yet -
that is Phase 6 in the roadmap). The scheduler never books over
anything; it simply lays tasks and breaks end-to-end within the window
and stops when the window runs out, flagging leftover work.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from database.models import Task, ScheduleBlock


@dataclass
class SchedulerInput:
    tasks: List[Task]
    window_start: str          # "HH:MM"
    window_end: str            # "HH:MM"
    focus_minutes: int = 50
    break_minutes: int = 10


@dataclass
class SchedulerResult:
    blocks: List[ScheduleBlock]
    total_available_minutes: int
    total_planned_minutes: int
    unscheduled_tasks: List[Task]


class Scheduler:
    """Generates suggestions only; the user always retains control."""

    def generate(self, scheduler_input: SchedulerInput) -> SchedulerResult:
        start = self._parse_time(scheduler_input.window_start)
        end = self._parse_time(scheduler_input.window_end)

        if end <= start:
            return SchedulerResult(blocks=[], total_available_minutes=0,
                                    total_planned_minutes=0,
                                    unscheduled_tasks=list(scheduler_input.tasks))

        total_available = int((end - start).total_seconds() // 60)
        cursor = start
        blocks: List[ScheduleBlock] = []
        unscheduled: List[Task] = []
        sessions_since_break = 0

        pending = [t for t in scheduler_input.tasks if t.status != "COMPLETED" and t.status != "CANCELLED"]

        for task in pending:
            remaining_minutes = task.estimated_minutes
            scheduled_any = False

            while remaining_minutes > 0:
                room_left = int((end - cursor).total_seconds() // 60)
                if room_left <= 0:
                    break

                chunk = min(remaining_minutes, scheduler_input.focus_minutes, room_left)
                if chunk <= 0:
                    break

                block_end = cursor + timedelta(minutes=chunk)
                blocks.append(ScheduleBlock(
                    label=task.title,
                    start=cursor.strftime("%H:%M"),
                    end=block_end.strftime("%H:%M"),
                    duration_minutes=chunk,
                    kind="TASK",
                    task_id=task.id,
                ))
                cursor = block_end
                remaining_minutes -= chunk
                scheduled_any = True
                sessions_since_break += 1

                # Insert a break if there's still room and more work to do.
                room_left = int((end - cursor).total_seconds() // 60)
                more_work = remaining_minutes > 0 or task != pending[-1]
                if more_work and room_left > 0 and sessions_since_break >= 1:
                    break_len = min(scheduler_input.break_minutes, room_left)
                    if break_len > 0:
                        break_end = cursor + timedelta(minutes=break_len)
                        blocks.append(ScheduleBlock(
                            label="Break",
                            start=cursor.strftime("%H:%M"),
                            end=break_end.strftime("%H:%M"),
                            duration_minutes=break_len,
                            kind="BREAK",
                        ))
                        cursor = break_end
                        sessions_since_break = 0

            if not scheduled_any or remaining_minutes > 0:
                unscheduled.append(task)

        # Leftover buffer time at the end of the window.
        room_left = int((end - cursor).total_seconds() // 60)
        if room_left > 0:
            blocks.append(ScheduleBlock(
                label="Buffer / free time",
                start=cursor.strftime("%H:%M"),
                end=end.strftime("%H:%M"),
                duration_minutes=room_left,
                kind="BUFFER",
            ))

        total_planned = sum(b.duration_minutes for b in blocks if b.kind == "TASK")

        return SchedulerResult(
            blocks=blocks,
            total_available_minutes=total_available,
            total_planned_minutes=total_planned,
            unscheduled_tasks=unscheduled,
        )

    @staticmethod
    def _parse_time(value: str) -> datetime:
        today = datetime.now().date()
        hour, minute = [int(p) for p in value.split(":")]
        return datetime(today.year, today.month, today.day, hour, minute)
