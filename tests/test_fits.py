"""FITS: round-trip lossless (counts/shape/dtype/metadata/masca), WCS
energetico, BSCALE/BZERO, XRF_META/ENERGY, cross-format, CLI (schema:
output_schema.md §FITS)."""
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from _synthetic import GRID32, PIXELS, write_format_a
from xrfraw import read_fits, read_ome, read_raw, rebin_to, with_calibration
from xrfraw.io import write_dataset

U32MAX = np.iinfo(np.uint32).max
BASE = Path(__file__).resolve().parents[1] / "data_example"


def _dataset(tmp_path, dtype="uint32", calibrated=True):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = read_raw(p, n_channels=16, dtype=dtype)
    return with_calibration(ds, 1.5, -0.25, provenance="xml") if calibrated else ds


def test_round_trip_uint32_bzero(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32")
    ds.img[0, 0, 0] = U32MAX  # sentinela convenzione BZERO
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    back = read_fits(out)
    np.testing.assert_array_equal(back.img, ds.img)
    assert back.img.dtype == np.uint32
    np.testing.assert_array_equal(back.mask, ds.mask)
    assert back.metadata == ds.metadata
    np.testing.assert_array_equal(back.energy, ds.energy)
    assert (back.source_file, back.n_events, back.calibrated) == \
        (ds.source_file, ds.n_events, True)
    with fits.open(out) as h:
        assert [x.name for x in h] == ["PRIMARY", "XRF_META", "MASK", "ENERGY"]
        assert h[0].header["BSCALE"] == 1
        assert h[0].header["BZERO"] == 2**31
        assert h[0].header["OBJECT"] == "a.txt"
        assert h[0].header["INSTRUME"] == "MA-XRF"
        h.verify()  # strict: header/estensioni conformi


def test_round_trip_uint16(tmp_path):
    ds = _dataset(tmp_path, dtype="uint16")
    ds.img[0, 0, 0] = np.iinfo(np.uint16).max
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    back = read_fits(out)
    np.testing.assert_array_equal(back.img, ds.img)
    assert back.img.dtype == np.uint16
    with fits.open(out) as h:
        assert h[0].header["BZERO"] == 32768


def test_round_trip_float32(tmp_path):
    ds = _dataset(tmp_path, dtype="float32", calibrated=False)
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    back = read_fits(out)
    np.testing.assert_array_equal(back.img, ds.img)
    assert back.img.dtype == np.float32
    with fits.open(out) as h:
        assert h[0].header.get("BZERO") is None


def test_float64_fallback_float32(tmp_path):
    # FITS non ha float 64-bit: il cubo e' salvato come float32 (documentato);
    # il metadata JSON e' conservato invariato.
    ds = _dataset(tmp_path, dtype="float64", calibrated=False)
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    back = read_fits(out)
    assert back.img.dtype == np.float32
    np.testing.assert_array_equal(back.img, ds.img.astype(np.float32))
    assert back.metadata == ds.metadata
    assert back.metadata["dtype"] == "float64"


def test_unsupported_dtype(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32")
    ds.img = ds.img.astype(np.int64)
    with pytest.raises(ValueError, match="dtype"):
        write_dataset(ds, tmp_path / "c.fits", fmt="fits")


def test_wcs_energy(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32")
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    with fits.open(out) as h:
        hdr = h[0].header
        assert hdr["CTYPE3"] == "ENERGY"
        assert hdr["CRPIX3"] == 1.0
        assert hdr["CDELT3"] == 1.5 and hdr["CRVAL3"] == -0.25
        assert hdr["CUNIT3"] == "keV"
        assert (hdr["CTYPE1"], hdr["CTYPE2"]) == ("X", "Y")
        assert (hdr["CDELT1"], hdr["CDELT2"]) == (1000.0, 5000.0)
        assert (hdr["CUNIT1"], hdr["CUNIT2"]) == ("um", "um")
        w = WCS(hdr)
        world = w.pixel_to_world_values(np.ones(16), np.ones(16), np.arange(16.0))
        np.testing.assert_allclose(world[2], ds.energy, rtol=0, atol=1e-12)
        assert list(w.world_axis_units) == ["um", "um", "keV"]


def test_energy_extension(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32")
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    with fits.open(out) as h:
        assert h["ENERGY"].columns["E"].format == "D"
        en = np.asarray(h["ENERGY"].data["E"], dtype=np.float64)
        np.testing.assert_array_equal(en, ds.energy)


def test_uncalibrated_no_wcs3(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32", calibrated=False)
    out = write_dataset(ds, tmp_path / "c.fits", fmt="fits")
    back = read_fits(out)
    assert back.calibrated is False and back.energy is None
    with fits.open(out) as h:
        assert h[0].header.get("CTYPE3") is None
        assert "ENERGY" not in [x.name for x in h]


def test_cross_formats(tmp_path):
    ds = _dataset(tmp_path, dtype="uint32")
    back_ome = read_ome(write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome"))
    back_fits = read_fits(write_dataset(back_ome, tmp_path / "c.fits", fmt="fits"))
    for b in (back_ome, back_fits):
        np.testing.assert_array_equal(b.img, ds.img)
        assert b.metadata == ds.metadata
        np.testing.assert_array_equal(b.energy, ds.energy)
    h5 = write_dataset(back_fits, tmp_path / "c.h5", fmt="h5")
    with h5py.File(h5, "r") as f:
        np.testing.assert_array_equal(f["img"][()], ds.img)
        np.testing.assert_array_equal(f["energy_axis"][()], ds.energy)


def test_cli_fits(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    r = subprocess.run([sys.executable, "-m", "xrfraw", str(a), "-o",
                        str(tmp_path / "out"), "--format", "fits",
                        "--n-channels", "16", "--rebin", "2", "sum"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    back = read_fits(tmp_path / "out" / "a.fits")
    assert back.img.shape == (2, 3, 8)
    assert int(back.img.sum()) == 8  # rebin sum preserves totals
    assert back.calibration_m == 3.0  # XML m=1.5, rescaled by rebin 2
    assert back.energy is not None and back.energy.shape == (8,)


@pytest.mark.slow
@pytest.mark.skipif(not (BASE / "mappa11.txt").is_file(),
                    reason="data_example/ files not present")
def test_fits_round_trip_real_512(tmp_path):
    # E2E reale: cubo 512 canali (rebin sum) lossless su FITS non compresso.
    ds = rebin_to(read_raw(BASE / "mappa11.txt"), 512)
    out = write_dataset(ds, tmp_path / "m.fits", fmt="fits")
    assert out.stat().st_size >= ds.img.nbytes  # non compresso
    back = read_fits(out)
    np.testing.assert_array_equal(back.img, ds.img)
    assert back.img.dtype == np.uint32
    assert back.metadata == ds.metadata
    np.testing.assert_array_equal(back.energy, ds.energy)