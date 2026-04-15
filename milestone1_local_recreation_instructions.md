# Milestone 1 Recreation Instructions (LLM-Optimized)

## Goal
Recreate only Milestone 1 of this project: generate the daily Lichess puzzle video locally as files on disk.

Milestone 1 is complete when a local run produces:
- `artifacts/YYYY-MM-DD/puzzle.json`
- `artifacts/YYYY-MM-DD/metadata.json`
- `artifacts/YYYY-MM-DD/frames/frame_00000.png` (and additional frames)
- `artifacts/YYYY-MM-DD/video.mp4`

## Copy-Paste Prompt For Coding Agents
Use this exact prompt when asking an LLM coding agent to recreate Milestone 1:

You are implementing Milestone 1 only for a local-first chess puzzle video pipeline.

Objective:
- Build a local pipeline that fetches the daily Lichess puzzle, normalizes data, renders frames, and creates a silent MP4.

Allowed output artifacts:
- artifacts/YYYY-MM-DD/puzzle.json
- artifacts/YYYY-MM-DD/metadata.json
- artifacts/YYYY-MM-DD/frames/frame_00000.png and additional frames
- artifacts/YYYY-MM-DD/video.mp4

Hard exclusions:
- Do not implement YouTube API integration.
- Do not add OAuth flow code.
- Do not add token generation steps.
- Do not add upload automation.
- Do not add documentation for YouTube setup.

API contract:
- Fetch from https://lichess.org/api/puzzle/daily
- Parse fen from puzzle.fen first, then raw.fen, then game.fen.

Implementation requirements:
- Python 3.11+
- Use requests, python-chess, Pillow, cairosvg.
- Render board using chess.svg.board plus cairosvg conversion.
- Ensure no board clipping in 1920x1080.
- Ensure pieces are filled SVG set (not Unicode text glyphs).
- Keep run path focused on local generation using --skip-upload.

Acceptance:
- python -m src.main smoke-test exits 0
- python -m src.main run --skip-upload exits 0
- expected artifacts are created and playable
- no YouTube credentials required for this milestone

Stop at Milestone 1 boundary.

## Local LLM and Cloud Execution Profile

### Execution modes
- Local LLM mode:
  - Keep edits incremental and verify each stage locally.
  - Prefer existing virtual environment and editable install.
- Cloud agent mode:
  - Assume stateless workers.
  - Recreate environment from scratch per run.
  - Persist only milestone artifacts and logs.

### Stateless cloud assumptions
- Never rely on previous shell state.
- Always run from repository root.
- Always run explicit setup before verification:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -e .[dev]`

### Deterministic run contract
- Primary validation command for Milestone 1:
  - `python -m src.main run --skip-upload --force`
- Required post-run checks:
  - exit code is `0`
  - `artifacts/YYYY-MM-DD/video.mp4` exists
  - `artifacts/YYYY-MM-DD/puzzle.json` exists
  - `artifacts/YYYY-MM-DD/frames/` exists and is non-empty

### Context budget optimization for small local models
When prompting a local LLM, provide only these files first:
1. `src/main.py`
2. `src/fetch_puzzle.py`
3. `src/puzzle_model.py`
4. `src/render_board.py`
5. `src/build_video.py`
6. `config/app.json`

Only include additional files if the task cannot be solved with this set.

### Prompt shaping for local LLM reliability
- Use short, constraint-heavy prompts.
- Include explicit stop boundary: Milestone 1 only.
- Require exact commands and pass/fail checks.
- Forbid speculative refactors and optional features.

Use this compact instruction suffix in local-model prompts:

```text
Constraints: Milestone1 only. No YouTube/OAuth/upload code or docs. Use existing project structure. Make minimal edits. After changes, run smoke-test and run --skip-upload --force. Report only failing checks and exact file paths changed.
```

### Cloud CI-friendly verification block
Use this exact block in cloud runners:

```bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m src.main smoke-test
python -m src.main run --skip-upload --force
test -f "artifacts/$(date +%F)/video.mp4"
test -f "artifacts/$(date +%F)/puzzle.json"
```

### Failure triage order for local and cloud
1. Dependency import failures (`python-chess`, `Pillow`, `cairosvg`, `requests`).
2. FFmpeg not found or codec invocation issues.
3. Puzzle schema handling errors (`puzzle.fen` fallback logic).
4. Rendering layout issues (board clipping).
5. Illegal move sequence vs provided FEN.

### Artifact portability guidance
- Treat `artifacts/YYYY-MM-DD/` as the portable milestone output bundle.
- Do not include credentials in artifacts.
- Preserve `puzzle.json` and `metadata.json` for reproducibility.

## Strict Scope
Implement only local pipeline behavior:
1. Fetch daily puzzle JSON from Lichess.
2. Normalize puzzle data.
3. Render board frames.
4. Build a silent MP4 with FFmpeg.
5. Save local artifacts and structured logs.

Do not implement or document YouTube automation in this milestone.

## Do Not Include
- Any YouTube API setup steps
- OAuth client creation
- Token generation
- Upload automation instructions
- Scheduling instructions for upload

## Source of Truth for Input API
Endpoint:
- `https://lichess.org/api/puzzle/daily`

Expected shape (schema stable, values change daily):
```json
{
  "game": {
    "id": "MwZcnjIz",
    "perf": {"key": "classical", "name": "Classical"},
    "rated": true,
    "players": [
      {"name": "antigua1956", "id": "antigua1956", "color": "white", "rating": 1747},
      {"name": "Shalaza", "id": "shalaza", "color": "black", "rating": 1735}
    ],
    "pgn": "e4 e5 f4 Nf6 fxe5 Nxe4 Nf3 d5 exd6 Nxd6 Nc3 Bg4 Be2 Be7 O-O O-O Ne5 Bxe2 Qxe2 Bf6 d3 Re8 Bf4 Nd7 d4 c5 dxc5",
    "clock": "15+15"
  },
  "puzzle": {
    "id": "N5nr0",
    "rating": 1804,
    "plays": 89042,
    "solution": ["f6e5", "f4e5", "e8e5"],
    "themes": ["middlegame", "advantage", "short"],
    "fen": "r2qr1k1/pp1n1ppp/3n1b2/2P1N3/5B2/2N5/PPP1Q1PP/R4RK1 b - - 0 1",
    "lastMove": "d4c5",
    "initialPly": 26
  }
}
```

Important parsing rule:
- Prefer `puzzle.fen` first.
- Fallback order: `raw.fen`, then `game.fen`.

## Build Requirements
- Python 3.11+
- FFmpeg available on PATH (or configured in `config/app.json`)
- Dependencies:
  - `requests`
  - `python-chess`
  - `Pillow`
  - `cairosvg`

## Implementation Blueprint

### 1. Create project environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Keep these local runtime commands as the milestone verification path
```bash
python -m src.main smoke-test
python -m src.main run --skip-upload
```

### 3. Implement/verify these modules and responsibilities
- `src/fetch_puzzle.py`
  - GET daily puzzle JSON.
  - Raise explicit error on non-200 response.
  - Persist raw JSON to `puzzle.json`.

- `src/puzzle_model.py`
  - Normalize required fields: `id`, `rating`, `themes`, `solution`, `fen`.
  - Derive side to move from FEN using `python-chess`.
  - Handle `game.perf` as either a string or object.

- `src/render_board.py`
  - Render board visuals from `chess.svg.board()`.
  - Convert SVG to image using `cairosvg`.
  - Fit board within video dimensions (no clipping).
  - Render intro, think-time, solution move, and outro scenes.

- `src/build_video.py`
  - Build silent MP4 from frame sequence with FFmpeg.
  - Use configured width/height/fps/codec/pixel format.

- `src/metadata.py`
  - Save deterministic local metadata JSON for the run.

- `src/state_manager.py`
  - Create per-step markers and run completion marker.
  - Support rerun safety and `--force` behavior.

- `src/main.py`
  - Orchestrate fetch -> normalize -> render -> video -> metadata.
  - Keep `--skip-upload` path as standard Milestone 1 run mode.
  - On error: write step-scoped error file and structured log event.

## Logging and Error Rules
- Structured logs should include step, event, date, and artifact path where relevant.
- Do not pass duplicate `message` fields to structured logger APIs.
  - If logger has positional `message`, use a different key for exception text (example: `error_message`).

## Rendering Rules from Current Working Baseline
- Board must be fully visible in 1920x1080 frames.
- Board should be vertically centered in available space below header text.
- Use filled chess piece graphics via SVG renderer (not Unicode glyph pieces).
- `render.board_size` should be safe for layout (current baseline uses `740`).

## Suggested Milestone 1 Config Baseline
Use these values in `config/app.json` for reliable local generation:
- `video.width`: `1920`
- `video.height`: `1080`
- `video.fps`: `30`
- `render.board_size`: `740`
- `render.show_coordinates`: `true`

## Milestone 1 Acceptance Checklist
All items must pass:
1. `python -m src.main smoke-test` exits with status 0.
2. `python -m src.main run --skip-upload` exits with status 0.
3. `artifacts/YYYY-MM-DD/video.mp4` exists and is playable.
4. `artifacts/YYYY-MM-DD/puzzle.json` and `metadata.json` exist.
5. `artifacts/YYYY-MM-DD/frames/` contains generated PNGs.
6. No board clipping and pieces visually centered in squares.
7. No YouTube credential requirement for this milestone path.

## Explicit Milestone Boundary
Stop after local file generation is verified.

Do not add any additional implementation or documentation for YouTube API automation in Milestone 1 outputs.