"""Beat and onset detection using librosa."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import librosa
import numpy as np

from video_editor.types import BeatDetectionError, BeatMap

logger = logging.getLogger(__name__)

CutStrategy = Literal["beats", "bars", "onsets"]


def detect_beats(audio_path: Path) -> BeatMap:
    """Load audio and detect tempo, beat times, and onset times.

    Args:
        audio_path: Path to an audio file (mp3, wav, etc.).

    Returns:
        A :class:`BeatMap` with tempo in BPM and times in seconds.

    Raises:
        BeatDetectionError: If the file cannot be read or analyzed.
    """
    if not audio_path.is_file():
        raise BeatDetectionError(f"Audio file not found: {audio_path}")

    try:
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    except Exception as exc:  # noqa: BLE001 — wrap librosa failures
        raise BeatDetectionError(f"Failed to analyze audio: {audio_path}") from exc

    bpm = float(np.atleast_1d(tempo)[0])
    beat_times, bpm = _ensure_beat_grid(beat_times, onset_times, bpm, float(len(y) / sr))
    logger.info(
        "Detected %.1f BPM, %d beats, %d onsets",
        bpm,
        len(beat_times),
        len(onset_times),
    )
    return BeatMap(tempo=bpm, beat_times=beat_times, onset_times=onset_times)


def _estimate_bpm_from_onsets(onset_times: np.ndarray) -> float:
    """Estimate tempo from median interval between onsets."""
    if len(onset_times) < 2:
        return 120.0
    intervals = np.diff(onset_times)
    positive = intervals[intervals > 0]
    if len(positive) == 0:
        return 120.0
    return float(60.0 / np.median(positive))


def _ensure_beat_grid(
    beat_times: np.ndarray,
    onset_times: np.ndarray,
    bpm: float,
    duration: float,
) -> tuple[np.ndarray, float]:
    """Fill missing beats and tempo when librosa returns sparse results."""
    if bpm <= 0 or len(beat_times) == 0:
        if len(onset_times) >= 2:
            bpm = _estimate_bpm_from_onsets(onset_times)
            beat_times = onset_times
        else:
            bpm = 120.0
            interval = 60.0 / bpm
            beat_times = np.arange(0.0, max(duration, interval), interval)

    if len(beat_times) == 0:
        interval = 60.0 / bpm
        beat_times = np.arange(0.0, max(duration, interval), interval)

    return beat_times, bpm


def select_cut_points(
    beat_map: BeatMap,
    n_clips: int,
    strategy: CutStrategy = "bars",
    audio_path: Path | None = None,
) -> list[float]:
    """Select timestamps for clip boundaries based on the beat map.

    Args:
        beat_map: Detected beats and onsets.
        n_clips: Number of clip segments to produce (needs n_clips + 1 boundaries
            for durations between cuts; we return segment start times).
        strategy: ``beats`` (every beat), ``bars`` (every 4th beat), or
            ``onsets`` (strongest onsets).

    Returns:
        Sorted list of cut times in seconds, length ``n_clips + 1`` (includes 0
        and end boundary when possible).
    """
    if n_clips < 1:
        return [0.0]

    if strategy == "beats":
        candidates = list(beat_map.beat_times)
    elif strategy == "bars":
        candidates = list(beat_map.beat_times[::4])
    else:
        if audio_path is not None:
            return select_cut_points_with_strength(audio_path, beat_map, n_clips)
        candidates = _top_onset_times(beat_map, n_clips + 1)

    if len(candidates) == 0:
        candidates = [0.0]

    candidates = sorted(set(float(t) for t in candidates if t >= 0.0))
    if candidates[0] != 0.0:
        candidates.insert(0, 0.0)

    # Need n_clips segments => n_clips + 1 boundaries
    needed = n_clips + 1
    if len(candidates) >= needed:
        return candidates[:needed]

    # Pad by interpolating between last beat and estimated track end
    last = candidates[-1]
    step = 60.0 / beat_map.tempo if beat_map.tempo > 0 else 0.5
    while len(candidates) < needed:
        last += step
        candidates.append(last)

    return candidates[:needed]


def _top_onset_times(beat_map: BeatMap, count: int) -> list[float]:
    """Return up to ``count`` onset times (sorted)."""
    times = beat_map.onset_times
    if len(times) == 0:
        return list(beat_map.beat_times[:count])
    if len(times) <= count:
        return sorted(float(t) for t in times)
    # Without stored strengths, take evenly spaced onsets
    indices = np.linspace(0, len(times) - 1, count, dtype=int)
    return sorted(float(times[i]) for i in indices)


def select_cut_points_with_strength(
    audio_path: Path,
    beat_map: BeatMap,
    n_clips: int,
) -> list[float]:
    """Select cut points from onsets ranked by onset strength."""
    if n_clips < 1:
        return [0.0]

    try:
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        strength = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=strength, sr=sr, units="frames"
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        frame_strengths = strength[onset_frames]
        order = np.argsort(frame_strengths)[::-1]
        top = sorted(float(onset_times[i]) for i in order[: n_clips + 1])
    except Exception:
        top = sorted(float(t) for t in beat_map.onset_times[: n_clips + 1])

    if len(top) == 0:
        return select_cut_points(beat_map, n_clips, strategy="beats")

    if top[0] != 0.0:
        top.insert(0, 0.0)
    return top[: n_clips + 1]
