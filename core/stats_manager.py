"""
Statistics tracking and session history for FocusTomato.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict

from core.models import Session, SessionType, DailyStats
from core.storage import get_data_dir, atomic_write_json, read_json, export_to_csv, export_to_json

logger = logging.getLogger(__name__)
SESSIONS_FILE = get_data_dir() / "sessions.json"


class StatsManager:
    """Manages session history and computes statistics."""

    def __init__(self) -> None:
        self._sessions: List[Session] = self._load()

    def _load(self) -> List[Session]:
        raw = read_json(SESSIONS_FILE, default=[])
        sessions = []
        for item in raw:
            try:
                sessions.append(Session.from_dict(item))
            except Exception as e:
                logger.warning(f"Skipping corrupt session: {e}")
        return sessions

    def _save(self) -> None:
        try:
            atomic_write_json(SESSIONS_FILE, [s.to_dict() for s in self._sessions])
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def record_session(self, session: Session) -> None:
        self._sessions.append(session)
        self._save()

    def get_all_sessions(self) -> List[Session]:
        return list(self._sessions)

    def get_sessions_today(self) -> List[Session]:
        today = date.today().isoformat()
        return [s for s in self._sessions if s.started_at[:10] == today]

    def get_focus_sessions_today(self) -> List[Session]:
        return [s for s in self.get_sessions_today()
                if s.session_type == SessionType.FOCUS and s.completed]

    def get_total_focus_minutes(self) -> int:
        return sum(
            s.duration_seconds // 60
            for s in self._sessions
            if s.session_type == SessionType.FOCUS and s.completed
        )

    def get_focus_minutes_today(self) -> int:
        return sum(
            s.duration_seconds // 60
            for s in self.get_sessions_today()
            if s.session_type == SessionType.FOCUS and s.completed
        )

    def get_current_streak(self) -> int:
        """Count consecutive days with at least one completed focus session."""
        focus_dates = set(
            s.started_at[:10]
            for s in self._sessions
            if s.session_type == SessionType.FOCUS and s.completed
        )
        if not focus_dates:
            return 0
        streak = 0
        check = date.today()
        while check.isoformat() in focus_dates:
            streak += 1
            check -= timedelta(days=1)
        return streak

    def get_longest_streak(self) -> int:
        focus_dates = sorted(set(
            s.started_at[:10]
            for s in self._sessions
            if s.session_type == SessionType.FOCUS and s.completed
        ))
        if not focus_dates:
            return 0
        longest = 1
        current = 1
        for i in range(1, len(focus_dates)):
            d1 = date.fromisoformat(focus_dates[i - 1])
            d2 = date.fromisoformat(focus_dates[i])
            if (d2 - d1).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        return longest

    def get_weekly_data(self) -> List[DailyStats]:
        """Return stats for last 7 days."""
        result = []
        for i in range(6, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            day_sessions = [s for s in self._sessions if s.started_at[:10] == d]
            stats = DailyStats(
                date=d,
                focus_sessions=sum(1 for s in day_sessions
                                   if s.session_type == SessionType.FOCUS and s.completed),
                focus_minutes=sum(s.duration_seconds // 60 for s in day_sessions
                                  if s.session_type == SessionType.FOCUS and s.completed),
                break_sessions=sum(1 for s in day_sessions
                                   if s.session_type != SessionType.FOCUS),
            )
            result.append(stats)
        return result

    def get_summary(self) -> Dict:
        total_focus = [s for s in self._sessions
                       if s.session_type == SessionType.FOCUS and s.completed]
        return {
            "total_sessions": len(total_focus),
            "total_focus_minutes": sum(s.duration_seconds // 60 for s in total_focus),
            "today_sessions": len(self.get_focus_sessions_today()),
            "today_minutes": self.get_focus_minutes_today(),
            "current_streak": self.get_current_streak(),
            "longest_streak": self.get_longest_streak(),
        }

    def export_csv(self, path) -> None:
        rows = [s.to_dict() for s in self._sessions]
        export_to_csv(path, rows)

    def export_json(self, path) -> None:
        export_to_json(path, [s.to_dict() for s in self._sessions])

    def clear_history(self) -> None:
        self._sessions.clear()
        self._save()
