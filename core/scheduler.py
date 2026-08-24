"""
Scheduler: turns a manual availability window + a list of tasks into
a suggested sequence of work/break blocks. Pure logic, no PySide6,
no database - fully unit-testable in isolation.

MVP scope: manual availability, plus optional pre-normalized busy
intervals supplied by the caller (Stage 1). The scheduler does not
know or care where busy intervals came from - weekly commitments,
calendar events, and manually blocked time can all feed the same
`busy_intervals` field later without touching this module again.
Wiring an actual source (e.g. weekly commitments) into a caller is
out of scope here - see Stage 2.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from database.models import Task, ScheduleBlock


@dataclass
class BusyInterval:
    """A single normalized, unavailable period inside the scheduling
    window. Deliberately source-agnostic: the Scheduler treats this as
    opaque input and never depends on where it came from (a weekly
    commitment, a calendar event, a manual block, ...). `label` is
    optional and purely cosmetic - it ends up on the resulting BUSY
    ScheduleBlock if provided."""
    start: str          # "HH:MM"
    end: str             # "HH:MM"
    label: str = ""


@dataclass
class SchedulerInput:
    tasks: List[Task]
    window_start: str          # "HH:MM"
    window_end: str            # "HH:MM"
    focus_minutes: int = 50
    break_minutes: int = 10
    # Optional and defaults to empty so every existing caller keeps
    # working, and scheduling behavior is unchanged, without passing this.
    busy_intervals: List[BusyInterval] = field(default_factory=list)


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

        merged_busy = self._normalize_busy_intervals(scheduler_input.busy_intervals, start, end)
        timeline = self._build_timeline(start, end, merged_busy)

        pending = [t for t in scheduler_input.tasks if t.status != "COMPLETED" and t.status != "CANCELLED"]

        blocks: List[ScheduleBlock] = []
        unscheduled: List[Task] = []
        total_available = 0

        task_ptr = 0
        remaining_minutes = 0

        def prime_next_task() -> None:
            nonlocal task_ptr, remaining_minutes
            while task_ptr < len(pending) and pending[task_ptr].estimated_minutes <= 0:
                unscheduled.append(pending[task_ptr])
                task_ptr += 1
            remaining_minutes = pending[task_ptr].estimated_minutes if task_ptr < len(pending) else 0

        prime_next_task()

        for entry in timeline:
            if entry[0] == "BUSY":
                _, seg_start, seg_end, label = entry
                blocks.append(ScheduleBlock(
                    label=label or "Busy",
                    start=seg_start.strftime("%H:%M"),
                    end=seg_end.strftime("%H:%M"),
                    duration_minutes=int((seg_end - seg_start).total_seconds() // 60),
                    kind="BUSY",
                ))
                continue

            _, seg_start, seg_end = entry
            total_available += int((seg_end - seg_start).total_seconds() // 60)
            cursor = seg_start
            sessions_since_break = 0

            while task_ptr < len(pending) and remaining_minutes > 0:
                room_left = int((seg_end - cursor).total_seconds() // 60)
                if room_left <= 0:
                    break

                chunk = min(remaining_minutes, scheduler_input.focus_minutes, room_left)
                if chunk <= 0:
                    break

                task = pending[task_ptr]
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
                sessions_since_break += 1

                room_left = int((seg_end - cursor).total_seconds() // 60)
                more_work = remaining_minutes > 0 or task_ptr != len(pending) - 1
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

                if remaining_minutes <= 0:
                    task_ptr += 1
                    prime_next_task()

            leftover = int((seg_end - cursor).total_seconds() // 60)
            if leftover > 0:
                blocks.append(ScheduleBlock(
                    label="Buffer / free time",
                    start=cursor.strftime("%H:%M"),
                    end=seg_end.strftime("%H:%M"),
                    duration_minutes=leftover,
                    kind="BUFFER",
                ))

        unscheduled.extend(pending[task_ptr:])

        total_planned = sum(b.duration_minutes for b in blocks if b.kind == "TASK")

        return SchedulerResult(
            blocks=blocks,
            total_available_minutes=total_available,
            total_planned_minutes=total_planned,
            unscheduled_tasks=unscheduled,
        )

    @classmethod
    def _normalize_busy_intervals(
        cls,
        busy_intervals: List[BusyInterval],
        window_start: datetime,
        window_end: datetime,
    ) -> List[Tuple[datetime, datetime, str]]:
        parsed: List[Tuple[datetime, datetime, str]] = []
        for interval in busy_intervals:
            b_start = cls._parse_time(interval.start)
            b_end = cls._parse_time(interval.end)
            if b_end <= b_start:
                raise ValueError(
                    f"BusyInterval end ({interval.end!r}) must be after "
                    f"start ({interval.start!r})"
                )

            clipped_start = max(b_start, window_start)
            clipped_end = min(b_end, window_end)
            if clipped_end <= clipped_start:
                continue
            parsed.append((clipped_start, clipped_end, interval.label))

        parsed.sort(key=lambda item: item[0])

        merged: List[Tuple[datetime, datetime, str]] = []
        for b_start, b_end, label in parsed:
            if merged and b_start < merged[-1][1]:
                # Genuine overlap (not just touching) - combine into one
                # block. Adjacent/touching intervals are intentionally
                # kept separate below so each commitment keeps its own
                # label and time range.
                prev_start, prev_end, prev_label = merged[-1]
                merged[-1] = (prev_start, max(prev_end, b_end), prev_label)
            else:
                merged.append((b_start, b_end, label))
        return merged

    @staticmethod
    def _build_timeline(
        window_start: datetime,
        window_end: datetime,
        merged_busy: List[Tuple[datetime, datetime, str]],
    ) -> List[tuple]:
        timeline: List[tuple] = []
        cursor = window_start
        for b_start, b_end, label in merged_busy:
            if b_start > cursor:
                timeline.append(("FREE", cursor, b_start))
            timeline.append(("BUSY", b_start, b_end, label))
            cursor = max(cursor, b_end)
        if cursor < window_end:
            timeline.append(("FREE", cursor, window_end))
        return timeline

    @staticmethod
    def _parse_time(value: str) -> datetime:
        today = datetime.now().date()
        hour, minute = [int(p) for p in value.split(":")]
        return datetime(today.year, today.month, today.day, hour, minute)