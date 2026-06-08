"""
Settings management for FocusTomato.
All settings are persisted to disk and provide type-safe access.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

from core.storage import get_data_dir, atomic_write_json, read_json

logger = logging.getLogger(__name__)

SETTINGS_FILE = get_data_dir() / "settings.json"


@dataclass
class Settings:
    """All application settings with defaults."""
    # Timer durations (seconds)
    focus_duration: int = 25 * 60
    short_break_duration: int = 5 * 60
    long_break_duration: int = 15 * 60
    sessions_before_long_break: int = 4

    # Behaviour
    auto_start_breaks: bool = False
    auto_start_focus: bool = False
    loop_sessions: bool = True

    # Notifications
    desktop_notifications: bool = True
    sound_alerts: bool = True
    sound_volume: int = 70  # 0–100
    sound_theme: str = "gentle"  # gentle | classic | minimal

    # Appearance
    theme: str = "dark"  # dark | light
    accent_color: str = "#E85D4A"
    font_size: int = 14

    # System tray
    minimize_to_tray: bool = True
    show_tray_icon: bool = True

    # Data
    data_dir: str = ""  # empty = default

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Settings":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class SettingsManager:
    """Loads, saves, and provides access to Settings."""

    def __init__(self) -> None:
        self._settings = self._load()

    def _load(self) -> Settings:
        data = read_json(SETTINGS_FILE, default={})
        try:
            return Settings.from_dict(data)
        except Exception as e:
            logger.warning(f"Settings load failed ({e}), using defaults")
            return Settings()

    def save(self) -> None:
        try:
            atomic_write_json(SETTINGS_FILE, self._settings.to_dict())
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    @property
    def settings(self) -> Settings:
        return self._settings

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self._settings, k):
                setattr(self._settings, k, v)
            else:
                logger.warning(f"Unknown setting: {k}")
        self.save()

    def reset_to_defaults(self) -> None:
        self._settings = Settings()
        self.save()
