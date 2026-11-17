"""Post-read processing (M2): calibration attachment and explicit rebin.

Contract (output_schema.md; scientific_notes.md §9-11):
- `with_calibration` is a pure attachment: `energy[i] = m*i + q` (float64);
  counts stay element-identical (no resampling, no crop, no overwrite).
- `rebin` is explicit only (never automatic), on the channel axis, uniform
  groups (n_channels % size == 0 or explicit error). `sum` preserves totals
  (uint32 output); `mean` = group sum / width (float64 output, legacy
  semantics). Declared in metadata `transforms`. If calibrated, m is
  multiplied by size (q unchanged) so the energy axis and metadata stay
  consistent.
- `rebin_to` maps (h, w, N) -> (h, w, n_new) with n_new in {512, 1024, 2048,
  4096, 8192}, sum-only (totals preserved).
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
    index of each group; if calibrated, energy follows the same indices and
    m/q are updated (m *= size, q unchanged). ``n_events`` stays the physical
    event count. Declared in ``transforms``.
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

    # Block sums over the uniform groups (starts = arange(n_out)*size).
    # reshape keeps a VIEW (no copy) and numpy accumulates uint32 -> uint64
    # (safe), so group sums are exact and the overflow check below is
    # rigorous. (np.add.reduceat on axis=2 would materialize a full uint64
    # copy of the cube, ~2x its size in RAM.)
    h, w, _ = acc.shape
    s = acc.reshape(h, w, n_out, size).sum(axis=-1)
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
    cal_m = cal_q = None
    if ds.calibration_m is not None:
        # The new channel i holds the group starting at i*size, so
        # energy[i] = m*(i*size) + q = (m*size)*i + q.
        cal = dict(meta["calibration"])
        cal["m"] = float(cal["m"]) * size
        meta["calibration"] = cal
        cal_m = ds.calibration_m * size
        cal_q = ds.calibration_q
    meta["transforms"] = list(meta.get("transforms") or []) + [{
        "type": "rebin", "size": size, "how": how,
        "n_channels_from": nc, "n_channels_to": n_out,
    }]
    return replace(ds, img=out, channel=starts.astype(np.uint32),
                   energy=ds.energy[starts] if ds.energy is not None else None,
                   calibration_m=cal_m, calibration_q=cal_q,
                   metadata=meta)


REBIN_TO_TARGETS = (512, 1024, 2048, 4096, 8192)


def rebin_to(ds: Dataset, n_new: int) -> Dataset:
    """Rebin the channel axis down to an exact target depth ``n_new``.

    Maps (h, w, n_channels) -> (h, w, n_new) with n_new in {512, 1024, 2048,
    4096, 8192} (powers of 2). Uses sum rebinning, so total counts are
    preserved. Requires ``n_new < n_channels`` and
    ``n_channels % n_new == 0``. If calibrated, m/q are updated (see rebin).
    """
    if not isinstance(n_new, int) or isinstance(n_new, bool):
        raise ValueError(f"rebin_to must be an int, got {n_new!r}")
    if n_new not in REBIN_TO_TARGETS:
        raise ValueError(f"rebin_to must be one of {REBIN_TO_TARGETS}, got {n_new!r}")
    nc = ds.img.shape[2]
    if n_new >= nc:
        raise ValueError(f"rebin_to {n_new} must be < current n_channels {nc}")
    if nc % n_new:
        raise ValueError(f"rebin_to {n_new} does not divide n_channels {nc} "
                         "(uniform groups required)")
    return rebin(ds, nc // n_new, how="sum")