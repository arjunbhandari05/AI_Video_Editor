"""AI video editor: sync short-form clips to music beats."""

from video_editor.beat_detector import detect_beats, select_cut_points
from video_editor.clip_manager import load_clips, trim_clip, validate_clips
from video_editor.config import AppConfig
from video_editor.editor import sync_clips_to_beats
from video_editor.types import (
    BeatDetectionError,
    BeatMap,
    ClipLoadError,
    ClipSegment,
    ExportError,
    ExportSettings,
)

__all__ = [
    "AppConfig",
    "BeatDetectionError",
    "BeatMap",
    "ClipLoadError",
    "ClipSegment",
    "ExportError",
    "ExportSettings",
    "detect_beats",
    "load_clips",
    "select_cut_points",
    "sync_clips_to_beats",
    "trim_clip",
    "validate_clips",
]
