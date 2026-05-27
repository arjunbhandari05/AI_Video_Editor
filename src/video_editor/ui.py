"""Rich terminal UI helpers."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from video_editor.config import AppConfig, CutStrategy
from video_editor.types import BeatMap, ClipSegment

console = Console()

BANNER = r"""
    _    ___   __     ___     _ _         _       _           
   / \  |_ _|  \ \   / (_) __| (_) __ _  | | ___ | |__   ___  
  / _ \  | |    \ \ / /| |/ _` | |/ _` | | |/ _ \| '_ \ / _ \ 
 / ___ \ | |     \ V / | | (_| | | (_| | | | (_) | |_) |  __/ 
/_/   \_\___|     \_/  |_|\__,_|_|\__,_| |_|\___/|_.__/ \___| 
"""


def display_welcome() -> None:
    """Print ASCII banner and project description."""
    console.print(Text(BANNER, style="bold cyan"))
    console.print(
        Panel(
            "[bold]AI Video Editor[/bold]\n\n"
            "Sync your clips to music beats and export vertical short-form "
            "content for Reels, TikTok, and YouTube Shorts.",
            title="Welcome",
            border_style="green",
        )
    )


def prompt_clips_dir(default: Path | None = None) -> Path:
    """Prompt for the folder containing video clips."""
    default_str = str(default or Path("./clips"))
    raw = Prompt.ask(
        "Clips folder path",
        default=default_str,
        console=console,
    )
    return Path(raw).expanduser().resolve()


def prompt_music_file(default: Path | None = None) -> Path:
    """Prompt for the music/audio file path."""
    default_str = str(default or Path("./music/track.mp3"))
    raw = Prompt.ask(
        "Music file path",
        default=default_str,
        console=console,
    )
    return Path(raw).expanduser().resolve()


def prompt_settings(config: AppConfig) -> AppConfig:
    """Interactively edit export and cut settings."""
    res = Prompt.ask(
        "Resolution (WxH)",
        default=f"{config.resolution[0]}x{config.resolution[1]}",
        console=console,
    )
    w, h = (int(x) for x in res.lower().split("x"))
    strategy = Prompt.ask(
        "Cut strategy",
        choices=["beats", "bars", "onsets"],
        default=config.cut_strategy,
        console=console,
    )
    fps_str = Prompt.ask("FPS", default=str(config.fps), console=console)
    out_dir = Prompt.ask(
        "Output directory",
        default=str(config.output_dir),
        console=console,
    )
    cut = cast(CutStrategy, strategy)
    return config.model_copy(
        update={
            "resolution": (w, h),
            "cut_strategy": cut,
            "fps": int(fps_str),
            "output_dir": Path(out_dir).expanduser().resolve(),
        }
    )


def show_beat_analysis(beat_map: BeatMap) -> None:
    """Display tempo, beat count, and estimated duration."""
    duration = (
        float(beat_map.beat_times[-1])
        if len(beat_map.beat_times) > 0
        else 0.0
    )
    table = Table(title="Beat Analysis", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Tempo (BPM)", f"{beat_map.tempo:.1f}")
    table.add_row("Total beats", str(len(beat_map.beat_times)))
    table.add_row("Total onsets", str(len(beat_map.onset_times)))
    table.add_row("Track duration (approx)", f"{duration:.2f}s")
    console.print(table)


def show_clip_list(clips: list[ClipSegment]) -> None:
    """Display a table of loaded clips."""
    table = Table(title="Loaded Clips", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("File")
    table.add_column("Duration (s)", justify="right")
    for i, clip in enumerate(clips, start=1):
        table.add_row(str(i), clip.path.name, f"{clip.duration:.2f}")
    console.print(table)


def show_warnings(warnings: list[str]) -> None:
    """Print validation warnings."""
    if not warnings:
        return
    console.print(Panel("\n".join(f"• {w}" for w in warnings), title="Warnings", style="yellow"))


def export_progress_bar() -> Progress:
    """Return a Rich progress bar configured for export."""
    return Progress(console=console)


def show_export_complete(output_path: Path) -> None:
    """Show success panel with path and file size."""
    size_mb = output_path.stat().st_size / (1024 * 1024)
    console.print(
        Panel(
            f"[bold green]Export complete![/bold green]\n\n"
            f"Path: [cyan]{output_path}[/cyan]\n"
            f"Size: {size_mb:.2f} MB",
            title="Success",
            border_style="green",
        )
    )


def confirm_export() -> bool:
    """Ask user to confirm before exporting."""
    return Confirm.ask("Start export?", default=True, console=console)
