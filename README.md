# AI Video Editor

Python tool that automatically builds short-form social videos (Reels, TikTok, YouTube Shorts) by syncing user-uploaded clips to music using beat detection. Features a Rich terminal UI, strict typing for Pylance/pyright, and a Typer CLI.

## Features

- **Beat-aware cuts** — librosa tempo, beat, and onset detection
- **Clip pipeline** — load, validate, trim, and cycle clips across segments
- **Vertical export** — crop/resize to 1080×1920 (configurable)
- **Interactive or headless** — `run` wizard, `export` with flags, or **web UI**
- **Web UI** — Streamlit app at `http://localhost:8501`
- **Typed codebase** — Pydantic settings, dataclasses, strict pyright

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) (required by MoviePy for encode/decode)

## Setup

```bash
cd "AI Video Editor"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

### Web UI (localhost)

```bash
video-editor web
```

Opens **http://localhost:8501** in your browser. Upload a music track and video clips, click **Analyze & preview**, then **Export video** and download the MP4.

Custom port or host:

```bash
video-editor web --port 8502
video-editor web --host 0.0.0.0   # accessible on your LAN
```

Alternatively:

```bash
streamlit run src/video_editor/web/app.py
```

### Interactive terminal

```bash
video-editor run
```

### Headless export

```bash
video-editor export \
  --clips-dir ./clips \
  --music ./music/track.mp3 \
  --output ./output/reel.mp4 \
  --strategy bars \
  --resolution 1080x1920 \
  --fps 30
```

### Analyze music

```bash
video-editor analyze ./music/track.mp3
```

### Validate clips

```bash
video-editor validate ./clips
```

### Help

```bash
video-editor --help
video-editor export --help
```

## Environment variables

Prefix: `VE_` (see `.env` support in `AppConfig`)

| Variable | Default |
|----------|---------|
| `VE_CLIPS_DIR` | `./clips` |
| `VE_MUSIC_PATH` | `./music/track.mp3` |
| `VE_OUTPUT_DIR` | `./output` |
| `VE_CUT_STRATEGY` | `bars` |

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│  main.py    │────▶│  beat_detector │────▶│   BeatMap    │
│  (Typer)    │     │  (librosa)     │     └──────────────┘
└──────┬──────┘     └────────────────┘            │
       │                                           ▼
       │              ┌────────────────┐     ┌──────────────┐
       ├─────────────▶│  clip_manager  │────▶│ ClipSegment  │
       │              │  (moviepy)     │     └──────────────┘
       │              └────────────────┘            │
       ▼                                           ▼
┌─────────────┐                            ┌──────────────┐
│    ui.py    │                            │   editor.py  │
│   (rich)    │                            │ sync + export│
└─────────────┘                            └──────┬───────┘
                                                  │
                                                  ▼
                                           output/*.mp4
```

**Flow:** load clips → detect beats in music → select cut points (`beats` / `bars` / `onsets`) → trim and concatenate segments → layer audio → export.

## Development

```bash
# Type check
pyright src tests

# Tests
pytest -v

# Format
black src tests
```

## Project layout

```
src/video_editor/   # Application package
tests/              # pytest suite
assets/sample/      # Placeholder for sample media
```

## License

MIT
