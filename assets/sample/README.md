# Sample assets

Place sample video clips (`.mp4`, `.mov`, `.avi`, `.mkv`) and music tracks here for local testing.

Example layout:

```
clips/
  clip1.mp4
  clip2.mp4
music/
  track.mp3
```

Then run:

```bash
video-editor run
```

or:

```bash
video-editor export --clips-dir ./clips --music ./music/track.mp3 --output ./output/reel.mp4
```
