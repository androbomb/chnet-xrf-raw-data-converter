"""Raw file metadata: line-based XML header (format A) and external JSON.

The XML is not standard (tag names contain (), / and spaces) and is
line-oriented: one field per line. It is parsed line by line instead of with
ElementTree (the legacy escape+ET dance, see legacy_audit.md).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..errors import MetadataConflictError

_FIELD_RE = re.compile(r'^\s*<([^>]+)>\s*"([^"]*)"\s*</\1>\s*$')
_OPEN_RE = re.compile(r"^\s*<([^>][^>]*)>\s*$")
_CLOSE_RE = re.compile(r"^\s*</([^>]+)>\s*$")
_GRID_KEYS = ("x_min", "x_max", "x_step", "y_min", "y_max", "y_step")


def parse_xml_header(lines: list[str]) -> dict:
    """Parse the format A header.

    Returns ``{"raw": {section.name: value}, "m": float|None, "q": float|None,
    "velocity": float|None, "grid": dict|None}``.
    """
    raw: dict[str, object] = {}
    section = ""
    for line in lines:
        m = _FIELD_RE.match(line)
        if m:
            name, value = m.group(1), m.group(2)
            raw[f"{section}.{name}" if section else name] = _to_number(value)
            continue
        m = _OPEN_RE.match(line)
        if m:
            section = m.group(1)
            continue
        m = _CLOSE_RE.match(line)
        if m:
            section = ""
    out = {
        "raw": raw,
        "m": raw.get("calibration.calibration_keV/ch"),
        "q": raw.get("calibration.calibration_Offset"),
        "velocity": raw.get("analysisInfo.Velocity"),
    }
    out["grid"] = _grid_from_raw(raw)
    return out


def _to_number(s: str):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s  # non-numeric values (e.g. "y"/"n" flags) kept as strings


def _grid_from_raw(raw: dict):
    try:
        return {
            "x_min": int(raw["analysisInfo.Xmin"]),
            "x_max": int(raw["analysisInfo.Xmax"]),
            "x_step": int(raw["analysisInfo.Xstep"]),
            "y_min": int(raw["analysisInfo.Ymin"]),
            "y_max": int(raw["analysisInfo.Ymax"]),
            "y_step": int(raw["analysisInfo.Ystep"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def load_metadata(path) -> dict:
    """Load external metadata (JSON object: "grid" / "calibration" / extras)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"external metadata not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"external metadata must be a JSON object: {p}")
    return data


def merge_metadata(base: dict, external: dict | None) -> dict:
    """Merge external metadata into file metadata (base: XML header or {}).

    Same key with a different value -> MetadataConflictError (no silent
    overwrite); missing key -> adopted from external.
    """
    if external is None:
        return dict(base)
    merged = dict(base)

    ext_cal = external.get("calibration") or {}
    for key in ("m", "q"):
        ext_v = ext_cal.get(key)
        if ext_v is None:
            continue
        base_v = base.get(key)
        if base_v is not None and float(base_v) != float(ext_v):
            raise MetadataConflictError(f"calibration.{key}", base_v, ext_v)
        merged[key] = float(ext_v)

    ext_grid = external.get("grid") or {}
    if ext_grid:
        base_grid = dict(base.get("grid") or {})
        for k in _GRID_KEYS:
            ext_v = ext_grid.get(k)
            if ext_v is None:
                continue
            base_v = base_grid.get(k)
            if base_v is not None and int(base_v) != int(ext_v):
                raise MetadataConflictError(f"grid.{k}", base_v, ext_v)
            base_grid[k] = int(ext_v)
        merged["grid"] = base_grid if all(k in base_grid for k in _GRID_KEYS) else None

    ext_v = external.get("velocity")
    if ext_v is not None:
        base_v = base.get("velocity")
        if base_v is not None and float(base_v) != float(ext_v):
            raise MetadataConflictError("velocity", base_v, ext_v)
        merged["velocity"] = float(ext_v)

    for k, v in external.items():
        if k not in ("grid", "calibration", "velocity") and k not in merged:
            merged[k] = v
    return merged
