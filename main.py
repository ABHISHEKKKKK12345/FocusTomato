"""
FocusTomato - Production-Grade Pomodoro Timer
Entry point for the application.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure the app directory is in the path
APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase

from core.app_controller import AppController
from core.logger import setup_logging


def main() -> None:
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("FocusTomato starting up...")

    # High DPI support
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("FocusTomato")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FocusTomato")
    app.setOrganizationDomain("focustomato.app")

    # Prevent app from quitting when last window is hidden (for system tray)
    app.setQuitOnLastWindowClosed(False)

    # Load embedded fonts
    _load_fonts()

    # Initialize and start the application controller
    controller = AppController(app)
    controller.start()

    logger.info("Entering main event loop")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)


def _load_fonts() -> None:
    """Load any bundled fonts."""
    fonts_dir = APP_DIR / "assets" / "fonts"
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))
        for font_file in fonts_dir.glob("*.otf"):
            QFontDatabase.addApplicationFont(str(font_file))


if __name__ == "__main__":
    main()
