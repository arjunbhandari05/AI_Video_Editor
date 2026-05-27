"""Streamlit web UI — run with ``video-editor web`` or ``streamlit run``."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Final

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from video_editor.beat_detector import detect_beats
from video_editor.clip_manager import load_clips, validate_clips
from video_editor.compat import ensure_pillow_moviepy_compat
from video_editor.config import CutStrategy
from video_editor.editor import sync_clips_to_beats
from video_editor.types import (
    BeatDetectionError,
    BeatMap,
    ClipLoadError,
    ClipSegment,
    ExportError,
    ExportSettings,
)

ensure_pillow_moviepy_compat()

logger = logging.getLogger(__name__)

VIDEO_TYPES: Final = ["mp4", "mov", "avi", "mkv"]
AUDIO_TYPES: Final = ["mp3", "wav", "m4a", "flac", "ogg"]

CUSTOM_CSS = """
<style>
    .main-header { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
    .sub-header { color: #888; margin-bottom: 1.5rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #0f3460;
    }
</style>
"""


def _save_uploads(files: list[UploadedFile], directory: Path) -> list[Path]:
    """Write uploaded files to ``directory`` and return paths."""
    paths: list[Path] = []
    for uploaded in files:
        dest = directory / uploaded.name
        dest.write_bytes(uploaded.getvalue())
        paths.append(dest)
    return paths


def _render_beat_metrics(beat_map: BeatMap) -> None:
    """Show beat analysis as Streamlit metrics."""
    duration = (
        float(beat_map.beat_times[-1]) if len(beat_map.beat_times) > 0 else 0.0
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tempo", f"{beat_map.tempo:.1f} BPM")
    c2.metric("Beats", str(len(beat_map.beat_times)))
    c3.metric("Onsets", str(len(beat_map.onset_times)))
    c4.metric("Duration (approx)", f"{duration:.1f}s")


def _render_clip_table(clips: list[ClipSegment]) -> None:
    """Show loaded clips in a dataframe-style table."""
    st.dataframe(
        {
            "#": list(range(1, len(clips) + 1)),
            "File": [c.path.name for c in clips],
            "Duration (s)": [round(c.duration, 2) for c in clips],
        },
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    """Streamlit app entry."""
    st.set_page_config(
        page_title="AI Video Editor",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown('<p class="main-header">AI Video Editor</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Sync clips to music beats · Reels · TikTok · Shorts</p>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Export settings")
        width = st.number_input("Width", min_value=360, max_value=3840, value=1080)
        height = st.number_input("Height", min_value=360, max_value=3840, value=1920)
        strategy: CutStrategy = st.selectbox(
            "Cut strategy",
            options=["bars", "beats", "onsets"],
            index=0,
            help="bars = every 4th beat, beats = every beat, onsets = strongest onsets",
        )
        fps = st.number_input("FPS", min_value=15, max_value=60, value=30)
        bitrate = st.selectbox("Bitrate", ["5000k", "8000k", "12000k"], index=1)
        st.divider()
        st.caption("Requires FFmpeg on your PATH for export.")

    col_upload, col_preview = st.columns([1, 1], gap="large")

    with col_upload:
        st.subheader("1. Upload media")
        music_file = st.file_uploader(
            "Music track",
            type=AUDIO_TYPES,
            help="Audio used for beat detection and the final mix",
        )
        clip_files = st.file_uploader(
            "Video clips",
            type=VIDEO_TYPES,
            accept_multiple_files=True,
            help="One or more short clips to cut on the beat",
        )

    beat_map: BeatMap | None = st.session_state.get("beat_map")
    clips: list[ClipSegment] | None = st.session_state.get("clips")
    music_path: Path | None = st.session_state.get("music_path")
    work_dir: Path | None = st.session_state.get("work_dir")

    if music_file is not None and clip_files:
        if st.button("Analyze & preview", type="primary", use_container_width=True):
            if work_dir is not None and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
            work_dir = Path(tempfile.mkdtemp(prefix="ve_web_"))
            clips_dir = work_dir / "clips"
            clips_dir.mkdir()
            _save_uploads(list(clip_files), clips_dir)
            music_path = work_dir / f"music{Path(music_file.name).suffix}"
            music_path.write_bytes(music_file.getvalue())

            try:
                clips = load_clips(clips_dir)
                beat_map = detect_beats(music_path)
            except (ClipLoadError, BeatDetectionError) as exc:
                st.error(str(exc))
                clips = None
                beat_map = None
            else:
                st.session_state["work_dir"] = work_dir
                st.session_state["clips"] = clips
                st.session_state["beat_map"] = beat_map
                st.session_state["music_path"] = music_path
                st.success("Analysis complete.")

    with col_preview:
        st.subheader("2. Preview")
        if clips is None or beat_map is None:
            st.info("Upload music and clips, then click **Analyze & preview**.")
        else:
            _render_beat_metrics(beat_map)
            warnings = validate_clips(clips)
            if warnings:
                st.warning("\n".join(f"• {w}" for w in warnings))
            st.markdown("**Clips**")
            _render_clip_table(clips)

    st.divider()
    st.subheader("3. Export")

    if (
        clips is None
        or beat_map is None
        or music_path is None
        or work_dir is None
    ):
        st.caption("Complete analysis before exporting.")
        return

    if st.button("Export video", type="primary", use_container_width=True):
        output_path = work_dir / "export.mp4"
        settings = ExportSettings(
            output_path=output_path,
            resolution=(int(width), int(height)),
            fps=int(fps),
            codec="libx264",
            audio_codec="aac",
            bitrate=bitrate,
        )
        progress = st.progress(0.0, text="Exporting…")

        def on_progress(value: float) -> None:
            progress.progress(value, text=f"Exporting… {int(value * 100)}%")

        try:
            result = sync_clips_to_beats(
                clips=clips,
                beat_map=beat_map,
                audio_path=music_path,
                settings=settings,
                strategy=strategy,
                progress_callback=on_progress,
            )
        except ExportError as exc:
            st.error(str(exc))
            logger.exception("Export failed")
            return

        progress.progress(1.0, text="Done!")
        size_mb = result.stat().st_size / (1024 * 1024)
        st.success(f"Exported · {size_mb:.2f} MB")

        st.video(str(result))
        st.download_button(
            label="Download MP4",
            data=result.read_bytes(),
            file_name="export.mp4",
            mime="video/mp4",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
