"""
MainWindow — top-level application window for FocusTomato.

Architecture:
  - Left sidebar: app icon, navigation, and settings
  - Right content area: Timer | Tasks | Dashboard panels
  - System tray integration
  - Theme-aware stylesheet via build_stylesheet()
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QIcon, QAction, QCloseEvent, QPixmap,
    QPainter, QColor, QFont, QBrush,
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget,
    QSystemTrayIcon, QMenu, QSizePolicy,
    QButtonGroup,
)

from ui.theme import build_stylesheet, get_palette
from ui.timer_widget import TimerWidget
from ui.task_panel import TaskPanel
from ui.dashboard_widget import DashboardWidget
from ui.settings_dialog import SettingsDialog

if TYPE_CHECKING:
    from core.app_controller import AppController

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("timer",     "⏰", "Timer"),
    ("tasks",     "📋",  "Tasks"),
    ("dashboard", "📊",  "Dashboard"),
]


def _make_tomato_icon(size: int = 32, color: str = "#E85D4A") -> QPixmap:
    """Generate a tomato icon programmatically using float coords for HiDPI accuracy."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    body_size = size - margin * 2

    # Body
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(
        int(margin), int(margin + size * 0.08),
        int(body_size), int(body_size * 0.88),
    )

    # Stem — use QRectF form since stem coords are floats
    stem_color = QColor("#4CAF82")
    painter.setBrush(QBrush(stem_color))
    stem_w = max(2.0, size / 14.0)
    stem_h = size / 5.0
    stem_x = size / 2.0 - stem_w / 2.0
    stem_y = margin
    r = stem_w / 2.0
    painter.drawRoundedRect(QRectF(stem_x, stem_y, stem_w, stem_h), r, r)

    # Leaf ellipse
    painter.setBrush(QBrush(stem_color))
    painter.drawEllipse(
        int(size / 2.0), int(margin - size / 12.0),
        int(size / 4.0), int(size / 8.0),
    )

    painter.end()
    return px


class NavButton(QPushButton):
    def __init__(self, icon_text: str, label: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(110, 90)
        self.setToolTip(label)
        self._icon_text = icon_text
        self._label = label
        self._update_content()

    def _update_content(self) -> None:
        self.setText(f"{self._icon_text}\n{self._label}")
        font = QFont()
        font.setPointSize(11)  
        self.setFont(font)


class Sidebar(QWidget):
    nav_clicked = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(130)   
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._nav_buttons: dict[str, NavButton] = {}
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # App icon
        self._logo = QLabel()
        self._logo.setFixedSize(110, 90)
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        px = _make_tomato_icon(56)
        self._logo.setPixmap(px)
        layout.addWidget(self._logo)
        layout.addSpacing(6)

        for key, icon, label in NAV_ITEMS:
            btn = NavButton(icon, label)
            self._nav_buttons[key] = btn
            self._btn_group.addButton(btn)
            btn.clicked.connect(lambda checked, k=key: self.nav_clicked.emit(k))
            layout.addWidget(btn)
            layout.addSpacing(8)

        layout.addStretch()

        # Settings gear at bottom
        self._btn_settings = QPushButton("⚙️")
        self._btn_settings.setFixedSize(56, 56)
        self._btn_settings.setToolTip("Settings  (Ctrl+,)")
        self._btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_settings.setProperty("flat", True)
        font = QFont()
        font.setPointSize(22)
        self._btn_settings.setFont(font)
        layout.addWidget(self._btn_settings, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(4)

    def set_active(self, key: str) -> None:
        if key in self._nav_buttons:
            self._nav_buttons[key].setChecked(True)

    def apply_theme(self, theme: str) -> None:
        p = get_palette(theme)
        self.setStyleSheet(f"""
            Sidebar {{
                background: {p.bg_surface};
                border-right: 1px solid {p.border};
            }}
            NavButton {{
                background: transparent;
                border: none;
                border-radius: 12px;
                color: {p.text_secondary};
            }}
            NavButton:checked {{
                background: {p.bg_elevated};
                color: {p.text_primary};
            }}
            NavButton:hover:!checked {{
                background: {p.bg_overlay};
                color: {p.text_primary};
            }}
            QPushButton[flat="true"] {{
                background: transparent;
                border: none;
                color: {p.text_secondary};
            }}
            QPushButton[flat="true"]:hover {{
                color: {p.text_primary};
                background: {p.bg_elevated};
                border-radius: 8px;
            }}
        """)


class TitleBar(QWidget):
    """
    Minimal title bar.
    Shows the panel name only — no "FocusTomato —" prefix (redundant with window title).
    """

    def __init__(self, title: str = "Timer",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        self._title_label = QLabel(title)
        # Use the display font stack with proper fallbacks
        font = QFont()
        font.setPointSize(13)
        font.setStyleHint(QFont.StyleHint.Serif)
        self._title_label.setFont(font)
        layout.addWidget(self._title_label)
        layout.addStretch()

    def set_title(self, text: str) -> None:
        self._title_label.setText(text)

    def apply_theme(self, theme: str) -> None:
        p = get_palette(theme)
        self.setStyleSheet(f"""
            TitleBar {{
                background: {p.bg_surface};
                border-bottom: 1px solid {p.border};
            }}
            QLabel {{
                color: {p.text_primary};
                background: transparent;
            }}
        """)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self, controller: "AppController") -> None:
        super().__init__()
        self._ctrl = controller
        self._tray: Optional[QSystemTrayIcon] = None
        self._current_nav = "timer"

        self.setWindowTitle("FocusTomato")
        self.setMinimumSize(720, 540)  
        self.resize(780, 600)

        px = _make_tomato_icon(64)
        self.setWindowIcon(QIcon(px))

        self._setup_ui()
        self._setup_tray()
        self._apply_theme()
        self._navigate("timer")

        self._ctrl.engine.tick.connect(self._update_tray_tooltip)
        self._ctrl.session_type_changed.connect(self._update_tray_tooltip)

    # ── UI Construction ──────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = TitleBar()
        root.addWidget(self._title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.nav_clicked.connect(self._navigate)
        self._sidebar._btn_settings.clicked.connect(self._open_settings)
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        self._timer_widget = TimerWidget(self._ctrl)
        self._task_panel = TaskPanel(self._ctrl)
        self._dashboard = DashboardWidget(self._ctrl)

        self._stack.addWidget(self._timer_widget)   # 0
        self._stack.addWidget(self._task_panel)     # 1
        self._stack.addWidget(self._dashboard)      # 2

        self._nav_index = {"timer": 0, "tasks": 1, "dashboard": 2}

    # ── Navigation ───────────────────────────────────────────────────

    def _navigate(self, key: str) -> None:
        self._current_nav = key
        self._sidebar.set_active(key)
        self._stack.setCurrentIndex(self._nav_index.get(key, 0))

        # Panel name only — no app name prefix
        panel_names = {
            "timer": "Timer",
            "tasks": "Tasks",
            "dashboard": "Dashboard",
        }
        self._title_bar.set_title(panel_names.get(key, "FocusTomato"))

        if key == "dashboard":
            self._dashboard.refresh()

    # ── System Tray ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray not available")
            return

        s = self._ctrl.settings.settings
        if not s.show_tray_icon:
            return

        icon = QIcon(_make_tomato_icon(22, "#E85D4A"))
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("FocusTomato")

        menu = QMenu()
        act_show = QAction("Show FocusTomato", self)
        act_show.triggered.connect(self._show_from_tray)
        act_start = QAction("Start / Pause", self)
        act_start.triggered.connect(self._ctrl.toggle_pause)
        act_skip = QAction("Skip Session", self)
        act_skip.triggered.connect(self._ctrl.skip_session)
        act_quit = QAction("Quit FocusTomato", self)
        act_quit.triggered.connect(self._ctrl.quit)

        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_start)
        menu.addAction(act_skip)
        menu.addSeparator()
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        self._ctrl.notifications.set_tray_icon(self._tray)
        logger.info("System tray icon set up")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _update_tray_tooltip(self, *args) -> None:
        if not self._tray:
            return
        engine = self._ctrl.engine
        remaining = engine.remaining_seconds
        m, s = divmod(remaining, 60)
        stype = engine.session_type.value.replace("_", " ").title()
        state = engine.state.value.title()
        self._tray.setToolTip(f"FocusTomato — {stype} {m:02d}:{s:02d} [{state}]")

    # ── Settings ─────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._ctrl, parent=self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _on_settings_changed(self) -> None:
        self._apply_theme()
        self._timer_widget.refresh_theme()
        self._task_panel.refresh_theme()
        self._dashboard.refresh_theme()
        s = self._ctrl.settings.settings
        if self._tray is None and s.show_tray_icon:
            self._setup_tray()
        elif self._tray and not s.show_tray_icon:
            self._tray.hide()

    # ── Theme ────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        s = self._ctrl.settings.settings
        self.setStyleSheet(build_stylesheet(s.theme, s.accent_color))
        self._sidebar.apply_theme(s.theme)
        self._title_bar.apply_theme(s.theme)
        p = get_palette(s.theme)
        self._stack.setStyleSheet(f"background: {p.bg_base};")

    # ── Window close ─────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        s = self._ctrl.settings.settings
        if s.minimize_to_tray and self._tray and self._tray.isVisible():
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "FocusTomato",
                "Running in the background. Right-click the tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
        else:
            event.accept()
            self._ctrl.quit()

    # ── Keyboard shortcuts ───────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mods = event.modifiers()

        if key == Qt.Key.Key_Space:
            self._ctrl.toggle_pause()
            return
        if mods == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Comma:
                self._open_settings()
                return
            if key == Qt.Key.Key_1:
                self._navigate("timer")
                return
            if key == Qt.Key.Key_2:
                self._navigate("tasks")
                return
            if key == Qt.Key.Key_3:
                self._navigate("dashboard")
                return

        super().keyPressEvent(event)
