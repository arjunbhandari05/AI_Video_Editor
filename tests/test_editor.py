"""End-to-end editor smoke tests."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import BlackClipFactory
from video_editor.beat_detector import detect_beats
from video_editor.clip_manager import load_clips
from video_editor.editor import sync_clips_to_beats
from video_editor.types import ExportSettings


def test_sync_clips_to_beats_smoke(
    tmp_path: Path,
    black_clip_factory: BlackClipFactory,
    synthetic_click_track: Path,
) -> None:
    """Three clips plus click track should produce a non-empty export."""
    for name in ("c1.mp4", "c2.mp4", "c3.mp4"):
        black_clip_factory(name, duration=1.0)

    clips = load_clips(tmp_path)
    beat_map = detect_beats(synthetic_click_track)
    output = tmp_path / "out.mp4"
    settings = ExportSettings(
        output_path=output,
        resolution=(64, 64),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="500k",
    )

    result = sync_clips_to_beats(
        clips=clips,
        beat_map=beat_map,
        audio_path=synthetic_click_track,
        settings=settings,
        strategy="bars",
    )

    assert result == output
    assert output.is_file()
    assert output.stat().st_size > 0
