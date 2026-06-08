# 🍅 FocusTomato v1.0.0

A production-grade, cross-platform Pomodoro timer built with Python 3 and PyQt6.

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
.venv\Scripts\activate          # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

### Optional enhancements

```bash
# Richer OS-native desktop notifications
pip install plyer

# Sound support on some Linux distros
sudo apt install libqt6multimedia6 python3-pyqt6.qtmultimedia
```

## Features

| Feature | Details |
|---|---|
| **Timer** | Focus · Short Break · Long Break with animated progress ring |
| **Session control** | Start · Pause · Resume · Reset · Skip |
| **Cycle tracking** | Configurable sessions-before-long-break; dot progress indicator |
| **Task management** | Add / edit / complete / delete tasks; per-task pomodoro counter |
| **Active task** | Link a task to a focus session; shown in ring and banner |
| **Dashboard** | Today stats · Weekly chart · All-time totals · Session history |
| **Themes** | Dark and Light, with custom accent colour |
| **Sound alerts** | Procedurally generated tones: Gentle · Classic · Minimal |
| **Notifications** | OS-native (via plyer) or tray balloon fallback |
| **System tray** | Minimize to tray; tray tooltip shows live timer state |
| **Export** | CSV and JSON session history export |
| **Persistence** | All settings, tasks, and history survive restarts |
| **Packaging** | PyInstaller-ready spec included |

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Start / Pause / Resume |
| `R` | Reset current session |
| `Ctrl+1` | Go to Timer |
| `Ctrl+2` | Go to Tasks |
| `Ctrl+3` | Go to Dashboard |
| `Ctrl+,` | Open Settings |

## Data Storage

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\FocusTomato\` |
| macOS | `~/Library/Application Support/FocusTomato/` |
| Linux | `~/.local/share/FocusTomato/` |

Files: `settings.json` · `tasks.json` · `sessions.json` · `logs/focustomato.log`

## Building a Binary

```bash
pip install pyinstaller
pyinstaller focustomato.spec
# Output in: dist/FocusTomato/
```

## Project Structure

```
focustomato/
├── main.py                      # Entry point
├── requirements.txt
├── focustomato.spec             # PyInstaller packaging config
├── CHANGELOG.md
├── core/
│   ├── app_controller.py        # Central orchestrator & session lifecycle
│   ├── timer_engine.py          # Precise monotonic-clock countdown
│   ├── models.py                # Domain models (Task, Session, enums)
│   ├── settings_manager.py      # Typed settings with atomic persistence
│   ├── task_manager.py          # Task CRUD with JSON storage
│   ├── stats_manager.py         # Session history & statistics
│   ├── sound_manager.py         # Procedural WAV tone generation
│   ├── notification_manager.py  # Cross-platform desktop notifications
│   ├── storage.py               # Atomic JSON I/O, data dir, CSV export
│   └── logger.py                # Rotating file logger
└── ui/
    ├── main_window.py           # Top-level window, sidebar, system tray
    ├── timer_widget.py          # Timer panel (ring, controls, task banner)
    ├── task_panel.py            # Task list with add/edit/complete/delete
    ├── dashboard_widget.py      # Stats, weekly chart, session history
    ├── settings_dialog.py       # Tabbed settings panel
    ├── widgets.py               # ProgressRing, BarChart, StatCard, etc.
    └── theme.py                 # Design tokens, QSS stylesheet generator
```

## Architecture Notes

- **No blocking operations** — timer uses `QTimer` (500ms) + `time.monotonic()` for drift-free precision
- **Atomic writes** — JSON persistence uses temp-file + `os.replace()` to prevent corruption
- **Graceful degradation** — sound and notifications fall back silently when optional deps are absent
- **Theme system** — single `build_stylesheet()` call regenerates full QSS from design tokens
- **Zero circular imports** — verified with full import-order test suite

## Author

Built by **Abhishek Srivastava**.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Abhishek%20Srivastava-blue?logo=linkedin)](https://www.linkedin.com/in/abhishek-srivastava-1538461b1)

---

*FocusTomato is released under the [MIT License](LICENSE).*
