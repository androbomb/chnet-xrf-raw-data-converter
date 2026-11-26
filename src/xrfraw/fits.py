"""FITS (.fits) export e lettura (schema: output_schema.md §FITS).

Primary HDU: cubo ``(C,H,W)`` — NAXIS1=W, NAXIS2=H, NAXIS3=C — con WCS
energetica lineare sull'asse 3 (``CTYPE3/CRPIX3/CRVAL3/CDELT3/CUNIT3``)
e WCS spaziale sugli assi 1-2. Integri unsigned in convenzione standard
``BSCALE=1/BZERO`` (uint16: 32768, uint32: 2**31). Estensioni:
``XRF_META`` (JSON completo e versionato, senza troncamenti), ``MASK``
(pixel validi, uint8) e ``ENERGY`` (asse esplicito, float64). I cubi
float64 sono salvati come float32 (FITS non ha float 64-bit).
Senza compressione: primary non compresso = compatibilita' massima.

Richiede astropy: pip install chnet-xrf-raw-data-converter[fits].
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .dataset import Dataset
from .ome import _software

_DTYPES = {np.dtype(t) for t in (np.uint16, np.uint32, np.float32, np.float64)}
_FITS_UNITS = {"µm": "um"}  # forma ASCII standard FITS dell'unita'


def _fits():
    try:
        from astropy.io import fits
    except ImportError as e:
        raise ImportError("FITS support requires astropy: "
                          "pip install chnet-xrf-raw-data-converter[fits]") from e
    return fits


def _ascii(s) -> str:
    """I header FITS sono 7-bit ASCII (es. unita' 'µm' -> '\\xb5m')."""
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def _ascii_unit(u: str) -> str:
    """CUNIT deve essere unita' FITS parseabile: 'µm' ha forma ASCII 'um'."""
    return _FITS_UNITS.get(u, _ascii(u))


def write_fits(ds: Dataset, path) -> Path:
    """Scrivi ``ds`` come FITS multi-extension (senza compressione)."""
    fits = _fits()
    path = Path(path)
    ny, nx, nc = ds.img.shape
    if ds.img.dtype not in _DTYPES:
        raise ValueError(f"FITS: dtype non supportato {ds.img.dtype!r} "
                         f"(uint16/uint32/float32/float64)")
    data = np.ascontiguousarray(np.moveaxis(ds.img, -1, 0))  # (C,H,W)
    if data.dtype == np.float64:  # FITS non ha float 64-bit
        data = data.astype(np.float32)
    meta = ds.metadata
    grid = meta["grid"]
    hdu = fits.PrimaryHDU(data)
    h = hdu.header
    h["OBJECT"] = _ascii(meta["source_file"])[:66]
    h["INSTRUME"] = "MA-XRF"
    h["DATE"] = meta["created_utc"][:19]  # FITS DATE: YYYY-MM-DDTHH:MM:SS
    h["SOFTWARE"] = _software()
    # WCS spaziale (assi 1-2): griglia pixel uniforme
    h["CTYPE1"], h["CTYPE2"] = "X", "Y"
    h["CRPIX1"], h["CRPIX2"] = 1.0, 1.0
    h["CRVAL1"], h["CRVAL2"] = float(grid["x_min"]), float(grid["y_min"])
    h["CDELT1"], h["CDELT2"] = float(grid["x_step"]), float(grid["y_step"])
    h["CUNIT1"] = _ascii_unit(meta["units"]["x"])
    h["CUNIT2"] = _ascii_unit(meta["units"]["y"])
    cal = meta.get("calibration")
    if cal:
        # WCS energetica (asse 3): E = m'*(p-1) + q' <=> CRPIX3=1, CDELT3=m',
        # CRVAL3=q'. Esatto: rebin accetta solo gruppi uniformi.
        h["CTYPE3"] = "ENERGY"
        h["CRPIX3"] = 1.0
        h["CRVAL3"] = cal.get("q_rebinned", cal["q"])
        h["CDELT3"] = cal.get("m_rebinned", cal["m"])
        h["CUNIT3"] = _ascii(cal.get("energy_unit", "keV"))
    # XRF_META: JSON completo come array 1D uint8 (byte UTF-8, no troncamenti)
    xrf_meta = fits.ImageHDU(np.frombuffer(
        json.dumps(meta, ensure_ascii=False).encode("utf-8"), dtype=np.uint8))
    xrf_meta.name = "XRF_META"
    mask = fits.ImageHDU(ds.mask.astype(np.uint8))  # FITS non ha bool
    mask.name = "MASK"
    hdus = [hdu, xrf_meta, mask]
    if ds.energy is not None:
        en = fits.BinTableHDU.from_columns(
            [fits.Column(name="E", format="D", array=ds.energy)])
        en.name = "ENERGY"
        hdus.append(en)
    with fits.HDUList(hdus) as hl:
        hl.writeto(path)
    return path


def read_fits(path) -> Dataset:
    """Leggi un FITS scritto da ``write_fits`` e restituisce un Dataset."""
    fits = _fits()
    path = Path(path)
    with fits.open(path) as hdul:
        if "XRF_META" not in hdul:
            raise ValueError(f"missing XRF_META extension (file non xrfraw?): {path}")
        prim = hdul[0]
        if prim.data.ndim != 3:
            raise ValueError(f"primary HDU must be 3D (C,H,W): {path}")
        nc, ny, nx = prim.data.shape
        img = np.moveaxis(np.asarray(prim.data), 0, -1)  # (H,W,C), BZERO applicato
        if img.dtype.byteorder == ">":  # float FITS: big-endian -> nativo
            img = np.ascontiguousarray(img).byteswap().view(img.dtype.newbyteorder("="))
        meta = json.loads(hdul["XRF_META"].data.tobytes().decode("utf-8"))
        mask = hdul["MASK"].data.astype(bool)
        energy = None
        if "ENERGY" in hdul:
            energy = np.asarray(hdul["ENERGY"].data["E"], dtype=np.float64)
            if energy.size != nc:
                raise ValueError("stored energy axis does not match NAXIS3")
    grid = meta["grid"]
    channel = np.arange(nc, dtype=np.uint32)
    x_axis = (grid["x_min"] + np.arange(nx) * grid["x_step"]).astype(np.float64)
    y_axis = (grid["y_min"] + np.arange(ny) * grid["y_step"]).astype(np.float64)
    cal = meta.get("calibration")
    cal_m = cal_q = None
    calibrated = False
    if cal:
        cal_m = cal.get("m_rebinned", cal["m"])
        cal_q = cal.get("q_rebinned", cal["q"])
        if energy is None:  # file senza asse esplicito: ri-deriva da m/q
            energy = cal_m * channel.astype(np.float64) + cal_q
        calibrated = True
    return Dataset(img=img, channel=channel, x_axis=x_axis, y_axis=y_axis,
                   mask=mask, metadata=meta, source_file=meta["source_file"],
                   n_events=meta["n_events"], energy=energy,
                   calibration_m=cal_m, calibration_q=cal_q, calibrated=calibrated)