from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict

import chess
import chess.svg
import cairosvg
from PIL import Image, ImageDraw, ImageFont

from .puzzle_model import Puzzle


class RenderError(Exception):
    """Raised when board rendering fails."""


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _svg_board_image(board: chess.Board, render_config: Dict[str, Any]) -> Image.Image:
    board_size = int(render_config.get("board_size", 740))
    show_coords = bool(render_config.get("show_coordinates", True))
    svg = chess.svg.board(board=board, size=board_size, coordinates=show_coords)
    png_bytes = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=board_size,
        output_height=board_size,
    )
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def _draw_text_center(draw: ImageDraw.ImageDraw, width: int, y: int, text: str, font: ImageFont.FreeTypeFont, color: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, y), text, fill=color, font=font)


def _compose_frame(
    base_size: tuple[int, int],
    board_img: Image.Image,
    header: str,
    caption: str,
    render_config: Dict[str, Any],
) -> Image.Image:
    width, height = base_size
    background_color = render_config.get("background_color", "#0b1622")
    text_color = render_config.get("text_color", "#e8e6e3")
    padding = int(render_config.get("padding", 32))
    font_size = int(render_config.get("font_size", 48))

    font = _load_font(font_size)
    small_font = _load_font(max(24, font_size // 2))

    frame = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(frame)

    _draw_text_center(draw, width, padding, header, font, text_color)

    board_x = (width - board_img.width) // 2
    board_y = (height - board_img.height) // 2
    frame.paste(board_img, (board_x, board_y), board_img)

    if caption:
        caption_y = board_y + board_img.height + padding
        if caption_y + font_size + padding > height:
            caption_y = height - (font_size + padding)
        _draw_text_center(draw, width, caption_y, caption, small_font, text_color)

    return frame


def _save_frame(frame: Image.Image, frames_dir: Path, index: int) -> int:
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frames_dir / f"frame_{index:05d}.png"
    frame.save(frame_path)
    return index + 1


def render_frames(
    puzzle: Puzzle,
    config: Dict[str, Any],
    frames_dir: Path,
) -> int:
    render_cfg = config.get("render", {})
    video_cfg = config.get("video", {})
    width = int(video_cfg.get("width", 1920))
    height = int(video_cfg.get("height", 1080))
    fps = int(video_cfg.get("fps", 30))

    try:
        board = chess.Board(puzzle.fen)
    except ValueError as exc:
        raise RenderError(f"Unable to create board from FEN: {exc}") from exc

    intro_seconds = float(render_cfg.get("intro_seconds", 2))
    think_seconds = float(render_cfg.get("think_seconds", 2))
    move_hold_seconds = float(render_cfg.get("move_hold_seconds", 1))
    outro_seconds = float(render_cfg.get("outro_seconds", 2))

    header = f"Lichess Daily Puzzle {puzzle.puzzle_id}"
    caption_intro = f"{puzzle.perf.title()} • Rating {puzzle.rating} • {puzzle.side_to_move.title()} to move"

    frame_index = 0

    board_img = _svg_board_image(board, render_cfg)
    intro_frame = _compose_frame((width, height), board_img, header, caption_intro, render_cfg)
    for _ in range(int(intro_seconds * fps)):
        frame_index = _save_frame(intro_frame, frames_dir, frame_index)

    think_frame = _compose_frame((width, height), board_img, header, "Find the best line", render_cfg)
    for _ in range(int(think_seconds * fps)):
        frame_index = _save_frame(think_frame, frames_dir, frame_index)

    for move_idx, move_uci in enumerate(puzzle.solution, start=1):
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError as exc:
            raise RenderError(f"Invalid move in solution: {move_uci}") from exc
        if move not in board.legal_moves:
            raise RenderError(f"Illegal move for current position: {move_uci}")
        san = board.san(move)
        board.push(move)
        board_img = _svg_board_image(board, render_cfg)
        caption = f"Move {move_idx}: {san}"
        move_frame = _compose_frame((width, height), board_img, header, caption, render_cfg)
        for _ in range(int(move_hold_seconds * fps)):
            frame_index = _save_frame(move_frame, frames_dir, frame_index)

    outro_frame = _compose_frame((width, height), board_img, header, "Puzzle solved", render_cfg)
    for _ in range(int(outro_seconds * fps)):
        frame_index = _save_frame(outro_frame, frames_dir, frame_index)

    return frame_index
