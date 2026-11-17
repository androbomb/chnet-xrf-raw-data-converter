# raw-xrf-to-h5-opener-python — operational plan

Status: M3 (2026-11-17) — contratto kickstart assorbito e confermato
(N1-N4); reader (M1) + processing (M2) + io/CLI (M3) chiusi;
verifica file reali a M4.

## 1. Scope (KEEP / REMOVE / ADD / DEFER)

| item | decisione | perché |
| ---- | --------- | ------ |
| Reader raw formato A (XML+dati) | KEEP (ri-implantato, streaming 2-passate) | core; grammatica in data_format.md |
| Reader raw formato B (solo dati) | **ADD** | il legacy crasha (L1); è presente in data_example |
| `inspect_raw` (validazione pre-allocazione) | **ADD** | kickstart: validare prima di allocare il cubo |
| populate eventi → datacube | KEEP (ri-implantato, uint32, streaming) | core; fix L2, L9, L10 |
| Calibrazione energia | KEEP come **allegato** (`energy[i]=m·i+q`, conteggi element-identical) | contratto kickstart; fix L3, L4, L5 |
| Rebin | **niente automatico**; opzione esplicita (sum/mean) off di default | contratto kickstart; Q3 rifinito |
| Writer HDF5 | KEEP (esteso: assi, mask, channel, metadata_json) | core |
| Writer NPZ | **ADD** | schema NPZ/HDF5 comune |
| CLI batch | KEEP (loop semplice, niente pool) | fix L6, L12 |
| UI minimale (Dash, embeddabile in Jupyter) | **ADD — milestone tardiva** dopo il converter core | kickstart goal 6 + Q1 ("ma dopo") |
| `pandas` / `torch` / JAX | **REMOVE** | mai importati / N/A (L11) |
| PyPI / TestPyPI / push | **OUT** | vietato in questa fase (utente) |

## 2. API pubblica (entry points del kickstart)

```python
inspect_raw(path) -> dict
    # validazione in sola lettura: formato, griglia dichiarata/osservata,
    # max canale, memoria stimata, anomalie — nessuna allocazione del cubo
read_raw(path, *, n_channels=16384, dtype="uint32", metadata=None) -> Dataset
    # 2 passate streaming; griglia dichiarata (A) / inferita (B) / esterna
    # (metadati JSON); fuori-range → errore esplicito
with_calibration(ds, m, q, *, provenance) -> Dataset
    # allega energy[i] = m*i + q; i conteggi restano element-identical
write_dataset(ds, path, *, fmt="h5"|"npz") -> Path
    # schema output_schema.md; temp file + rename; no overwrite implicito
rebin(ds, size, how="sum"|"mean") -> Dataset
    # ESPLICITO, non di default, trasformativo (documentato in "transforms")
```

`Dataset` (dataclass): `img (NY,NX,NC)`, `channel (NC,)`, `x_axis`, `y_axis`,
`mask (NY,NX)`, `metadata` (dict), `format`, `source_file`, `n_events`,
`energy`, `calibration_m/q`, `calibrated`.

## 3. Layout (definitivo)

```
/workspace/exchange/xrf-raw-converter/
├── src/xrfraw/
│   ├── __init__.py        # version; no side effects
│   ├── data/              # reader A/B 2-passate + metadati + validazione
│   ├── processing.py      # populate / with_calibration / rebin (NumPy puro)
│   ├── io.py              # writer NPZ + HDF5 (schema comune)
│   ├── cli.py             # CLI: file singolo + batch
│   └── ui/                # UI minimale Dash (M5, dopo il core)
├── tests/                 # pytest: sintetici, invarianze, round-trip
├── deploy/                # ricetta backend (uv verificata; altre NOT TESTED)
├── .github/workflows/     # ci.yml (M6, UNVERIFIED — no push)
├── pyproject.toml         # hatchling, src layout, uv; deps: numpy, h5py, tqdm
├── (9 documenti)
└── original_code/         # gitignored, sola lettura, MAI importato
```

## 4. Milestones

- **M0 (chiuso)**: audit in sola lettura + 9 documenti v2 (contratto
  kickstart) + misure streaming (eventi, max canale, griglie, anomalie).
- **M1 (chiuso)**: scheletro `src/xrfraw` + layer dati: reader A/B 2-passate, metadati
  XML (escape+parse), inferenza griglia formato B, metadati esterni + regole
  conflitto, `inspect_raw`, errori fuori-range. Test su mini file sintetici.
  Accettazione: F1 (sintetici), F6a, F11.
- **M2 (chiuso)**: processing: `populate` (conservazione), `with_calibration`
  (element-identical), `rebin` esplicito (sum/mean), opzione uint16 +
  pre-check overflow. Test: casi a mano, conservazione, orientamento,
  canali finali. Accettazione: F2, F3, F4, F9, F10.
- **M3 (chiuso)**: `io.py` (schema output_schema.md) + round-trip + CLI
  (`--format h5|npz`, `--n-channels`, `--dtype`, `--metadata FILE.json`,
  `--rebin N sum|mean`, no-overwrite) + exit codes + tqdm.
  Accettazione: F5, F6b, F12.
- **M4**: pipeline completa sui 2 file reali (99/284 MB, single-thread):
  wall time, RAM peak, incroci (eventi == sum(img); max cella → overflow
  uint16; calibrazione su mappa11 → vettore energia), report anomalie
  (77/1 pixel non acquisiti). Accettazione: F1, F7.
- **M5**: UI minimale Dash (DARKLY, accent #4196B4, embeddabile via
  JupyterDash): carica TXT/XML, mostra validazione/metadati, imposta/
  conferma calibrazione, sceglie formato, scarica output. Test headless.
- **M6**: packaging (hatchling wheel/sdist locale), deploy recipe con status
  (uv verificata; docker/apptainer/wslc NOT TESTED — no daemon qui),
  `ci.yml` preparato ma UNVERIFIED (no push), **niente** PyPI/TestPyPI.

## 5. Criteri di accettazione

- **F1**: i 2 file reali parsati senza errori; eventi == 19 825 090 /
  56 661 209; `sum(img) == n_events`; pixel non acquisiti 77 (mappa11) /
  1 (Ragazzo) con `mask=False`. — M1 (sintetici) / M4 (reali).
- **F2**: `sum(img) == n_events` dopo `populate` (sintetico + reale). — M2/M4.
- **F3**: `with_calibration`: `img` element-identical (bitwise);
  `energy[i] == m*i + q`; caso a mano su 10 canali. — M2.
- **F4**: `rebin` esplicito: `sum` conserva i totali; `mean` ==
  somma/larghezza bin (split uniforme); trasformazione dichiarata in
  `transforms`. — M2.
- **F5**: round-trip NPZ/HDF5: array + `metadata_json` identici; leggibili
  con `h5py` / `np.load`. — M3.
- **F6**: (a) formato B senza metadati → cubo in canali grezzi + griglia
  inferita, nessun crash; (b) formato B + JSON esterni == formato A con gli
  stessi metadati (coppia sintetica). — M1/M3.
- **F7**: file reale 284 MB: single-thread, RAM peak + wall time riportati.
  Nota: con uint32 e NC=16384 il solo cubo pesa ~1.9 GB (215·145·16384·4);
  opzione `--dtype uint16` → ~0.95 GB. Target < 1.5 GB raggiungibile solo con
  uint16. — log M4.
- **F8**: nessun import torch/pandas/jax in `src/`; hatchling builda
  wheel+sdist. — M6.
- **F9**: canali finali: NC=16384 > max osservato →
  `img[..., max_obs+1:]` tutti zero e presenti (niente troncamento). — M2.
- **F10**: orientamento: sintetico asimmetrico (NY≠NX) → un evento in
  (x=2, y=5, c=3) finisce in `img[5, 2, 3]` (y, x, channel). — M2.
- **F11**: coordinate fuori-range / riga malformed → errore esplicito con
  numero di riga (niente skip silenziosi). — M1.
- **F12**: conflitto XML vs metadati esterni → errore esplicito con i due
  valori; niente overwrite. — M3.

## 6. Document ownership

Come AGENTS.md §7: operational_plan (decisioni), to_do (stato + log),
timeline (storico append-only), data_format/output_schema/scientific_notes
(convenzioni e schema), legacy_audit (problemi + differenze intenzionali),
README (stato onesto: verified vs UNVERIFIED).

## 7. Deferred / fuori scope

- JAX, Jupyter inline (oltre l'embedding dell'UI), GPU.
- Pubblicazione PyPI/TestPyPI, git push → vietati in questa fase.
- Parallelismo batch multi-processo (pool legacy) → DEFER (loop semplice).

## 8. Domande risolte (Q1-Q8, risposte utente 2026-11-17)

- **Q1** converter CLI/package ora; UI nuova (usabile in exemple.ipynb) dopo. ✓
- **Q2** calibrazione conservativa → **raffinata dal kickstart**: conteggi
  element-identical, allegato `energy[i]=m·i+q`, niente crop (D3).
- **Q3** rebin opzionale → **raffinato dal kickstart**: niente automatico;
  opzione esplicita off di default (D4, N3).
- **Q4** dtype come opzione utente, default uint32. ✓ (D5)
- **Q5** formato B: griglia inferita + metadati esterni opzionali. ✓ (D1)
- **Q6** import `xrfraw`, dist `raw-xrf-to-h5-opener-python`. ✓
- **Q7** unità µm/µm/s come default, da chiedere all'utente. ✓ (→ N4)
- **Q8** M4: pipeline completa sui 2 file reali, single-thread. ✓

## 9. Domande aperte (N1-N4, in attesa di conferma)

| # | Domanda | raccomandazione |
| - | ------- | --------------- |
| N1 | NC strumentale: confermare **16384** come default? (suggerito dal legacy L7; max canale osservato 15902/15999) | 16384 |
| N2 | UI minimale: milestone tardiva **di questo repo** (M5) o progetto separato? | M5 di questo repo |
| N3 | Rebin: mantenere l'opzione esplicita (sum/mean, off di default) o rimuoverla del tutto? | mantenerla |
| N4 | Unità: X/Y = **µm**, Velocity = **µm/s**? (l'XML non le dichiara) | sì, marcate `assumed` finché non confermato |

Nota minore (M1): anomalie di struttura = `missing_row`/`missing_column`
(77 px mappa11, 1 px Ragazzo) + 1 `dangling_x_marker` a fine file per file
(mappa11: X(5000); Ragazzo: X(219000); entrambi 0 eventi). Comportamento
reader: "anomalia riportata + mask=False", niente correzione silenziosa
(data_format.md §3-4).
