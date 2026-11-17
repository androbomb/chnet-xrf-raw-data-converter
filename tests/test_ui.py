"""UI: la CLI grafica per convert_file — headless (no server, no browser)."""
import json

import h5py
import numpy as np

from _synthetic import GRID32, N_EVENTS, PIXELS, write_format_a
from xrfraw.ui import build_app
from xrfraw.ui.app import run_convert


def _find(layout, wanted):
    """First component with ``id == wanted`` as a plain dict."""

    def walk(node):
        if hasattr(node, "to_plotly_json"):  # dash 4: to_plotly_json è pigro
            return walk(node.to_plotly_json())
        if isinstance(node, dict):
            if node.get("id") == wanted:
                return node
            for v in node.values():
                found = walk(v)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = walk(v)
                if found is not None:
                    return found
        return None

    return walk(layout)


def _ids(layout):
    out = set()

    def walk(node):
        if hasattr(node, "to_plotly_json"):
            walk(node.to_plotly_json())
        elif isinstance(node, dict):
            if isinstance(node.get("id"), str):
                out.add(node["id"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(layout)
    return out


def test_build_app_components():
    app = build_app(src="/tmp/a.txt")
    need = {"upload", "url", "load-url", "in-path", "in-out", "in-fmt", "in-nc",
            "in-dtype", "in-meta", "in-rebin-n", "in-rebin-how", "in-rebin-to",
            "in-cal-m", "in-cal-q", "in-compress", "in-overwrite",
            "btn-convert", "btn-download", "download", "out-status", "file-store"}
    assert need <= _ids(app.layout)
    # src precompila path_to_file (come build_app(cube) in dash-xrf-visualizer)
    assert _find(app.layout, "in-path")["value"] == "/tmp/a.txt"
    assert _find(app.layout, "in-overwrite")["value"] == ["overwrite"]


def test_run_convert_h5_roundtrip(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out, summary = run_convert(str(p), str(tmp_path / "o.h5"), "h5", 16, "uint32",
                               None, None, None, None, 4, True)
    assert out.name == "o.h5" and "calibrato" in summary
    with h5py.File(out) as f:
        assert int(f["img"][()].sum()) == N_EVENTS
        assert f.attrs["calibration_m"] == 1.5  # applied from XML when cal=None
        assert f["energy"].shape == (16,)
        assert json.loads(f.attrs["metadata_json"])["calibration"]["provenance"] == "xml"


def test_run_convert_npz_rebin_explicit_cal(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out, summary = run_convert(str(p), str(tmp_path / "o.npz"), "npz", 16, "uint16",
                               None, (2, "sum"), None,
                               {"m": 0.5, "q": 0.0, "provenance": "user"}, 4, True)
    assert out.name == "o.npz"
    z = np.load(out)
    assert z["img"].shape == (2, 3, 8)
    assert z["img"].dtype == np.uint32  # rebin sum output is uint32 by contract
    assert int(z["img"].sum()) == N_EVENTS  # rebin sum preserves totals
    cal = json.loads(json.loads(z["attrs"][()])["metadata_json"])
    assert cal["calibration"]["provenance"] == "user"
    assert cal["transforms"][0]["type"] == "rebin"
    z.close()


def test_run_convert_default_outpath(tmp_path, monkeypatch):
    # out_path vuoto -> temp dir (non tmp_path del test): il file deve esistere
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out, _ = run_convert(str(p), "", "h5", 16, "uint32", None, None, None, None, 0, True)
    assert out.is_file() and out.name == f"a_16.h5" and out.parent.name == "xrfraw_ui"