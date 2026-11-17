"""2-pass streaming reader for MA-XRF raw files (format A: XML+data, B: data-only).

Stream grammar, anomaly behavior and grid rules: docs/data_format.md.

Pass 1 (scan): read-only — format, XML header, event count, max channel,
observed grid, anomalies. No cube allocation.
Pass 2 (populate): builds img (NY, NX, NC) and the acquisition mask.
"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path

import numpy as np
from tqdm import tqdm

from .. import __version__
from ..dataset import SCHEMA_VERSION, Dataset
from ..errors import XRFReadError
from .meta import load_metadata, merge_metadata, parse_xml_header

X_HEADER_OFFSET = 50_000_000
Y_HEADER_OFFSET = 60_000_000
DEFAULT_N_CHANNELS = 16384  # instrument MCA depth (user-confirmed default, N1)
# Units are not declared in the file: assumed defaults (N4), marked in metadata.
DEFAULT_UNITS = {"x": "µm", "y": "µm", "velocity": "µm/s"}
_TOLERATED_TAIL = {"</analysisData>", "</XRFanalysis>"}
_ALLOWED_DTYPES = (np.dtype("uint32"), np.dtype("uint16"))


def _is_x_header(s: str) -> bool:
    return len(s) == 8 and s[0] == "5" and s.isdigit()


def _is_y_header(s: str) -> bool:
    return len(s) == 8 and s[0] == "6" and s.isdigit()


def _next_pow2(m: int) -> int:
    """Smallest power of 2 >= m (m >= 1). Detector MCA depth is a power of 2."""
    return 1 << (m - 1).bit_length()


def _open(path, verbose: bool, desc: str):
    f = open(path, "r", encoding="utf-8")
    if not verbose:
        return f
    return tqdm(f, unit="ln", mininterval=1.0, desc=desc)


def _scan(path, *, n_channels: int, verbose: bool = False) -> dict:
    """Pass 1 (read-only, no cube allocation). See module docstring."""
    path = os.fspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"raw file not found: {path}")

    fmt: str | None = None
    header_lines: list[str] = []
    data_started = False
    n_events = 0
    n_events_over = 0
    max_channel = -1
    col_y: dict[int, set[int]] = {}
    anomalies: list[dict] = []
    last_header = None
    x_cur: int | None = None
    y_cur: int | None = None
    line_no = 0

    f = _open(path, verbose, "scan    ")
    try:
        for line in f:
            line_no += 1
            s = line.strip()
            if not data_started:
                if s == "":
                    continue
                if fmt is None:
                    fmt = "xml" if s.startswith("<?xml") else "data-only"
                if s.startswith("<"):
                    if fmt != "xml":
                        raise XRFReadError(line_no, f"unexpected XML line in data-only file: {s!r}")
                    header_lines.append(s)
                    continue
                data_started = True

            if s == "" or s in _TOLERATED_TAIL:
                continue
            if not s.isdigit():
                raise XRFReadError(line_no, f"malformed line (expected integer or XML tag): {s!r}")

            if _is_x_header(s):
                x = int(s) - X_HEADER_OFFSET
                if last_header == "X":
                    anomalies.append(
                        {"type": "dangling_x_marker", "line": line_no, "x": x, "y_prev": y_cur}
                    )
                last_header = "X"
                x_cur = x
                col_y.setdefault(x, set())
                continue
            if _is_y_header(s):
                y = int(s) - Y_HEADER_OFFSET
                if x_cur is None:
                    anomalies.append({"type": "y_header_before_x", "line": line_no, "y": y})
                else:
                    col_y[x_cur].add(y)
                last_header = "Y"
                y_cur = y
                continue

            c = int(s)
            if x_cur is None or y_cur is None:
                raise XRFReadError(line_no, "event before any X/Y header")
            n_events += 1
            if c > max_channel:
                max_channel = c
            if c >= n_channels:
                n_events_over += 1
            last_header = "E"
    finally:
        f.close()

    if fmt is None:
        raise XRFReadError(None, "empty file (no data lines)")
    if last_header == "X":
        anomalies.append(
            {"type": "dangling_x_marker", "line": line_no, "x": x_cur, "y_prev": y_cur, "at": "eof"}
        )

    header = parse_xml_header(header_lines) if fmt == "xml" else {"raw": {}}
    if fmt == "xml" and not any(l.strip() == "<analysisData>" for l in header_lines):
        raise XRFReadError(None, "format A header without <analysisData> section")

    return {
        "path": path,
        "fmt": fmt,
        "header": header,
        "n_lines": line_no,
        "n_events": n_events,
        "n_events_over": n_events_over,
        "max_channel": max_channel,
        "col_y": col_y,
        "anomalies": anomalies,
    }


def _resolve_grid(scan: dict, meta: dict) -> tuple[dict, str, list[dict]]:
    """Resolve the grid: declared (XML/external) or inferred (format B).

    Raises XRFReadError for out-of-range headers or ambiguous grids.
    Returns (grid, grid_source, grid_anomalies).
    """
    col_y = scan["col_y"]
    observed_x = sorted(col_y.keys())
    all_y: set[int] = set()
    for yset in col_y.values():
        all_y |= yset
    anomalies: list[dict] = []
    declared = meta.get("grid")

    if declared:
        x_min, x_max, x_step = declared["x_min"], declared["x_max"], declared["x_step"]
        y_min, y_max, y_step = declared["y_min"], declared["y_max"], declared["y_step"]
        if x_step <= 0 or y_step <= 0:
            raise XRFReadError(None, f"invalid grid steps: x_step={x_step}, y_step={y_step}")
        if (x_max - x_min) % x_step != 0 or (y_max - y_min) % y_step != 0:
            raise XRFReadError(None, "grid max not on grid step (max-min not divisible by step)")
        nx = (x_max - x_min) // x_step + 1
        ny = (y_max - y_min) // y_step + 1
        for x in observed_x:
            if not (x_min <= x <= x_max and (x - x_min) % x_step == 0):
                raise XRFReadError(
                    None, f"observed X header {x} outside declared grid [{x_min}..{x_max} step {x_step}]"
                )
        for y in all_y:
            if not (y_min <= y <= y_max and (y - y_min) % y_step == 0):
                raise XRFReadError(
                    None, f"observed Y header {y} outside declared grid [{y_min}..{y_max} step {y_step}]"
                )
        for k in range(nx):
            xv = x_min + k * x_step
            if xv not in col_y:
                anomalies.append({"type": "missing_column", "x": xv, "n_pixels": ny})
        for x, yset in col_y.items():
            for k in range(ny):
                yv = y_min + k * y_step
                if yv not in yset:
                    anomalies.append({"type": "missing_row", "x": x, "y": yv})
        return (
            {"x_min": x_min, "x_max": x_max, "x_step": x_step,
             "y_min": y_min, "y_max": y_max, "y_step": y_step},
            "declared",
            anomalies,
        )

    # Inferred (format B, no declared grid): unambiguous only with uniform step.
    def _infer(vals, axis: str) -> tuple[int, int, list[int]]:
        vs = sorted(vals)
        if not vs:
            raise XRFReadError(None, f"no {axis} headers observed - cannot infer grid")
        if len(vs) == 1:
            return vs[0], 1, vs
        step = vs[1] - vs[0]
        if step <= 0 or any(b - a != step for a, b in zip(vs, vs[1:])):
            raise XRFReadError(
                None, f"non-uniform {axis} step in observed headers - grid ambiguous; "
                      f"supply external metadata with a 'grid'"
            )
        return vs[0], step, vs

    x_min, x_step, vs_x = _infer(observed_x, "X")
    y_min, y_step, vs_y = _infer(all_y, "Y")
    nx, ny = len(vs_x), len(vs_y)
    for x, yset in col_y.items():
        for k in range(ny):
            yv = y_min + k * y_step
            if yv not in yset:
                anomalies.append({"type": "missing_row", "x": x, "y": yv})
    return (
        {"x_min": x_min, "x_max": x_min + (nx - 1) * x_step, "x_step": x_step,
         "y_min": y_min, "y_max": y_min + (ny - 1) * y_step, "y_step": y_step},
        "inferred",
        anomalies,
    )


def _populate(path, *, grid: dict, n_channels: int, dtype: np.dtype, verbose: bool = False):
    """Pass 2: build img (NY, NX, NC) and the acquisition mask."""
    x_min, x_max, x_step = grid["x_min"], grid["x_max"], grid["x_step"]
    y_min, y_max, y_step = grid["y_min"], grid["y_max"], grid["y_step"]
    nx = (x_max - x_min) // x_step + 1
    ny = (y_max - y_min) // y_step + 1
    if dtype == np.dtype("uint16"):
        img = np.zeros((ny, nx, n_channels), dtype=np.uint32)  # safe accumulate, downcast after
    else:
        img = np.zeros((ny, nx, n_channels), dtype=dtype)
    mask = np.zeros((ny, nx), dtype=bool)
    px = py = None
    data_started = False
    line_no = 0
    f = _open(path, verbose, "populate")
    try:
        for line in f:
            line_no += 1
            s = line.strip()
            if s == "":
                continue
            if s.startswith("<"):
                if not data_started:
                    continue  # format A header XML
                if s not in _TOLERATED_TAIL:
                    raise XRFReadError(line_no, f"unexpected XML line in data: {s!r}")
                continue
            data_started = True
            if not s.isdigit():
                raise XRFReadError(line_no, f"malformed line (expected integer): {s!r}")
            if _is_x_header(s):
                x = int(s) - X_HEADER_OFFSET
                if x < x_min or x > x_max or (x - x_min) % x_step:
                    raise XRFReadError(line_no, f"X header {x} off-grid")
                px = (x - x_min) // x_step
                continue
            if _is_y_header(s):
                y = int(s) - Y_HEADER_OFFSET
                if y < y_min or y > y_max or (y - y_min) % y_step:
                    raise XRFReadError(line_no, f"Y header {y} off-grid")
                py = (y - y_min) // y_step
                if px is not None:
                    mask[py, px] = True
                continue
            c = int(s)
            if px is None or py is None:
                raise XRFReadError(line_no, "event before any X/Y header")
            img[py, px, c] += 1
    finally:
        f.close()
    if dtype == np.dtype("uint16"):
        if img.max() > np.iinfo(np.uint16).max:
            raise XRFReadError(
                None, f"cell max {int(img.max())} overflows uint16 (max 65535) - use dtype='uint32'"
            )
        img = img.astype(np.uint16)
    return img, mask


def _calibration_block(scan: dict, meta: dict, meta_in: dict | None) -> dict | None:
    m, q = meta.get("m"), meta.get("q")
    if m is None or q is None:
        return None
    if scan["fmt"] == "xml" and scan["header"].get("m") is not None:
        prov = "xml"
    elif meta_in is not None:
        prov = "external"
    else:
        prov = "unknown"
    return {"m": float(m), "q": float(q), "provenance": prov}


def read_raw(path, *, n_channels: int = DEFAULT_N_CHANNELS, dtype: str = "uint32",
             metadata=None, verbose: bool = False) -> Dataset:
    """Read a raw MA-XRF file into a Dataset.

    n_channels: explicit channel depth (default 16384, instrument MCA). If the max
        observed channel reaches it, snaps UP to the next power of 2 (declared as
        anomaly `n_channels_snapped`); never derived from max(observed)+1.
    dtype: "uint32" (default) or "uint16" (checked for per-cell overflow).
    metadata: optional path to a JSON with external "grid" / "calibration"
        (needed for format B; conflict-checked against the XML when present).
    """
    if n_channels <= 0:
        raise ValueError(f"n_channels must be > 0, got {n_channels}")
    np_dtype = np.dtype(dtype)
    if np_dtype not in _ALLOWED_DTYPES:
        raise ValueError(f"dtype must be 'uint32' or 'uint16', got {dtype!r}")
    meta_in = load_metadata(metadata) if metadata is not None else None

    n_channels_requested = n_channels
    scan = _scan(path, n_channels=n_channels, verbose=verbose)
    meta = merge_metadata(scan["header"], meta_in)
    anomalies: list[dict] = []
    if scan["max_channel"] >= n_channels:
        # Detector MCA depth is a power of 2: instead of failing, snap UP to the
        # smallest power of 2 containing every observed channel (no events lost).
        n_channels = _next_pow2(scan["max_channel"] + 1)
        print(f"xrfraw: n_channels {n_channels_requested} too small for max observed "
              f"channel {scan['max_channel']} -> using {n_channels} (next power of 2)")
        anomalies.append({
            "type": "n_channels_snapped",
            "requested": n_channels_requested,
            "effective": n_channels,
            "max_channel": scan["max_channel"],
        })
    grid, grid_source, g_anoms = _resolve_grid(scan, meta)
    anomalies = anomalies + list(scan["anomalies"]) + g_anoms

    img, mask = _populate(path, grid=grid, n_channels=n_channels, dtype=np_dtype, verbose=verbose)
    total = int(img.sum())
    if total != scan["n_events"]:
        raise XRFReadError(None, f"internal error: populated {total} events, pass 1 counted {scan['n_events']}")

    nx = (grid["x_max"] - grid["x_min"]) // grid["x_step"] + 1
    ny = (grid["y_max"] - grid["y_min"]) // grid["y_step"] + 1
    x_axis = (grid["x_min"] + np.arange(nx) * grid["x_step"]).astype(np.float64)
    y_axis = (grid["y_min"] + np.arange(ny) * grid["y_step"]).astype(np.float64)

    meta_out = {
        "schema_version": SCHEMA_VERSION,
        "format": scan["fmt"],
        "source_file": os.path.basename(path),
        "n_channels": n_channels,
        "dtype": dtype,
        "n_events": scan["n_events"],
        "units": dict(DEFAULT_UNITS),
        "units_status": "assumed",
        "grid": grid,
        "grid_source": grid_source,
        "anomalies": anomalies,
        "transforms": [],
        "software": f"xrfraw {__version__}",
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    cal = _calibration_block(scan, meta, meta_in)
    if cal:
        # Known but NOT applied: with_calibration() is the explicit step that
        # materializes the energy axis (output_schema.md: calibration/energy
        # only exist once calibrated).
        meta_out["known_calibration"] = cal
    if meta.get("velocity") is not None:
        meta_out["velocity"] = float(meta["velocity"])
    raw_extra = {k: v for k, v in meta.items() if k not in {"raw", "m", "q", "grid", "velocity"}}
    if meta.get("raw") or raw_extra:
        meta_out["raw"] = {**(meta.get("raw") or {}), **raw_extra}

    return Dataset(
        img=img,
        channel=np.arange(n_channels, dtype=np.uint32),
        x_axis=x_axis,
        y_axis=y_axis,
        mask=mask,
        metadata=meta_out,
        source_file=os.path.basename(path),
        n_events=scan["n_events"],
    )


def inspect_raw(path, *, n_channels: int = DEFAULT_N_CHANNELS, dtype: str = "uint32",
                metadata=None) -> dict:
    """Validate a raw file WITHOUT allocating the cube.

    Returns format, grid, event count, max channel, memory estimate and the
    anomaly list. Grid/validation failures come back as ok=False with the
    error message instead of raising.
    """
    meta_in = load_metadata(metadata) if metadata is not None else None
    scan = _scan(path, n_channels=n_channels)
    meta = merge_metadata(scan["header"], meta_in)
    anomalies = list(scan["anomalies"])
    if scan["n_events_over"]:
        anomalies.append({
            "type": "channel_exceeds_n_channels",
            "max_channel": scan["max_channel"],
            "n_channels": n_channels,
            "n_events_affected": scan["n_events_over"],
        })
    try:
        grid, grid_source, g_anoms = _resolve_grid(scan, meta)
        anomalies += g_anoms
    except XRFReadError as e:
        return {
            "path": str(path), "format": scan["fmt"], "ok": False, "error": str(e),
            "n_events": scan["n_events"], "max_channel": scan["max_channel"],
            "n_channels": n_channels, "anomalies": anomalies,
        }
    nx = (grid["x_max"] - grid["x_min"]) // grid["x_step"] + 1
    ny = (grid["y_max"] - grid["y_min"]) // grid["y_step"] + 1
    itemsize = np.dtype(dtype).itemsize
    cal = _calibration_block(scan, meta, meta_in)
    if cal:
        # mirror read_raw(): known but NOT applied calibration block
        meta = {**meta, "known_calibration": cal}
    return {
        "path": str(path),
        "format": scan["fmt"],
        "ok": True,
        "n_lines": scan["n_lines"],
        "n_events": scan["n_events"],
        "max_channel": scan["max_channel"],
        "n_channels": n_channels,
        "dtype": dtype,
        "grid": grid,
        "grid_source": grid_source,
        "n_pixels": nx * ny,
        "n_pixels_acquired": sum(len(v) for v in scan["col_y"].values()),
        "estimated_memory_bytes": nx * ny * n_channels * itemsize,
        "anomalies": anomalies,
        "metadata": meta,
    }
