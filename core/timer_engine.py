"""
TimerEngine: a countdown timer decoupled from any UI. It emits Qt
signals so widgets can subscribe without the engine knowing about them.
Uses QTimer (1s tick) rather than raw threads to stay on the Qt event loop.
"""

from PySide6.QtCore import QObject, QTimer, Signal


class TimerEngine(QObject):
    tick = Signal(int)          # remaining_seconds
    finished = Signal()
    paused = Signal()
    resumed = Signal()

    def __init__(self):
        super().__init__()
        self._qtimer = QTimer()
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._on_tick)

        self.total_seconds = 0
        self.remaining_seconds = 0
        self.is_running = False
        self.is_paused = False
        self.elapsed_paused_seconds = 0

    def start(self, duration_minutes: int) -> None:
        self.total_seconds = int(duration_minutes * 60)
        self.remaining_seconds = self.total_seconds
        self.elapsed_paused_seconds = 0
        self.is_running = True
        self.is_paused = False
        self._qtimer.start()

    def pause(self) -> None:
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self._qtimer.stop()
            self.paused.emit()

    def resume(self) -> None:
        if self.is_running and self.is_paused:
            self.is_paused = False
            self._qtimer.start()
            self.resumed.emit()

    def stop(self) -> None:
        self.is_running = False
        self.is_paused = False
        self._qtimer.stop()

    def elapsed_seconds(self) -> int:
        return self.total_seconds - self.remaining_seconds

    def _on_tick(self) -> None:
        if self.remaining_seconds <= 0:
            self.stop()
            self.finished.emit()
            return
        self.remaining_seconds -= 1
        self.tick.emit(self.remaining_seconds)
        if self.remaining_seconds <= 0:
            self.stop()
            self.finished.emit()

    @staticmethod
    def format_seconds(seconds: int) -> str:
        seconds = max(0, seconds)
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
