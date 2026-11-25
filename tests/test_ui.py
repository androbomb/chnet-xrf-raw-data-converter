"""UI: la CLI grafica per convert_file — headless (no server, no browser)."""
import json
from pathlib import Path

import h5py
import numpy as np
from plotly.utils import PlotlyJSONEncoder

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
            "btn-convert", "btn-download", "out-status"}
    assert need <= _ids(app.layout)
    # src precompila path_to_file (come build_app(cube) in dash-xrf-visualizer)
    assert _find(app.layout, "in-path")["value"] == "/tmp/a.txt"
    assert _find(app.layout, "in-overwrite")["value"] == ["overwrite"]
    # src come Path (case del notebook): il layout deve serializzarsi come in serving
    app_p = build_app(src=Path("/tmp/b.txt"))
    assert _find(app_p.layout, "in-path")["value"] == "/tmp/b.txt"
    json.dumps(app_p.layout.to_plotly_json(), cls=PlotlyJSONEncoder)


def test_run_convert_h5_roundtrip(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out, summary = run_convert(str(p), str(tmp_path / "o.h5"), "h5", 16, "uint32",
                               None, None, None, None, 4, True)
    assert out.name == "o.h5" and "calibrato" in summary
    with h5py.File(out) as f:
        assert int(f["img"][()].sum()) == N_EVENTS
        assert f.attrs["calibration_m"] == 1.5  # applied from XML when cal=None
        assert f["energy_axis"].shape == (16,)
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


def _update(app, outputs, inputs, state, changed):
    """POST /_dash-update-component: il percorso reale di un callback Dash (no browser)."""
    spec = [f"{o['id']}.{o['property']}" for o in outputs]
    # chiave come dash._utils.create_callback_id: singolo -> "id.prop", multi -> "..id.prop...id.prop.."
    out_key = spec[0] if len(spec) == 1 else ".." + "...".join(spec) + ".."
    # body Dash 4 (types.CallbackExecutionBody): output singolo -> target unico,
    # multi -> lista; una lista anche per un singolo fa 500 in _prepare_response
    out_body = outputs[0] if len(outputs) == 1 else outputs
    body = {
        "output": out_key,
        "outputs": out_body,
        "inputs": inputs,
        "changedPropIds": changed,
        "state": state,
    }
    r = app.server.test_client().post("/_dash-update-component", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()["response"]


def test_convert_callback_http_roundtrip(tmp_path):
    # E2E headless: click su Convert via HTTP (un solo callback, come Load)
    # -> file scritto + status OK. Doppio click coperto dal lock.
    import xrfraw.ui.app as uiapp
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out_h5 = tmp_path / "o.h5"
    app = build_app(src=str(p))
    state = [
        {"id": "in-path", "property": "value", "value": str(p)},
        {"id": "in-out", "property": "value", "value": str(out_h5)},
        {"id": "in-fmt", "property": "value", "value": "h5"},
        {"id": "in-nc", "property": "value", "value": "16"},
        {"id": "in-dtype", "property": "value", "value": "uint32"},
        {"id": "in-meta", "property": "value", "value": ""},
        {"id": "in-rebin-n", "property": "value", "value": ""},
        {"id": "in-rebin-how", "property": "value", "value": "off"},
        {"id": "in-rebin-to", "property": "value", "value": ""},  # vuoto = off: era il crash 500
        {"id": "in-cal-m", "property": "value", "value": ""},
        {"id": "in-cal-q", "property": "value", "value": ""},
        {"id": "in-compress", "property": "value", "value": "0"},
        {"id": "in-overwrite", "property": "value", "value": ["overwrite"]},
    ]
    resp = _update(app,
                   [{"id": "out-status", "property": "children"}],
                   [{"id": "btn-convert", "property": "n_clicks", "value": 1}],
                   state, ["btn-convert.n_clicks"])
    assert out_h5.is_file()
    assert "OK" in json.dumps(resp["out-status"]["children"])
    # doppio click: il tasto non viene piu' disabilitato, il lock risponde
    # "già in corso"
    uiapp._CONVERT_LOCK.acquire()
    try:
        resp = _update(app,
                       [{"id": "out-status", "property": "children"}],
                       [{"id": "btn-convert", "property": "n_clicks", "value": 2}],
                       state, ["btn-convert.n_clicks"])
        assert "già in corso" in json.dumps(resp["out-status"]["children"],
                                     ensure_ascii=False)
    finally:
        uiapp._CONVERT_LOCK.release()

def test_index_declares_light_color_scheme():
    # Forced dark mode del browser: i campi erano bianco-su-bianco
    # (valore presente ma invisibile). La pagina deve dichiarare light.
    app = build_app()
    html_text = app.server.test_client().get("/").get_data(as_text=True)
    assert "color-scheme:light" in html_text
    assert ".xrfraw-dd" in html_text  # dropdown allineati ai campi bianchi
    assert "background-color:#fff!important" in html_text


def test_download_route_serves_last_output(tmp_path):
    # Download è un link diretto /xrfraw-download: 404 esplicito senza output,
    # altrimenti attachment byte-identico all'ultimo convert (niente stato client).
    import xrfraw.ui.app as uiapp
    uiapp._LAST_OUT = None  # reset: i test precedenti lasciano un output globale
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    out_h5 = tmp_path / "o.h5"
    app = build_app(src=str(p))
    client = app.server.test_client()
    r = client.get("/xrfraw-download")
    assert r.status_code == 404
    state = [
        {"id": "in-path", "property": "value", "value": str(p)},
        {"id": "in-out", "property": "value", "value": str(out_h5)},
        {"id": "in-fmt", "property": "value", "value": "h5"},
        {"id": "in-nc", "property": "value", "value": "16"},
        {"id": "in-dtype", "property": "value", "value": "uint32"},
        {"id": "in-meta", "property": "value", "value": ""},
        {"id": "in-rebin-n", "property": "value", "value": ""},
        {"id": "in-rebin-how", "property": "value", "value": "off"},
        {"id": "in-rebin-to", "property": "value", "value": ""},
        {"id": "in-cal-m", "property": "value", "value": ""},
        {"id": "in-cal-q", "property": "value", "value": ""},
        {"id": "in-compress", "property": "value", "value": "0"},
        {"id": "in-overwrite", "property": "value", "value": ["overwrite"]},
    ]
    _update(app,
            [{"id": "out-status", "property": "children"}],
            [{"id": "btn-convert", "property": "n_clicks", "value": 1}],
            state, ["btn-convert.n_clicks"])
    r = client.get("/xrfraw-download")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("Content-Disposition", "")
    assert r.data == out_h5.read_bytes()
