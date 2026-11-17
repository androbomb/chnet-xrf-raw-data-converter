"""xrf-raw-to-h5 UI: la CLI grafica per convert_file (M5).

upload | load from link | path_to_file + un input per parametro di
convert_file -> Convert -> Download file. Template grafico dash-xrf-visualizer
(DARKLY, accent #4196B4). Embeddabile in Jupyter:
app.run(jupyter_mode="inline") — vedi example.ipynb.
"""
from __future__ import annotations

import base64
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, dcc, html, no_update

from ..io import convert_file

ACCENT = "#4196B4"
_ACCENT_BTN = {
    "--bs-btn-bg": ACCENT,
    "--bs-btn-border-color": ACCENT,
    "--bs-btn-hover-bg": "#35789B",
    "--bs-btn-hover-border-color": "#35789B",
    "--bs-btn-active-bg": "#35789B",
    "--bs-btn-active-border-color": "#35789B",
}
# Carica gli upload e gli output default: deve sopravvivere tra Convert e Download.
_WORKDIR = Path(tempfile.gettempdir()) / "xrfraw_ui"


def _alert(msg: str, color: str) -> dbc.Alert:
    return dbc.Alert(msg, color=color, is_open=True, className="mb-2")


def _field(label: str, control) -> dbc.Row:
    return dbc.Row([dbc.Col(dbc.Label(label, width="md"), md=4),
                    dbc.Col(control, md=8)], className="mb-1")


def run_convert(path, out_path, fmt, nc, dtype, meta, rebin_spec, rebin_to,
                cal, compress, overwrite) -> tuple[Path, str]:
    """Convert button core: convert_file in un file reale (Download lo legge).

    out_path vuoto -> _WORKDIR/<stem>_<nc>.<fmt>. Returns (path, summary).
    """
    t0 = time.monotonic()
    out = Path(out_path) if out_path else _WORKDIR / f"{Path(path).stem}_{nc}.{fmt}"
    out.parent.mkdir(parents=True, exist_ok=True)  # write_dataset fa rename atomico
    ds = convert_file(path, out, fmt=fmt, n_channels=int(nc or 16384), dtype=dtype,
                      metadata=meta, rebin_spec=rebin_spec, rebin_to=rebin_to,
                      cal=cal, compress=int(compress if compress is not None else 4),
                      overwrite=bool(overwrite))
    dt = time.monotonic() - t0
    note = "calibrato" if ds.energy is not None else "non calibrato"
    return out, (f"OK: {ds.img.shape} {ds.metadata['dtype']}, "
                 f"{ds.metadata['n_events']:,} eventi, {note}, "
                 f"{out.stat().st_size / 1e6:.1f} MB in {dt:.1f} s")


def build_app(src: str | Path | None = None) -> dash.Dash:
    """Dash app: la CLI grafica per convert_file.

    ``src`` (str o Path) precompila path_to_file (il notebook lo passa come
    dash-xrf-visualizer con build_app(cube)). Run with app.run(...) or
    app.run(jupyter_mode="inline") inside a notebook.
    """
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY],
                    suppress_callback_exceptions=True)
    app.title = "xrf-raw-to-h5"

    app.layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col([
                html.H3("xrf-raw-to-h5", style={"display": "inline-block", "margin-right": 12}),
                html.Span("— raw MA-XRF → HDF5/NPZ", style={"verticalAlign": "middle"}),
            ]),
        ]),
        dbc.Navbar(
            [dbc.NavbarBrand("convert_file: raw (.txt, formato A/B) → .h5 / .npz")],
            color=ACCENT,
        ),
        html.Br(),
        # --- caricamento file (template dash-xrf-visualizer): upload | link | path ---
        dbc.Row([
            dbc.Col(md=5, children=[
                dcc.Upload(
                    id="upload",
                    children=html.Div("Upload raw .txt (formato A o B, drag & drop or click)",
                                      style={"display": "inline-block", "width": "100%",
                                             "lineHeight": "50px", "border": "1px dashed #999",
                                             "textAlign": "center"}),
                    multiple=False,
                ),
            ]),
            dbc.Col(md=4, children=[
                dbc.Input(id="url", type="text",
                          placeholder="https://… (share/download link: ownCloud, nextCloud, Zenodo, …)",
                          style={"width": "100%"}),
            ]),
            dbc.Col(md=3, children=[
                dbc.Button("Load from link", id="load-url", n_clicks=0,
                           outline=True, color="info"),
            ]),
        ]),
        html.Div(id="load-msg", style={"color": "orange"}),
        _field("path_to_file",
               dcc.Input(id="in-path", type="text",
                          value=str(src) if src is not None else "",  # Path non e' JSON-serializzabile nel layout
                         placeholder="/path/to/scan.txt (oppure upload / load from link)")),
        html.Br(),
        html.B("Parametri convert_file"),
        _field("out_path (vuoto: temp/<stem>_<n_channels>.<fmt>)",
               dcc.Input(id="in-out", type="text",
                         placeholder="/path/to/out.h5")),
        dbc.Row([
            dbc.Col(_field("fmt",
                           dcc.Dropdown(id="in-fmt", value="h5",
                                        options=[{"label": v, "value": v}
                                                 for v in ("h5", "npz")])), md=4),
            dbc.Col(_field("n_channels (profondità ESATTA)",
                           dcc.Input(id="in-nc", type="number", value=16384, min=1)), md=4),
            dbc.Col(_field("dtype cubo",
                           dcc.Dropdown(id="in-dtype", value="uint32",
                                        options=[{"label": v, "value": v}
                                                 for v in ("uint32", "uint16",
                                                           "float32", "float64")])), md=4),
        ]),
        _field("metadata (path a JSON: griglia/calibrazione, formato B)",
               dcc.Input(id="in-meta", type="text", placeholder="meta.json (opzionale)")),
        dbc.Row([
            dbc.Col(_field("rebin size",
                           dcc.Input(id="in-rebin-n", type="number", value=2, min=2)), md=4),
            dbc.Col(_field("rebin how",
                           dcc.Dropdown(id="in-rebin-how", value="off",
                                        options=[{"label": v, "value": v}
                                                 for v in ("off", "sum", "mean")])), md=4),
            dbc.Col(_field("rebin_to (solo sum; mutually exclusive)",
                           dcc.Dropdown(id="in-rebin-to", value="off",
                                        options=[{"label": v, "value": v}
                                                 for v in ("off", "512", "1024", "2048",
                                                           "4096", "8192")])), md=4),
        ]),
        dbc.Row([
            dbc.Col(_field("cal m (keV/ch; vuoto: XML/esterna)",
                           dcc.Input(id="in-cal-m", type="number",
                                     placeholder="vuoto: usa XML/esterna")), md=4),
            dbc.Col(_field("cal q (keV)",
                           dcc.Input(id="in-cal-q", type="number",
                                     placeholder="vuoto: usa XML/esterna")), md=4),
            dbc.Col(_field("compress (gzip 0-9, 0=none)",
                           dcc.Input(id="in-compress", type="number", value=4, min=0, max=9)), md=4),
        ]),
        _field("overwrite (rifiuta di sovrascrivere se spento)",
               dcc.Checklist(id="in-overwrite",
                             options=[{"label": "overwrite", "value": "overwrite"}],
                             value=["overwrite"],
                             labelStyle={"color": "var(--bs-body-color)"})),
        dbc.Row([
            dbc.Button("Convert", id="btn-convert", color="primary", style=_ACCENT_BTN),
            dbc.Button("Download file", id="btn-download", color="primary", style=_ACCENT_BTN),
        ], className="mt-3 mb-2"),
        dcc.Download(id="download"),
        dbc.Alert(id="out-status", is_open=False),
        dcc.Store(id="file-store", data=None),
    ])

    @app.callback([Output("in-path", "value"), Output("load-msg", "children")],
                  [Input("upload", "contents"), Input("load-url", "n_clicks")],
                  [State("upload", "filename"), State("url", "value")],
                  prevent_initial_call=True)
    def _on_load(contents, n_url, filename, url):
        # Dispatch su triggered_id: i contatori n_clicks sono cumulativi.
        try:
            if ctx.triggered_id == "load-url":
                url = (url or "").strip()
                if not url:
                    return no_update, "Inserisci prima l'URL"
                name = Path(urllib.parse.urlparse(url).path).name or "raw.txt"
                _WORKDIR.mkdir(parents=True, exist_ok=True)
                dest = _WORKDIR / name
                with urllib.request.urlopen(url) as r:
                    dest.write_bytes(r.read())
            elif contents:
                _, b64 = contents.split(",", 1)
                _WORKDIR.mkdir(parents=True, exist_ok=True)
                dest = _WORKDIR / (Path(filename or "raw.txt").name)
                dest.write_bytes(base64.b64decode(b64))
            else:
                return no_update, no_update
        except Exception as e:
            return no_update, f"Caricamento fallito: {e}"
        return str(dest), f"Caricato {dest.name} -> path_to_file"

    @app.callback([Output("out-status", "children"), Output("file-store", "data")],
                  [Input("btn-convert", "n_clicks")],
                  [State("in-path", "value"), State("in-out", "value"),
                   State("in-fmt", "value"), State("in-nc", "value"),
                   State("in-dtype", "value"), State("in-meta", "value"),
                   State("in-rebin-n", "value"), State("in-rebin-how", "value"),
                   State("in-rebin-to", "value"), State("in-cal-m", "value"),
                   State("in-cal-q", "value"), State("in-compress", "value"),
                   State("in-overwrite", "value")],
                  prevent_initial_call=True)
    def _on_convert(_n, path, out_path, fmt, nc, dtype, meta, rn, how, rto,
                    m, q, compress, overwrite):
        path = (path or "").strip()
        if not path:
            return _alert("Indica il file raw: upload, load from link o path_to_file",
                          "warning"), no_update
        if not Path(path).is_file():
            return _alert(f"File non trovato: {path}", "danger"), no_update
        if (m in (None, "")) != (q in (None, "")):
            return _alert("Calibrazione: m e q servono entrambi (o entrambi vuoti)",
                          "warning"), no_update
        rebin_spec = (int(rn or 2), how) if how not in (None, "off") else None
        rebin_to = int(rto) if rto not in (None, "off") else None
        if rebin_spec and rebin_to:
            return _alert("rebin_spec e rebin_to sono mutuamente esclusivi",
                          "warning"), no_update
        cal = {"m": float(m), "q": float(q), "provenance": "user"} if m not in (None, "") else None
        try:
            out, summary = run_convert(path, (out_path or "").strip(), fmt, nc, dtype,
                                       (meta or "").strip() or None, rebin_spec,
                                       rebin_to, cal, compress,
                                       "overwrite" in (overwrite or []))
        except Exception as e:
            return _alert(f"Conversione fallita: {e}", "danger"), no_update
        return _alert(summary, "success"), {"path": str(out), "filename": out.name}

    @app.callback(Output("download", "contents"),
                  [Input("btn-download", "n_clicks")],
                  [State("file-store", "data")],
                  prevent_initial_call=True)
    def _on_download(_n, file):
        if not file:
            return no_update
        p = Path(file["path"])
        if not p.is_file():
            return no_update
        return dcc.send_bytes(p.read_bytes(), filename=file["filename"])

    return app