from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import requests

DAILY_PUZZLE_URL = "https://lichess.org/api/puzzle/daily"


class PuzzleFetchError(Exception):
    """Raised when fetching the daily puzzle fails."""


def fetch_daily_puzzle() -> Dict[str, Any]:
    try:
        response = requests.get(DAILY_PUZZLE_URL, timeout=15)
    except requests.RequestException as exc:
        raise PuzzleFetchError(f"Failed to contact Lichess: {exc}") from exc
    if response.status_code != 200:
        raise PuzzleFetchError(f"Unexpected status {response.status_code} from Lichess.")
    try:
        return response.json()
    except ValueError as exc:
        raise PuzzleFetchError("Failed to parse Lichess daily puzzle JSON.") from exc


def save_puzzle_json(target_path: Path, payload: Dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2))
