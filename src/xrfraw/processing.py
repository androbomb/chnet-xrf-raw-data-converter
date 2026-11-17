"""Post-read processing (M2): calibration attachment and explicit rebin.

Contract (output_schema.md; scientific_notes.md §9-11):
- `with_calibration` is a pure attachment: `energy[i] = m*i + q` (float64);
  counts stay element-identical (no resampling, no crop, no overwrite).
- `rebin` is explicit only (never automatic), on the channel axis, uniform
  groups (n_channels % size == 0 or explicit error). `sum` preserves totals
  (uint32 output); `mean` = group sum / width (float64 output, legacy
  semantics). Declared in metadata `transforms`.
Both return new Datasets; inputs are never mutated (img is shared, not copied).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .dataset import Dataset

_PROVENANCES = ("xml", "external", "user")


def with_calibration(ds: Dataset, m: float, q: float, *, provenance: str) -> Dataset:
    """Attach the energy axis ``energy[i] = m*i + q``; counts unchanged (bitwise).

    Replaces any unapplied ``known_calibration`` metadata block with
    ``calibration`` (applied). An explicit call always wins over values
    embedded in the file.
    """
    m, q = float(m), float(q)
    if not (np.isfinite(m) and np.isfinite(q)):
        raise ValueError(f"calibration m/q must be finite, got m={m!r}, q={q!r}")
    if m <= 0:
        raise ValueError(f"calibration slope m must be > 0 (keV/channel), got {m!r}")
    if provenance not in _PROVENANCES:
        raise ValueError(f"provenance must be one of {_PROVENANCES}, got {provenance!r}")
    nc = ds.img.shape[2]
    energy = np.arange(nc, dtype=np.float64) * m + q
    meta = dict(ds.metadata)
    meta.pop("known_calibration", None)
    meta["calibration"] = {"m": m, "q": q, "provenance": provenance}
    return replace(ds, energy=energy, calibration_m=m, calibration_q=q,
                   calibrated=True, metadata=meta)


def rebin(ds: Dataset, size: int, how: str = "sum") -> Dataset:
    """Rebin the channel axis into uniform groups of ``size`` (explicit only).

    ``sum`` preserves totals (uint32 output); ``mean`` = group sum / width
    (float64 output, legacy semantics). Requires ``n_channels % size == 0``
    (uniform groups, no silent truncation). Output channel axis = first
    index of each group; if calibrated, energy follows the same indices.
    ``n_events`` stays the physical event count. Declared in ``transforms``.
    """
    if not isinstance(size, int) or isinstance(size, bool) or size < 2:
        raise ValueError(f"rebin size must be an int >= 2, got {size!r}")
    if how not in ("sum", "mean"):
        raise ValueError(f"how must be 'sum' or 'mean', got {how!r}")
    nc = ds.img.shape[2]
    if nc % size:
        raise ValueError(
            f"rebin size {size} does not divide n_channels {nc} "
            "(uniform groups required)")
    n_out = nc // size
    starts = np.arange(n_out, dtype=np.intp) * size

    img = ds.img
    if img.dtype == np.uint16:
        acc = img.astype(np.uint32)
    else:
        acc = img  # uint32 or float64 (previous mean rebin)

    # np.add.reduceat accumulates uint32 in uint64 (numpy safe-accumulation):
    # group sums are exact, so the overflow check below is rigorous.
    s = np.add.reduceat(acc, starts, axis=2)
    if how == "mean":
        out = s.astype(np.float64) / float(size)
    elif s.dtype == np.float64:
        out = s
    else:
        if s.max() > np.iinfo(np.uint32).max:
            raise ValueError(
                f"rebin(sum): group sum {int(s.max())} overflows uint32 "
                "(max 4294967295); use how='mean' or a smaller size")
        out = s.astype(np.uint32)

    meta = dict(ds.metadata)
    meta["n_channels"] = n_out
    meta["dtype"] = str(out.dtype)
    meta["transforms"] = list(meta.get("transforms") or []) + [{
        "type": "rebin", "size": size, "how": how,
        "n_channels_from": nc, "n_channels_to": n_out,
    }]
    return replace(ds, img=out, channel=starts.astype(np.uint32),
                   energy=ds.energy[starts] if ds.energy is not None else None,
                   metadata=meta)