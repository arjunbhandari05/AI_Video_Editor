"""Shared types and custom exceptions for the video editor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating]


class BeatDetectionError(Exception):
    """Raised when beat or onset detection fails."""


class ClipLoadError(Exception):
    """Raised when a video clip cannot be loaded or validated."""


class ExportError(Exception):
    """Raised when video export fails."""


@dataclass(frozen=True)
class BeatMap:
    """Beat and onset timing information derived from an audio track."""

    tempo: float
    beat_times: FloatArray
    onset_times: FloatArray


@dataclass(frozen=True)
class ClipSegment:
    """A video file segment with trim boundaries in seconds."""

    path: Path
    start: float
    end: float
    duration: float


@dataclass(frozen=True)
class ExportSettings:
    """Parameters used when writing the final video file."""

    output_path: Path
    resolution: tuple[int, int]
    fps: int
    codec: str
    audio_codec: str
    bitrate: str
