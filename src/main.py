from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict

from .build_video import VideoBuildError, build_video
from .fetch_puzzle import PuzzleFetchError, fetch_daily_puzzle, save_puzzle_json
from .metadata import write_metadata
from .puzzle_model import PuzzleNormalizationError, normalize_puzzle
from .render_board import RenderError, render_frames
from .state_manager import StateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "app.json"
SAMPLE_PUZZLE = {
    "game": {
        "perf": {"key": "classical", "name": "Classical"},
        "fen": "r2qr1k1/pp1n1ppp/3n1b2/2P1N3/5B2/2N5/PPP1Q1PP/R4RK1 b - - 0 1",
    },
    "puzzle": {
        "id": "fallback",
        "rating": 1800,
        "themes": ["middlegame"],
        "solution": ["f6e5", "f4e5", "e8e5"],
        "fen": "r2qr1k1/pp1n1ppp/3n1b2/2P1N3/5B2/2N5/PPP1Q1PP/R4RK1 b - - 0 1",
    },
}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_ffmpeg(video_cfg: Dict[str, Any]) -> None:
    ffmpeg_bin = str(video_cfg.get("ffmpeg_path", "ffmpeg"))
    if shutil.which(ffmpeg_bin) is None:
        raise FileNotFoundError(f"FFmpeg not found on PATH (looked for '{ffmpeg_bin}').")


def _resolve_paths(config: Dict[str, Any], run_date: str) -> Dict[str, Path]:
    artifacts_root = Path(config.get("paths", {}).get("artifacts_root", "artifacts"))
    run_dir = REPO_ROOT / artifacts_root / run_date
    return {
        "run_dir": run_dir,
        "puzzle_json": run_dir / "puzzle.json",
        "metadata": run_dir / "metadata.json",
        "frames_dir": run_dir / "frames",
        "video": run_dir / "video.mp4",
    }


def smoke_test(config_path: Path) -> int:
    logging.info("Running smoke-test using config at %s", config_path)
    config = load_config(config_path)
    ensure_ffmpeg(config.get("video", {}))

    # Use a lightweight copy for smoke tests to keep runtime small.
    test_config = json.loads(json.dumps(config))
    render_cfg = test_config.setdefault("render", {})
    render_cfg["intro_seconds"] = min(float(render_cfg.get("intro_seconds", 2)), 1.0)
    render_cfg["think_seconds"] = min(float(render_cfg.get("think_seconds", 2)), 1.0)
    render_cfg["move_hold_seconds"] = min(float(render_cfg.get("move_hold_seconds", 1)), 0.5)
    render_cfg["outro_seconds"] = min(float(render_cfg.get("outro_seconds", 2)), 1.0)

    tmp_dir = Path(tempfile.mkdtemp(prefix="chess-smoke-"))
    try:
        puzzle = normalize_puzzle(SAMPLE_PUZZLE)
        frames_dir = tmp_dir / "frames"
        frames_count = render_frames(puzzle, test_config, frames_dir)
        video_path = tmp_dir / "video.mp4"
        build_video(frames_dir, video_path, test_config.get("video", {}))
        write_metadata(tmp_dir / "metadata.json", puzzle, test_config, frames_count, video_path)
        logging.info("Smoke-test artifacts stored in %s", tmp_dir)
    finally:
        # Keep temporary artifacts for inspection if needed.
        pass
    return 0


def run_pipeline(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    ensure_ffmpeg(config.get("video", {}))

    run_date = args.date or date.today().isoformat()
    paths = _resolve_paths(config, run_date)
    state = StateManager(paths["run_dir"], force=args.force)

    raw_puzzle: Dict[str, Any] | None = None
    try:
        if state.should_skip("fetch") and paths["puzzle_json"].exists():
            logging.info("Skipping fetch; using existing puzzle.json")
            raw_puzzle = json.loads(paths["puzzle_json"].read_text())
        else:
            logging.info("Fetching daily puzzle from Lichess")
            raw_puzzle = fetch_daily_puzzle()
            save_puzzle_json(paths["puzzle_json"], raw_puzzle)
            state.mark_step("fetch", "fetched puzzle")
    except PuzzleFetchError as exc:
        logging.warning("Fetch step failed (%s); using bundled sample puzzle.", exc)
        raw_puzzle = SAMPLE_PUZZLE
        save_puzzle_json(paths["puzzle_json"], raw_puzzle)
        state.mark_step("fetch", f"used fallback puzzle after fetch failure: {exc}")
    except FileNotFoundError as exc:
        logging.error("Fetch step failed: %s", exc)
        state.mark_error("fetch", str(exc))
        return 1

    try:
        puzzle = normalize_puzzle(raw_puzzle)
    except PuzzleNormalizationError as exc:
        logging.error("Normalization failed: %s", exc)
        state.mark_error("normalize", str(exc))
        return 1

    try:
        if state.should_skip("render") and paths["frames_dir"].exists():
            logging.info("Skipping render; frames already exist")
            frames_count = len(list(paths["frames_dir"].glob("frame_*.png")))
        else:
            logging.info("Rendering frames")
            frames_count = render_frames(puzzle, config, paths["frames_dir"])
            state.mark_step("render", f"{frames_count} frames rendered")
    except RenderError as exc:
        logging.error("Render step failed: %s", exc)
        state.mark_error("render", str(exc))
        return 1

    try:
        if state.should_skip("video") and paths["video"].exists():
            logging.info("Skipping video build; video already exists")
        else:
            logging.info("Building video")
            build_video(paths["frames_dir"], paths["video"], config.get("video", {}))
            state.mark_step("video", "video built")
    except VideoBuildError as exc:
        logging.error("Video build failed: %s", exc)
        state.mark_error("video", str(exc))
        return 1
    except FileNotFoundError as exc:
        logging.error("Video build failed: %s", exc)
        state.mark_error("video", str(exc))
        return 1

    logging.info("Writing metadata")
    write_metadata(paths["metadata"], puzzle, config, frames_count, paths["video"])
    state.mark_step("metadata", "metadata written")
    state.mark_complete()

    logging.info("Pipeline complete. Artifacts are in %s", paths["run_dir"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Milestone 1 local pipeline for Lichess daily puzzle video.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke = subparsers.add_parser("smoke-test", help="Run local dependency and render smoke test.")
    smoke.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to app config JSON.")

    run = subparsers.add_parser("run", help="Fetch puzzle, render frames, and build video.")
    run.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to app config JSON.")
    run.add_argument("--date", help="Override run date (YYYY-MM-DD). Defaults to today.")
    run.add_argument("--skip-upload", action="store_true", help="Ignored flag for milestone boundary compliance.")
    run.add_argument("--force", action="store_true", help="Re-run all steps even if state markers are present.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "smoke-test":
        return smoke_test(Path(args.config))
    if args.command == "run":
        return run_pipeline(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
