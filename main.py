"""
Application entry point.

Wires together the Database, repositories, core managers, and the
MainWindow shell, then starts the Qt event loop. No business logic
lives here - this module only constructs objects in the correct
dependency order and hands control to Qt.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT
from database.database import Database
from database.repositories.task_repository import TaskRepository
from database.repositories.session_repository import SessionRepository
from core.task_manager import TaskManager
from core.session_manager import SessionManager
from core.focus_manager import FocusManager
from core.scheduler import Scheduler
from ui.main_window import MainWindow
from ui.theme import STYLESHEET


DB_PATH = Path(__file__).resolve().parent / "data" / "focus.db"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLESHEET)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    db = Database(DB_PATH)
    db.initialize()

    task_repo = TaskRepository(db)
    session_repo = SessionRepository(db)

    task_manager = TaskManager(task_repo)
    session_manager = SessionManager(session_repo, task_repo)
    focus_manager = FocusManager(session_manager)
    scheduler = Scheduler()

    window = MainWindow(task_manager, session_manager, focus_manager, scheduler)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
