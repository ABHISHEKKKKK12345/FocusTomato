"""
SettingsDialog — comprehensive settings panel.

Tabs:
  Timer       — durations, cycle length, auto-start behaviour
  Sound       — alerts toggle, volume, tone style
  Alerts      — desktop notifications
  Appearance  — colour theme, accent colour, system tray
  Data        — storage info, history management, about
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QSpinBox, QSlider, QComboBox,
    QFrame, QMessageBox, QSizePolicy, QGroupBox, QColorDialog,
    QScrollArea,
)

from ui.widgets import AnimatedToggle, _display_font

if TYPE_CHECKING:
    from core.app_controller import AppController

logger = logging.getLogger(__name__)


class _Row(QWidget):
    """Horizontal label + control row with optional description."""

    def __init__(self, label: str, control: QWidget,
                 description: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(2)

        h = QHBoxLayout()
        h.setSpacing(12)
        lbl = QLabel(label)
        lbl_f = QFont()
        lbl_f.setPointSize(13)
        lbl.setFont(lbl_f)
        h.addWidget(lbl, 1)
        h.addWidget(control)
        v.addLayout(h)

        if description:
            desc = QLabel(description)
            desc.setObjectName("SettingDesc")
            desc.setWordWrap(True)
            v.addWidget(desc)


class _ToggleRow(QWidget):
    """Label + AnimatedToggle with optional description."""

    toggled = pyqtSignal(bool)

    def __init__(self, label: str, checked: bool,
                 description: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(2)

        h = QHBoxLayout()
        h.setSpacing(12)

        lbl = QLabel(label)
        lbl_f = QFont()
        lbl_f.setPointSize(13)
        lbl.setFont(lbl_f)
        h.addWidget(lbl, 1)

        self._toggle = AnimatedToggle()
        self._toggle.setChecked(checked)
        # Animate thumb to correct position on load
        self._toggle._thumb_x = float(self._toggle.width() - 24) if checked else 2.0
        self._toggle.toggled_state.connect(self.toggled)
        h.addWidget(self._toggle)
        v.addLayout(h)

        if description:
            desc = QLabel(description)
            desc.setObjectName("SettingDesc")
            desc.setWordWrap(True)
            v.addWidget(desc)

    def is_checked(self) -> bool:
        return self._toggle.isChecked()

    def set_checked(self, value: bool) -> None:
        self._toggle.setChecked(value)
        self._toggle._thumb_x = float(self._toggle.width() - 24) if value else 2.0
        self._toggle.update()


class _DurationRow(QWidget):
    """Label + minute spinbox row."""

    def __init__(self, label: str, value_min: int,
                 min_m: int = 1, max_m: int = 120,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(12)

        lbl = QLabel(label)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        h.addWidget(lbl)

        self._spin = QSpinBox()
        self._spin.setRange(min_m, max_m)
        self._spin.setValue(value_min)
        self._spin.setSuffix(" min")
        self._spin.setFixedWidth(100)
        h.addWidget(self._spin)

    @property
    def value_seconds(self) -> int:
        return self._spin.value() * 60

    @property
    def spin(self) -> QSpinBox:
        return self._spin


def _make_group(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    g = QGroupBox(title)
    lay = QVBoxLayout(g)
    lay.setSpacing(2)
    lay.setContentsMargins(12, 12, 12, 8)
    return g, lay


class SettingsDialog(QDialog):
    """Full settings panel dialog."""

    settings_changed = pyqtSignal()

    def __init__(self, controller: "AppController",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self.setWindowTitle("Settings")
        self.resize(500, 450)
        self.setMinimumSize(450, 380)
        self.setModal(True)
        self._setup_ui()
        self._load_values()

    def _scrollable(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("SettingsTitleBar")
        title_bar.setFixedHeight(52)
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(24, 0, 20, 0)
        title_lbl = QLabel("Settings")
        tf = _display_font(17)  # cross-platform serif
        title_lbl.setFont(tf)
        tb.addWidget(title_lbl)
        tb.addStretch()
        root.addWidget(title_bar)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._scrollable(self._build_timer_tab()), "Timer")
        self._tabs.addTab(self._scrollable(self._build_sound_tab()), "Sound")
        self._tabs.addTab(self._scrollable(self._build_notif_tab()), "Alerts")
        self._tabs.addTab(self._scrollable(self._build_appearance_tab()), "Appearance")
        self._tabs.addTab(self._scrollable(self._build_data_tab()), "Data")

        # Footer
        footer = QWidget()
        footer.setObjectName("SettingsFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 12, 20, 16)
        fl.setSpacing(8)

        self._btn_reset = QPushButton("Reset to Defaults")
        self._btn_reset.setProperty("danger", True)
        self._btn_reset.setFixedHeight(34)
        fl.addWidget(self._btn_reset)
        fl.addStretch()

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setFixedHeight(34)
        self._btn_save = QPushButton("Save Changes")
        self._btn_save.setProperty("primary", True)
        self._btn_save.setFixedSize(140, 34)
        fl.addWidget(self._btn_cancel)
        fl.addWidget(self._btn_save)
        root.addWidget(footer)

        self._btn_cancel.clicked.connect(self.reject)
        self._btn_save.clicked.connect(self._save)
        self._btn_reset.clicked.connect(self._reset_defaults)

    # ── Tab builders ─────────────────────────────────────────────────

    def _build_timer_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        dur_g, dur_lay = _make_group("Session Durations")
        self._row_focus = _DurationRow("Focus session", 25,
                                       min_m=1, max_m=120)
        self._row_short = _DurationRow("Short break", 5,
                                       min_m=1, max_m=60)
        self._row_long  = _DurationRow("Long break", 15,
                                       min_m=1, max_m=90)
        dur_lay.addWidget(self._row_focus)
        dur_lay.addWidget(self._row_short)
        dur_lay.addWidget(self._row_long)
        lay.addWidget(dur_g)

        cycle_g, cycle_lay = _make_group("Focus Cycle")
        self._spin_cycle = QSpinBox()
        self._spin_cycle.setRange(2, 10)
        self._spin_cycle.setSuffix(" sessions")
        self._spin_cycle.setFixedWidth(130)
        self._spin_cycle.setToolTip(
            "How many focus sessions before a long break is offered"
        )
        cycle_lay.addWidget(_Row(
            "Sessions before long break",
            self._spin_cycle,
            "After this many focus sessions, a long break will be suggested.",
        ))
        lay.addWidget(cycle_g)

        auto_g, auto_lay = _make_group("Auto-start")
        self._toggle_auto_break = _ToggleRow(
            "Start breaks automatically",
            False,
            "Breaks begin immediately after a focus session ends.",
        )
        self._toggle_auto_focus = _ToggleRow(
            "Start focus sessions automatically",
            False,
            "The next focus session starts immediately after a break ends.",
        )
        auto_lay.addWidget(self._toggle_auto_break)
        auto_lay.addWidget(self._toggle_auto_focus)
        lay.addWidget(auto_g)

        lay.addStretch(1)
        return w

    def _build_sound_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        g, gl = _make_group("Sound Alerts")
        self._toggle_sound = _ToggleRow(
            "Enable sound alerts",
            True,
            "Play a chime when each session starts and ends.",
        )
        gl.addWidget(self._toggle_sound)

        # Volume
        vol_widget = QWidget()
        vh = QHBoxLayout(vol_widget)
        vh.setContentsMargins(0, 0, 0, 0)
        vh.setSpacing(12)
        vh.addWidget(QLabel("Volume"))
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(70)
        self._volume_slider.setMinimumWidth(140)
        vh.addWidget(self._volume_slider, 1)
        self._volume_label = QLabel("70%")
        self._volume_label.setFixedWidth(38)
        self._volume_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vh.addWidget(self._volume_label)
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        gl.addWidget(vol_widget)

        # Sound style
        self._combo_sound_theme = QComboBox()
        self._combo_sound_theme.addItem("Gentle chime", "gentle")
        self._combo_sound_theme.addItem("Classic beep", "classic")
        self._combo_sound_theme.addItem("Minimal tone", "minimal")
        self._combo_sound_theme.setFixedWidth(160)
        gl.addWidget(_Row("Alert style", self._combo_sound_theme))

        lay.addWidget(g)
        lay.addStretch()
        return w

    def _build_notif_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        g, gl = _make_group("Desktop Notifications")
        self._toggle_notif = _ToggleRow(
            "Show desktop notifications",
            True,
            "Display a system notification when each session ends.",
        )
        gl.addWidget(self._toggle_notif)

        note = QLabel(
            "Notifications appear via your operating system's notification "
            "centre. For richer alerts on Linux, install the optional "
            "'plyer' package: pip install plyer"
        )
        note.setWordWrap(True)
        note.setObjectName("SettingDesc")
        gl.addWidget(note)
        lay.addWidget(g)

        lay.addStretch()
        return w

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        theme_g, theme_gl = _make_group("Colour Theme")

        self._combo_theme = QComboBox()
        self._combo_theme.addItem("Dark", "dark")
        self._combo_theme.addItem("Light", "light")
        self._combo_theme.setFixedWidth(120)
        theme_gl.addWidget(_Row("Theme", self._combo_theme))

        # Accent colour
        accent_w = QWidget()
        ah = QHBoxLayout(accent_w)
        ah.setContentsMargins(0, 4, 0, 4)
        ah.setSpacing(10)
        ah.addWidget(QLabel("Accent colour"), 1)
        self._accent_preview = QLabel()
        self._accent_preview.setFixedSize(28, 28)
        self._current_accent = "#E85D4A"
        self._update_accent_preview()
        self._btn_pick_accent = QPushButton("Change…")
        self._btn_pick_accent.setFixedWidth(90)
        self._btn_pick_accent.clicked.connect(self._pick_accent)
        ah.addWidget(self._accent_preview)
        ah.addSpacing(4)
        ah.addWidget(self._btn_pick_accent)
        theme_gl.addWidget(accent_w)
        lay.addWidget(theme_g)

        tray_g, tray_gl = _make_group("System Tray")
        self._toggle_tray = _ToggleRow(
            "Show tray icon",
            True,
            "Keep FocusTomato accessible in the system tray.",
        )
        self._toggle_minimize_tray = _ToggleRow(
            "Minimize to tray on close",
            True,
            "Clicking × hides the window instead of quitting.",
        )
        tray_gl.addWidget(self._toggle_tray)
        tray_gl.addWidget(self._toggle_minimize_tray)
        lay.addWidget(tray_g)

        lay.addStretch()
        return w

    def _build_data_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        from core.storage import get_data_dir
        data_dir = get_data_dir()

        storage_g, storage_gl = _make_group("Storage")
        dir_lbl = QLabel(f"Settings, tasks, and history are saved to:\n{data_dir}")
        dir_lbl.setWordWrap(True)
        dir_lbl.setObjectName("SettingDesc")
        storage_gl.addWidget(dir_lbl)
        lay.addWidget(storage_g)

        danger_g, danger_gl = _make_group("Danger Zone")
        self._btn_clear_history = QPushButton("Clear All Session History…")
        self._btn_clear_history.setProperty("danger", True)
        self._btn_clear_history.setFixedHeight(34)
        self._btn_clear_history.setToolTip(
            "Permanently delete all recorded focus sessions. Cannot be undone."
        )
        self._btn_clear_history.clicked.connect(self._clear_history)
        danger_gl.addWidget(self._btn_clear_history)
        lay.addWidget(danger_g)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        about = QLabel(
            "<b>FocusTomato 1.0.0</b><br>"
            "A professional Pomodoro timer for deep work.<br>"
            "Built with Python 3 and PyQt6.<br>"
        )
        about.setWordWrap(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setObjectName("SettingDesc")
        lay.addWidget(about)

        lay.addStretch()
        return w

    # ── Load / Save ──────────────────────────────────────────────────

    def _load_values(self) -> None:
        s = self._ctrl.settings.settings

        self._row_focus.spin.setValue(s.focus_duration // 60)
        self._row_short.spin.setValue(s.short_break_duration // 60)
        self._row_long.spin.setValue(s.long_break_duration // 60)
        self._spin_cycle.setValue(s.sessions_before_long_break)

        self._toggle_auto_break.set_checked(s.auto_start_breaks)
        self._toggle_auto_focus.set_checked(s.auto_start_focus)

        self._toggle_sound.set_checked(s.sound_alerts)
        self._volume_slider.setValue(s.sound_volume)
        # Map stored value to combo index
        theme_to_idx = {"gentle": 0, "classic": 1, "minimal": 2}
        self._combo_sound_theme.setCurrentIndex(theme_to_idx.get(s.sound_theme, 0))

        self._toggle_notif.set_checked(s.desktop_notifications)

        theme_idx = 0 if s.theme == "dark" else 1
        self._combo_theme.setCurrentIndex(theme_idx)
        self._current_accent = s.accent_color
        self._update_accent_preview()

        self._toggle_tray.set_checked(s.show_tray_icon)
        self._toggle_minimize_tray.set_checked(s.minimize_to_tray)

    def _save(self) -> None:
        sound_themes = ["gentle", "classic", "minimal"]
        sound_theme = sound_themes[self._combo_sound_theme.currentIndex()]
        ui_theme = "dark" if self._combo_theme.currentIndex() == 0 else "light"

        self._ctrl.settings.update(
            focus_duration=self._row_focus.value_seconds,
            short_break_duration=self._row_short.value_seconds,
            long_break_duration=self._row_long.value_seconds,
            sessions_before_long_break=self._spin_cycle.value(),
            auto_start_breaks=self._toggle_auto_break.is_checked(),
            auto_start_focus=self._toggle_auto_focus.is_checked(),
            sound_alerts=self._toggle_sound.is_checked(),
            sound_volume=self._volume_slider.value(),
            sound_theme=sound_theme,
            desktop_notifications=self._toggle_notif.is_checked(),
            theme=ui_theme,
            accent_color=self._current_accent,
            show_tray_icon=self._toggle_tray.is_checked(),
            minimize_to_tray=self._toggle_minimize_tray.is_checked(),
        )
        self._ctrl.apply_settings_changes()
        self.settings_changed.emit()
        self.accept()

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self, "Reset All Settings",
            "This will restore all settings to their defaults.\n"
            "Your tasks and session history will not be affected.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._ctrl.settings.reset_to_defaults()
            self._load_values()

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Session History",
            "This will permanently delete all recorded sessions.\n"
            "Your tasks and settings will not be affected.\n\n"
            "This cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._ctrl.stats.clear_history()
            QMessageBox.information(
                self, "History Cleared",
                "All session history has been deleted."
            )

    def _pick_accent(self) -> None:
        color = QColorDialog.getColor(
            QColor(self._current_accent), self, "Choose Accent Colour"
        )
        if color.isValid():
            self._current_accent = color.name()
            self._update_accent_preview()

    def _update_accent_preview(self) -> None:
        from ui.theme import get_palette
        p = get_palette(self._ctrl.settings.settings.theme)
        self._accent_preview.setStyleSheet(
            f"background: {self._current_accent}; "
            f"border-radius: 6px; "
            f"border: 2px solid {p.border};"
        )
