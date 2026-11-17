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
        for k in ("img", "channel", "energy", "x_axis", "y_axis", "mask"):
            np.testing.assert_array_equal(f[k][()], getattr(ds, k))
        assert f.attrs["n_channels"] == 8
        assert f.attrs["dtype"] == "uint32"
        assert f.attrs["n_events"] == ds.n_events
        assert f.attrs["format"] == "xml"
        assert f.attrs["source_file"] == "a.txt"
        assert f.attrs["calibration_m"] == 1.5
        assert f.attrs["calibration_q"] == -0.25
        meta = json.loads(f.attrs["metadata_json"])
        assert meta["schema_version"] == 1
        assert meta["calibration"] == {"m": 1.5, "q": -0.25, "provenance": "xml"}
        assert meta["transforms"] == [{"type": "rebin", "size": 2, "how": "sum",
                                       "n_channels_from": 16, "n_channels_to": 8}]


def test_npz_round_trip_uncalibrated(tmp_path):
    ds = _uncal_ds(tmp_path)
    out = write_dataset(ds, tmp_path / "out.npz", fmt="npz")
    z = np.load(out)
    for k in ("img", "channel", "x_axis", "y_axis", "mask"):
        np.testing.assert_array_equal(z[k], getattr(ds, k))
    assert "energy" not in z.files
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
        assert "energy" not in f
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