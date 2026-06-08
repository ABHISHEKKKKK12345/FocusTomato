"""
FocusTomato design system — v1.2

Two themes: dark (default) and light.
All colours, font families, sizes, radii, and spacing are defined here.
The QSS stylesheet is generated from these tokens for consistency.

Font strategy:
  - Body: system-native sans-serif stack (Segoe UI on Windows, SF Pro on macOS, Ubuntu/Cantarell on Linux)
  - Display/timer: platform-native serif for the countdown digits
  - All stacks include generic fallbacks for robustness
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ColorPalette:
    bg_base: str
    bg_surface: str
    bg_elevated: str
    bg_overlay: str
    border: str
    border_subtle: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_inverse: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_text: str
    success: str
    warning: str
    error: str
    focus_color: str
    short_break_color: str
    long_break_color: str
    ring_track: str


DARK = ColorPalette(
    bg_base="#111111",
    bg_surface="#1C1C1C",
    bg_elevated="#262626",
    bg_overlay="#303030",
    border="#383838",
    border_subtle="#282828",
    text_primary="#F0F0F0",
    text_secondary="#8A8A8A",
    text_disabled="#4A4A4A",
    text_inverse="#111111",
    accent="#E85D4A",
    accent_hover="#EF6E5C",
    accent_pressed="#D14F3C",
    accent_text="#FFFFFF",
    success="#4CAF82",
    warning="#F0A500",
    error="#E85D4A",
    focus_color="#E85D4A",
    short_break_color="#4CAF82",
    long_break_color="#5B8DD9",
    ring_track="#2C2C2C",
)

LIGHT = ColorPalette(
    bg_base="#F5F3EF",
    bg_surface="#FFFFFF",
    bg_elevated="#FFFFFF",
    bg_overlay="#EEEBE5",
    border="#DDD9D2",
    border_subtle="#E8E4DE",
    text_primary="#1A1A1A",
    text_secondary="#6B6560",
    text_disabled="#B0ACA8",
    text_inverse="#FFFFFF",
    accent="#E85D4A",
    accent_hover="#EF6E5C",
    accent_pressed="#D14F3C",
    accent_text="#1A1A1A",
    success="#3D9E6A",
    warning="#C8880A",
    error="#E85D4A",
    focus_color="#E85D4A",
    short_break_color="#3D9E6A",
    long_break_color="#4A7CC5",
    ring_track="#E0DDD8",
)


@dataclass(frozen=True)
class Typography:
    # Cross-platform body font stack — system-native on every OS
    family_body: str = (
        "'Segoe UI', 'SF Pro Text', 'Ubuntu', 'Cantarell', Helvetica, Arial, sans-serif"
    )
    # Cross-platform display/serif font stack for timer digits and headings
    family_display: str = (
        "Georgia, 'Times New Roman', 'Noto Serif', serif"
    )
    family_mono: str = (
        "'SF Mono', 'Cascadia Code', 'Consolas', 'Courier New', monospace"
    )

    size_xs: int = 10
    size_sm: int = 12
    size_base: int = 14
    size_md: int = 16
    size_lg: int = 20
    size_xl: int = 26
    size_2xl: int = 36


TYPOGRAPHY = Typography()


def get_palette(theme: str) -> ColorPalette:
    return DARK if theme == "dark" else LIGHT


def _lighten(hex_color: str, amount: int = 20) -> str:
    """Shift each RGB channel by amount (positive = lighter, negative = darker)."""
    hex_color = hex_color.lstrip("#")
    r = max(0, min(255, int(hex_color[0:2], 16) + amount))
    g = max(0, min(255, int(hex_color[2:4], 16) + amount))
    b = max(0, min(255, int(hex_color[4:6], 16) + amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def build_stylesheet(theme: str, accent: str = "") -> str:
    """Generate the full application QSS from design tokens."""
    p = get_palette(theme)
    t = TYPOGRAPHY

    ac = accent if accent else p.accent
    ac_hover = _lighten(ac, 18)
    ac_pressed = _lighten(ac, -18) if theme == "light" else _lighten(ac, -12)

    qss = f"""
/* ================================================================
   FocusTomato Global Stylesheet  —  theme: {theme}
   ================================================================ */

/* ── Base ─────────────────────────────────────────────────────── */
QWidget {{
    background-color: {p.bg_base};
    color: {p.text_primary};
    font-family: {t.family_body};
    font-size: {t.size_base}px;
    outline: none;
    selection-background-color: {ac};
    selection-color: {p.accent_text};
}}
QMainWindow, QDialog {{
    background-color: {p.bg_base};
}}

/* ── Scroll bars ──────────────────────────────────────────────── */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {p.border}; border-radius: 4px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.text_disabled}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    height: 8px; background: transparent; margin: 0 2px;
}}
QScrollBar::handle:horizontal {{
    background: {p.border}; border-radius: 4px; min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p.text_disabled}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Labels ───────────────────────────────────────────────────── */
QLabel {{ background: transparent; color: {p.text_primary}; }}

/* ── Buttons ──────────────────────────────────────────────────── */
QPushButton {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 7px 18px;
    font-size: {t.size_base}px;
    font-weight: 500;
    min-height: 34px;
}}
QPushButton:hover {{
    background-color: {p.bg_overlay};
    border-color: {p.text_disabled};
}}
QPushButton:pressed {{ background-color: {p.border}; }}
QPushButton:disabled {{
    color: {p.text_disabled};
    border-color: {p.border_subtle};
    background-color: {p.bg_surface};
}}
QPushButton[primary="true"] {{
    background-color: {ac};
    color: {p.accent_text};
    border: none;
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{ background-color: {ac_hover}; }}
QPushButton[primary="true"]:pressed {{ background-color: {ac_pressed}; }}
QPushButton[primary="true"]:disabled {{
    background-color: {p.text_disabled}; color: {p.bg_surface};
}}
QPushButton[flat="true"] {{
    background: transparent; border: none;
    color: {p.text_secondary}; padding: 4px 10px; min-height: 0;
}}
QPushButton[flat="true"]:hover {{
    color: {p.text_primary}; background: {p.bg_elevated}; border-radius: 8px;
}}
QPushButton[flat="true"]:pressed {{ background: {p.bg_overlay}; }}
QPushButton[danger="true"] {{
    background-color: transparent; color: {p.error};
    border: 1px solid {p.error};
}}
QPushButton[danger="true"]:hover {{
    background-color: {p.error}; color: {p.accent_text}; border-color: {p.error};
}}

/* ── Inputs ───────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {p.bg_elevated}; color: {p.text_primary};
    border: 1.5px solid {p.border}; border-radius: 8px;
    padding: 9px 12px; font-size: {t.size_base}px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {ac};
}}
QLineEdit:hover, QTextEdit:hover {{ border-color: {p.text_disabled}; }}
QLineEdit[error="true"] {{ border-color: {p.error}; }}

QSpinBox {{
    background-color: {p.bg_elevated}; color: {p.text_primary};
    border: 1.5px solid {p.border}; border-radius: 8px;
    padding: 6px 8px; font-size: {t.size_base}px;
}}
QSpinBox:focus {{ border-color: {ac}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 22px; border: none; background: {p.bg_overlay};
    border-radius: 4px; margin: 2px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {p.border}; }}
QSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {p.text_secondary};
}}
QSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.text_secondary};
}}

/* ── Combo box ────────────────────────────────────────────────── */
QComboBox {{
    background-color: {p.bg_elevated}; color: {p.text_primary};
    border: 1.5px solid {p.border}; border-radius: 8px;
    padding: 8px 36px 8px 12px; font-size: {t.size_base}px;
    min-height: 36px;
}}
QComboBox:hover {{ border-color: {p.text_disabled}; }}
QComboBox:focus {{ border-color: {ac}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.text_secondary};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {p.bg_elevated}; color: {p.text_primary};
    border: 1px solid {p.border}; border-radius: 8px;
    selection-background-color: {ac}; selection-color: {p.accent_text};
    outline: none; padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px; border-radius: 4px; min-height: 28px;
}}

/* ── Sliders ──────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px; background: {p.ring_track}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ac}; border-radius: 9px;
    width: 18px; height: 18px; margin: -7px 0;
}}
QSlider::handle:horizontal:hover {{
    background: {ac_hover}; width: 20px; height: 20px;
    margin: -8px 0; border-radius: 10px;
}}
QSlider::sub-page:horizontal {{ background: {ac}; border-radius: 2px; }}

/* ── Check box ────────────────────────────────────────────────── */
QCheckBox {{ spacing: 10px; color: {p.text_primary}; }}
QCheckBox::indicator {{
    width: 20px; height: 20px;
    border: 2px solid {p.border}; border-radius: 5px;
    background: {p.bg_elevated};
}}
QCheckBox::indicator:checked {{ background: {ac}; border-color: {ac}; }}
QCheckBox::indicator:hover {{ border-color: {ac}; }}

/* ── Tab widget ───────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {p.border}; border-radius: 10px;
    background: {p.bg_surface}; top: -1px;
}}
QTabBar::tab {{
    background: transparent; color: {p.text_secondary};
    padding: 10px 20px; border: none;
    font-size: {t.size_base}px; font-weight: 500; min-width: 80px;
}}
QTabBar::tab:selected {{
    color: {p.text_primary}; border-bottom: 2px solid {ac}; font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {p.text_primary}; background: {p.bg_elevated}; border-radius: 6px;
}}

/* ── List ─────────────────────────────────────────────────────── */
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border-radius: 8px; padding: 2px; }}
QListWidget::item:selected {{ background: {p.bg_elevated}; color: {p.text_primary}; }}
QListWidget::item:hover {{ background: {p.bg_surface}; }}

/* ── Tooltips ─────────────────────────────────────────────────── */
QToolTip {{
    background: {p.bg_overlay}; color: {p.text_primary};
    border: 1px solid {p.border}; border-radius: 6px;
    padding: 5px 10px; font-size: {t.size_sm}px;
}}

/* ── Separator ────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {p.border}; border: none; background: {p.border}; max-height: 1px;
}}

/* ── Menu ─────────────────────────────────────────────────────── */
QMenu {{
    background: {p.bg_elevated}; color: {p.text_primary};
    border: 1px solid {p.border}; border-radius: 10px; padding: 6px;
}}
QMenu::item {{
    padding: 8px 20px 8px 12px; border-radius: 6px; font-size: {t.size_base}px;
}}
QMenu::item:selected {{ background: {p.bg_overlay}; color: {p.text_primary}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 8px; }}

/* ── GroupBox ─────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {p.border}; border-radius: 10px;
    margin-top: 18px; padding: 14px 12px 12px 12px;
    font-weight: 600; color: {p.text_secondary};
    font-size: 11px; letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 10px; left: 12px;
    color: {p.text_secondary}; background: {p.bg_base}; border-radius: 4px;
}}

/* ── MessageBox ───────────────────────────────────────────────── */
QMessageBox {{ background: {p.bg_surface}; }}
QMessageBox QLabel {{
    color: {p.text_primary}; font-size: {t.size_base}px; min-width: 280px;
}}
QDialogButtonBox QPushButton {{ min-width: 90px; }}

/* ── Named component rules ────────────────────────────────────── */
#SectionHeader {{
    color: {p.text_secondary};
    font-size: 11px;
    letter-spacing: 0.8px;
    font-weight: 600;
}}
#EmptyStateLabel {{ color: {p.text_disabled}; font-size: {t.size_base}px; }}
#SettingDesc {{ color: {p.text_secondary}; font-size: {t.size_sm}px; }}
"""
    return qss
