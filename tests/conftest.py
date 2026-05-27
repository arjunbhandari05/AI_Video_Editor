"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from moviepy.editor import ColorClip

from tests.helpers import BlackClipFactory
from video_editor.compat import ensure_pillow_moviepy_compat

ensure_pillow_moviepy_compat()


@pytest.fixture
def synthetic_click_track(tmp_path: Path) -> Path:
    """Generate a 120 BPM click track (sine bursts on each beat)."""
    sr = 22050
    bpm = 120.0
    beat_interval = 60.0 / bpm
    duration = 4.0
    n_samples = int(sr * duration)
    y = np.zeros(n_samples, dtype=np.float32)
    beat_times = np.arange(0, duration, beat_interval)
    click_len = int(0.02 * sr)
    t_click = np.linspace(0, 1, click_len, endpoint=False)
    click = np.sin(2 * np.pi * 1000 * t_click).astype(np.float32) * np.hanning(
        click_len
    ).astype(np.float32)

    for bt in beat_times:
        start = int(bt * sr)
        end = min(start + click_len, n_samples)
        length = end - start
        if length > 0:
            y[start:end] = click[:length]

    path = tmp_path / "click_120bpm.wav"
    sf.write(str(path), y, sr)
    return path


@pytest.fixture
def black_clip_factory(tmp_path: Path) -> BlackClipFactory:
    """Factory that creates short black MP4 clips."""

    def _make(name: str, duration: float = 1.0) -> Path:
        path = tmp_path / name
        clip = ColorClip(size=(64, 64), color=(0, 0, 0), duration=duration)
        clip.write_videofile(
            str(path),
            fps=24,
            codec="libx264",
            audio=False,
            logger=None,
        )
        clip.close()
        return path

    return _make
