"""M3 CLI: happy path, F6b (format B + JSON == format A), F12 (conflict),
exit codes, batch dir, no silent overwrite."""
import json
import subprocess
import sys

import h5py
import numpy as np

from _synthetic import GRID32, PIXELS, write_format_a, write_format_b

GRID_JSON = {"x_min": 0, "x_max": 2000, "x_step": 1000,
             "y_min": 0, "y_max": 5000, "y_step": 5000}
META = {"grid": GRID_JSON, "calibration": {"m": 1.5, "q": -0.25}, "velocity": 8000}


def run(*args):
    return subprocess.run([sys.executable, "-m", "xrfraw", *map(str, args)],
                          capture_output=True, text=True)


def test_cli_happy_path_h5_rebin(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    r = run(a, "-o", tmp_path / "out", "--format", "h5",
            "--n-channels", 16, "--rebin", "2", "sum")
    assert r.returncode == 0, r.stderr
    with h5py.File(tmp_path / "out" / "a.h5", "r") as f:
        img = f["img"][()]
        assert img.shape == (2, 3, 8)
        assert int(img.sum()) == 8  # rebin sum preserves totals
        assert f.attrs["calibration_m"] == 3.0  # XML m=1.5, rescaled by rebin 2
        assert f["energy"][()].shape == (8,)
        meta = json.loads(f.attrs["metadata_json"])
        assert meta["transforms"][0]["type"] == "rebin"


def test_cli_format_b_pair_equals_format_a(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    write_format_a(a, GRID32, PIXELS)
    write_format_b(b, PIXELS)
    m = tmp_path / "meta.json"
    m.write_text(json.dumps(META))
    assert run(a, "-o", tmp_path / "outA", "--n-channels", 16,
               "--format", "npz").returncode == 0
    r = run(b, "-o", tmp_path / "outB", "--n-channels", 16,
            "--format", "npz", "--metadata", m)
    assert r.returncode == 0, r.stderr
    za, zb = np.load(tmp_path / "outA" / "a.npz"), np.load(tmp_path / "outB" / "b.npz")
    for k in ("img", "channel", "x_axis", "y_axis", "mask"):
        np.testing.assert_array_equal(za[k], zb[k])  # F6b: identical data
    ma = json.loads(json.loads(za["attrs"].item())["metadata_json"])
    mb = json.loads(json.loads(zb["attrs"].item())["metadata_json"])
    for k in ("grid", "n_channels", "dtype", "n_events", "units", "velocity"):
        assert ma[k] == mb[k]
    assert ma["calibration"]["m"] == mb["calibration"]["m"] == 1.5
    assert ma["calibration"]["q"] == mb["calibration"]["q"] == -0.25
    # provenance legitimately differs: xml vs external
    assert (ma["calibration"]["provenance"], mb["calibration"]["provenance"]) == ("xml", "external")
    za.close()
    zb.close()


def test_cli_metadata_conflict_exit1_both_values(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    m = tmp_path / "meta.json"
    m.write_text(json.dumps({"grid": {**GRID_JSON, "x_min": 100}}))  # file=0 vs external=100
    r = run(a, "-o", tmp_path / "out", "--metadata", m)
    assert r.returncode == 1
    assert "x_min" in r.stderr and "file=0" in r.stderr and "external=100" in r.stderr


def test_cli_usage_and_missing_exit_codes(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    assert run(a, "-o", tmp_path / "o", "--dtype", "float16").returncode == 2
    assert run(a, "-o", tmp_path / "o", "--rebin", "1", "sum").returncode == 2
    assert run(a, "-o", tmp_path / "o", "--rebin", "2", "max").returncode == 2
    assert run(tmp_path / "nope.txt", "-o", tmp_path / "o").returncode == 1


def test_cli_batch_dir_and_overwrite(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    write_format_a(d / "a.txt", GRID32, PIXELS)
    write_format_a(d / "b.txt", GRID32, PIXELS)
    assert run(d, "-o", tmp_path / "out", "--n-channels", 16).returncode == 0
    assert (tmp_path / "out" / "a.h5").is_file()
    assert (tmp_path / "out" / "b.h5").is_file()
    r = run(d, "-o", tmp_path / "out", "--n-channels", 16)  # no silent overwrite
    assert r.returncode == 1 and "exists" in r.stderr
    assert run(d, "-o", tmp_path / "out", "--n-channels", 16,
               "--overwrite").returncode == 0


def test_cli_rebin_to_and_compress(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    r = run(a, "-o", tmp_path / "out", "--rebin-to", "2048", "--compress", "6")
    assert r.returncode == 0, r.stderr
    with h5py.File(tmp_path / "out" / "a.h5", "r") as f:
        img = f["img"][()]
        assert img.shape == (2, 3, 2048)
        assert int(img.sum()) == 8  # sum rebin preserves totals
        assert f.attrs["calibration_m"] == 1.5 * 8  # m rescaled by the rebin size
        assert f.attrs["compression"] == 6
        assert f["img"].compression == "gzip"
    # --rebin and --rebin-to are mutually exclusive; targets are powers of 2
    assert run(a, "-o", tmp_path / "out2", "--rebin", "2", "sum",
               "--rebin-to", "2048").returncode == 2
    assert run(a, "-o", tmp_path / "out2", "--rebin-to", "100").returncode == 2
    assert run(a, "-o", tmp_path / "out2", "--compress", "10").returncode == 2