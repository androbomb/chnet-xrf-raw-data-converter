"""Write Dataset to NPZ/HDF5 (M3) — contract in output_schema.md.

No silent overwrite (FileExistsError), atomic write via temp file + rename.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

import h5py
import numpy as np

from .dataset import Dataset


def _arrays(ds: Dataset) -> dict:
    a = {"img": ds.img, "channel": ds.channel,
         "x_axis": ds.x_axis, "y_axis": ds.y_axis, "mask": ds.mask}
    if ds.energy is not None:
        a["energy"] = ds.energy
    return a


def _attrs(ds: Dataset) -> dict:
    """Scalar fields for the HDF5 root attrs / NPZ 'attrs' JSON (output_schema)."""
    meta = ds.metadata
    attrs = {
        "format": meta["format"],
        "source_file": meta["source_file"],
        "n_channels": meta["n_channels"],
        "dtype": meta["dtype"],
        "n_events": meta["n_events"],
        "metadata_json": json.dumps(meta, ensure_ascii=False),
        "software": meta["software"],
        "created_utc": meta["created_utc"],
    }
    cal = meta.get("calibration")
    if cal:
        attrs["calibration_m"] = cal["m"]
        attrs["calibration_q"] = cal["q"]
    return attrs


def write_dataset(ds: Dataset, path, fmt: str = "h5", overwrite: bool = False) -> Path:
    """Write ``ds`` to ``path`` as .h5 or .npz (atomic, no silent overwrite)."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {path} (use overwrite=True)")
    fmt = fmt.lower()
    if fmt not in ("h5", "npz"):
        raise ValueError(f"fmt must be 'h5' or 'npz', got {fmt!r}")

    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    os.close(fd)
    try:
        if fmt == "h5":
            with h5py.File(tmp, "w") as f:
                for k, v in _arrays(ds).items():
                    f.create_dataset(k, data=v)
                f.attrs.update(_attrs(ds))
            os.replace(tmp, path)
        else:
            a = _arrays(ds)
            a["attrs"] = np.array(json.dumps(_attrs(ds), ensure_ascii=False))
            np.savez(tmp, **a)
            os.replace(tmp + ".npz", path)  # np.savez appends ".npz"
    except BaseException:
        for p in (tmp, tmp + ".npz"):
            with contextlib.suppress(OSError):
                os.unlink(p)
        raise
    return path