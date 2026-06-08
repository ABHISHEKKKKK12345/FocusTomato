"""
Cross-platform persistent storage helpers for FocusTomato.
"""

import os
import sys
import json
import csv
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Return the cross-platform user data directory for FocusTomato."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "FocusTomato"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON data atomically using a temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_json(path: Path, default: Any = None) -> Any:
    """Read JSON file safely, returning *default* on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read {path}: {e}")
        return default


def export_to_csv(path: Path, rows: list[dict]) -> None:
    """Export a list of dicts to CSV."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def export_to_json(path: Path, data: Any) -> None:
    """Export data to JSON file."""
    atomic_write_json(path, data)
