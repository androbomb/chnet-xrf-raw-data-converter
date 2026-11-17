# raw-xrf-to-h5-opener-python — operational plan

Status: M0 completo (2026-11-17) — **piano in attesa di approvazione**.

## 1. Scope (KEEP / REMOVE / ADD / DEFER)

| item | decisione | perché |
| ---- | --------- | ------ |
| Reader raw formato A (XML+dati) | KEEP (ri-implantato) | core; grammatica in data_format.md |
| Reader raw formato B (solo dati) | **ADD** | il legacy crasha (L1); è presente in data_example |
| populate eventi → datacube | KEEP (ri-implantato, uint32, streaming) | core; fix L2, L9, L10 |
| Calibrazione energia | KEEP (ri-implantata, conservativa) | core; fix L3, L4, L5 |
| Rebin | KEEP (sum/mean, NumPy) | core; drop torch (L11), fix L7 |
| Writer HDF5 | KEEP (esteso con attributi/assi) | core |
| Writer NPZ | **ADD** | schema NPZ/HDF5 comune richiesto |
| CLI batch | KEEP (loop semplice, niente pool) | fix L6, L12 |
| `pandas` | **REMOVE** | mai importato (L11) |
| `torch` | **REMOVE** | solo per AdaptiveAvgPool1d (L11) |
| JAX / Dash / UI / Jupyter | **DEFER** (fuori scope) | questo repo è il converter; l'UI vive in dash-xrf-visualizer (Q1) |
| PyPI / TestPyPI / push | **OUT** | vietato in questa fase (utente) |

## 2. Layout (definitivo)

```
/workspace/exchange/xrf-raw-converter/
├── src/xrfraw/
│   ├── __init__.py        # version; no side effects
│   ├── data/              # reader formato A/B (streaming) + metadati + validazione
│   ├── processing/        # populate / calibrate / rebin — NumPy puro, no I/O
│   ├── io.py              # writer NPZ + HDF5 (schema comune)
│   └── cli.py             # CLI: file singolo + batch, --metadata, --rebin, --E-range
├── tests/                 # pytest: reader su file sintetici, invarianze, round-trip
├── deploy/                # ricetta per backend (uv verificata; altre NOT TESTED)
├── .github/workflows/     # ci.yml (M5, UNVERIFIED — no push)
├── pyproject.toml         # hatchling, src layout, uv; deps: numpy, h5py, tqdm
├── AGENTS.md / operational_plan.md / legacy_audit.md / data_format.md
├── output_schema.md / scientific_notes.md / README.md / to_do.md / timeline.md
└── original_code/         # gitignored, sola lettura, MAI importato
```

## 3. Technical boundaries

- `data/`: legge solo i file input; nessun altro I/O, niente torch/jax/dash.
  I path dei dati sono variabili di runtime (argomenti CLI), mai hardcoded.
- `processing/`: funzioni NumPy pure; uint32 per il cubo, float64 per
  griglie energia e aritmetica (AGENTS.md §4).
- `io.py`: unico modulo che scrive output.
- Dipendenze runtime: `numpy`, `h5py`, `tqdm`. Dev: `pytest`. Niente
  torch/pandas/JAX/Dash (elementi di template non applicabili a un converter).

## 4. Milestones

- **M0 (chiuso)**: audit in sola lettura + 9 documenti.
- **M1**: scheletro `src/xrfraw` + layer dati (reader A/B streaming,
  container metadati, validazione alla trust boundary) + test su mini file
  sintetici. Accettazione: F1 (su sintetici), F6a.
- **M2**: processing: `populate` (conservazione conteggi), `calibrate`
  (`searchsorted`, conservativa, E_range crop opzionale), `rebin` (sum/mean).
  Test: casi piccoli a mano + proprietà di conservazione + test
  compatibilità-semantica-legacy (modo mean) su sintetico. Accettazione: F2-F4.
- **M3**: `io.py` (NPZ+HDF5, attributi/assi per output_schema.md) + round-trip
  + CLI (`--format h5|npz`, `--rebin none|sum|mean --rebin-size N`,
  `--E-range LO HI`, `--metadata FILE.json`) + tqdm. Accettazione: F5, F6b.
- **M4**: verifica sui 2 file reali (99/284 MB, single-thread): wall time,
  RAM peak, incroci (totale eventi == somma cubo; max cella → rischio
  overflow uint16 legacy; pipeline completa con calibrazione su mappa11).
  Esito nel verification log + README (verified). Accettazione: F1, F7, Q8.
- **M5**: packaging (build wheel/sdist hatchling locale), deploy recipe con
  status (uv: verificata; docker/apptainer/wslc: NOT TESTED — no daemon qui),
  `ci.yml` preparato ma UNVERIFIED (no push), **niente** PyPI/TestPyPI.
  Accettazione: F8.

## 5. Criteri di accettazione

- **F1**: entrambi i file reali parsati senza errori; eventi == 19 825 090 /
  56 661 209 (baseline awk, data_format.md §4). — test M4.
- **F2**: `sum(datacube) == numero eventi` dopo `populate`. — test M2.
- **F3**: `calibrate`: `sum(out) == sum(in)` dentro E_range; asse energia
  monotona; caso 10 canali a mano riproduce E = m·ch + q. — test M2.
- **F4**: `rebin` sum: somma conservata; mean: == somma/larghezza bin
  (split uniforme) e parità di semantica con il legacy su sintetico. — test M2.
- **F5**: round-trip NPZ/HDF5: array e attributi identici; leggibili con
  `h5py` / `np.load`. — test M3.
- **F6**: (a) formato B senza metadati → cubo in canali grezzi + griglia
  inferita, nessun crash; (b) formato B + `--metadata` JSON == risultato del
  formato A con gli stessi metadati (coppia sintetica). — test M2/M3.
- **F7**: file reale 284 MB: single-thread, RAM peak < 1.5 GB, wall time
  riportato (target indicativo < 120 s). — log M4.
- **F8**: nessun import torch/pandas/jax/dash in `src/`; `hatchling` builda
  wheel+sdist. — M5.

## 6. Document ownership

Come AGENTS.md §7: operational_plan (decisioni), to_do (stato + log),
timeline (storico append-only), data_format/output_schema/scientific_notes
(convenzioni e schema), legacy_audit (problemi + differenze intenzionali),
README (stato onesto: verified vs UNVERIFIED).

## 7. Deferred / fuori scope

- UI Dash/Plotly, JAX, Jupyter inline → progetto separato (Q1).
- Pubblicazione PyPI/TestPyPI, git push → vietati in questa fase.
- Parallelismo batch multi-processo (pool legacy) → DEFER (loop semplice).
- GPU → non applicabile (solo NumPy).

## 8. Domande aperte (in attesa di conferma)

| # | Domanda | raccomandazione |
| - | ------- | --------------- |
| Q1 | Repo = solo converter (niente UI/JAX/Jupyter)? | sì |
| Q2 | Calibrazione: E_range default = nessuna crop; binning conservativo (somma nei bin)? | sì |
| Q3 | Rebin: default `sum`, opzione `mean` per compatibilità legacy? | sì |
| Q4 | Datacube uint32 (vs uint16 legacy)? | sì |
| Q5 | Formato B: griglia inferita dagli header + metadati esterni opzionali (JSON) per la calibrazione? | sì |
| Q6 | Nomi: import `xrfraw`, dist PyPI `raw-xrf-to-h5-opener-python`? | sì |
| Q7 | Unità assi X/Y = µm (e Velocity µm/s)? l'XML non le dichiara | da conferma |
| Q8 | M4: esecuzione pipeline completa sui 2 file reali (99/284 MB, single-thread)? | sì |