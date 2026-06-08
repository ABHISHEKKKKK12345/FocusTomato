"""
Task management with persistent storage.
"""

import logging
from typing import List, Optional

from core.models import Task, TaskStatus
from core.storage import get_data_dir, atomic_write_json, read_json

logger = logging.getLogger(__name__)
TASKS_FILE = get_data_dir() / "tasks.json"


class TaskManager:
    """CRUD operations for tasks, persisted to JSON."""

    def __init__(self) -> None:
        self._tasks: List[Task] = self._load()

    def _load(self) -> List[Task]:
        raw = read_json(TASKS_FILE, default=[])
        tasks = []
        for item in raw:
            try:
                tasks.append(Task.from_dict(item))
            except Exception as e:
                logger.warning(f"Skipping corrupt task: {e}")
        return tasks

    def _save(self) -> None:
        try:
            atomic_write_json(TASKS_FILE, [t.to_dict() for t in self._tasks])
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    def get_all(self, include_archived: bool = False) -> List[Task]:
        if include_archived:
            return list(self._tasks)
        return [t for t in self._tasks if t.status != TaskStatus.ARCHIVED]

    def get_active(self) -> List[Task]:
        return [t for t in self._tasks if t.status == TaskStatus.ACTIVE]

    def get_by_id(self, task_id: str) -> Optional[Task]:
        return next((t for t in self._tasks if t.id == task_id), None)

    def add(self, task: Task) -> Task:
        self._tasks.insert(0, task)
        self._save()
        return task

    def update(self, task: Task) -> None:
        for i, t in enumerate(self._tasks):
            if t.id == task.id:
                self._tasks[i] = task
                self._save()
                return
        logger.warning(f"Task {task.id} not found for update")

    def delete(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._save()

    def complete_task(self, task_id: str) -> None:
        from datetime import datetime
        task = self.get_by_id(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            self.update(task)

    def increment_pomodoro(self, task_id: str) -> None:
        task = self.get_by_id(task_id)
        if task:
            task.completed_pomodoros += 1
            self.update(task)

    def reorder(self, task_ids: List[str]) -> None:
        """Reorder tasks by providing new order of IDs."""
        id_to_task = {t.id: t for t in self._tasks}
        reordered = [id_to_task[tid] for tid in task_ids if tid in id_to_task]
        rest = [t for t in self._tasks if t.id not in set(task_ids)]
        self._tasks = reordered + rest
        self._save()
