"""Data layer: 2-pass streaming reader for raw files (format A/B) and metadata."""

from .meta import load_metadata
from .reader import DEFAULT_N_CHANNELS, inspect_raw, read_raw

__all__ = ["DEFAULT_N_CHANNELS", "inspect_raw", "load_metadata", "read_raw"]
