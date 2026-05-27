"""Runtime compatibility shims for third-party libraries."""


def ensure_pillow_moviepy_compat() -> None:
    """Restore ``Image.ANTIALIAS`` removed in Pillow 10+ (used by MoviePy 1.x)."""
    import PIL.Image

    if not hasattr(PIL.Image, "ANTIALIAS"):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS  # type: ignore[attr-defined]
