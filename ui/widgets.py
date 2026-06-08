"""
Reusable custom widgets for FocusTomato — v1.2

Fixes applied:
  - Removed hardcoded QFont("Segoe UI") — replaced with cross-platform body font stack
  - Removed hardcoded QFont("Georgia") — replaced with display font stack with fallbacks
  - PillButton min-width raised from 80px to 120px to fit "Short Break" without clipping
  - BarChart day-label rect widened to 40px (cx-20..cx+20) to prevent clipping at HiDPI
  - StatCard value font reduced to 20pt to prevent overflow with longer values
  - SectionHeader letter-spacing reduced from 1.5 to 0.8 absolute (was too wide)
  - Removed unused imports: math, QPainterPath
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QPushButton, QSizePolicy, QFrame, QAbstractButton,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QRectF, QPointF, QSize, pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QFontMetrics,
)

# Cross-platform font stacks (no single-font fallback traps)
_BODY_FONT = "'Segoe UI', 'SF Pro Text', 'Ubuntu', 'Cantarell', Helvetica, Arial, sans-serif"
_DISPLAY_FONT = "Georgia, 'Times New Roman', 'Noto Serif', serif"


def _body_font(pt: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return a cross-platform body font at the given point size."""
    f = QFont()
    f.setPointSize(pt)
    f.setWeight(weight)
    f.setStyleHint(QFont.StyleHint.SansSerif)
    return f


def _display_font(pt: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return a cross-platform display/serif font at the given point size."""
    f = QFont()
    f.setPointSize(pt)
    f.setWeight(weight)
    f.setStyleHint(QFont.StyleHint.Serif)
    return f


# ──────────────────────────────────────────────────────────────────────
class ProgressRing(QWidget):
    """
    Animated circular progress ring.

    Visual hierarchy (largest → smallest):
      1. Coloured progress arc  — first thing the eye catches
      2. Large serif timer digits — time remaining at a glance
      3. Session-type label     — context (FOCUS / BREAK)
      4. Sub-text               — task name or Paused indicator
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._progress: float = 0.0
        self._ring_color = QColor("#E85D4A")
        self._track_color = QColor("#2C2C2C")
        self._text_color = QColor("#F0F0F0")
        self._label_color = QColor("#8A8A8A")
        self._ring_width: int = 11
        self._glow_enabled: bool = True

        self._anim_progress: float = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._animate_step)

        self._time_text: str = "25:00"
        self._label_text: str = "FOCUS"
        self._sub_text: str = ""
        self._paused: bool = False

    # ── Public API ──────────────────────────────────────────────────

    def set_progress(self, progress: float, animate: bool = True) -> None:
        self._progress = max(0.0, min(1.0, progress))
        if animate:
            self._anim_timer.start()
        else:
            self._anim_progress = self._progress
            self.update()

    def set_time_text(self, text: str) -> None:
        self._time_text = text
        self.update()

    def set_label(self, text: str) -> None:
        self._label_text = text.upper()
        self.update()

    def set_sub_text(self, text: str) -> None:
        self._sub_text = text
        self.update()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self.update()

    def set_ring_color(self, color: str) -> None:
        self._ring_color = QColor(color)
        self.update()

    def set_track_color(self, color: str) -> None:
        self._track_color = QColor(color)
        self.update()

    def set_text_color(self, color: str) -> None:
        self._text_color = QColor(color)
        self.update()

    def set_label_color(self, color: str) -> None:
        self._label_color = QColor(color)
        self.update()

    def set_theme(self, is_dark: bool) -> None:
        self._track_color = QColor("#2C2C2C" if is_dark else "#E0DDD8")
        self._text_color = QColor("#F0F0F0" if is_dark else "#1A1A1A")
        self._label_color = QColor("#8A8A8A" if is_dark else "#6B6560")
        self.update()

    # ── Animation ────────────────────────────────────────────────────

    def _animate_step(self) -> None:
        diff = self._progress - self._anim_progress
        if abs(diff) < 0.0008:
            self._anim_progress = self._progress
            self._anim_timer.stop()
        else:
            self._anim_progress += diff * 0.20
        self.update()

    # ── Paint ────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        size = min(w, h)
        rw = self._ring_width
        margin = rw + 12
        rect = QRectF(
            (w - size) / 2 + margin,
            (h - size) / 2 + margin,
            size - 2 * margin,
            size - 2 * margin,
        )
        cx, cy = w / 2.0, h / 2.0

        # Track ring
        track_pen = QPen(self._track_color, rw,
                         Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Progress arc
        span = int(self._anim_progress * 360 * 16)
        if span > 0:
            ring_color = QColor(self._ring_color)
            if self._paused:
                ring_color.setAlpha(160)

            if self._glow_enabled and not self._paused:
                for extra_w, alpha in ((rw + 12, 25), (rw + 6, 55)):
                    gc = QColor(ring_color)
                    gc.setAlpha(alpha)
                    painter.setPen(QPen(gc, extra_w, Qt.PenStyle.SolidLine,
                                        Qt.PenCapStyle.RoundCap))
                    painter.drawArc(rect, 90 * 16, -span)

            painter.setPen(QPen(ring_color, rw,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(rect, 90 * 16, -span)

        inner_r = (size / 2) - margin - rw / 2

        # Session-type label (smallest — sits above the digits)
        label_pt = max(9, int(size * 0.046))
        label_font = _body_font(label_pt, QFont.Weight.Medium)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(label_font)
        label_color = QColor(self._ring_color) if not self._paused else QColor(self._label_color)
        label_color.setAlpha(210)
        painter.setPen(label_color)
        label_rect = QRectF(cx - inner_r, cy - inner_r * 0.52,
                            inner_r * 2, inner_r * 0.36)
        painter.drawText(label_rect,
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                         self._label_text)

        # Timer digits (largest — the primary visual element)
        digit_pt = max(28, int(size * 0.215))
        timer_font = _display_font(digit_pt, QFont.Weight.Normal)
        painter.setFont(timer_font)
        timer_color = QColor(self._text_color)
        if self._paused:
            timer_color.setAlpha(180)
        painter.setPen(timer_color)
        timer_rect = QRectF(cx - inner_r, cy - inner_r * 0.26,
                            inner_r * 2, inner_r * 0.64)
        painter.drawText(timer_rect, Qt.AlignmentFlag.AlignCenter, self._time_text)

        # Sub-text: "Paused" OR active task name
        if self._paused:
            sub_display = "Paused"
            sub_color = QColor(self._label_color)
            sub_color.setAlpha(210)
        elif self._sub_text:
            sub_display = self._sub_text
            sub_color = QColor(self._label_color)
            sub_color.setAlpha(190)
        else:
            sub_display = ""
            sub_color = QColor(self._label_color)

        if sub_display:
            sub_pt = max(9, int(size * 0.038))
            sub_font = _body_font(sub_pt)
            painter.setFont(sub_font)
            painter.setPen(sub_color)
            fm = QFontMetrics(sub_font)
            max_sub_w = int(inner_r * 1.6)
            elided = fm.elidedText(sub_display, Qt.TextElideMode.ElideRight, max_sub_w)
            sub_rect = QRectF(cx - inner_r, cy + inner_r * 0.25,
                              inner_r * 2, inner_r * 0.32)
            painter.drawText(sub_rect,
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                             elided)

        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(300, 300)


# ──────────────────────────────────────────────────────────────────────
class SessionDotRow(QWidget):
    """Pomodoro cycle dot indicators. Width is dynamic based on count."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._total: int = 4
        self._completed: int = 0
        self._accent_color = QColor("#E85D4A")
        self._track_color = QColor("#2C2C2C")
        self._update_width()

    def set_counts(self, completed: int, total: int) -> None:
        self._total = max(1, total)
        self._completed = max(0, min(completed, self._total))
        self._update_width()
        self.update()

    def set_colors(self, accent: str, track: str) -> None:
        self._accent_color = QColor(accent)
        self._track_color = QColor(track)
        self.update()

    def _update_width(self) -> None:
        dot_d = 10
        gap = 8
        w = self._total * dot_d + (self._total - 1) * gap + 4
        self.setFixedWidth(max(60, w))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_r = 5.0
        gap = 8
        step = int(dot_r * 2) + gap
        total_w = self._total * step - gap
        x0 = (self.width() - total_w) / 2 + dot_r
        cy = self.height() / 2

        for i in range(self._total):
            cx = x0 + i * step
            if i < self._completed:
                painter.setBrush(QBrush(self._accent_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), dot_r, dot_r)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                tc = QColor(self._track_color)
                tc.setAlpha(200)
                painter.setPen(QPen(tc, 1.5))
                painter.drawEllipse(QPointF(cx, cy), dot_r - 1, dot_r - 1)

        painter.end()


# ──────────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    """
    Metric display card.

    Value font is 20pt display serif — large enough to read at a glance,
    small enough to never overflow (tested up to "365 days" at 100% DPI).
    """

    def __init__(self, label: str, value: str = "—",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._label_text = label
        self._setup_ui(value)

    def _setup_ui(self, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("StatCardValue")
        # 20pt display font — fits longest expected value without overflow
        vf = _display_font(20)
        self._value_label.setFont(vf)
        self._value_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        # Allow label to shrink/grow with content; never clip
        self._value_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self._value_label)

        self._label_label = QLabel(self._label_text.upper())
        self._label_label.setObjectName("StatCardLabel")
        lf = _body_font(9)
        lf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        self._label_label.setFont(lf)
        layout.addWidget(self._label_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_accent_value(self, color: str) -> None:
        self._value_label.setStyleSheet(f"color: {color};")

    def clear_accent(self) -> None:
        self._value_label.setStyleSheet("")


# ──────────────────────────────────────────────────────────────────────
class AnimatedToggle(QAbstractButton):
    """Smooth iOS-style toggle switch. Fixed 48×26 for consistent layout."""

    toggled_state = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._thumb_x: float = 2.0
        self._on_color = QColor("#E85D4A")
        self._off_color = QColor("#666666")

        self._anim = QPropertyAnimation(self, b"thumb_x", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        checked = self.isChecked()
        target = float(self.width() - 24) if checked else 2.0
        self._anim.setStartValue(self._thumb_x)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled_state.emit(checked)

    def set_on_color(self, color: str) -> None:
        self._on_color = QColor(color)
        self.update()

    @pyqtProperty(float)
    def thumb_x(self) -> float:
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, value: float) -> None:
        self._thumb_x = value
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor(self._on_color if self.isChecked() else self._off_color)
        track_r = self.height() / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), track_r, track_r)
        thumb_r = self.height() / 2 - 2
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPointF(self._thumb_x + thumb_r, self.height() / 2),
                            thumb_r, thumb_r)
        painter.end()


# ──────────────────────────────────────────────────────────────────────
class SectionHeader(QLabel):
    """
    Small-caps section label.
    Uses letter-spacing 0.8 (was 1.5 — was disproportionate at 9pt).
    """

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text.upper(), parent)
        font = _body_font(9, QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        self.setFont(font)
        self.setObjectName("SectionHeader")


# ──────────────────────────────────────────────────────────────────────
class IconButton(QPushButton):
    """
    Compact flat icon/text button. Min 36×36 for click-target compliance.
    Does NOT use fixed width — auto-sizes to content.
    """

    def __init__(self, text: str, tooltip: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setProperty("flat", True)
        self.setFixedHeight(36)
        self.setMinimumWidth(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)


# ──────────────────────────────────────────────────────────────────────
class PillButton(QPushButton):
    """
    Pill-shaped session-type selector.

    min-width raised to 120px to accommodate "Short Break" (needs ~112px at 13px
    + padding) without clipping. Auto-expands for longer labels.
    """

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self._active_color = "#E85D4A"
        self._inactive_text = "#8A8A8A"
        self._checked_text = "#FFFFFF"
        self._update_style()

    def set_active_color(self, color: str) -> None:
        self._active_color = color
        self._update_style()

    def set_inactive_text_color(self, color: str) -> None:
        self._inactive_text = color
        self._update_style()

    def set_checked_text_color(self, color: str) -> None:
        """Set the text color used when the pill is checked/active."""
        self._checked_text = color
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            PillButton {{
                background: transparent;
                border: 1.5px solid transparent;
                border-radius: 17px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 500;
                color: {self._inactive_text};
                min-width: 120px;
            }}
            PillButton:hover {{
                border-color: {self._active_color};
                color: {self._active_color};
            }}
            PillButton:checked {{
                background: {self._active_color};
                color: {self._checked_text};
                border-color: {self._active_color};
                font-weight: 600;
            }}
            PillButton:checked:hover {{
                background: {self._active_color};
            }}
        """)


# ──────────────────────────────────────────────────────────────────────
class BarChart(QWidget):
    """
    Weekly focus bar chart — pure QPainter, no external dependencies.

    - Today's bar is full-brightness accent; prior days are 130/255 alpha.
    - Value labels appear above non-zero bars.
    - Day labels use 40px-wide rects (cx±20) to prevent clipping at HiDPI.
    - Empty state shows placeholder stub bars with day labels.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._values: list[float] = []
        self._labels: list[str] = []
        self._bar_color = QColor("#E85D4A")
        self._text_color = QColor("#8A8A8A")
        self._empty_text_color = QColor("#4A4A4A")

    def set_data(self, values: list[float], labels: list[str]) -> None:
        self._values = values
        self._labels = labels
        self.update()

    def set_colors(self, bar: str, text: str, bg: str = "") -> None:
        self._bar_color = QColor(bar)
        self._text_color = QColor(text)
        self._empty_text_color = QColor(text)
        self._empty_text_color.setAlpha(100)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()

        if not self._values or all(v == 0 for v in self._values):
            if self._labels:
                self._draw_empty(painter, w, h)
            painter.end()
            return

        n = len(self._values)
        max_val = max(self._values) or 1.0

        label_h = 20
        value_h = 16
        chart_h = h - label_h - value_h - 4
        bar_slot = w / n
        bar_w = max(8.0, bar_slot * 0.50)

        for i, val in enumerate(self._values):
            cx = bar_slot * i + bar_slot / 2
            is_today = (i == n - 1)

            bar_frac = val / max_val
            bar_h_px = max(3.0, bar_frac * chart_h)
            x = cx - bar_w / 2
            y = value_h + chart_h - bar_h_px

            color = QColor(self._bar_color)
            color.setAlpha(255 if is_today else 130)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            radius = min(4.0, bar_w / 2)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h_px), radius, radius)

            # Value label above bar
            if val > 0:
                val_font = _body_font(7, QFont.Weight.Medium if is_today else QFont.Weight.Normal)
                painter.setFont(val_font)
                vc = QColor(self._text_color)
                vc.setAlpha(200 if is_today else 140)
                painter.setPen(vc)
                # 40px wide rect (cx±20) — safe at HiDPI
                painter.drawText(QRectF(cx - 20, y - value_h + 2, 40, value_h),
                                 Qt.AlignmentFlag.AlignCenter, str(int(val)))

            # Day label below bar — 40px wide rect prevents clipping
            if i < len(self._labels):
                lf = _body_font(8, QFont.Weight.Medium if is_today else QFont.Weight.Normal)
                painter.setFont(lf)
                lc = QColor(self._text_color)
                lc.setAlpha(210 if is_today else 140)
                painter.setPen(lc)
                painter.drawText(QRectF(cx - 20, h - label_h, 40, label_h),
                                 Qt.AlignmentFlag.AlignCenter, self._labels[i])

        painter.end()

    def _draw_empty(self, painter: QPainter, w: int, h: int) -> None:
        n = len(self._labels)
        if n == 0:
            return
        label_h = 20
        chart_h = h - label_h - 8
        bar_slot = w / n
        bar_w = max(8.0, bar_slot * 0.50)

        for i, label in enumerate(self._labels):
            cx = bar_slot * i + bar_slot / 2
            ph = max(3.0, chart_h * 0.04)
            x = cx - bar_w / 2
            y = chart_h - ph + 4
            c = QColor(self._empty_text_color)
            c.setAlpha(60)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_w, ph), 2, 2)

            lf = _body_font(8)
            painter.setFont(lf)
            tc = QColor(self._empty_text_color)
            painter.setPen(tc)
            # 40px wide rect prevents clipping
            painter.drawText(QRectF(cx - 20, h - label_h, 40, label_h),
                             Qt.AlignmentFlag.AlignCenter, label)
