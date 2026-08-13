"""
Thin wrapper around sqlite3 responsible for connection management
and schema creation. No business logic lives here.
"""

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    estimated_minutes INTEGER DEFAULT 25,
    priority TEXT DEFAULT 'MEDIUM',
    deadline TEXT,
    status TEXT DEFAULT 'TODO',
    category TEXT DEFAULT '',
    actual_minutes INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    planned_minutes INTEGER NOT NULL,
    actual_minutes REAL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    paused_seconds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    exit_reason TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks (id)
);

CREATE TABLE IF NOT EXISTS time_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    task_id INTEGER,
    record_type TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    duration_seconds REAL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions (id),
    FOREIGN KEY (task_id) REFERENCES tasks (id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS weekly_commitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""


class Database:
    """Owns the SQLite connection lifecycle."""

    def __init__(self, path: Path):
        self.path = path
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def initialize(self) -> None:
        """Create tables if they do not already exist."""
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
