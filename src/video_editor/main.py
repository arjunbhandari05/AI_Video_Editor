"""Typer CLI entry point for the AI video editor."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
import video_editor.web.app as web_app_module

from video_editor.beat_detector import detect_beats
from video_editor.clip_manager import load_clips, validate_clips
from video_editor.config import AppConfig, CutStrategy, parse_resolution
from video_editor.editor import sync_clips_to_beats
from video_editor.types import BeatDetectionError, ClipLoadError, ExportError
from video_editor.ui import (
    confirm_export,
    display_welcome,
    export_progress_bar,
    prompt_clips_dir,
    prompt_music_file,
    prompt_settings,
    show_beat_analysis,
    show_clip_list,
    show_export_complete,
    show_warnings,
)

app = typer.Typer(
    name="video-editor",
    help="Sync video clips to music beats for short-form social content.",
    no_args_is_help=True,
)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.callback()
def main_callback(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging"),
    ] = False,
) -> None:
    """Global options."""
    _configure_logging(verbose)


@app.command()
def run(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Full interactive flow: load clips, analyze music, export."""
    _configure_logging(verbose)
    display_welcome()
    config = AppConfig()

    clips_dir = prompt_clips_dir(config.clips_dir)
    try:
        clips = load_clips(clips_dir)
    except ClipLoadError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    show_clip_list(clips)
    show_warnings(validate_clips(clips))

    music_path = prompt_music_file(config.music_path)
    try:
        beat_map = detect_beats(music_path)
    except BeatDetectionError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    show_beat_analysis(beat_map)
    config = prompt_settings(config)

    if not confirm_export():
        typer.echo("Export cancelled.")
        raise typer.Exit()

    output_path = config.output_dir / "export.mp4"
    settings = config.export_settings(output_path)

    with export_progress_bar() as progress:
        task = progress.add_task("Exporting video...", total=100)

        def on_progress(value: float) -> None:
            progress.update(task, completed=int(value * 100))

        try:
            result = sync_clips_to_beats(
                clips=clips,
                beat_map=beat_map,
                audio_path=music_path,
                settings=settings,
                strategy=config.cut_strategy,
                progress_callback=on_progress,
            )
        except ExportError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

    show_export_complete(result)


@app.command()
def export(
    clips_dir: Annotated[Path, typer.Option("--clips-dir", help="Folder of clips")],
    music: Annotated[Path, typer.Option("--music", help="Music/audio file")],
    output: Annotated[
        Path,
        typer.Option("--output", help="Output video path"),
    ] = Path("./output/export.mp4"),
    strategy: Annotated[
        CutStrategy,
        typer.Option("--strategy", help="Cut point strategy"),
    ] = "bars",
    resolution: Annotated[
        str,
        typer.Option("--resolution", help="e.g. 1080x1920"),
    ] = "1080x1920",
    fps: Annotated[int, typer.Option("--fps")] = 30,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Non-interactive export with CLI flags."""
    _configure_logging(verbose)
    try:
        clips = load_clips(clips_dir)
        beat_map = detect_beats(music)
    except (ClipLoadError, BeatDetectionError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    w, h = parse_resolution(resolution)
    settings = AppConfig(
        resolution=(w, h),
        fps=fps,
        cut_strategy=strategy,
    ).export_settings(output.resolve())

    try:
        result = sync_clips_to_beats(
            clips=clips,
            beat_map=beat_map,
            audio_path=music,
            settings=settings,
            strategy=strategy,
        )
    except ExportError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Exported: {result}")


@app.command()
def analyze(
    music: Annotated[Path, typer.Argument(help="Music file to analyze")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Analyze a music file and print beat map statistics."""
    _configure_logging(verbose)
    try:
        beat_map = detect_beats(music)
    except BeatDetectionError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    show_beat_analysis(beat_map)


@app.command()
def validate(
    clips_dir: Annotated[Path, typer.Argument(help="Directory of video clips")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Validate all clips in a directory."""
    _configure_logging(verbose)
    try:
        clips = load_clips(clips_dir)
    except ClipLoadError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    show_clip_list(clips)
    warnings = validate_clips(clips)
    if warnings:
        show_warnings(warnings)
        raise typer.Exit(code=1)
    typer.secho("All clips passed validation.", fg=typer.colors.GREEN)


@app.command()
def web(
    port: Annotated[int, typer.Option("--port", "-p", help="Server port")] = 8501,
    host: Annotated[
        str,
        typer.Option("--host", help="Bind address (use 0.0.0.0 for LAN)"),
    ] = "localhost",
) -> None:
    """Launch the Streamlit web UI in your browser."""
    app_path = Path(web_app_module.__file__).resolve()
    typer.echo(f"Starting web UI at http://{host}:{port}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(port),
            "--server.address",
            host,
            "--browser.gatherUsageStats",
            "false",
        ],
        check=True,
    )


if __name__ == "__main__":
    app()
