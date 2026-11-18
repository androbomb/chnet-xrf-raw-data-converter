"""xrf-raw-to-h5 UI: la CLI grafica per convert_file (M5).

upload | load from link | path_to_file + un input per parametro di
convert_file -> Convert -> Download file. Template grafico dash-xrf-visualizer
(DARKLY, accent #4196B4). Embeddabile in Jupyter:
app.run(jupyter_mode="inline") — vedi example.ipynb.
"""
from __future__ import annotations

import base64
import hashlib
import os
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, dcc, html, no_update
from flask import Response, send_file

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
# Ultimo output scritto da run_convert: Download lo serve via link diretto,
# senza passare per lo stato client-side (che in iframe può andare perso).
_LAST_OUT: Path | None = None
# Upload > ~48 MB raw: il browser deve base64-il file in memoria (crash/gray screen);
# i file grandi passano per path_to_file (già sul disco).
_MAX_UPLOAD_B64 = 64 * 1024 * 1024
# Un solo Convert alla volta: i doppio-click non duplicano la conversione.
_CONVERT_LOCK = threading.Lock()


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
                      cal=cal, compress=int(compress if compress not in (None, "") else 4),
                      overwrite=bool(overwrite))
    dt = time.monotonic() - t0
    note = "calibrato" if ds.energy is not None else "non calibrato"
    global _LAST_OUT
    _LAST_OUT = out
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
    # "Forced dark mode" del browser (es. Chrome auto-dark) inverte testo e
    # sfondi: i campi diventavano bianco-su-bianco (valore presente ma invisibile).
    # color-scheme:light disattiva l'inversione; i colori espliciti sono scudo.
    # .xrfraw-dd: i dropdown (react-select) hanno styling interno proprio —
    # li si allinea ai campi bianchi con un override scoped.
    app.index_string = app.index_string.replace(
        "{%css%}",
        "{%css%}\n<style>"
        ":root{color-scheme:light}"
        "input,select{background-color:#fff!important;color:#212529!important}"
        ".xrfraw-dd,.xrfraw-dd *{background-color:#fff!important;color:#212529!important}"
        ".xrfraw-dd{border:1px solid #ccc!important}"
        "</style>")
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
        dcc.Loading([
        # --- caricamento file (template dash-xrf-visualizer): upload | link | path ---
        dbc.Row([
            dbc.Col(md=5, children=[
                dcc.Upload(
                    id="upload",
                    children=html.Div("Upload raw .txt (piccoli file; drag & drop or click)",
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
        _field("out_path (vuoto: <temp>/xrfraw_ui/<nome_file>_<n_channels>.<fmt>)",
               dcc.Input(id="in-out", type="text",
                         placeholder="/path/to/out.h5")),
        dbc.Row([
            dbc.Col(_field("fmt",
                           dcc.Dropdown(id="in-fmt", value="h5", className="xrfraw-dd",
                                        options=[{"label": v, "value": v}
                                                 for v in ("h5", "npz")])), md=4),
            dbc.Col(_field("n_channels (profondità ESATTA)",
                           dcc.Input(id="in-nc", type="number", value=16384, min=1)), md=4),
            dbc.Col(_field("dtype cubo",
                           dcc.Dropdown(id="in-dtype", value="uint32", className="xrfraw-dd",
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
                           dcc.Dropdown(id="in-rebin-how", value="off", className="xrfraw-dd",
                                        options=[{"label": v, "value": v}
                                                 for v in ("off", "sum", "mean")])), md=4),
            dbc.Col(_field("rebin_to (solo sum; mutually exclusive)",
                           dcc.Dropdown(id="in-rebin-to", value="off", className="xrfraw-dd",
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
            # Link diretto (non callback): lo stato client-side in iframe può
            # andare perso e il Download moriva in silenzio; qui il browser
            # scarica il file dall'ultimo Convert riuscito, sempre.
            html.A(dbc.Button("Download file", id="btn-download", color="primary",
                              style=_ACCENT_BTN),
                   href="/xrfraw-download",
                   style={"textDecoration": "none", "display": "inline-block"}),
        ], className="mt-3 mb-2"),
        dbc.Alert(id="out-status", is_open=False),
        # --- tooltip: cosa fa ogni campo (hover) ---
        dbc.Tooltip("Percorso del file raw (formato A: XML+dati; formato B: solo dati). "
                    "Oppure usa upload o Load from link sopra. Per file grandi usa SEMPRE "
                    "il percorso, non l'upload.", target="in-path", placement="top"),
        dbc.Tooltip("Dove scrivere l'output. Se vuoto: <temp>/xrfraw_ui/<nome_file>_<n_channels>.<fmt> "
                    "(poi Download file).", target="in-out", placement="top"),
        dbc.Tooltip("Formato output: h5 (HDF5) o npz.", target="in-fmt", placement="top"),
        dbc.Tooltip("Profondità ESATTA di lettura: l'output è (y, x, n_channels). "
                    "Default strumentale 16384; errore se un canale la supera.",
                    target="in-nc", placement="top"),
        dbc.Tooltip("Tipo dati del cubo. float32/float64 per consumer che richiedono "
                    "floating (es. dash-xrf-visualizer).", target="in-dtype", placement="top"),
        dbc.Tooltip("Percorso a un JSON con griglia/calibrazione (servire al formato B). "
                    "Vuoto: griglia inferita, calibrazione dall'XML (formato A) o assente.",
                    target="in-meta", placement="top"),
        dbc.Tooltip("Raggruppamento dei canali (k, how): es. (2, sum) = somma coppie di "
                    "canali. off = disattivo. Mutuo esclusivo con rebin_to.",
                    target="in-rebin-n", placement="top"),
        dbc.Tooltip("Modalità rebin: off | sum | mean.", target="in-rebin-how", placement="top"),
        dbc.Tooltip("Riduce il cubo a profondità target (somma per gruppi, totali "
                    "conservati): 512…8192. Solo sum. Mutuo esclusivo con rebin size/how.",
                    target="in-rebin-to", placement="top"),
        dbc.Tooltip("Pendenza calibrazione energia (keV/ch). Vuota: usa quella "
                    "dichiarata nell'XML (formato A) o nel metadata JSON.",
                    target="in-cal-m", placement="top"),
        dbc.Tooltip("Intercetta calibrazione energia (keV). Serve con m.",
                    target="in-cal-q", placement="top"),
        dbc.Tooltip("Compressione gzip dell'output: 0 (nessuna) … 9.", target="in-compress",
                    placement="top"),
        dbc.Tooltip("Spento: il writer rifiuta di sovrascrivere un file esistente.",
                    target="in-overwrite", placement="top"),
        dbc.Tooltip("Lancia convert_file. Durante la conversione appare lo spinner "
                    "(i file grandi richiedono minuti); un secondo click "
                    "risponde 'già in corso'.",
                    target="btn-convert", placement="top"),
        dbc.Tooltip("Scarica l'output dell'ultimo Convert riuscito.", target="btn-download",
                    placement="top"),
        dbc.Tooltip("Percorso di un share/download link (ownCloud, nextCloud, Zenodo, …). "
                    "Per file grandi preferisci path_to_file.", target="load-url",
                    placement="top"),
        ], type="circle"),
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
                name = Path(urllib.parse.urlparse(url).path).name or "download"
                if "." not in name:
                    # link stile ownCloud ("/download"): nome unico per URL,
                    # altrimenti ogni caricamento sovrascrive il file precedente
                    name = f"download_{hashlib.sha1(url.encode()).hexdigest()[:8]}.txt"
                _WORKDIR.mkdir(parents=True, exist_ok=True)
                dest = _WORKDIR / name
                part = dest.with_suffix(dest.suffix + ".part")
                with urllib.request.urlopen(url) as r:
                    part.write_bytes(r.read())
                os.replace(part, dest)  # atomico: un download interrotto non lascia un file tronco
            elif contents:
                _, b64 = contents.split(",", 1)
                if len(b64) > _MAX_UPLOAD_B64:
                    return no_update, ("File troppo grande per l'upload nel browser "
                                       "(limite ~48 MB): usa path_to_file")
                _WORKDIR.mkdir(parents=True, exist_ok=True)
                dest = _WORKDIR / (Path(filename or "raw.txt").name)
                dest.write_bytes(base64.b64decode(b64))
            else:
                return no_update, no_update
        except Exception as e:
            return no_update, f"Caricamento fallito: {e}"
        # Il messaggio e' autocontenuto (path + size): il valore di in-path non
        # sempre si vede in iframe notebook, qui invece si vede sempre.
        return str(dest), f"Caricato: {dest} ({dest.stat().st_size / 1e6:.0f} MB)"

    # UN solo callback (stessa forma di Load, che funziona anche col proxy
    # iframe instabile): due callback sullo stesso click = due round-trip,
    # e basta uno perso per sembrare un tasto morto. Lo spinner "in corso"
    # lo dà dcc.Loading (lato client, zero round-trip); il doppio click è
    # coperto da _CONVERT_LOCK. Il tasto non viene mai disabilitato: non
    # esiste stato che possa restare bloccato.
    @app.callback(Output("out-status", "children"),
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
                          "warning")
        if not Path(path).is_file():
            return _alert(f"File non trovato: {path}", "danger")
        if not _CONVERT_LOCK.acquire(blocking=False):
            return _alert("Una conversione è già in corso", "warning")
        try:
            # i campi vuoti arrivano come "" (placeholder != value): parsing difensivo,
            # ogni errore è un alert rosso, non un 500 che rompe la UI
            if (m in (None, "")) != (q in (None, "")):
                raise ValueError("calibrazione: m e q servono entrambi (o entrambi vuoti)")
            rebin_spec = (int(rn or 2), how) if (how or "off") not in (None, "off") else None
            rebin_to = int(rto) if (rto or "").strip() not in ("", "off") else None
            if rebin_spec and rebin_to:
                raise ValueError("rebin_spec e rebin_to sono mutuamente esclusivi")
            cal = {"m": float(m), "q": float(q), "provenance": "user"} if m not in (None, "") else None
            out, summary = run_convert(path, (out_path or "").strip(), fmt, nc, dtype,
                                       (meta or "").strip() or None, rebin_spec,
                                       rebin_to, cal, compress,
                                       "overwrite" in (overwrite or []))
        except Exception as e:
            return _alert(f"Conversione fallita: {e}", "danger")
        finally:
            _CONVERT_LOCK.release()
        return _alert(summary, "success")

    @app.server.route("/xrfraw-download")
    def _xrfraw_download():
        # Download = link diretto all'ultimo output di run_convert: niente
        # stato client-side, niente base64 nel callback.
        if _LAST_OUT is None or not _LAST_OUT.is_file():
            return Response("Nessun output da scaricare: esegui prima un Convert riuscito.",
                            mimetype="text/plain; charset=utf-8", status=404)
        return send_file(_LAST_OUT, as_attachment=True, download_name=_LAST_OUT.name)

    return app