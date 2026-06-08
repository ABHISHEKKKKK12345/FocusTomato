"""
Domain models for FocusTomato: tasks, sessions, and statistics.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionType(str, Enum):
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Task:
    """A task that can be linked to focus sessions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    notes: str = ""
    estimated_pomodoros: int = 1
    completed_pomodoros: int = 0
    status: TaskStatus = TaskStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    color: str = "#E85D4A"

    @property
    def is_done(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "estimated_pomodoros": self.estimated_pomodoros,
            "completed_pomodoros": self.completed_pomodoros,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        d = dict(d)
        if "status" in d:
            d["status"] = TaskStatus(d["status"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Session:
    """A completed or in-progress timer session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_type: SessionType = SessionType.FOCUS
    duration_seconds: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    completed: bool = False
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    interruptions: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_type": self.session_type.value,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "completed": self.completed,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "interruptions": self.interruptions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        d = dict(d)
        if "session_type" in d:
            d["session_type"] = SessionType(d["session_type"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DailyStats:
    """Aggregated statistics for a single day."""
    date: str = ""
    focus_sessions: int = 0
    focus_minutes: int = 0
    break_sessions: int = 0
    tasks_completed: int = 0
    streak_day: bool = False
