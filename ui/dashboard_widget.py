"""
DashboardWidget — productivity overview.

Sections:
  1. Today at-a-glance — 3 stat cards (sessions, minutes, streak)
  2. Weekly focus chart — 7-day bar chart with day labels
  3. All-time stats — total sessions, total hours, best streak
  4. Session history — last 30 sessions, scrollable
  5. Export controls
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QSizePolicy,
    QGridLayout,
)

from ui.widgets import StatCard, SectionHeader, BarChart

if TYPE_CHECKING:
    from core.app_controller import AppController

logger = logging.getLogger(__name__)


class DashboardWidget(QWidget):
    """Productivity stats and history panel."""

    def __init__(self, controller: "AppController",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._setup_ui()
        self._connect_signals()
        self.refresh()

    def _setup_ui(self) -> None:
        # Outer scroll area so the whole dashboard scrolls on small windows
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(16)

        # ── Header ──
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader("Your Progress"))
        header_row.addStretch()

        self._btn_export_csv = QPushButton("Export CSV")
        self._btn_export_csv.setFixedHeight(30)
        self._btn_export_csv.setToolTip("Download session history as a spreadsheet")
        self._btn_export_json = QPushButton("Export JSON")
        self._btn_export_json.setFixedHeight(30)
        self._btn_export_json.setToolTip("Download session history as JSON data")
        export_row = QHBoxLayout()
        export_row.setSpacing(8)
        export_row.addWidget(self._btn_export_csv)
        export_row.addWidget(self._btn_export_json)
        header_row.addLayout(export_row)
        root.addLayout(header_row)

        # ── Today row (3 cards) ──
        root.addWidget(SectionHeader("Today"))
        today_row = QHBoxLayout()
        today_row.setSpacing(10)
        self._card_today_sessions = StatCard("Focus Sessions", "0")
        self._card_today_minutes = StatCard("Focus Time", "0 min")
        self._card_streak = StatCard("Day Streak", "0 days")
        today_row.addWidget(self._card_today_sessions)
        today_row.addWidget(self._card_today_minutes)
        today_row.addWidget(self._card_streak)
        root.addLayout(today_row)

        # ── Weekly chart ──
        chart_frame = QFrame()
        chart_frame.setObjectName("ChartFrame")
        cf_layout = QVBoxLayout(chart_frame)
        cf_layout.setContentsMargins(16, 14, 16, 12)
        cf_layout.setSpacing(8)

        chart_header = QHBoxLayout()
        chart_header.addWidget(SectionHeader("This Week"))
        chart_header.addStretch()
        self._chart_total_label = QLabel("")
        self._chart_total_label.setObjectName("ChartTotalLabel")
        ct_font = QFont()
        ct_font.setPointSize(10)
        self._chart_total_label.setFont(ct_font)
        chart_header.addWidget(self._chart_total_label)
        cf_layout.addLayout(chart_header)

        self._bar_chart = BarChart()
        self._bar_chart.setMinimumHeight(140)
        cf_layout.addWidget(self._bar_chart)
        root.addWidget(chart_frame)

        # ── All-time stats (3 cards) ──
        root.addWidget(SectionHeader("All Time"))
        alltime_row = QHBoxLayout()
        alltime_row.setSpacing(10)
        self._card_total_sessions = StatCard("Sessions", "0")
        self._card_total_hours = StatCard("Focus Hours", "0 h")
        self._card_best_streak = StatCard("Best Streak", "0 days")
        alltime_row.addWidget(self._card_total_sessions)
        alltime_row.addWidget(self._card_total_hours)
        alltime_row.addWidget(self._card_best_streak)
        root.addLayout(alltime_row)

        # ── Recent sessions ──
        history_header = QHBoxLayout()
        history_header.addWidget(SectionHeader("Recent Sessions"))
        history_header.addStretch()
        root.addLayout(history_header)

        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._history_scroll.setFixedHeight(240)

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(4)
        self._history_layout.addStretch()

        self._history_scroll.setWidget(self._history_container)
        root.addWidget(self._history_scroll)

        # Empty history state
        self._empty_history = QWidget()
        eh_layout = QVBoxLayout(self._empty_history)
        eh_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        eh_icon = QLabel("📊")
        eh_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eh_icon_f = QFont()
        eh_icon_f.setPointSize(24)
        eh_icon.setFont(eh_icon_f)
        eh_layout.addWidget(eh_icon)

        eh_text = QLabel("No sessions recorded yet.\nComplete your first focus session to see history here.")
        eh_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eh_text.setWordWrap(True)
        eh_text.setObjectName("EmptyStateLabel")
        eh_layout.addWidget(eh_text)

        self._empty_history.hide()
        root.addWidget(self._empty_history)

    def _connect_signals(self) -> None:
        self._ctrl.session_completed.connect(lambda _: self.refresh())
        self._btn_export_csv.clicked.connect(self._export_csv)
        self._btn_export_json.clicked.connect(self._export_json)

    # ── Refresh ──────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._refresh_stats()
        self._refresh_chart()
        self._refresh_history()
        self._refresh_theme()

    def _refresh_stats(self) -> None:
        s = self._ctrl.stats.get_summary()
        p = self._get_palette()

        # Today
        self._card_today_sessions.set_value(str(s["today_sessions"]))
        today_min = s["today_minutes"]
        if today_min >= 60:
            time_str = f"{today_min // 60}h {today_min % 60}m"
        else:
            time_str = f"{today_min} min"
        self._card_today_minutes.set_value(time_str)

        streak = s["current_streak"]
        self._card_streak.set_value(f"{streak} {'day' if streak == 1 else 'days'}")
        if streak >= 3:
            self._card_streak.set_accent_value(p.success)
        else:
            self._card_streak.clear_accent()

        # All-time
        self._card_total_sessions.set_value(str(s["total_sessions"]))
        total_min = s["total_focus_minutes"]
        total_h = total_min / 60
        if total_h >= 10:
            self._card_total_hours.set_value(f"{total_h:.0f} h")
        else:
            self._card_total_hours.set_value(f"{total_h:.1f} h")

        best = s["longest_streak"]
        self._card_best_streak.set_value(f"{best} {'day' if best == 1 else 'days'}")

    def _refresh_chart(self) -> None:
        weekly = self._ctrl.stats.get_weekly_data()
        values = [float(d.focus_sessions) for d in weekly]
        labels = []
        for d in weekly:
            try:
                dt = datetime.fromisoformat(d.date)
                labels.append(dt.strftime("%a"))
            except Exception:
                labels.append("?")
        self._bar_chart.set_data(values, labels)

        # Weekly total label
        week_total = int(sum(values))
        week_min = sum(d.focus_minutes for d in weekly)
        if week_total > 0:
            self._chart_total_label.setText(
                f"{week_total} sessions · {week_min} min this week"
            )
        else:
            self._chart_total_label.setText("No sessions this week yet")

    def _refresh_history(self) -> None:
        # Clear rows (keep trailing stretch)
        while self._history_layout.count() > 1:
            item = self._history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = list(reversed(self._ctrl.stats.get_all_sessions()[-40:]))
        p = self._get_palette()

        has_sessions = bool(sessions)
        self._history_scroll.setVisible(has_sessions)
        self._empty_history.setVisible(not has_sessions)

        type_icons = {"focus": "🍅", "short_break": "☕", "long_break": "🛋️"}
        type_labels = {"focus": "Focus", "short_break": "Short Break", "long_break": "Long Break"}
        type_colors = {
            "focus": p.focus_color,
            "short_break": p.short_break_color,
            "long_break": p.long_break_color,
        }

        for session in sessions:
            row = QFrame()
            row.setObjectName("HistoryRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(10)

            stype = session.session_type.value
            color = type_colors.get(stype, p.accent)

            # Icon
            icon_lbl = QLabel(type_icons.get(stype, "⏱"))
            icon_lbl.setFixedWidth(24)
            rl.addWidget(icon_lbl)

            # Type label
            type_lbl = QLabel(type_labels.get(stype, stype))
            type_lbl.setStyleSheet(
                f"color: {color}; font-weight: 600; font-size: 12px;"
            )
            type_lbl.setFixedWidth(88)
            rl.addWidget(type_lbl)

            # Task title (if any)
            if session.task_title:
                task_lbl = QLabel(session.task_title)
                task_lbl.setStyleSheet(f"color: {p.text_secondary}; font-size: 12px;")
                task_lbl.setWordWrap(False)
                rl.addWidget(task_lbl, 1)
            else:
                rl.addStretch(1)

            # Duration
            dur_min = session.duration_seconds // 60
            dur_lbl = QLabel(f"{dur_min} min")
            dur_lbl.setStyleSheet(f"color: {p.text_secondary}; font-size: 11px;")
            dur_lbl.setMinimumWidth(52)  # was 46px — "90 min" needs ~50px
            rl.addWidget(dur_lbl)

            # Timestamp
            try:
                dt = datetime.fromisoformat(session.started_at)
                now = datetime.now()
                if dt.date() == now.date():
                    time_str = dt.strftime("Today %H:%M")
                elif (now.date() - dt.date()).days == 1:
                    time_str = dt.strftime("Yesterday %H:%M")
                else:
                    time_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                time_str = "—"
            time_lbl = QLabel(time_str)
            time_lbl.setStyleSheet(f"color: {p.text_disabled}; font-size: 11px;")
            time_lbl.setMinimumWidth(120)  # was 110px — "Yesterday HH:MM" needs ~120px
            rl.addWidget(time_lbl)

            # Completion status
            if session.completed:
                done_lbl = QLabel("✓")
                done_lbl.setStyleSheet(f"color: {p.success}; font-size: 12px; font-weight: 600;")
            else:
                done_lbl = QLabel("—")
                done_lbl.setStyleSheet(f"color: {p.text_disabled}; font-size: 12px;")
            done_lbl.setFixedWidth(18)
            rl.addWidget(done_lbl)

            row.setStyleSheet(f"""
                #HistoryRow {{
                    background: {p.bg_elevated};
                    border-radius: 8px;
                    border: 1px solid transparent;
                }}
                #HistoryRow:hover {{
                    border-color: {p.border};
                }}
            """)
            self._history_layout.insertWidget(
                self._history_layout.count() - 1, row
            )

    def _get_palette(self):
        from ui.theme import get_palette
        return get_palette(self._ctrl.settings.settings.theme)

    def _refresh_theme(self) -> None:
        p = self._get_palette()
        self._bar_chart.set_colors(p.accent, p.text_secondary)

        card_style = f"""
            QFrame#StatCard {{
                background: {p.bg_elevated};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
            QLabel#StatCardValue {{
                color: {p.text_primary};
            }}
            QLabel#StatCardLabel {{
                color: {p.text_secondary};
            }}
        """
        for card in (self._card_today_sessions, self._card_today_minutes,
                     self._card_streak, self._card_total_sessions,
                     self._card_total_hours, self._card_best_streak):
            card.setStyleSheet(card_style)

        chart_style = f"""
            #ChartFrame {{
                background: {p.bg_elevated};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """
        for child in self.findChildren(QFrame, "ChartFrame"):
            child.setStyleSheet(chart_style)

        self._chart_total_label.setStyleSheet(f"color: {p.text_secondary};")

        for lbl in self._empty_history.findChildren(QLabel, "EmptyStateLabel"):
            lbl.setStyleSheet(f"color: {p.text_secondary};")

    # ── Export ───────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session History",
            "focustomato_sessions.csv",
            "CSV Spreadsheet (*.csv)",
        )
        if path:
            try:
                from pathlib import Path
                self._ctrl.stats.export_csv(Path(path))
                QMessageBox.information(
                    self, "Export Complete",
                    f"Session history saved to:\n{path}"
                )
            except Exception as e:
                logger.error(f"CSV export failed: {e}")
                QMessageBox.critical(self, "Export Failed",
                                     f"Could not write file:\n{e}")

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session History",
            "focustomato_sessions.json",
            "JSON Data (*.json)",
        )
        if path:
            try:
                from pathlib import Path
                self._ctrl.stats.export_json(Path(path))
                QMessageBox.information(
                    self, "Export Complete",
                    f"Session history saved to:\n{path}"
                )
            except Exception as e:
                logger.error(f"JSON export failed: {e}")
                QMessageBox.critical(self, "Export Failed",
                                     f"Could not write file:\n{e}")

    def refresh_theme(self) -> None:
        self.refresh()
