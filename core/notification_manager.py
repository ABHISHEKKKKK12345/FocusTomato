"""
Cross-platform desktop notification manager for FocusTomato.
Uses PyQt6's QSystemTrayIcon for tray-based popups (works on all platforms),
with optional plyer fallback for richer OS-native notifications.
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QSystemTrayIcon

logger = logging.getLogger(__name__)

# Try plyer for richer OS notifications
_plyer_available = False
try:
    from plyer import notification as _plyer_notification
    _plyer_available = True
    logger.info("plyer notifications available")
except ImportError:
    logger.info("plyer not available; using tray notifications")


class NotificationManager:
    """
    Sends desktop notifications via tray icon or plyer.

    Designed to work even when no tray icon is present
    (degrades gracefully to log-only).
    """

    def __init__(self) -> None:
        self._enabled: bool = True
        self._tray_icon: Optional["QSystemTrayIcon"] = None

    def set_tray_icon(self, tray: "QSystemTrayIcon") -> None:
        self._tray_icon = tray

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def notify(self, title: str, message: str, duration: int = 5) -> None:
        """Send a desktop notification."""
        if not self._enabled:
            return
        logger.info(f"Notification: {title} — {message}")

        sent = False

        # Prefer plyer for native OS notifications
        if _plyer_available:
            try:
                _plyer_notification.notify(
                    title=title,
                    message=message,
                    app_name="FocusTomato",
                    timeout=duration,
                )
                sent = True
            except Exception as e:
                logger.debug(f"plyer notify failed: {e}")

        # Fall back to tray balloon
        if not sent and self._tray_icon is not None:
            try:
                from PyQt6.QtWidgets import QSystemTrayIcon
                self._tray_icon.showMessage(
                    title,
                    message,
                    QSystemTrayIcon.MessageIcon.Information,
                    duration * 1000,
                )
                sent = True
            except Exception as e:
                logger.debug(f"Tray notification failed: {e}")

        if not sent:
            logger.warning("No notification backend available")

    def notify_focus_complete(self) -> None:
        self.notify(
            "🍅 Focus session complete!",
            "Great work! Time for a well-earned break.",
        )

    def notify_break_complete(self) -> None:
        self.notify(
            "⏰ Break over!",
            "Ready to get back to it? Start your next focus session.",
        )

    def notify_long_break_complete(self) -> None:
        self.notify(
            "☕ Long break complete!",
            "You've earned it — now let's tackle the next round!",
        )
