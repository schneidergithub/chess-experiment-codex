from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict


class VideoBuildError(Exception):
    """Raised when FFmpeg fails to produce the video."""


def build_video(frames_dir: Path, output_path: Path, video_config: Dict[str, object]) -> None:
    if not frames_dir.exists():
        raise VideoBuildError(f"Frames directory does not exist: {frames_dir}")
    if not list(frames_dir.glob("frame_*.png")):
        raise VideoBuildError("No frames found to build video.")

    frame_pattern = str(frames_dir / "frame_%05d.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(video_config.get("ffmpeg_path", "ffmpeg")),
        "-y",
        "-framerate",
        str(video_config.get("fps", 30)),
        "-i",
        frame_pattern,
        "-s",
        f"{video_config.get('width', 1920)}x{video_config.get('height', 1080)}",
        "-c:v",
        str(video_config.get("codec", "libx264")),
        "-pix_fmt",
        str(video_config.get("pixel_format", "yuv420p")),
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise VideoBuildError(
            f"FFmpeg failed with code {exc.returncode}: {exc.stderr.decode() if exc.stderr else exc}"
        ) from exc
