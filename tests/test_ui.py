"""M5: minimal Dash UI — headless (no server, no browser)."""
import io as _io
import json

import h5py
import numpy as np

from _synthetic import GRID32, N_EVENTS, PIXELS, write_format_a
from xrfraw.ui import build_app
from xrfraw.ui.app import run_convert, run_validate


def _ids(layout):
    out = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str):
                out.add(node["id"])
            for v in node.values():
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif hasattr(node, "to_plotly_json"):  # dash 3+/4 component objects
            walk(node.to_plotly_json())

    walk(layout)
    return out


def test_build_app_components():
    app = build_app()
    ids = _ids(app.layout)
    need = {"in-path", "in-meta", "in-nc", "in-dtype", "in-fmt", "in-rebin",
            "in-rebin-n", "in-cal-m", "in-cal-q", "btn-validate", "btn-convert",
            "download", "out-status", "out-report", "out-meta", "out-cal"}
    assert need <= ids


def test_run_validate_report(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    rep = run_validate(str(p), None, 16, "uint32")
    assert rep["ok"] and rep["format"] == "xml"
    assert rep["n_events"] == N_EVENTS
    assert rep["max_channel"] == 12
    assert rep["metadata"]["known_calibration"]["m"] == 1.5
    # missing file raises (file-level error), not ok=False
    try:
        run_validate(str(tmp_path / "nope.txt"), None, 16, "uint32")
        assert False, "expected exception"
    except Exception:
        pass


def test_run_convert_h5_roundtrip(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    data, name, summary = run_convert(str(p), None, 16, "uint32", None, None, "h5")
    assert name == "a.h5" and "calibrato" in summary
    with h5py.File(_io.BytesIO(data)) as f:
        assert int(f["img"][()].sum()) == N_EVENTS
        assert f.attrs["calibration_m"] == 1.5  # applied from XML when cal=None
        assert f["energy"].shape == (16,)
        assert json.loads(f.attrs["metadata_json"])["calibration"]["provenance"] == "xml"


def test_run_convert_npz_rebin_explicit_cal(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    data, name, summary = run_convert(str(p), None, 16, "uint16", (2, "sum"),
                                      {"m": 0.5, "q": 0.0, "provenance": "user"}, "npz")
    assert name == "a.npz"
    z = np.load(_io.BytesIO(data))
    assert z["img"].shape == (2, 3, 8)
    assert z["img"].dtype == np.uint32  # rebin sum output is uint32 by contract
    assert int(z["img"].sum()) == N_EVENTS  # rebin sum preserves totals
    cal = json.loads(json.loads(z["attrs"][()])["metadata_json"])
    assert cal["calibration"]["provenance"] == "user"
    assert cal["transforms"][0]["type"] == "rebin"
    z.close()