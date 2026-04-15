from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .puzzle_model import Puzzle


def write_metadata(
    target_path: Path,
    puzzle: Puzzle,
    config: Dict[str, Any],
    frames_count: int,
    video_path: Path,
) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "puzzle": {
            "id": puzzle.puzzle_id,
            "rating": puzzle.rating,
            "themes": puzzle.themes,
            "solution_length": len(puzzle.solution),
            "fen": puzzle.fen,
            "side_to_move": puzzle.side_to_move,
            "perf": puzzle.perf,
        },
        "artifacts": {
            "metadata": str(target_path),
            "video": str(video_path),
            "frames_dir": str(video_path.parent / "frames"),
            "puzzle_json": str(video_path.parent / "puzzle.json"),
        },
        "video": config.get("video", {}),
        "render": config.get("render", {}),
        "frames_count": frames_count,
    }
    target_path.write_text(json.dumps(payload, indent=2))
