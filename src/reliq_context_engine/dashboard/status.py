from __future__ import annotations

from collections import deque
from threading import Lock
from uuid import uuid4

from ..models import DashboardTask, RuntimeStatus, utc_now


class DashboardState:
    def __init__(self, history_limit: int = 50) -> None:
        self.history_limit = history_limit
        self._queued: dict[str, DashboardTask] = {}
        self._running: dict[str, DashboardTask] = {}
        self._history: deque[DashboardTask] = deque(maxlen=history_limit)
        self._lock = Lock()

    def enqueue(self, goal: str, agent_type: str) -> DashboardTask:
        task = DashboardTask(task_id=str(uuid4()), goal=goal, agent_type=agent_type, status="queued")
        with self._lock:
            self._queued[task.task_id] = task
        return task

    def start(self, task_id: str) -> DashboardTask | None:
        with self._lock:
            task = self._queued.pop(task_id, None)
            if task is None:
                return None
            task.status = "running"
            task.updated_at = utc_now()
            self._running[task.task_id] = task
            return task

    def finish(
        self,
        task_id: str,
        status: str,
        detail: str | None = None,
        evaluation_score: float | None = None,
    ) -> DashboardTask | None:
        with self._lock:
            task = self._running.pop(task_id, None) or self._queued.pop(task_id, None)
            if task is None:
                return None
            task.status = status
            task.detail = detail
            task.evaluation_score = evaluation_score
            task.updated_at = utc_now()
            self._history.appendleft(task)
            return task

    def history(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return [task.to_dict() for task in list(self._history)[:limit]]

    def summary(self, runtime: RuntimeStatus | None = None) -> dict:
        with self._lock:
            return {
                "runtime": runtime.to_dict() if runtime is not None else None,
                "queued": len(self._queued),
                "running": len(self._running),
                "history": [task.to_dict() for task in list(self._history)],
            }
