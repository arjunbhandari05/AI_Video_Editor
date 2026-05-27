"""Load, trim, and validate user video clips."""

from __future__ import annotations

import logging
from pathlib import Path

from moviepy.editor import VideoFileClip

from video_editor.types import ClipLoadError, ClipSegment

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv"})


def load_clips(clip_dir: Path) -> list[ClipSegment]:
    """Scan a directory for video files and return validated clip segments.

    Args:
        clip_dir: Directory containing user-uploaded clips.

    Returns:
        Sorted list of :class:`ClipSegment` with full-file duration.

    Raises:
        ClipLoadError: If the directory is missing or no valid clips are found.
    """
    if not clip_dir.is_dir():
        raise ClipLoadError(f"Clips directory not found: {clip_dir}")

    paths = sorted(
        p
        for p in clip_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not paths:
        raise ClipLoadError(f"No video clips found in {clip_dir}")

    clips: list[ClipSegment] = []
    for path in paths:
        try:
            segment = _load_single_clip(path)
            clips.append(segment)
        except Exception as exc:
            logger.warning("Skipping unreadable clip %s: %s", path, exc)

    if not clips:
        raise ClipLoadError(f"No readable video clips in {clip_dir}")

    return clips


def _load_single_clip(path: Path) -> ClipSegment:
    """Load one clip and return a segment spanning the full file."""
    with VideoFileClip(str(path)) as clip:
        raw_duration = clip.duration
        duration = float(raw_duration) if raw_duration is not None else 0.0
    if duration <= 0:
        raise ClipLoadError(f"Clip has zero duration: {path}")
    return ClipSegment(path=path, start=0.0, end=duration, duration=duration)


def trim_clip(clip: ClipSegment, start: float, end: float) -> ClipSegment:
    """Return a new segment with updated trim boundaries.

    Args:
        clip: Source segment.
        start: Start time in seconds (relative to file).
        end: End time in seconds (must be > start and <= file duration).

    Returns:
        A new :class:`ClipSegment` with updated bounds.
    """
    start_clamped = max(0.0, min(start, clip.duration))
    end_clamped = max(start_clamped, min(end, clip.duration))
    duration = end_clamped - start_clamped
    return ClipSegment(
        path=clip.path,
        start=start_clamped,
        end=end_clamped,
        duration=duration,
    )


def validate_clips(clips: list[ClipSegment]) -> list[str]:
    """Check clips for common issues and return warning messages.

    Args:
        clips: Loaded clip segments.

    Returns:
        Human-readable warning strings (empty if all checks pass).
    """
    warnings: list[str] = []
    if len(clips) == 0:
        warnings.append("No clips loaded.")
        return warnings

    durations = [c.duration for c in clips]
    min_dur = min(durations)
    max_dur = max(durations)
    if max_dur - min_dur > 5.0:
        warnings.append(
            f"Clip durations vary widely ({min_dur:.1f}s – {max_dur:.1f}s)."
        )

    for clip in clips:
        if clip.duration < 0.5:
            warnings.append(f"Very short clip ({clip.duration:.2f}s): {clip.path.name}")
        if clip.duration > 120.0:
            warnings.append(f"Very long clip ({clip.duration:.1f}s): {clip.path.name}")

    return warnings
