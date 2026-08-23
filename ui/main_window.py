"""
MainWindow: the Normal Mode shell. Holds a sidebar for navigation and
a QStackedWidget for the Dashboard / Schedule / Statistics screens.
Focus Mode is launched as its own fullscreen window rather than a
stack page, so it can visually take over the whole screen.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QButtonGroup,
)

from app.config import APP_NAME, MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT
from core.task_manager import TaskManager
from core.session_manager import SessionManager
from core.focus_manager import FocusManager
from core.scheduler import Scheduler
from core.onboarding_manager import OnboardingManager
from ui.dashboard.dashboard import DashboardScreen
from ui.schedule.schedule_screen import ScheduleScreen
from ui.statistics.statistics_screen import StatisticsScreen
from ui.focus.focus_screen import FocusScreen


class MainWindow(QMainWindow):
    def __init__(
        self,
        task_manager: TaskManager,
        session_manager: SessionManager,
        focus_manager: FocusManager,
        scheduler: Scheduler,
        onboarding_manager: OnboardingManager,
    ):
        super().__init__()
        self.task_manager = task_manager
        self.session_manager = session_manager
        self.focus_manager = focus_manager
        self.scheduler = scheduler
        self.onboarding_manager = onboarding_manager
        self.focus_window: FocusScreen | None = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 24, 16, 16)
        side_layout.setSpacing(4)

        logo = QLabel("FOCUS")
        logo.setStyleSheet("font-size: 16px; font-weight: 700; letter-spacing: 2px;")
        side_layout.addWidget(logo)
        side_layout.addSpacing(24)

        self.stack = QStackedWidget()

        self.dashboard = DashboardScreen(self.task_manager, self.session_manager, self._launch_focus)
        self.schedule_screen = ScheduleScreen(self.task_manager, self.scheduler, self.onboarding_manager)
        self.statistics_screen = StatisticsScreen(self.session_manager)

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.schedule_screen)
        self.stack.addWidget(self.statistics_screen)

        nav_items = [
            ("Dashboard", 0),
            ("Schedule", 1),
            ("Statistics", 2),
        ]
        self.nav_buttons = []
        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self._navigate(i))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        side_layout.addStretch()

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self._navigate(0)

    def _navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("NavButtonActive" if i == index else "NavButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if index == 0:
            self.dashboard.refresh()
        elif index == 1:
            self.schedule_screen.refresh()
        elif index == 2:
            self.statistics_screen.refresh()

    def _launch_focus(self, task, duration_minutes: int) -> None:
        self.focus_window = FocusScreen(
            focus_manager=self.focus_manager,
            task=task,
            duration_minutes=duration_minutes,
            on_close=self._on_focus_closed,
        )
        self.focus_window.showFullScreen()

    def _on_focus_closed(self) -> None:
        self.focus_window = None
        self.show()
        self.dashboard.refresh()
        self.statistics_screen.refresh()