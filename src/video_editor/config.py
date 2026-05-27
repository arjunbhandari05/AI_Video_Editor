"""Application configuration via Pydantic settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from video_editor.types import ExportSettings

CutStrategy = Literal["beats", "bars", "onsets"]


class AppConfig(BaseSettings):
    """Environment- and file-backed defaults for the video editor."""

    clips_dir: Path = Path("./clips")
    music_path: Path = Path("./music/track.mp3")
    output_dir: Path = Path("./output")
    resolution: tuple[int, int] = (1080, 1920)
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"
    bitrate: str = "8000k"
    cut_strategy: CutStrategy = "bars"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="VE_")

    def export_settings(self, output_path: Path | None = None) -> ExportSettings:
        """Build export settings from this config."""
        path = output_path or (self.output_dir / "export.mp4")
        return ExportSettings(
            output_path=path,
            resolution=self.resolution,
            fps=self.fps,
            codec=self.codec,
            audio_codec=self.audio_codec,
            bitrate=self.bitrate,
        )


def parse_resolution(value: str) -> tuple[int, int]:
    """Parse a resolution string like ``1080x1920`` into width and height."""
    parts = value.lower().split("x")
    if len(parts) != 2:
        msg = f"Invalid resolution format: {value!r}. Use WIDTHxHEIGHT (e.g. 1080x1920)."
        raise ValueError(msg)
    return (int(parts[0]), int(parts[1]))
