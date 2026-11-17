"""Dataset: in-memory result of read_raw (schema: output_schema.md)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

SCHEMA_VERSION = 1


@dataclass
class Dataset:
    """One converted raw scan.

    ``img`` has shape (NY, NX, NC) — order (y, x, channel). Counts are the raw
    event counts; calibration attaches ``energy`` and never modifies them.
    """

    img: np.ndarray  # (NY, NX, NC) counts, uint32/uint16
    channel: np.ndarray  # (NC,) uint32 ADC indices 0..NC-1
    x_axis: np.ndarray  # (NX,) float64
    y_axis: np.ndarray  # (NY,) float64
    mask: np.ndarray  # (NY, NX) bool — acquisition mask (False = not acquired)
    metadata: dict[str, Any]  # serializable metadata (output_schema.md)
    source_file: str  # basename of the input file
    n_events: int  # total event count (== int(img.sum()))
    energy: np.ndarray | None = None  # (NC,) float64, set by with_calibration
    calibration_m: float | None = None
    calibration_q: float | None = None
    calibrated: bool = False
