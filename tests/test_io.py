"""M3 io: F5 round-trip NPZ/HDF5 (arrays + metadata_json, h5py / np.load)."""
import json

import h5py
import numpy as np
import pytest

from _synthetic import GRID32, PIXELS, write_format_a, write_format_b
from xrfraw import read_raw, rebin, with_calibration
from xrfraw.io import write_dataset


def _uncal_ds(tmp_path):
    p = tmp_path / "b.txt"
    write_format_b(p, PIXELS)
    return read_raw(p, n_channels=16)


def test_h5_round_trip_calibrated_rebinned(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = read_raw(p, n_channels=16)
    ds = with_calibration(ds, 1.5, -0.25, provenance="xml")
    ds = rebin(ds, 2)
    out = write_dataset(ds, tmp_path / "out.h5")
    with h5py.File(out, "r") as f:
        attr = {"energy_axis": "energy"}  # nome serializzato != nome in memoria
        for k in ("img", "channel", "energy_axis", "x_axis", "y_axis", "mask"):
            np.testing.assert_array_equal(f[k][()], getattr(ds, attr.get(k, k)))
        assert f.attrs["n_channels"] == 8
        assert f.attrs["dtype"] == "uint32"
        assert f.attrs["n_events"] == ds.n_events
        assert f.attrs["format"] == "xml"
        assert f.attrs["source_file"] == "a.txt"
        # rebin size 2: m' = 1.5*2, q' = q + (2-1)/2*m = 0.5 (bin-mean)
        assert f.attrs["calibration_m"] == 3.0
        assert f.attrs["calibration_q"] == 0.5
        # originale distinta, fattore R, unita', convenzione (schema v2)
        assert f.attrs["calibration_m_original"] == 1.5
        assert f.attrs["calibration_q_original"] == -0.25
        assert f.attrs["rebin_factor"] == 2
        assert f.attrs["energy_unit"] == "keV"
        assert f.attrs["bin_convention"] == "bin-mean"
        np.testing.assert_array_equal(f["energy_axis"][()], 3.0 * np.arange(8) + 0.5)
        assert f.attrs["compression"] == 4  # default gzip level
        meta = json.loads(f.attrs["metadata_json"])
        assert meta["schema_version"] == 2
        assert meta["calibration"]["m"] == 1.5 and meta["calibration"]["q"] == -0.25
        assert meta["calibration"]["rebin_factor"] == 2
        assert meta["transforms"] == [{"type": "rebin", "size": 2, "how": "sum",
                                       "n_channels_from": 16, "n_channels_to": 8}]


def test_npz_round_trip_calibrated_rebinned(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = with_calibration(read_raw(p, n_channels=16), 1.5, -0.25,
                          provenance="xml")
    ds = rebin(ds, 2)
    out = write_dataset(ds, tmp_path / "out.npz", fmt="npz")
    z = np.load(out)
    np.testing.assert_array_equal(z["img"], ds.img)
    np.testing.assert_array_equal(z["energy_axis"], 3.0 * np.arange(8) + 0.5)
    assert int(z["img"].sum()) == ds.n_events
    attrs = json.loads(z["attrs"].item())
    assert (attrs["calibration_m"], attrs["calibration_q"]) == (3.0, 0.5)
    assert (attrs["calibration_m_original"],
            attrs["calibration_q_original"]) == (1.5, -0.25)
    assert attrs["rebin_factor"] == 2 and attrs["energy_unit"] == "keV"
    z.close()


def test_h5_attrs_calibrated_no_rebin(tmp_path):
    # R = 1: originale e post-rebin coincidono, fattore esplicito = 1
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = with_calibration(read_raw(p, n_channels=16), 1.5, -0.25,
                          provenance="xml")
    out = write_dataset(ds, tmp_path / "o.h5")
    with h5py.File(out, "r") as f:
        assert f.attrs["rebin_factor"] == 1
        assert f.attrs["calibration_m"] == f.attrs["calibration_m_original"] == 1.5
        assert f.attrs["calibration_q"] == f.attrs["calibration_q_original"] == -0.25


def test_npz_round_trip_uncalibrated(tmp_path):
    ds = _uncal_ds(tmp_path)
    out = write_dataset(ds, tmp_path / "out.npz", fmt="npz")
    z = np.load(out)
    for k in ("img", "channel", "x_axis", "y_axis", "mask"):
        np.testing.assert_array_equal(z[k], getattr(ds, k))
    assert "energy_axis" not in z.files
    attrs = json.loads(z["attrs"].item())
    assert attrs["n_channels"] == 16
    assert "calibration_m" not in attrs
    meta = json.loads(attrs["metadata_json"])
    assert meta["format"] == "data-only"
    assert meta["n_events"] == 8
    z.close()


def test_h5_uncalibrated_has_no_energy_or_cal_attrs(tmp_path):
    ds = _uncal_ds(tmp_path)
    out = write_dataset(ds, tmp_path / "o.h5")
    with h5py.File(out, "r") as f:
        assert "energy_axis" not in f
        assert "calibration_m" not in f.attrs


def test_refuses_overwrite(tmp_path):
    ds = _uncal_ds(tmp_path)
    out = tmp_path / "o.h5"
    write_dataset(ds, out)
    with pytest.raises(FileExistsError, match="exists"):
        write_dataset(ds, out)
    write_dataset(ds, out, overwrite=True)  # explicit replace works


def test_bad_fmt(tmp_path):
    ds = _uncal_ds(tmp_path)
    with pytest.raises(ValueError, match="fmt"):
        write_dataset(ds, tmp_path / "o.x", fmt="csv")


def test_no_partial_file_on_failure(tmp_path, monkeypatch):
    ds = _uncal_ds(tmp_path)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(h5py, "File", boom)
    with pytest.raises(OSError, match="disk full"):
        write_dataset(ds, tmp_path / "o.h5")
    assert list(tmp_path.glob("o.h5*")) == []


# --- compress (gzip, both formats) -------------------------------------------

def test_h5_compression_default_and_off(tmp_path):
    ds = _uncal_ds(tmp_path)
    out = write_dataset(ds, tmp_path / "c.h5")          # default compress=4
    with h5py.File(out, "r") as f:
        assert f["img"].compression == "gzip" and f["img"].compression_opts == 4
        assert f.attrs["compression"] == 4
        np.testing.assert_array_equal(f["img"][()], ds.img)
    out0 = write_dataset(ds, tmp_path / "c0.h5", compress=0)
    with h5py.File(out0, "r") as f:
        assert f["img"].compression is None
        assert f.attrs["compression"] == 0


def test_npz_compression(tmp_path):
    import zipfile
    ds = _uncal_ds(tmp_path)
    out = write_dataset(ds, tmp_path / "c.npz", fmt="npz", compress=6)
    with zipfile.ZipFile(out) as z:
        assert z.getinfo("img.npy").compress_type == zipfile.ZIP_DEFLATED
    z = np.load(out)
    np.testing.assert_array_equal(z["img"], ds.img)
    attrs = json.loads(z["attrs"].item())
    assert attrs["compression"] == 6
    z.close()
    out0 = write_dataset(ds, tmp_path / "c0.npz", fmt="npz", compress=0)
    with zipfile.ZipFile(out0) as z:
        assert z.getinfo("img.npy").compress_type == zipfile.ZIP_STORED


def test_compress_validation(tmp_path):
    ds = _uncal_ds(tmp_path)
    for bad in (10, -1, "4", True):
        with pytest.raises(ValueError, match="compress"):
            write_dataset(ds, tmp_path / f"o{bad}.h5", compress=bad)  # type: ignore[arg-type]