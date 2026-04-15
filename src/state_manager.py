from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional


@dataclass
class StateManager:
    run_dir: Path
    force: bool = False

    def __post_init__(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir = self.run_dir / "_state"
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def _marker_path(self, step: str) -> Path:
        return self._state_dir / f"{step}.done"

    def _error_path(self, step: str) -> Path:
        return self._state_dir / f"{step}.error.log"

    def should_skip(self, step: str) -> bool:
        return self._marker_path(step).exists() and not self.force

    def mark_step(self, step: str, details: Optional[str] = None) -> None:
        marker = self._marker_path(step)
        content = {
            "step": step,
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "details": details or "",
        }
        marker.write_text(f"{content}\n")
        error_path = self._error_path(step)
        if error_path.exists():
            error_path.unlink()

    def mark_error(self, step: str, message: str) -> None:
        self._error_path(step).write_text(message + "\n")

    def completion_marker(self) -> Path:
        return self._marker_path("complete")

    def mark_complete(self) -> None:
        self.mark_step("complete", "pipeline finished")
