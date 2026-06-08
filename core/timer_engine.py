"""
Core timer engine for FocusTomato.
Uses QTimer for UI thread safety and a watchdog thread for drift correction.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from core.models import SessionType, TimerState, Session

logger = logging.getLogger(__name__)


class TimerEngine(QObject):
    """
    Precise countdown timer engine.

    Signals:
        tick(remaining_seconds)   - emitted every second
        state_changed(state)      - emitted when timer state changes
        session_completed(session)- emitted when session finishes naturally
        session_started(session)  - emitted when a new session starts
    """

    tick = pyqtSignal(int)
    state_changed = pyqtSignal(str)
    session_completed = pyqtSignal(object)
    session_started = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = TimerState.IDLE
        self._session_type = SessionType.FOCUS
        self._total_seconds = 25 * 60
        self._remaining_seconds = 25 * 60
        self._current_session: Optional[Session] = None
        self._interruptions = 0

        # Precise timing
        self._start_time: float = 0.0
        self._elapsed_at_pause: int = 0

        # Qt timer fires every 500ms for responsiveness; we track seconds ourselves
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(500)
        self._qtimer.timeout.connect(self._on_tick)
        self._last_emitted_second = -1

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def configure(self, session_type: SessionType, duration_seconds: int) -> None:
        """Configure timer for a new session without starting it."""
        if self._state == TimerState.RUNNING:
            self.stop()
        self._session_type = session_type
        self._total_seconds = duration_seconds
        self._remaining_seconds = duration_seconds
        self._elapsed_at_pause = 0
        self._interruptions = 0
        self._state = TimerState.IDLE
        self.state_changed.emit(self._state.value)
        self.tick.emit(self._remaining_seconds)

    def start(self) -> None:
        """Start or resume the timer."""
        if self._state == TimerState.RUNNING:
            return

        if self._state == TimerState.IDLE:
            # Brand-new session
            self._current_session = Session(
                session_type=self._session_type,
                duration_seconds=self._total_seconds,
                started_at=datetime.now().isoformat(),
            )
            self._elapsed_at_pause = 0
            self.session_started.emit(self._current_session)

        self._start_time = time.monotonic()
        self._state = TimerState.RUNNING
        self._last_emitted_second = -1
        self._qtimer.start()
        self.state_changed.emit(self._state.value)
        logger.debug(f"Timer started: {self._session_type.value} {self._remaining_seconds}s")

    def pause(self) -> None:
        """Pause a running timer."""
        if self._state != TimerState.RUNNING:
            return
        self._qtimer.stop()
        elapsed_now = time.monotonic() - self._start_time
        self._elapsed_at_pause += int(elapsed_now)
        self._remaining_seconds = max(0, self._total_seconds - self._elapsed_at_pause)
        self._interruptions += 1
        self._state = TimerState.PAUSED
        self.state_changed.emit(self._state.value)
        self.tick.emit(self._remaining_seconds)
        logger.debug(f"Timer paused at {self._remaining_seconds}s")

    def stop(self) -> None:
        """Stop and reset the timer without completing the session."""
        self._qtimer.stop()
        self._state = TimerState.IDLE
        self._remaining_seconds = self._total_seconds
        self._elapsed_at_pause = 0
        self._current_session = None
        self.state_changed.emit(self._state.value)
        self.tick.emit(self._remaining_seconds)

    def skip(self) -> Optional[Session]:
        """Skip current session, returning incomplete session data."""
        session = self._current_session
        if session:
            session.completed = False
            session.ended_at = datetime.now().isoformat()
            session.interruptions = self._interruptions
        self.stop()
        return session

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def remaining_seconds(self) -> int:
        return self._remaining_seconds

    @property
    def total_seconds(self) -> int:
        return self._total_seconds

    @property
    def session_type(self) -> SessionType:
        return self._session_type

    @property
    def progress(self) -> float:
        """0.0 (start) → 1.0 (end)"""
        if self._total_seconds == 0:
            return 0.0
        elapsed = self._total_seconds - self._remaining_seconds
        return min(1.0, elapsed / self._total_seconds)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _on_tick(self) -> None:
        if self._state != TimerState.RUNNING:
            return

        elapsed = time.monotonic() - self._start_time
        total_elapsed = self._elapsed_at_pause + int(elapsed)
        remaining = max(0, self._total_seconds - total_elapsed)

        # Emit only on second boundaries to avoid redundant UI updates
        if remaining != self._last_emitted_second:
            self._last_emitted_second = remaining
            self._remaining_seconds = remaining
            self.tick.emit(remaining)

        if remaining == 0:
            self._complete_session()

    def _complete_session(self) -> None:
        self._qtimer.stop()
        self._state = TimerState.COMPLETED
        self.state_changed.emit(self._state.value)

        if self._current_session:
            self._current_session.completed = True
            self._current_session.ended_at = datetime.now().isoformat()
            self._current_session.interruptions = self._interruptions
            session = self._current_session
        else:
            session = Session(
                session_type=self._session_type,
                duration_seconds=self._total_seconds,
                completed=True,
                ended_at=datetime.now().isoformat(),
            )

        logger.info(f"Session completed: {session.session_type.value}")
        self.session_completed.emit(session)
        self._current_session = None
