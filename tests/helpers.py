"""Shared test types."""

from collections.abc import Callable
from pathlib import Path

BlackClipFactory = Callable[[str, float], Path]
