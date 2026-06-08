"""
TimerWidget — main timer panel.

Fixes applied (v1.2):
  - QFont("Georgia", 16) replaced with cross-platform display font helper
  - Reset/Skip buttons: removed fixed width (was 64px), use min-width + padding instead
  - QToolButton unused import removed
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QButtonGroup, QFrame,
)

from core.models import SessionType, TimerState
from ui.widgets import ProgressRing, SessionDotRow, PillButton, _display_font

if TYPE_CHECKING:
    from core.app_controller import AppController

logger = logging.getLogger(__name__)

SESSION_LABELS = {
    SessionType.FOCUS: "Focus",
    SessionType.SHORT_BREAK: "Short Break",
    SessionType.LONG_BREAK: "Long Break",
}

SESSION_RING_LABELS = {
    SessionType.FOCUS: "FOCUS",
    SessionType.SHORT_BREAK: "BREAK",
    SessionType.LONG_BREAK: "LONG BREAK",
}


def _fmt_time(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    return f"{m:02d}:{s:02d}"


class TimerWidget(QWidget):
    """Main timer panel."""

    session_type_requested = pyqtSignal(str)

    def __init__(self, controller: "AppController",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._current_type = SessionType.FOCUS
        self._setup_ui()
        self._connect_signals()
        self._refresh_theme()

    # ── Build UI ────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(0)

        # ── Session-type pills ──
        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        pill_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._pill_group = QButtonGroup(self)
        self._pill_group.setExclusive(True)
        self._pills: dict[SessionType, PillButton] = {}

        for stype in [SessionType.FOCUS, SessionType.SHORT_BREAK, SessionType.LONG_BREAK]:
            btn = PillButton(SESSION_LABELS[stype])
            self._pills[stype] = btn
            self._pill_group.addButton(btn)
            pill_row.addWidget(btn)
            btn.clicked.connect(lambda checked, st=stype: self._on_pill_clicked(st))

        self._pills[SessionType.FOCUS].setChecked(True)
        root.addLayout(pill_row)
        root.addSpacing(24)

        # ── Progress ring (hero element) ──
        self._ring = ProgressRing()
        self._ring.set_time_text("25:00")
        self._ring.set_label("FOCUS")
        root.addWidget(self._ring, 1, Qt.AlignmentFlag.AlignCenter)
        root.addSpacing(18)

        # ── Cycle progress dots ──
        dots_row = QHBoxLayout()
        dots_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dots = SessionDotRow()
        s = self._ctrl.settings.settings
        self._dots.set_counts(0, s.sessions_before_long_break)
        dots_row.addWidget(self._dots)
        root.addLayout(dots_row)
        root.addSpacing(6)

        self._cycle_label = QLabel("Session 1 of 4")
        self._cycle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cycle_label.setObjectName("CycleLabel")
        cf = QFont()
        cf.setPointSize(10)
        self._cycle_label.setFont(cf)
        root.addWidget(self._cycle_label)
        root.addSpacing(24)

        # ── Controls ──
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Reset — auto-width, not fixed, so it never clips
        self._btn_reset = QPushButton("Reset")
        self._btn_reset.setProperty("flat", True)
        self._btn_reset.setFixedHeight(44)
        self._btn_reset.setMinimumWidth(70)
        self._btn_reset.setToolTip("Reset timer to the start of this session")
        self._btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)

        # Primary action — display font for the main CTA
        self._btn_start = QPushButton("Start")
        self._btn_start.setProperty("primary", True)
        self._btn_start.setFixedSize(140, 52)
        self._btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_start.setFont(_display_font(16))
        self._btn_start.setToolTip("Start / pause the timer  (Space)")

        # Skip — auto-width
        self._btn_skip = QPushButton("Skip")
        self._btn_skip.setProperty("flat", True)
        self._btn_skip.setFixedHeight(44)
        self._btn_skip.setMinimumWidth(70)
        self._btn_skip.setToolTip("Skip to the next session")
        self._btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)

        controls.addWidget(self._btn_reset)
        controls.addWidget(self._btn_start)
        controls.addWidget(self._btn_skip)
        root.addLayout(controls)
        root.addSpacing(20)

        # ── Active task banner ──
        self._task_banner = QFrame()
        self._task_banner.setObjectName("TaskBanner")
        task_layout = QHBoxLayout(self._task_banner)
        task_layout.setContentsMargins(14, 10, 14, 10)
        task_layout.setSpacing(10)

        self._task_icon = QLabel("○")
        self._task_icon.setFixedWidth(20)
        self._task_label = QLabel("No task selected — go to Tasks to pick one")
        self._task_label.setObjectName("TaskBannerLabel")
        self._task_label.setWordWrap(False)
        task_layout.addWidget(self._task_icon)
        task_layout.addWidget(self._task_label, 1)
        root.addWidget(self._task_banner)

    # ── Signals ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        engine = self._ctrl.engine
        engine.tick.connect(self._on_tick)
        engine.state_changed.connect(self._on_state_changed)
        self._ctrl.session_type_changed.connect(self._on_session_type_changed)
        self._ctrl.pomodoro_count_changed.connect(self._on_pomodoro_count_changed)
        self._ctrl.active_task_changed.connect(self._on_active_task_changed)
        self._btn_start.clicked.connect(self._ctrl.toggle_pause)
        self._btn_reset.clicked.connect(self._ctrl.reset_timer)
        self._btn_skip.clicked.connect(self._ctrl.skip_session)

    # ── Handlers ─────────────────────────────────────────────────────

    def _on_tick(self, remaining: int) -> None:
        self._ring.set_time_text(_fmt_time(remaining))
        self._ring.set_progress(self._ctrl.engine.progress)

    def _on_state_changed(self, state_str: str) -> None:
        state = TimerState(state_str)
        if state == TimerState.RUNNING:
            self._btn_start.setText("Pause")
            self._ring.set_paused(False)
        elif state == TimerState.PAUSED:
            self._btn_start.setText("Resume")
            self._ring.set_paused(True)
        elif state in (TimerState.IDLE, TimerState.COMPLETED):
            self._btn_start.setText("Start")
            self._ring.set_paused(False)

    def _on_session_type_changed(self, type_str: str) -> None:
        stype = SessionType(type_str)
        self._current_type = stype
        self._pills[stype].setChecked(True)
        self._ring.set_label(SESSION_RING_LABELS[stype])

        from ui.theme import get_palette
        palette = get_palette(self._ctrl.settings.settings.theme)
        colour_map = {
            SessionType.FOCUS: palette.focus_color,
            SessionType.SHORT_BREAK: palette.short_break_color,
            SessionType.LONG_BREAK: palette.long_break_color,
        }
        self._ring.set_ring_color(colour_map.get(stype, palette.accent))

        for st, pill in self._pills.items():
            pill.set_active_color(colour_map.get(st, palette.accent))

        total = self._ctrl.engine.total_seconds
        self._ring.set_time_text(_fmt_time(total))
        self._ring.set_progress(0.0, animate=False)

    def _on_pomodoro_count_changed(self, count: int) -> None:
        s = self._ctrl.settings.settings
        total = s.sessions_before_long_break
        cycle_pos = count % total
        self._dots.set_counts(cycle_pos, total)
        session_num = cycle_pos + 1
        if cycle_pos < total:
            self._cycle_label.setText(
                f"Session {session_num} of {total} — "
                f"{total - cycle_pos} until long break"
            )
        else:
            self._cycle_label.setText("Long break next!")

    def _on_active_task_changed(self, task) -> None:
        if task:
            self._task_label.setText(task.title)
            self._task_icon.setText("🎯")
            if self._ctrl.engine.state == TimerState.RUNNING:
                self._ring.set_sub_text(task.title)
        else:
            self._task_label.setText("No task selected — go to Tasks to pick one")
            self._task_icon.setText("○")
            self._ring.set_sub_text("")

    def _on_pill_clicked(self, stype: SessionType) -> None:
        if stype != self._current_type:
            self._ctrl.set_session_type(stype)

    # ── Theme ────────────────────────────────────────────────────────

    def _refresh_theme(self) -> None:
        s = self._ctrl.settings.settings
        self._ring.set_theme(s.theme == "dark")

        from ui.theme import get_palette
        p = get_palette(s.theme)
        self._dots.set_colors(p.accent, p.ring_track)

        self._task_banner.setStyleSheet(f"""
            #TaskBanner {{
                background: {p.bg_elevated};
                border: 1px solid {p.border};
                border-radius: 10px;
            }}
            #TaskBannerLabel {{
                color: {p.text_secondary};
                font-size: 12px;
            }}
        """)
        self._cycle_label.setStyleSheet(f"color: {p.text_disabled};")

        for pill in self._pills.values():
            pill.set_inactive_text_color(p.text_secondary)
            pill.set_checked_text_color(p.accent_text)

    def refresh_theme(self) -> None:
        self._refresh_theme()
        self._on_session_type_changed(self._current_type.value)
