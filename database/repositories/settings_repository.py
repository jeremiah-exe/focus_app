"""
Persistence layer for simple key-value application settings and
onboarding state, backed by the existing `settings` table. Contains
only read/write + type conversion for that table - no business rules
(those belong in a future core manager, same as TaskRepository vs
TaskManager).
"""

from typing import Optional

from database.database import Database


class SettingsRepository:
    def __init__(self, database: Database):
        self.db = database

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.db.connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set(self, key: str, value) -> None:
        self.db.connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        self.db.connection.commit()

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.strip().lower() in ("1", "true", "yes", "on")

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
