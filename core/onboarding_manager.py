"""
OnboardingManager: coordinates SettingsRepository and CommitmentRepository
to drive the app's first-run onboarding flow - wake/sleep time, preferred
focus/break lengths, minimum useful focus block length, and the user's
recurring weekly commitments (school, work, tuition, etc.) - and records
whether onboarding has been completed.

Follows the same pattern as TaskManager/SessionManager: business rules and
validation live here, the repositories stay pure persistence, and the UI
(not yet built) should only ever talk to this manager. No schema changes,
no PySide6 imports.
"""

from dataclasses import dataclass
from typing import List

from database.models import WeeklyCommitment
from database.repositories.settings_repository import SettingsRepository
from database.repositories.commitment_repository import CommitmentRepository


# Namespaced keys so onboarding data doesn't collide with other future
# uses of the generic key/value `settings` table.
_KEY_COMPLETE = "onboarding.complete"
_KEY_WAKE_TIME = "onboarding.wake_time"
_KEY_SLEEP_TIME = "onboarding.sleep_time"
_KEY_FOCUS_MINUTES = "onboarding.focus_minutes"
_KEY_BREAK_MINUTES = "onboarding.break_minutes"
_KEY_MIN_BLOCK_MINUTES = "onboarding.min_block_minutes"

# Bounds kept consistent with the ranges already used elsewhere in the app
# (DashboardScreen/ScheduleScreen focus & break QSpinBox ranges).
_MIN_FOCUS_MINUTES, _MAX_FOCUS_MINUTES = 5, 240
_MIN_BREAK_MINUTES, _MAX_BREAK_MINUTES = 0, 60
_MIN_BLOCK_MINUTES, _MAX_BLOCK_MINUTES = 1, 240

DEFAULT_WAKE_TIME = "07:00"
DEFAULT_SLEEP_TIME = "23:00"
DEFAULT_FOCUS_MINUTES = 50
DEFAULT_BREAK_MINUTES = 10
DEFAULT_MIN_BLOCK_MINUTES = 15


@dataclass
class OnboardingPreferences:
    """Plain data shape a future onboarding UI can bind to directly."""
    wake_time: str = DEFAULT_WAKE_TIME            # "HH:MM", 24-hour
    sleep_time: str = DEFAULT_SLEEP_TIME           # "HH:MM", 24-hour
    focus_minutes: int = DEFAULT_FOCUS_MINUTES
    break_minutes: int = DEFAULT_BREAK_MINUTES
    min_block_minutes: int = DEFAULT_MIN_BLOCK_MINUTES


class OnboardingManager:
    def __init__(self, settings_repository: SettingsRepository, commitment_repository: CommitmentRepository):
        self.settings_repo = settings_repository
        self.commitment_repo = commitment_repository

    # -- Onboarding state -------------------------------------------------

    def is_complete(self) -> bool:
        return self.settings_repo.get_bool(_KEY_COMPLETE, default=False)

    def complete_onboarding(self) -> None:
        self.settings_repo.set(_KEY_COMPLETE, "true")

    # -- Preferences --------------------------------------------------------

    def get_preferences(self) -> OnboardingPreferences:
        return OnboardingPreferences(
            wake_time=self.settings_repo.get(_KEY_WAKE_TIME, DEFAULT_WAKE_TIME),
            sleep_time=self.settings_repo.get(_KEY_SLEEP_TIME, DEFAULT_SLEEP_TIME),
            focus_minutes=self.settings_repo.get_int(_KEY_FOCUS_MINUTES, DEFAULT_FOCUS_MINUTES),
            break_minutes=self.settings_repo.get_int(_KEY_BREAK_MINUTES, DEFAULT_BREAK_MINUTES),
            min_block_minutes=self.settings_repo.get_int(
                _KEY_MIN_BLOCK_MINUTES, DEFAULT_MIN_BLOCK_MINUTES
            ),
        )

    def save_preferences(self, preferences: OnboardingPreferences) -> None:
        """Validate then persist the full preference set. Rejects
        obviously invalid values instead of silently storing them,
        consistent with CommitmentRepository's own validation."""
        self._validate_time(preferences.wake_time, "wake_time")
        self._validate_time(preferences.sleep_time, "sleep_time")
        self._validate_range(preferences.focus_minutes, _MIN_FOCUS_MINUTES, _MAX_FOCUS_MINUTES, "focus_minutes")
        self._validate_range(preferences.break_minutes, _MIN_BREAK_MINUTES, _MAX_BREAK_MINUTES, "break_minutes")
        self._validate_range(
            preferences.min_block_minutes, _MIN_BLOCK_MINUTES, _MAX_BLOCK_MINUTES, "min_block_minutes"
        )
        if preferences.min_block_minutes > preferences.focus_minutes:
            raise ValueError(
                "min_block_minutes cannot exceed focus_minutes "
                f"({preferences.min_block_minutes} > {preferences.focus_minutes})"
            )

        self.settings_repo.set(_KEY_WAKE_TIME, preferences.wake_time)
        self.settings_repo.set(_KEY_SLEEP_TIME, preferences.sleep_time)
        self.settings_repo.set(_KEY_FOCUS_MINUTES, preferences.focus_minutes)
        self.settings_repo.set(_KEY_BREAK_MINUTES, preferences.break_minutes)
        self.settings_repo.set(_KEY_MIN_BLOCK_MINUTES, preferences.min_block_minutes)

    def set_wake_sleep(self, wake_time: str, sleep_time: str) -> None:
        """Convenience partial-update: reads current preferences, applies
        the change, and re-validates/saves the whole set."""
        prefs = self.get_preferences()
        prefs.wake_time = wake_time
        prefs.sleep_time = sleep_time
        self.save_preferences(prefs)

    def set_focus_break_minutes(self, focus_minutes: int, break_minutes: int) -> None:
        prefs = self.get_preferences()
        prefs.focus_minutes = focus_minutes
        prefs.break_minutes = break_minutes
        self.save_preferences(prefs)

    def set_min_block_minutes(self, min_block_minutes: int) -> None:
        prefs = self.get_preferences()
        prefs.min_block_minutes = min_block_minutes
        self.save_preferences(prefs)

    # -- Weekly commitments (thin delegation to CommitmentRepository) -----

    def add_commitment(self, day_of_week: int, start_time: str, end_time: str, label: str = "") -> WeeklyCommitment:
        commitment = WeeklyCommitment(
            id=None,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            label=label.strip() if label else "",
        )
        return self.commitment_repo.add(commitment)

    def update_commitment(self, commitment: WeeklyCommitment) -> None:
        self.commitment_repo.update(commitment)

    def delete_commitment(self, commitment_id: int) -> None:
        self.commitment_repo.delete(commitment_id)

    def get_commitments(self) -> List[WeeklyCommitment]:
        return self.commitment_repo.list_all()

    def get_commitments_for_day(self, day_of_week: int) -> List[WeeklyCommitment]:
        return self.commitment_repo.list_for_day(day_of_week)

    # -- Validation helpers -------------------------------------------------
    # Mirrors CommitmentRepository's own validation style/format so the
    # rules a caller has to reason about stay consistent across the app.

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
    def _validate_range(value: int, min_value: int, max_value: int, field_name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or not (min_value <= value <= max_value):
            raise ValueError(f"{field_name} must be an int between {min_value} and {max_value}, got {value!r}")
