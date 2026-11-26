"""Write Dataset to NPZ/HDF5 (M3) + core conversion pipeline (M5).

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
from .data import read_raw
from .processing import rebin, rebin_to as rebin_to_depth, with_calibration


def _arrays(ds: Dataset) -> dict:
    a = {"img": ds.img, "channel": ds.channel,
         "x_axis": ds.x_axis, "y_axis": ds.y_axis, "mask": ds.mask}
    if ds.energy is not None:
        a["energy_axis"] = ds.energy
    return a


def _attrs(ds: Dataset, compress: int) -> dict:
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
    attrs["compression"] = compress
    cal = meta.get("calibration")
    if cal:
        # effective (post-rebin) m/q; original kept distinct. File 0.1.1
        # hanno m/q gia' efficaci e niente m_rebinned/rebin_factor.
        attrs["calibration_m"] = cal.get("m_rebinned", cal["m"])
        attrs["calibration_q"] = cal.get("q_rebinned", cal["q"])
        attrs["calibration_m_original"] = cal["m"]
        attrs["calibration_q_original"] = cal["q"]
        attrs["rebin_factor"] = cal.get("rebin_factor", 1)
        attrs["energy_unit"] = cal.get("energy_unit", "keV")
        attrs["bin_convention"] = cal.get("convention", "bin-mean")
    return attrs


def write_dataset(ds: Dataset, path, fmt: str = "h5", compress: int = 4,
                  overwrite: bool = False) -> Path:
    """Write ``ds`` to ``path`` as .h5, .npz or .ome.tif (atomic, no silent overwrite).

    compress: level 0..9 (0 = uncompressed; default 4) — gzip for h5/npz,
    zlib for ome.
    """
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {path} (use overwrite=True)")
    fmt = fmt.lower()
    if fmt not in ("h5", "npz", "ome", "fits"):
        raise ValueError(f"fmt must be 'h5', 'npz', 'ome' or 'fits', got {fmt!r}")
    if not isinstance(compress, int) or isinstance(compress, bool) or not 0 <= compress <= 9:
        raise ValueError(f"compress must be an int 0..9 (0 = none), got {compress!r}")

    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    os.close(fd)
    try:
        if fmt == "h5":
            kw = {} if compress == 0 else {"compression": "gzip", "compression_opts": compress}
            with h5py.File(tmp, "w") as f:
                for k, v in _arrays(ds).items():
                    f.create_dataset(k, data=v, **kw)
                f.attrs.update(_attrs(ds, compress))
            os.replace(tmp, path)
        elif fmt == "ome":
            from . import ome  # lazy: ome riusa _attrs da questo modulo
            ome.write_ome(ds, tmp, compress=compress)
            os.replace(tmp, path)
        elif fmt == "fits":
            from . import fits as fits_mod  # lazy: astropy e' extra opzionale
            fits_mod.write_fits(ds, tmp)  # compress ignorato (compatibilita')
            os.replace(tmp, path)
        else:
            a = _arrays(ds)
            a["attrs"] = np.array(json.dumps(_attrs(ds, compress), ensure_ascii=False))
            if compress == 0:
                np.savez(tmp, **a)
            else:
                np.savez_compressed(tmp, **a, compresslevel=compress)
            os.replace(tmp + ".npz", path)  # np.savez appends ".npz"
    except BaseException:
        for p in (tmp, tmp + ".npz"):
            with contextlib.suppress(OSError):
                os.unlink(p)
        raise
    return path


def convert_file(src, out_path, *, fmt: str = "h5", n_channels: int | None = None,
                 dtype: str = "uint32", metadata=None, rebin_spec=None,
                 rebin_to=None, cal=None, compress: int = 4,
                 overwrite: bool = False) -> Dataset:
    """Core pipeline (shared CLI/UI, M5): read_raw -> with_calibration ->
    optional rebin -> write_dataset. Returns the written Dataset.

    n_channels: exact output depth (h, w, n_channels); default 16384.
    cal: None -> apply the dataset's known_calibration when present;
         dict(m=, q=, provenance=) -> apply that one explicitly.
    rebin_spec: None or (size, "sum" | "mean") — factor-based rebin.
    rebin_to: None or a target depth in (512, 1024, 2048, 4096, 8192) —
        (h, w, N) -> (h, w, rebin_to), sum-only, totals preserved;
        mutually exclusive with rebin_spec.
    compress: gzip level 0..9 for the output file (0 = none; default 4).
    """
    if rebin_spec and rebin_to is not None:
        raise ValueError("pass either rebin_spec or rebin_to, not both")
    kwargs = {"dtype": dtype}
    if n_channels:
        kwargs["n_channels"] = n_channels
    if metadata:
        kwargs["metadata"] = metadata
    ds = read_raw(src, **kwargs)
    c = cal if cal is not None else ds.metadata.get("known_calibration")
    if c:
        ds = with_calibration(ds, c["m"], c["q"],
                              provenance=c.get("provenance", "external"))
    if rebin_spec:
        ds = rebin(ds, rebin_spec[0], how=rebin_spec[1])
    elif rebin_to is not None:
        ds = rebin_to_depth(ds, rebin_to)
    write_dataset(ds, out_path, fmt=fmt, compress=compress, overwrite=overwrite)
    return ds