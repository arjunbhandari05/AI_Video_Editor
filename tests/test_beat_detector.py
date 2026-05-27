"""Tests for beat detection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from video_editor.beat_detector import detect_beats, select_cut_points


def test_detect_beats_tempo_and_count(synthetic_click_track: Path) -> None:
    """Synthetic 120 BPM click track should yield tempo near 120 and ~8 beats."""
    beat_map = detect_beats(synthetic_click_track)
    assert abs(beat_map.tempo - 120.0) <= 5.0
    # 4 seconds at 120 BPM => ~8 beat intervals
    assert 6 <= len(beat_map.beat_times) <= 12


def test_select_cut_points_bars() -> None:
    """Bar strategy should subsample every 4th beat."""
    beat_times = np.linspace(0, 4, 17)  # 16 beats over 4s
    from video_editor.types import BeatMap

    beat_map = BeatMap(tempo=120.0, beat_times=beat_times, onset_times=beat_times)
    cuts = select_cut_points(beat_map, n_clips=3, strategy="bars")
    assert cuts[0] == 0.0
    assert len(cuts) == 4


def test_detect_beats_missing_file() -> None:
    """Missing audio should raise BeatDetectionError."""
    from video_editor.types import BeatDetectionError

    with pytest.raises(BeatDetectionError):
        detect_beats(Path("/nonexistent/track.wav"))
