"""xrf-raw-to-h5 minimal UI (M5).

Carica raw .txt (formato A/B), validazione, imposta/conferma calibrazione,
sceglie formato, scarica l'output. DARKLY, accent #4196B4.
Embeddabile in Jupyter: app.run(jupyter_mode="inline") — vedi example.ipynb.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, no_update

from ..data import inspect_raw
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


def _alert(msg: str, color: str) -> dbc.Alert:
    return dbc.Alert(msg, color=color, is_open=True, className="mb-2")


def _json(obj) -> str | None:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str) if obj is not None else None


def run_validate(path: str, meta: str | None, nc: int, dtype: str) -> dict:
    """inspect_raw report (no cube allocated); raises if the file is unreadable."""
    return inspect_raw(path, n_channels=int(nc or 16384), dtype=dtype,
                       metadata=(meta or "").strip() or None)


def run_convert(path: str, meta: str | None, nc: int, dtype: str,
                rebin: tuple[int, str] | None, cal: dict | None,
                fmt: str) -> tuple[bytes, str, str]:
    """Convert button core: convert_file to a temp file.

    Returns (bytes, filename, status summary).
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file non trovato: {path}")
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"out.{fmt}"
        ds = convert_file(p, out, fmt=fmt, n_channels=int(nc or 16384), dtype=dtype,
                          metadata=(meta or "").strip() or None, rebin_spec=rebin, cal=cal)
        data = out.read_bytes()
    dt = time.monotonic() - t0
    note = "calibrato" if ds.energy is not None else "non calibrato"
    return (data, f"{p.stem}.{fmt}",
            f"OK: {ds.img.shape} {ds.metadata['dtype']}, {ds.metadata['n_events']:,} eventi, "
            f"{note}, {len(data) / 1e6:.0f} MB in {dt:.1f} s")


def _field(label: str, control) -> dbc.Row:
    return dbc.Row([dbc.Col(dbc.Label(label, width="md"), md=4),
                    dbc.Col(control, md=8)], className="mb-1")


def build_app() -> dash.Dash:
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY],
                    suppress_callback_exceptions=True)
    app.title = "xrf-raw-to-h5"

    app.layout = dbc.Container([
        html.H4("xrf-raw-to-h5 — raw MA-XRF → HDF5/NPZ", style={"color": ACCENT}),
        _field("File raw (.txt, formato A o B)",
               dcc.Input(id="in-path", type="text", placeholder="/path/to/scan.txt")),
        _field("Metadati JSON esterni (opzionale)",
               dcc.Input(id="in-meta", type="text", placeholder="meta.json")),
        dbc.Row([
            dbc.Col(_field("n_channels",
                           dcc.Input(id="in-nc", type="number", value=16384, min=1)), md=6),
            dbc.Col(_field("dtype cubo",
                           dcc.Dropdown(id="in-dtype", value="uint32",
                                        options=[{"label": v, "value": v}
                                                 for v in ("uint32", "uint16")])), md=6),
        ]),
        dbc.Row([
            dbc.Col(_field("rebin canale",
                           dcc.Dropdown(id="in-rebin", value="off",
                                        options=[{"label": v, "value": v}
                                                 for v in ("off", "sum", "mean")])), md=4),
            dbc.Col(_field("rebin size",
                           dcc.Input(id="in-rebin-n", type="number", value=2, min=2)), md=4),
            dbc.Col(_field("formato output",
                           dcc.Dropdown(id="in-fmt", value="h5",
                                        options=[{"label": v, "value": v}
                                                 for v in ("h5", "npz")])), md=4),
        ]),
        dbc.Row([
            dbc.Col(_field("cal m (keV/ch)",
                           dcc.Input(id="in-cal-m", type="number",
                                     placeholder="vuoto: usa XML/esterni")), md=6),
            dbc.Col(_field("cal q (keV)",
                           dcc.Input(id="in-cal-q", type="number",
                                     placeholder="vuoto: usa XML/esterni")), md=6),
        ]),
        dbc.Row([
            dbc.Button("Valida", id="btn-validate", color="primary", style=_ACCENT_BTN),
            dbc.Button("Converti e scarica", id="btn-convert", color="primary",
                       style=_ACCENT_BTN),
        ], className="mt-3 mb-2"),
        dcc.Download(id="download"),
        dbc.Alert(id="out-status", is_open=False),
        dbc.Card([dbc.CardHeader("Report validazione (inspect_raw)"),
                  dbc.CardBody(html.Code(id="out-report", style={"maxHeight": "30vh", "overflowY": "auto", "display": "block"}))]),
        dbc.Card([dbc.CardHeader("Metadati del file"),
                  dbc.CardBody(html.Code(id="out-meta", style={"maxHeight": "30vh", "overflowY": "auto", "display": "block"}))]),
        dbc.Card([dbc.CardHeader("Calibrazione nota (applicata in conversione se m/q vuoti)"),
                  dbc.CardBody(html.Code(id="out-cal"))]),
    ], fluid=True)

    @app.callback([Output("out-status", "children"), Output("out-report", "children"),
                   Output("out-meta", "children"), Output("out-cal", "children")],
                  [Input("btn-validate", "n_clicks")],
                  [State("in-path", "value"), State("in-meta", "value"),
                   State("in-nc", "value"), State("in-dtype", "value")],
                  prevent_initial_call=True)
    def _on_validate(_n, path, meta, nc, dtype):
        path = (path or "").strip()
        if not path:
            return _alert("Inserisci il percorso del file raw .txt", "warning"), None, None, None
        try:
            rep = run_validate(path, meta, nc, dtype)
        except Exception as e:
            return _alert(f"Validazione fallita: {e}", "danger"), None, None, None
        if not rep.get("ok"):
            return (_alert(f"File non valido: {rep.get('error')}", "danger"),
                    _json(rep), None, None)
        cal = (rep.get("metadata") or {}).get("known_calibration")
        cal_txt = (f"m = {cal['m']}, q = {cal['q']} (provenance: {cal['provenance']})"
                   if cal else "nessuna — output non calibrato se m/q lasciati vuoti")
        return (_alert(f"OK: formato {rep['format']}, {rep['n_events']:,} eventi, "
                       f"{rep['n_pixels']} px ({rep['n_pixels_acquired']} acquisiti), "
                       f"max channel {rep['max_channel']}", "success"),
                _json(rep), _json(rep.get("metadata")), cal_txt)

    @app.callback([Output("out-status", "children"), Output("download", "contents")],
                  [Input("btn-convert", "n_clicks")],
                  [State("in-path", "value"), State("in-meta", "value"),
                   State("in-nc", "value"), State("in-dtype", "value"),
                   State("in-rebin", "value"), State("in-rebin-n", "value"),
                   State("in-cal-m", "value"), State("in-cal-q", "value"),
                   State("in-fmt", "value")],
                  prevent_initial_call=True)
    def _on_convert(_n, path, meta, nc, dtype, how, rn, m, q, fmt):
        path = (path or "").strip()
        if not path:
            return _alert("Inserisci il percorso del file raw .txt", "warning"), no_update
        if (m in (None, "")) != (q in (None, "")):
            return _alert("Calibrazione: m e q servono entrambi (o entrambi vuoti)",
                          "warning"), no_update
        rebin_spec = (int(rn or 2), how) if how not in (None, "off") else None
        cal = {"m": float(m), "q": float(q), "provenance": "user"} if m not in (None, "") else None
        try:
            data, name, summary = run_convert(path, meta, nc, dtype, rebin_spec, cal, fmt)
        except Exception as e:
            return _alert(f"Conversione fallita: {e}", "danger"), no_update
        return _alert(summary, "success"), dcc.send_bytes(data, filename=name)

    return app