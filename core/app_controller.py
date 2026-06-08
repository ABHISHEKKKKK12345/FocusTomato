"""
AppController — the central orchestrator for FocusTomato.

Owns all core subsystems, drives the session lifecycle, and wires
signals between the engine and the UI layer.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

from core.models import SessionType, TimerState, Session
from core.timer_engine import TimerEngine
from core.settings_manager import SettingsManager
from core.task_manager import TaskManager
from core.stats_manager import StatsManager
from core.sound_manager import SoundManager
from core.notification_manager import NotificationManager

logger = logging.getLogger(__name__)


class AppController(QObject):
    """
    Drives the session lifecycle and exposes a clean API to the UI.

    Session sequence:
        focus → short_break → focus → ... → long_break (every N focus sessions)

    Signals (re-exported from engine or produced here):
        tick(remaining_seconds)
        state_changed(state_str)
        session_completed(session)
        session_started(session)
        session_type_changed(type_str)
        pomodoro_count_changed(count)
        active_task_changed(task_or_none)
    """

    tick = pyqtSignal(int)
    state_changed = pyqtSignal(str)
    session_completed = pyqtSignal(object)
    session_started = pyqtSignal(object)
    session_type_changed = pyqtSignal(str)
    pomodoro_count_changed = pyqtSignal(int)
    active_task_changed = pyqtSignal(object)

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app

        # Core subsystems
        self.settings = SettingsManager()
        self.tasks = TaskManager()
        self.stats = StatsManager()
        self.sounds = SoundManager()
        self.notifications = NotificationManager()

        # Timer engine
        self._engine = TimerEngine(self)
        self._engine.tick.connect(self.tick)
        self._engine.state_changed.connect(self.state_changed)
        self._engine.session_completed.connect(self._on_session_completed)
        self._engine.session_started.connect(self.session_started)

        # Session state
        self._pomodoro_count: int = 0      # focus sessions in current cycle
        self._total_today: int = 0
        self._active_task_id: Optional[str] = None
        self._pending_auto_start: Optional[SessionType] = None

        # Auto-start timer
        self._auto_start_timer = QTimer(self)
        self._auto_start_timer.setSingleShot(True)
        self._auto_start_timer.timeout.connect(self._do_auto_start)

        # Apply initial settings to subsystems
        self._apply_settings()

        # Main window (created lazily in start())
        self._main_window = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Create main window and show it."""
        # Import here to avoid circular imports at module load time
        from ui.main_window import MainWindow
        self._main_window = MainWindow(self)
        self._main_window.show()
        logger.info("Main window shown")

        # Configure engine with current settings
        self._configure_for_type(SessionType.FOCUS)

    def quit(self) -> None:
        logger.info("AppController.quit() called")
        self.sounds.cleanup()
        self._app.quit()

    # ------------------------------------------------------------------ #
    # Timer control (public API for UI)
    # ------------------------------------------------------------------ #

    def start_timer(self) -> None:
        self._engine.start()

    def pause_timer(self) -> None:
        self._engine.pause()

    def reset_timer(self) -> None:
        self._engine.stop()
        self._configure_for_type(self._engine.session_type)

    def skip_session(self) -> None:
        skipped = self._engine.skip()
        if skipped:
            self.stats.record_session(skipped)
        self._advance_session(force_advance=True)

    def toggle_pause(self) -> None:
        if self._engine.state == TimerState.RUNNING:
            self.pause_timer()
        else:
            self.start_timer()

    # ------------------------------------------------------------------ #
    # Session type
    # ------------------------------------------------------------------ #

    def set_session_type(self, session_type: SessionType) -> None:
        """Manually switch session type and reset."""
        self._engine.stop()
        self._configure_for_type(session_type)

    def _configure_for_type(self, session_type: SessionType) -> None:
        s = self.settings.settings
        durations = {
            SessionType.FOCUS: s.focus_duration,
            SessionType.SHORT_BREAK: s.short_break_duration,
            SessionType.LONG_BREAK: s.long_break_duration,
        }
        self._engine.configure(session_type, durations[session_type])
        self.session_type_changed.emit(session_type.value)
        logger.debug(f"Configured for {session_type.value}")

    def _advance_session(self, force_advance: bool = False) -> None:
        """Move to the logically next session."""
        current = self._engine.session_type
        s = self.settings.settings

        if current == SessionType.FOCUS:
            # Determine next break type
            if self._pomodoro_count % s.sessions_before_long_break == 0:
                next_type = SessionType.LONG_BREAK
            else:
                next_type = SessionType.SHORT_BREAK
            auto = s.auto_start_breaks
        else:
            next_type = SessionType.FOCUS
            auto = s.auto_start_focus

        self._configure_for_type(next_type)

        if auto and not force_advance:
            self._pending_auto_start = next_type
            self._auto_start_timer.start(1500)  # brief pause before auto-start
        else:
            self._pending_auto_start = None

    def _do_auto_start(self) -> None:
        if self._pending_auto_start is not None:
            logger.info(f"Auto-starting {self._pending_auto_start.value}")
            self._engine.start()
            self._pending_auto_start = None

    # ------------------------------------------------------------------ #
    # Session completion handler
    # ------------------------------------------------------------------ #

    def _on_session_completed(self, session: Session) -> None:
        # Attach active task info
        if self._active_task_id:
            task = self.tasks.get_by_id(self._active_task_id)
            if task:
                session.task_id = task.id
                session.task_title = task.title

        # Record to history
        self.stats.record_session(session)
        self.session_completed.emit(session)

        if session.session_type == SessionType.FOCUS:
            self._pomodoro_count += 1
            self._total_today += 1
            self.pomodoro_count_changed.emit(self._pomodoro_count)

            # Increment task counter
            if self._active_task_id:
                self.tasks.increment_pomodoro(self._active_task_id)

            # Sound + notification
            self.sounds.play_focus_complete()
            self.notifications.notify_focus_complete()

        elif session.session_type == SessionType.LONG_BREAK:
            self.sounds.play_break_complete()
            self.notifications.notify_long_break_complete()
        else:
            self.sounds.play_break_complete()
            self.notifications.notify_break_complete()

        self._advance_session()

    # ------------------------------------------------------------------ #
    # Task management
    # ------------------------------------------------------------------ #

    def set_active_task(self, task_id: Optional[str]) -> None:
        self._active_task_id = task_id
        task = self.tasks.get_by_id(task_id) if task_id else None
        self.active_task_changed.emit(task)

    def get_active_task_id(self) -> Optional[str]:
        return self._active_task_id

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    def apply_settings_changes(self) -> None:
        """Re-apply settings after user edits them."""
        self._apply_settings()
        # Reconfigure current session type with new durations
        if self._engine.state in (TimerState.IDLE, TimerState.COMPLETED):
            self._configure_for_type(self._engine.session_type)

    def _apply_settings(self) -> None:
        s = self.settings.settings
        self.sounds.set_enabled(s.sound_alerts)
        self.sounds.set_volume(s.sound_volume)
        self.sounds.set_theme(s.sound_theme)
        self.notifications.set_enabled(s.desktop_notifications)

    # ------------------------------------------------------------------ #
    # Read-only properties for UI
    # ------------------------------------------------------------------ #

    @property
    def engine(self) -> TimerEngine:
        return self._engine

    @property
    def pomodoro_count(self) -> int:
        return self._pomodoro_count

    @property
    def sessions_before_long_break(self) -> int:
        return self.settings.settings.sessions_before_long_break

    @property
    def main_window(self):
        return self._main_window
