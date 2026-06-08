"""
TaskPanel — task manager integrated with focus sessions.

UX principles:
  - Actions (Focus, Done, Edit, Delete) are always visible on each row.
  - Active task gets a clear accent-coloured left border.
  - Completed tasks are visually subdued (reduced opacity via color, not CSS opacity).
  - Empty state is informative and action-oriented.
  - Task dialog has inline validation feedback (red border on empty title).
  - Estimated vs completed pomodoros shown as a mini progress bar.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize, QRectF, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit,
    QSpinBox, QDialog, QDialogButtonBox, QTextEdit,
    QMessageBox, QSizePolicy,
)

from core.models import Task
from ui.widgets import SectionHeader, IconButton

if TYPE_CHECKING:
    from core.app_controller import AppController

logger = logging.getLogger(__name__)


class _PomoProgressBar(QWidget):
    """Mini horizontal progress bar showing completed/estimated pomodoros."""

    def __init__(self, completed: int, estimated: int,
                 accent: str = "#E85D4A", track: str = "#333333",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._completed = completed
        self._estimated = max(1, estimated)
        self._accent = QColor(accent)
        self._track = QColor(track)
        self.setFixedSize(56, 6)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # Track
        painter.setBrush(QBrush(self._track))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Fill
        frac = min(1.0, self._completed / self._estimated)
        if frac > 0:
            fw = max(r * 2, frac * w)
            painter.setBrush(QBrush(self._accent))
            painter.drawRoundedRect(QRectF(0, 0, fw, h), r, r)

        painter.end()


class TaskItemWidget(QFrame):
    """Single task row."""

    set_active_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    complete_requested = pyqtSignal(str)

    def __init__(self, task: Task, is_active: bool = False,
                 accent: str = "#E85D4A",
                 text_primary: str = "#F0F0F0",
                 text_secondary: str = "#8A8A8A",
                 text_disabled: str = "#4A4A4A",
                 bg_elevated: str = "#262626",
                 bg_overlay: str = "#303030",
                 border: str = "#383838",
                 success: str = "#4CAF82",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._task = task
        self._is_active = is_active
        self._colors = dict(
            accent=accent, text_primary=text_primary,
            text_secondary=text_secondary, text_disabled=text_disabled,
            bg_elevated=bg_elevated, bg_overlay=bg_overlay,
            border=border, success=success,
        )
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        c = self._colors
        is_done = self._task.is_done

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(0)

        # ── Accent left border strip (active indicator) ──
        self._border_strip = QFrame()
        self._border_strip.setFixedWidth(4)
        strip_color = c["accent"] if self._is_active else "transparent"
        self._border_strip.setStyleSheet(
            f"background: {strip_color}; border-radius: 2px; margin: 4px 0;"
        )
        layout.addWidget(self._border_strip)
        layout.addSpacing(12)

        # ── Title + notes column ──
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 10, 0, 10)

        title_text = self._task.title or "(Untitled task)"
        self._title = QLabel(title_text)
        tf = QFont()
        tf.setPointSize(12)
        if is_done:
            tf.setStrikeOut(True)
        self._title.setFont(tf)
        title_color = c["text_disabled"] if is_done else c["text_primary"]
        self._title.setStyleSheet(f"color: {title_color};")
        self._title.setWordWrap(False)
        text_col.addWidget(self._title)

        if self._task.notes:
            self._notes = QLabel(self._task.notes)
            nf = QFont()
            nf.setPointSize(10)
            self._notes.setFont(nf)
            self._notes.setStyleSheet(f"color: {c['text_secondary']};")
            text_col.addWidget(self._notes)

        layout.addLayout(text_col, 1)

        # ── Pomodoro progress ──
        pomo_col = QVBoxLayout()
        pomo_col.setSpacing(4)
        pomo_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pomo_col.setContentsMargins(0, 0, 12, 0)

        comp = self._task.completed_pomodoros
        est = self._task.estimated_pomodoros
        pomo_label = QLabel(f"{comp}/{est}")
        pf = QFont()
        pf.setPointSize(10)
        # (font already set above)
        pomo_label.setFont(pf)
        pomo_label.setStyleSheet(f"color: {c['text_secondary']};")
        pomo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pomo_label.setMinimumWidth(44)  # was 36px — clips "10/10" at 10pt
        pomo_col.addWidget(pomo_label, 0, Qt.AlignmentFlag.AlignHCenter)

        bar = _PomoProgressBar(comp, est, accent=c["accent"], track=c["border"])
        pomo_col.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(pomo_col)

        # ── Action buttons ──
        btn_col = QHBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setContentsMargins(0, 0, 0, 0)

        if not is_done:
            # Focus (set as active task)
            focus_label = "▣ Focusing" if self._is_active else "▷ Focus"
            self._btn_activate = QPushButton(focus_label)
            self._btn_activate.setFixedHeight(30)
            self._btn_activate.setMinimumWidth(86)  # auto-width for DPI robustness
            self._btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
            if self._is_active:
                self._btn_activate.setStyleSheet(
                    f"background: {c['accent']}22; color: {c['accent']}; "
                    f"border: 1px solid {c['accent']}; border-radius: 6px; font-size: 11px;"
                )
            else:
                self._btn_activate.setStyleSheet(
                    f"background: transparent; color: {c['text_secondary']}; "
                    f"border: 1px solid {c['border']}; border-radius: 6px; font-size: 11px;"
                )
            self._btn_activate.clicked.connect(
                lambda: self.set_active_requested.emit(self._task.id)
            )
            btn_col.addWidget(self._btn_activate)

            # Mark done
            self._btn_done = QPushButton("Done")
            self._btn_done.setFixedHeight(30)
            self._btn_done.setMinimumWidth(56)  # auto-width for DPI robustness
            self._btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_done.setStyleSheet(
                f"background: transparent; color: {c['success']}; "
                f"border: 1px solid {c['success']}44; border-radius: 6px; font-size: 11px;"
            )
            self._btn_done.clicked.connect(
                lambda: self.complete_requested.emit(self._task.id)
            )
            btn_col.addWidget(self._btn_done)

        # Edit
        self._btn_edit = IconButton("✎", "Edit task")
        self._btn_edit.setFixedSize(32, 32)
        self._btn_edit.clicked.connect(lambda: self.edit_requested.emit(self._task.id))
        btn_col.addWidget(self._btn_edit)

        # Delete
        self._btn_delete = IconButton("✕", "Delete task")
        self._btn_delete.setFixedSize(32, 32)
        self._btn_delete.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {c['text_disabled']}; }}"
            f"QPushButton:hover {{ color: {c['accent']}; background: {c['bg_overlay']}; border-radius: 8px; }}"
        )
        self._btn_delete.clicked.connect(lambda: self.delete_requested.emit(self._task.id))
        btn_col.addWidget(self._btn_delete)

        layout.addLayout(btn_col)

    def _apply_style(self) -> None:
        c = self._colors
        bg = c["bg_overlay"] if self._is_active else c["bg_elevated"]
        self.setStyleSheet(f"""
            TaskItemWidget {{
                background: {bg};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            TaskItemWidget:hover {{
                border-color: {c['accent'] if not self._task.is_done else c['border']};
            }}
        """)


class TaskEditDialog(QDialog):
    """Add or edit a task. Provides inline validation feedback."""

    def __init__(self, task: Optional[Task] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._task = task or Task()
        self._is_new = task is None
        self.setWindowTitle("New Task" if self._is_new else "Edit Task")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title field
        lbl_title = QLabel("Task name")
        lf = QFont()
        lf.setWeight(QFont.Weight.Medium)
        lbl_title.setFont(lf)
        layout.addWidget(lbl_title)

        self._title_edit = QLineEdit(self._task.title)
        self._title_edit.setPlaceholderText("What are you working on?")
        self._title_edit.setMinimumHeight(38)
        layout.addWidget(self._title_edit)

        self._title_error = QLabel("Task name is required.")
        self._title_error.setStyleSheet("color: #E85D4A; font-size: 11px;")
        self._title_error.hide()
        layout.addWidget(self._title_error)

        # Notes field
        lbl_notes = QLabel("Notes")
        lbl_notes.setFont(lf)
        layout.addWidget(lbl_notes)

        self._notes_edit = QTextEdit(self._task.notes)
        self._notes_edit.setFixedHeight(80)
        self._notes_edit.setPlaceholderText("Optional context or sub-tasks…")
        layout.addWidget(self._notes_edit)

        # Pomodoro estimate
        est_row = QHBoxLayout()
        lbl_est = QLabel("Estimated sessions")
        lbl_est.setFont(lf)
        est_row.addWidget(lbl_est)
        est_row.addStretch()

        self._spin = QSpinBox()
        self._spin.setRange(1, 50)
        self._spin.setValue(self._task.estimated_pomodoros)
        self._spin.setSuffix(" 🍅")
        self._spin.setFixedWidth(90)
        self._spin.setToolTip("How many 25-minute focus sessions will this take?")
        est_row.addWidget(self._spin)
        layout.addLayout(est_row)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Add Task" if self._is_new else "Save Changes"
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._title_edit.setFocus()
        self._title_edit.textChanged.connect(self._clear_error)

    def _clear_error(self) -> None:
        if self._title_edit.text().strip():
            self._title_edit.setProperty("error", False)
            self._title_edit.style().unpolish(self._title_edit)
            self._title_edit.style().polish(self._title_edit)
            self._title_error.hide()

    def _accept(self) -> None:
        title = self._title_edit.text().strip()
        if not title:
            self._title_edit.setProperty("error", True)
            self._title_edit.style().unpolish(self._title_edit)
            self._title_edit.style().polish(self._title_edit)
            self._title_error.show()
            self._title_edit.setFocus()
            return
        self._task.title = title
        self._task.notes = self._notes_edit.toPlainText().strip()
        self._task.estimated_pomodoros = self._spin.value()
        self.accept()

    def get_task(self) -> Task:
        return self._task


class TaskPanel(QWidget):
    """Full task management panel."""

    def __init__(self, controller: "AppController",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._setup_ui()
        self._connect_signals()
        self._refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Header ──
        header_row = QHBoxLayout()
        header_row.addWidget(SectionHeader("My Tasks"))
        header_row.addStretch()

        self._btn_add = QPushButton("+ New Task")
        self._btn_add.setProperty("primary", True)
        self._btn_add.setFixedHeight(34)
        self._btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(self._btn_add)
        root.addLayout(header_row)

        # ── Active task indicator ──
        self._active_frame = QFrame()
        self._active_frame.setObjectName("ActiveTaskFrame")
        af_layout = QHBoxLayout(self._active_frame)
        af_layout.setContentsMargins(12, 8, 12, 8)
        af_layout.setSpacing(8)

        self._active_icon = QLabel("○")
        self._active_icon.setFixedWidth(18)
        self._active_label = QLabel("Click ▷ Focus on any task to start focusing on it.")
        self._active_label.setObjectName("ActiveTaskHint")
        af_layout.addWidget(self._active_icon)
        af_layout.addWidget(self._active_label, 1)
        root.addWidget(self._active_frame)

        # ── Task list ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 4, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_container)
        root.addWidget(self._scroll, 1)

        # ── Empty state ──
        self._empty_widget = QWidget()
        ev = QVBoxLayout(self._empty_widget)
        ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ev.setSpacing(8)

        empty_icon = QLabel("📋")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ef = QFont()
        ef.setPointSize(28)
        empty_icon.setFont(ef)
        ev.addWidget(empty_icon)

        empty_title = QLabel("No tasks yet")
        et_font = QFont()
        et_font.setPointSize(14)
        et_font.setWeight(QFont.Weight.Medium)
        empty_title.setFont(et_font)
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setObjectName("EmptyTitle")
        ev.addWidget(empty_title)

        empty_hint = QLabel(
            "Add a task to track what you're working on.\n"
            "Tasks help you stay intentional during focus sessions."
        )
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setWordWrap(True)
        empty_hint.setObjectName("EmptyStateLabel")
        ev.addWidget(empty_hint)

        self._empty_widget.hide()
        root.addWidget(self._empty_widget)

    def _connect_signals(self) -> None:
        self._btn_add.clicked.connect(self._on_add)
        self._ctrl.active_task_changed.connect(self._on_active_task_changed)

    def _get_palette(self):
        from ui.theme import get_palette
        return get_palette(self._ctrl.settings.settings.theme)

    def _refresh(self) -> None:
        # Clear list rows (keep trailing stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = self._ctrl.tasks.get_all()
        active_id = self._ctrl.get_active_task_id()
        p = self._get_palette()

        has_tasks = bool(tasks)
        self._scroll.setVisible(has_tasks)
        self._empty_widget.setVisible(not has_tasks)

        for task in tasks:
            widget = TaskItemWidget(
                task,
                is_active=(task.id == active_id),
                accent=p.accent,
                text_primary=p.text_primary,
                text_secondary=p.text_secondary,
                text_disabled=p.text_disabled,
                bg_elevated=p.bg_elevated,
                bg_overlay=p.bg_overlay,
                border=p.border,
                success=p.success,
            )
            widget.set_active_requested.connect(self._on_set_active)
            widget.edit_requested.connect(self._on_edit)
            widget.delete_requested.connect(self._on_delete)
            widget.complete_requested.connect(self._on_complete)
            self._list_layout.insertWidget(self._list_layout.count() - 1, widget)

    def _on_active_task_changed(self, task) -> None:
        p = self._get_palette()
        if task:
            self._active_icon.setText("🎯")
            self._active_icon.setStyleSheet(f"font-size: 14px;")
            self._active_label.setText(f"Focusing on: {task.title}")
            self._active_label.setStyleSheet(f"color: {p.accent}; font-weight: 600;")
        else:
            self._active_icon.setText("○")
            self._active_icon.setStyleSheet(f"color: {p.text_disabled};")
            self._active_label.setText("Click ▷ Focus on any task to start focusing on it.")
            self._active_label.setStyleSheet(f"color: {p.text_secondary};")
        self._refresh()

    def _on_add(self) -> None:
        dlg = TaskEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._ctrl.tasks.add(dlg.get_task())
            self._refresh()

    def _on_edit(self, task_id: str) -> None:
        task = self._ctrl.tasks.get_by_id(task_id)
        if not task:
            return
        dlg = TaskEditDialog(task=task, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._ctrl.tasks.update(dlg.get_task())
            self._refresh()

    def _on_delete(self, task_id: str) -> None:
        task = self._ctrl.tasks.get_by_id(task_id)
        if not task:
            return
        reply = QMessageBox.question(
            self, "Delete Task",
            f'Delete "{task.title}"?\n\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._ctrl.get_active_task_id() == task_id:
                self._ctrl.set_active_task(None)
            self._ctrl.tasks.delete(task_id)
            self._refresh()

    def _on_complete(self, task_id: str) -> None:
        self._ctrl.tasks.complete_task(task_id)
        if self._ctrl.get_active_task_id() == task_id:
            self._ctrl.set_active_task(None)
        self._refresh()

    def _on_set_active(self, task_id: str) -> None:
        current = self._ctrl.get_active_task_id()
        self._ctrl.set_active_task(None if current == task_id else task_id)

    def refresh_theme(self) -> None:
        p = self._get_palette()
        self._active_frame.setStyleSheet(f"""
            #ActiveTaskFrame {{
                background: {p.bg_elevated};
                border: 1px solid {p.border};
                border-radius: 8px;
            }}
        """)
        # Refresh empty state colours
        for lbl in self._empty_widget.findChildren(QLabel, "EmptyStateLabel"):
            lbl.setStyleSheet(f"color: {p.text_secondary};")
        for lbl in self._empty_widget.findChildren(QLabel, "EmptyTitle"):
            lbl.setStyleSheet(f"color: {p.text_primary};")
        self._refresh()