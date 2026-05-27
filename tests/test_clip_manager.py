"""Tests for clip loading and trimming."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import BlackClipFactory
from video_editor.clip_manager import load_clips, trim_clip, validate_clips
from video_editor.types import ClipLoadError


def test_load_clips_count(
    tmp_path: Path,
    black_clip_factory: BlackClipFactory,
) -> None:
    """load_clips should find all MP4 files in a directory."""
    black_clip_factory("a.mp4", duration=1.0)
    black_clip_factory("b.mp4", duration=1.5)
    clips = load_clips(tmp_path)
    assert len(clips) == 2
    assert clips[0].path.name <= clips[1].path.name


def test_trim_clip_boundaries(
    black_clip_factory: BlackClipFactory, tmp_path: Path
) -> None:
    """trim_clip should clamp to segment duration."""
    path = black_clip_factory("one.mp4", duration=2.0)
    clips = load_clips(tmp_path)
    trimmed = trim_clip(clips[0], start=0.5, end=1.5)
    assert trimmed.start == 0.5
    assert trimmed.end == 1.5
    assert abs(trimmed.duration - 1.0) < 0.01
    assert trimmed.path == path


def test_load_clips_empty_dir(tmp_path: Path) -> None:
    """Empty directory should raise ClipLoadError."""
    with pytest.raises(ClipLoadError):
        load_clips(tmp_path)


def test_validate_clips_warnings(
    black_clip_factory: BlackClipFactory, tmp_path: Path
) -> None:
    """Very short clips should produce warnings."""
    black_clip_factory("short.mp4", duration=0.2)
    clips = load_clips(tmp_path)
    warnings = validate_clips(clips)
    assert any("short" in w.lower() or "0.2" in w for w in warnings)
