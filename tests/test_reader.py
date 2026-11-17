"""Reader: 2-pass streaming on synthetic files (F1-sint, F6a, F11, orientamenti)."""
import json

import numpy as np
import pytest

from _synthetic import GRID32, MAX_CHANNEL, N_EVENTS, PIXELS, write_format_a, write_format_b
from xrfraw import inspect_raw, read_raw
from xrfraw.errors import MetadataConflictError, XRFReadError


def test_read_orientation_and_counts(tmp_path):
    p = tmp_path / "s.a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = read_raw(p)
    assert ds.img.shape == (2, 3, 16384)  # (y, x, channel)
    assert ds.img.dtype == np.uint32
    assert ds.img[0, 0, 0] == 1 and ds.img[0, 0, 5] == 2 and ds.img[0, 0, 7] == 1
    assert ds.img[0, 2, 0] == 1 and ds.img[1, 1, 12] == 1 and ds.img[1, 2, 12] == 2
    assert int(ds.img.sum()) == ds.n_events == N_EVENTS
    assert ds.mask.all()
    assert ds.x_axis.tolist() == [0.0, 1000.0, 2000.0]
    assert ds.y_axis.tolist() == [0.0, 5000.0]
    assert ds.channel.tolist()[:3] == [0, 1, 2]
    assert not ds.calibrated and ds.energy is None
    assert ds.metadata["grid_source"] == "declared"
    assert ds.metadata["known_calibration"] == {"m": 1.5, "q": -0.25, "provenance": "xml"}
    assert ds.metadata["units"] == {"x": "µm", "y": "µm", "velocity": "µm/s"}
    assert ds.metadata["units_status"] == "assumed"


def test_inspect_format_a(tmp_path):
    p = tmp_path / "s.a.txt"
    write_format_a(p, GRID32, PIXELS)
    r = inspect_raw(p)
    assert r["ok"] and r["format"] == "xml"
    assert r["n_events"] == N_EVENTS and r["max_channel"] == MAX_CHANNEL
    assert r["grid"] == {"x_min": 0, "x_max": 2000, "x_step": 1000,
                         "y_min": 0, "y_max": 5000, "y_step": 5000}
    assert r["grid_source"] == "declared"
    assert r["n_pixels"] == 6 and r["n_pixels_acquired"] == 6
    assert r["metadata"]["m"] == 1.5 and r["metadata"]["q"] == -0.25
    assert r["estimated_memory_bytes"] == 6 * 16384 * 4
    assert r["anomalies"] == []


def test_format_b_inferred_grid(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, PIXELS)
    ds = read_raw(p)
    assert ds.metadata["format"] == "data-only"
    assert ds.metadata["grid_source"] == "inferred"
    assert ds.metadata["grid"] == {"x_min": 0, "x_max": 2000, "x_step": 1000,
                                   "y_min": 0, "y_max": 5000, "y_step": 5000}
    assert int(ds.img.sum()) == N_EVENTS
    assert "calibration" not in ds.metadata
    assert "velocity" not in ds.metadata


def test_format_b_with_external_metadata_equals_a(tmp_path):
    pa = tmp_path / "s.a.txt"
    pb = tmp_path / "s.b.txt"
    pj = tmp_path / "meta.json"
    write_format_a(pa, GRID32, PIXELS)
    write_format_b(pb, PIXELS)
    pj.write_text(json.dumps({
        "grid": {"x_min": 0, "x_max": 2000, "x_step": 1000,
                 "y_min": 0, "y_max": 5000, "y_step": 5000},
        "calibration": {"m": 1.5, "q": -0.25},
        "velocity": 8000,
    }))
    da = read_raw(pa)
    db = read_raw(pb, metadata=pj)
    assert np.array_equal(da.img, db.img)
    ca, cb = da.metadata["known_calibration"], db.metadata["known_calibration"]
    assert (ca["m"], ca["q"]) == (cb["m"], cb["q"]) == (1.5, -0.25)
    assert ca["provenance"] == "xml" and cb["provenance"] == "external"
    assert da.metadata["velocity"] == db.metadata["velocity"] == 8000


def test_n_channels_overflow_raises_with_pow2_hint(tmp_path):
    # Exact-depth contract: the output is (h, w, n_channels); data above the
    # depth is an error, with the next power of 2 suggested (MCA is a power of 2).
    p = tmp_path / "s.a.txt"
    write_format_a(p, GRID32, [(0, 0, [100])])
    with pytest.raises(XRFReadError, match="at least 128"):
        read_raw(p, n_channels=50)  # max channel 100 >= 50; 2^7 = 128 covers it
    # inspect_raw stays advisory (no raise)
    r = inspect_raw(p, n_channels=50)
    assert r["ok"]
    assert any(a["type"] == "channel_exceeds_n_channels" and a["max_channel"] == 100
               for a in r["anomalies"])


def test_n_channels_kept_when_it_fits(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [100])])
    ds = read_raw(p, n_channels=200)  # fits: explicit value respected
    assert ds.img.shape[2] == 200


def test_x_header_outside_declared_grid(tmp_path):
    p = tmp_path / "s.a.txt"
    write_format_a(p, (0, 1000, 1000, 0, 5000, 5000), [(0, 0, [1]), (2000, 0, [2])])
    with pytest.raises(XRFReadError, match="outside declared grid"):
        read_raw(p)


def test_malformed_line_in_data(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [1])])
    lines = p.read_text().splitlines()
    lines.insert(2, "garbage")
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(XRFReadError, match="malformed"):
        read_raw(p)


def test_dangling_x_marker_duplicate(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, PIXELS, dup_first_x=True)
    ds = read_raw(p)
    anoms = [a for a in ds.metadata["anomalies"] if a["type"] == "dangling_x_marker"]
    assert len(anoms) == 1 and anoms[0]["x"] == 0 and anoms[0]["y_prev"] is None
    assert int(ds.img.sum()) == N_EVENTS


def test_dangling_x_marker_at_eof(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, PIXELS, dangling_eof_x=2000)
    ds = read_raw(p)
    anoms = [a for a in ds.metadata["anomalies"] if a["type"] == "dangling_x_marker"]
    assert len(anoms) == 1 and anoms[0]["x"] == 2000 and anoms[0].get("at") == "eof"


def test_missing_column_mask(tmp_path):
    p = tmp_path / "s.a.txt"
    px = [(0, 0, [1]), (2000, 0, [2]), (0, 5000, [3]), (2000, 5000, [4])]
    write_format_a(p, GRID32, px)
    ds = read_raw(p)
    assert not ds.mask[:, 1].any()
    assert ds.mask[:, 0].all() and ds.mask[:, 2].all()
    mc = [a for a in ds.metadata["anomalies"] if a["type"] == "missing_column"]
    assert [a["x"] for a in mc] == [1000] and mc[0]["n_pixels"] == 2
    assert int(ds.img.sum()) == 4 and ds.n_events == 4


def test_non_uniform_grid_error(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [1]), (1000, 0, [2]), (3000, 0, [3])])
    with pytest.raises(XRFReadError, match="non-uniform"):
        read_raw(p)


def test_metadata_conflict(tmp_path):
    pa = tmp_path / "s.a.txt"
    pj = tmp_path / "meta.json"
    write_format_a(pa, GRID32, PIXELS)
    pj.write_text(json.dumps({"grid": {"x_min": 999, "x_max": 2000, "x_step": 1000,
                                       "y_min": 0, "y_max": 5000, "y_step": 5000}}))
    with pytest.raises(MetadataConflictError, match="x_min"):
        read_raw(pa, metadata=pj)


def test_uint16_overflow_rejected(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [7] * 70_000)])
    with pytest.raises(XRFReadError, match="overflows uint16"):
        read_raw(p, dtype="uint16")
    ds = read_raw(p, dtype="uint32")
    assert ds.img.dtype == np.uint32 and int(ds.img[0, 0, 7]) == 70_000
    p2 = tmp_path / "ok.b.txt"
    write_format_b(p2, [(0, 0, [7] * 100)])
    ds2 = read_raw(p2, dtype="uint16")
    assert ds2.img.dtype == np.uint16 and int(ds2.img[0, 0, 7]) == 100


def test_trailing_channels_preserved_zero(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [12])])
    ds = read_raw(p)
    assert ds.img.shape[2] == 16384
    assert int(ds.img[..., 13:].sum()) == 0  # channels above max observed kept, zero


def test_float_dtypes(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [1, 1, 2]), (1000, 0, [5])])
    ds = read_raw(p, dtype="float32")
    assert ds.img.dtype == np.float32
    assert ds.img[0, 0, :3].tolist() == [0.0, 2.0, 1.0] and ds.img[0, 1, 5] == 5.0
    assert int(ds.img.sum()) == 4
    ds64 = read_raw(p, dtype="float64")
    assert ds64.img.dtype == np.float64 and int(ds64.img.sum()) == 4
    with pytest.raises(ValueError, match="'float32'"):
        read_raw(p, dtype="float16")


def test_empty_file_error(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("\n\n")
    with pytest.raises(XRFReadError, match="empty file"):
        read_raw(p)
