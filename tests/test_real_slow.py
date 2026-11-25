"""Slow tests on the real data_example/ files (run: pytest -m slow)."""
from pathlib import Path

import numpy as np
import pytest

from xrfraw import inspect_raw, read_raw, read_ome
from xrfraw.io import convert_file

BASE = Path(__file__).resolve().parents[1] / "data_example"
MAPPA11 = BASE / "mappa11.txt"
RAGAZZO = BASE / "Ragazzo-triste_area4_centrodx_38-80.txt"


@pytest.mark.slow
@pytest.mark.skipif(not (MAPPA11.is_file() and RAGAZZO.is_file()),
                    reason="data_example/ files not present")
def test_inspect_real_files():
    r = inspect_raw(MAPPA11)
    assert r["ok"] and r["format"] == "xml"
    assert r["n_events"] == 19_825_090
    assert r["max_channel"] == 15902
    assert r["grid"] == {"x_min": 5000, "x_max": 290000, "x_step": 1000,
                         "y_min": 190000, "y_max": 265000, "y_step": 1000}
    assert r["n_pixels"] == 286 * 76
    assert r["n_pixels_acquired"] == 21_659
    mc = [a for a in r["anomalies"] if a["type"] == "missing_column"]
    assert [a["x"] for a in mc] == [290000] and mc[0]["n_pixels"] == 76
    assert any(a["type"] == "missing_row" and a["x"] == 5000 and a["y"] == 265000
               for a in r["anomalies"])
    dx = [a for a in r["anomalies"] if a["type"] == "dangling_x_marker"]
    assert len(dx) == 1 and dx[0]["x"] == 5000 and dx[0]["y_prev"] == 265000 \
        and dx[0].get("at") == "eof"

    r2 = inspect_raw(RAGAZZO)
    assert r2["ok"] and r2["format"] == "data-only"
    assert r2["n_events"] == 56_661_209
    assert r2["max_channel"] == 15999
    assert r2["grid_source"] == "inferred"
    assert r2["grid"] == {"x_min": 5000, "x_max": 219000, "x_step": 1000,
                          "y_min": 5000, "y_max": 149000, "y_step": 1000}
    assert r2["n_pixels"] == 215 * 145
    assert r2["n_pixels_acquired"] == 31_174
    assert any(a["type"] == "dangling_x_marker" and a["at"] == "eof" and a["x"] == 219000
               and a["y_prev"] == 149000 for a in r2["anomalies"])


@pytest.mark.slow
@pytest.mark.skipif(not (MAPPA11.is_file() and RAGAZZO.is_file()),
                    reason="data_example/ files not present")
def test_read_real_files_totals_mask_and_trailing():
    # F2 real: sum(img) == n_events; F9 real: channels above max observed zero.
    # RAM: ~1.4 GB + ~2.0 GB cubes allocated sequentially (uint32, NC=16384).
    ds = read_raw(MAPPA11)
    assert ds.img.shape == (76, 286, 16384)  # (y, x, channel)
    assert ds.img.dtype == np.uint32
    assert int(ds.img.sum()) == ds.n_events == 19_825_090
    assert int(ds.mask.sum()) == 21_659  # 286*76 - 77 unacquired pixels
    assert int(ds.img[..., 15903:].sum()) == 0  # max observed channel 15902
    assert ds.metadata["known_calibration"] == \
        {"m": 0.00259259, "q": -0.0355556, "provenance": "xml"}
    assert not ds.calibrated and ds.energy is None

    ds2 = read_raw(RAGAZZO)
    assert ds2.img.shape == (145, 215, 16384)
    assert int(ds2.img.sum()) == ds2.n_events == 56_661_209
    assert int(ds2.mask.sum()) == 31_174  # 215*145 - 1 unacquired pixel
    assert int(ds2.img[..., 16000:].sum()) == 0  # max observed channel 15999
    assert "known_calibration" not in ds2.metadata


@pytest.mark.slow
@pytest.mark.skipif(not MAPPA11.is_file(), reason="data_example/ files not present")
def test_ome_round_trip_real(tmp_path):
    # E2E reale: OME-TIFF (16384 IFD) identico al cubo in memoria.
    # RAM: due cubi ~1.4 GB (write -> read), compress=0 (velocita').
    ds = convert_file(MAPPA11, tmp_path / "mappa11.ome.tif", fmt="ome", compress=0)
    back = read_ome(tmp_path / "mappa11.ome.tif")
    assert back.img.shape == (76, 286, 16384) and back.img.dtype == np.uint32
    np.testing.assert_array_equal(back.img, ds.img)  # lossless completo
    np.testing.assert_array_equal(back.mask, ds.mask)
    assert back.metadata == ds.metadata
    assert back.n_events == 19_825_090
    assert back.calibrated and back.calibration_m == 0.00259259
    np.testing.assert_array_equal(back.energy, back.calibration_m * back.channel + back.calibration_q)
