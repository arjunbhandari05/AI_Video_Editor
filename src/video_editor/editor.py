"""Core video sync and export engine."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop  # pyright: ignore[reportAttributeAccessIssue]

from video_editor.beat_detector import select_cut_points
from video_editor.clip_manager import trim_clip
from video_editor.compat import ensure_pillow_moviepy_compat
from video_editor.types import BeatMap, ClipSegment, ExportError, ExportSettings

ensure_pillow_moviepy_compat()

logger = logging.getLogger(__name__)

CutStrategy = Literal["beats", "bars", "onsets"]

CROSSFADE_SEC = 0.05


def sync_clips_to_beats(
    clips: list[ClipSegment],
    beat_map: BeatMap,
    audio_path: Path,
    settings: ExportSettings,
    strategy: CutStrategy = "bars",
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    """Sync clips to beat cut points and export a single video.

    Args:
        clips: User video segments.
        beat_map: Detected beat/onset timing.
        audio_path: Music track to layer on the output.
        settings: Export resolution, codecs, and output path.
        strategy: How to pick cut points from the beat map.
        progress_callback: Optional callback receiving progress in [0, 1].

    Returns:
        Path to the written video file.

    Raises:
        ExportError: If export fails.
    """
    if len(clips) == 0:
        raise ExportError("No clips provided for export")

    def report(value: float) -> None:
        if progress_callback is not None:
            progress_callback(min(1.0, max(0.0, value)))

    report(0.05)
    n_segments = max(len(clips), 4)
    cut_points = select_cut_points(
        beat_map, n_segments, strategy=strategy, audio_path=audio_path
    )
    logger.info("Using %d cut points for %d segments", len(cut_points), n_segments)

    report(0.15)
    segments: list[VideoFileClip] = []
    opened: list[VideoFileClip] = []
    final: VideoFileClip | None = None
    music: AudioFileClip | None = None

    try:
        num_cuts = len(cut_points) - 1
        for i in range(num_cuts):
            t_start = cut_points[i]
            t_end = cut_points[i + 1]
            seg_duration = t_end - t_start
            if seg_duration <= 0:
                continue

            source = clips[i % len(clips)]
            trim_end = min(source.start + seg_duration, source.end)
            trimmed = trim_clip(source, source.start, trim_end)

            clip = VideoFileClip(str(trimmed.path)).subclip(
                trimmed.start, trimmed.end
            )
            opened.append(clip)

            target_w, target_h = settings.resolution
            clip = _fit_resolution(clip, target_w, target_h)
            if i > 0 and CROSSFADE_SEC > 0:
                clip = cast(VideoFileClip, clip.crossfadein(CROSSFADE_SEC))  # pyright: ignore[reportAttributeAccessIssue]
            segments.append(clip)
            report(0.15 + 0.5 * (i + 1) / max(num_cuts, 1))

        if not segments:
            raise ExportError("No video segments were built")

        report(0.7)
        final = cast(VideoFileClip, concatenate_videoclips(segments, method="compose"))

        report(0.8)
        music = AudioFileClip(str(audio_path))
        final_duration = float(final.duration or 0.0)
        music_duration = float(music.duration or 0.0)
        if final_duration > 0 and music_duration > 0:
            music = music.subclip(0, min(final_duration, music_duration))
        final = final.set_audio(music)

        if final is None:
            raise ExportError("No final video clip to export")

        report(0.85)
        settings.output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(settings.output_path),
            fps=settings.fps,
            codec=settings.codec,
            audio_codec=settings.audio_codec,
            bitrate=settings.bitrate,
            logger=None,
        )
        report(1.0)
        logger.info("Exported to %s", settings.output_path)
        return settings.output_path

    except ExportError:
        raise
    except Exception as exc:
        raise ExportError(f"Export failed: {exc}") from exc
    finally:
        for clip in opened:
            try:
                clip.close()
            except Exception:  # noqa: BLE001
                pass
        if final is not None:
            try:
                final.close()
            except Exception:  # noqa: BLE001
                pass
        if music is not None:
            try:
                music.close()
            except Exception:  # noqa: BLE001
                pass


def _fit_resolution(clip: VideoFileClip, width: int, height: int) -> VideoFileClip:
    """Crop and resize clip to target resolution (center crop, fill frame)."""
    size = clip.size
    w = int(size[0])
    h = int(size[1])
    if w == width and h == height:
        return clip

    target_aspect = width / height
    source_aspect = w / h

    if source_aspect > target_aspect:
        new_w = int(h * target_aspect)
        x1 = (w - new_w) // 2
        clip = cast(VideoFileClip, crop(clip, x1=x1, y1=0, x2=x1 + new_w, y2=h))
    elif source_aspect < target_aspect:
        new_h = int(w / target_aspect)
        y1 = (h - new_h) // 2
        clip = cast(VideoFileClip, crop(clip, x1=0, y1=y1, x2=w, y2=y1 + new_h))

    return cast(
        VideoFileClip,
        clip.resize(newsize=(width, height)),  # pyright: ignore[reportAttributeAccessIssue]
    )
