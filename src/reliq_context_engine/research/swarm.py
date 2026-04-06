from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ..cognition import UnifiedCognitionLayer
from ..dashboard.status import DashboardState
from ..models import SwarmRunResult
from ..resources.scheduler import VramAwareScheduler


def score_response(response: str | None) -> float:
    if not response:
        return 0.0
    trimmed = response.strip()
    if not trimmed:
        return 0.0
    return round(min(1.0, max(0.2, len(trimmed) / 250)), 3)


class ResearchSwarm:
    def __init__(
        self,
        cognition: UnifiedCognitionLayer | None = None,
        scheduler: VramAwareScheduler | None = None,
        dashboard: DashboardState | None = None,
        max_workers: int = 3,
    ) -> None:
        self.cognition = cognition or UnifiedCognitionLayer()
        self.scheduler = scheduler or VramAwareScheduler()
        self.dashboard = dashboard or DashboardState()
        self.max_workers = max_workers

    def run(
        self,
        goal: str,
        runner: Callable[[str], str] | None = None,
        agent_type: str = "research",
        task_type: str = "research",
        user_id: str | None = None,
        session_id: str | None = None,
        persist: bool = False,
    ) -> SwarmRunResult:
        decision = self.scheduler.can_schedule(agent_type)
        tracked = self.dashboard.enqueue(goal, agent_type)

        if not decision.allowed:
            self.dashboard.finish(tracked.task_id, "blocked", detail=decision.reason)
            return SwarmRunResult(
                goal=goal,
                agent_type=agent_type,
                decision=decision,
                task_id=tracked.task_id,
            )

        self.dashboard.start(tracked.task_id)
        cognition = self.cognition.run_cognition(
            goal,
            runner=runner,
            task_type=task_type,
            user_id=user_id,
            session_id=session_id,
            persist=persist,
        )
        evaluation_score = score_response(cognition.response)
        self.dashboard.finish(
            tracked.task_id,
            "completed" if cognition.response is not None else "context_ready",
            detail=decision.reason,
            evaluation_score=evaluation_score,
        )
        return SwarmRunResult(
            goal=goal,
            agent_type=agent_type,
            decision=decision,
            cognition=cognition,
            evaluation_score=evaluation_score,
            task_id=tracked.task_id,
        )

    def run_parallel(
        self,
        goals: list[str],
        runner: Callable[[str], str] | None = None,
        agent_type: str = "research",
        task_type: str = "research",
        user_id: str | None = None,
        persist: bool = False,
    ) -> list[SwarmRunResult]:
        if not goals:
            return []
        with ThreadPoolExecutor(max_workers=min(len(goals), self.max_workers)) as executor:
            futures = [
                executor.submit(
                    self.run,
                    goal,
                    runner,
                    agent_type,
                    task_type,
                    user_id,
                    f"swarm-{idx}",
                    persist,
                )
                for idx, goal in enumerate(goals, start=1)
            ]
            return [future.result() for future in futures]
