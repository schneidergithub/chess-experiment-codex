from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import chess


@dataclass
class Puzzle:
    puzzle_id: str
    rating: int
    themes: List[str]
    solution: List[str]
    fen: str
    side_to_move: str
    perf: str


class PuzzleNormalizationError(Exception):
    """Raised when required puzzle data is missing or invalid."""


def _extract_fen(raw: Dict[str, Any]) -> str:
    puzzle_block = raw.get("puzzle") or {}
    raw_block = raw.get("raw") or {}
    game_block = raw.get("game") or {}
    fen = puzzle_block.get("fen") or raw_block.get("fen") or game_block.get("fen")
    if not fen:
        raise PuzzleNormalizationError("Missing FEN in puzzle payload.")
    return fen


def _extract_perf(game_block: Dict[str, Any]) -> str:
    perf_block = game_block.get("perf")
    if isinstance(perf_block, dict):
        return perf_block.get("name") or perf_block.get("key") or "unknown"
    if isinstance(perf_block, str):
        return perf_block
    return "unknown"


def normalize_puzzle(raw: Dict[str, Any]) -> Puzzle:
    puzzle_block = raw.get("puzzle") or {}
    game_block = raw.get("game") or {}

    fen = _extract_fen(raw)
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise PuzzleNormalizationError(f"Invalid FEN supplied: {exc}") from exc

    solution_raw = puzzle_block.get("solution") or []
    if not isinstance(solution_raw, list):
        raise PuzzleNormalizationError("Puzzle solution must be a list.")
    solution = [str(move) for move in solution_raw]

    puzzle_id = str(puzzle_block.get("id") or "")
    if not puzzle_id:
        raise PuzzleNormalizationError("Puzzle id missing.")

    rating = int(puzzle_block.get("rating") or 0)
    themes = puzzle_block.get("themes") or []
    if not isinstance(themes, list):
        themes = [str(themes)]

    side_to_move = "white" if board.turn == chess.WHITE else "black"
    perf = _extract_perf(game_block)

    return Puzzle(
        puzzle_id=puzzle_id,
        rating=rating,
        themes=[str(t) for t in themes],
        solution=solution,
        fen=fen,
        side_to_move=side_to_move,
        perf=str(perf),
    )
