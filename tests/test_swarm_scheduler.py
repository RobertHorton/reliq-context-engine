from pathlib import Path

from reliq_context_engine.cognition import UnifiedCognitionLayer
from reliq_context_engine.context_engine import ContextEngine
from reliq_context_engine.dashboard.status import DashboardState
from reliq_context_engine.models import RuntimeStatus
from reliq_context_engine.research.swarm import ResearchSwarm
from reliq_context_engine.resources.scheduler import VramAwareScheduler


def seed_engine(tmp_path: Path) -> ContextEngine:
    wiki_dir = tmp_path / "knowledge" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "Research.md").write_text(
        "# Research\n\nUse task-aware retrieval, structured memory, and deterministic prompts.\n",
        encoding="utf-8",
    )
    (wiki_dir / "Diagnostics.md").write_text(
        "# Diagnostics\n\nPrioritize likely root causes and reduce noisy output.\n",
        encoding="utf-8",
    )
    memory_dir = tmp_path / "memory"
    return ContextEngine(wiki_dir=wiki_dir, memory_dir=memory_dir, knowledge_limit=5, memory_limit=5)


def test_scheduler_blocks_generation_in_gaming_mode() -> None:
    scheduler = VramAwareScheduler(
        status_provider=lambda: RuntimeStatus(
            mode="gaming",
            gpu_available=True,
            gpu_name="RTX 4080",
            gpu_utilization_pct=92.0,
            vram_total_gb=16.0,
            vram_used_gb=14.0,
            vram_free_gb=2.0,
        )
    )

    decision = scheduler.can_schedule("generation")

    assert decision.allowed is False
    assert decision.mode == "gaming"


def test_scheduler_allows_research_when_gpu_telemetry_is_missing() -> None:
    scheduler = VramAwareScheduler(
        status_provider=lambda: RuntimeStatus(
            mode="compatibility",
            gpu_available=False,
            notes=["no gpu"],
        )
    )

    decision = scheduler.can_schedule("research")

    assert decision.allowed is True
    assert decision.reason.startswith("GPU telemetry unavailable")


def test_research_swarm_runs_cognition_and_tracks_dashboard(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    layer = UnifiedCognitionLayer(context_engine=engine)
    scheduler = VramAwareScheduler(
        status_provider=lambda: RuntimeStatus(
            mode="full_power",
            gpu_available=True,
            gpu_name="RTX 4080",
            gpu_utilization_pct=22.0,
            vram_total_gb=16.0,
            vram_used_gb=4.0,
            vram_free_gb=12.0,
        )
    )
    dashboard = DashboardState()
    swarm = ResearchSwarm(cognition=layer, scheduler=scheduler, dashboard=dashboard)

    result = swarm.run(
        "Research a deterministic prompt strategy for diagnostics.",
        runner=lambda prompt: "Use deterministic prompting, minimal context, and scored retrieval.",
        user_id="robert",
        session_id="swarm-1",
        persist=True,
    )

    assert result.decision.allowed is True
    assert result.cognition is not None
    assert result.evaluation_score is not None
    snapshot = dashboard.summary(runtime=scheduler.get_status())
    assert snapshot["queued"] == 0
    assert snapshot["running"] == 0
    assert snapshot["history"]
