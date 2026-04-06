from __future__ import annotations

import shutil
import subprocess
from typing import Callable

from ..models import AgentProfile, RuntimeStatus, SchedulerDecision

DEFAULT_AGENT_PROFILES = {
    "memory": AgentProfile(name="memory", vram_gb=0.2, priority=0),
    "research": AgentProfile(name="research", vram_gb=1.0, priority=1),
    "llm": AgentProfile(name="llm", vram_gb=4.0, priority=2),
    "generation": AgentProfile(name="generation", vram_gb=6.0, priority=3),
}


class VramAwareScheduler:
    def __init__(
        self,
        profiles: dict[str, AgentProfile] | None = None,
        reserve_gb: float = 1.0,
        balanced_threshold_pct: float = 60.0,
        gaming_threshold_pct: float = 85.0,
        status_provider: Callable[[], RuntimeStatus] | None = None,
    ) -> None:
        self.profiles = profiles or DEFAULT_AGENT_PROFILES
        self.reserve_gb = reserve_gb
        self.balanced_threshold_pct = balanced_threshold_pct
        self.gaming_threshold_pct = gaming_threshold_pct
        self.status_provider = status_provider

    def get_profile(self, agent_type: str) -> AgentProfile:
        return self.profiles.get(agent_type, self.profiles["research"])

    def get_status(self) -> RuntimeStatus:
        if self.status_provider is not None:
            return self.status_provider()

        exe = shutil.which("nvidia-smi")
        if not exe:
            return RuntimeStatus(
                mode="compatibility",
                gpu_available=False,
                notes=["nvidia-smi not found; VRAM-aware scheduling is running in compatibility mode."],
            )

        try:
            completed = subprocess.run(
                [
                    exe,
                    "--query-gpu=name,utilization.gpu,memory.total,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except Exception as exc:
            return RuntimeStatus(
                mode="compatibility",
                gpu_available=False,
                notes=[f"nvidia-smi query failed: {exc!s}"],
            )

        line = next((item.strip() for item in completed.stdout.splitlines() if item.strip()), "")
        if not line:
            return RuntimeStatus(
                mode="compatibility",
                gpu_available=False,
                notes=["nvidia-smi returned no GPU rows."],
            )

        parts = [item.strip() for item in line.split(",")]
        if len(parts) < 4:
            return RuntimeStatus(
                mode="compatibility",
                gpu_available=False,
                notes=["nvidia-smi output was incomplete; scheduler skipped hard VRAM enforcement."],
            )

        name, util_raw, total_raw, used_raw = parts[:4]
        util_pct = float(util_raw)
        total_gb = round(float(total_raw) / 1024, 3)
        used_gb = round(float(used_raw) / 1024, 3)
        free_gb = round(max(total_gb - used_gb, 0.0), 3)
        mode = self._mode_for_utilization(util_pct)
        notes: list[str] = []
        if mode == "gaming":
            notes.append("High GPU utilization detected; heavy agents may be deferred.")
        elif mode == "balanced":
            notes.append("Moderate GPU utilization detected; large jobs should respect VRAM limits.")

        return RuntimeStatus(
            mode=mode,
            gpu_available=True,
            gpu_name=name,
            gpu_utilization_pct=util_pct,
            vram_total_gb=total_gb,
            vram_used_gb=used_gb,
            vram_free_gb=free_gb,
            notes=notes,
        )

    def can_schedule(self, agent_type: str, status: RuntimeStatus | None = None) -> SchedulerDecision:
        active_status = status or self.get_status()
        profile = self.get_profile(agent_type)

        if not active_status.gpu_available or active_status.vram_free_gb is None:
            return SchedulerDecision(
                allowed=True,
                mode=active_status.mode,
                agent_type=agent_type,
                required_vram_gb=profile.vram_gb,
                available_vram_gb=active_status.vram_free_gb,
                reason="GPU telemetry unavailable; allowing task in compatibility mode.",
                profile=profile,
            )

        effective_free = round(max(active_status.vram_free_gb - self.reserve_gb, 0.0), 3)
        if active_status.mode == "gaming" and profile.priority >= 3:
            return SchedulerDecision(
                allowed=False,
                mode=active_status.mode,
                agent_type=agent_type,
                required_vram_gb=profile.vram_gb,
                available_vram_gb=active_status.vram_free_gb,
                reason="Gaming mode is active; high-VRAM generation tasks are deferred.",
                profile=profile,
            )

        if effective_free < profile.vram_gb:
            return SchedulerDecision(
                allowed=False,
                mode=active_status.mode,
                agent_type=agent_type,
                required_vram_gb=profile.vram_gb,
                available_vram_gb=active_status.vram_free_gb,
                reason="Not enough free VRAM after reserve budget.",
                profile=profile,
            )

        return SchedulerDecision(
            allowed=True,
            mode=active_status.mode,
            agent_type=agent_type,
            required_vram_gb=profile.vram_gb,
            available_vram_gb=active_status.vram_free_gb,
            reason="Scheduler approved the task.",
            profile=profile,
        )

    def _mode_for_utilization(self, util_pct: float) -> str:
        if util_pct >= self.gaming_threshold_pct:
            return "gaming"
        if util_pct >= self.balanced_threshold_pct:
            return "balanced"
        return "full_power"
