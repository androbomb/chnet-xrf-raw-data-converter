# raw-xrf-to-h5-opener-python

Convertitore raw MA-XRF (Fi MA-XRF, INFN-CHNet) → NPZ/HDF5 comuni: datacube
di eventi per pixel in ordine **(y, x, channel)**, indici canale ADC, assi
spaziali, maschera di acquisizione, metadati serializzati, con calibrazione
energia come **allegato** (`energy[i] = m·i + q`, conteggi element-identical).

**Status: M2 (2026-11-17) — reader A/B + processing
(`with_calibration`, `rebin`) implementati e testati (32 fast + slow suite
sui file reali); writer NPZ/HDF5 e CLI a M3.**

## Cosa fa

- Legge le due varianti di file raw (XML+dati e solo-dati) — grammatica in
  `data_format.md`; valida prima di allocare il cubo (`inspect_raw`).
- Costruisce il datacube (Y, X, NC) uint32 (opzione uint16) con profondità
  canali **esplicita** (default strumentale 16384 — UNVERIFIED), conservando
  i canali finali a zero.
- Calibrazione energia come allegato: i conteggi non cambiano (il legacy ne
  perdeva silenziosamente — `legacy_audit.md` L4).
- Nessun auto-rebinning / auto energy-crop (contratto kickstart); rebin
  esplicito (sum/mean) solo su richiesta.
- Scrive `.h5` o `.npz` con lo stesso schema logico — `output_schema.md`.
- UI minimale Dash (DARKLY, accent #4196B4, embeddabile in Jupyter) prevista
  in milestone tardiva (M5), dopo il converter core.

## Setup (uv)

```bash
uv sync
.venv/bin/python -m pytest -q
```

## Uso (reader/processing: API attuale; writer/CLI: M3)

CLI:

```bash
xrf-raw-to-h5 FILE_OR_DIR -o OUT_DIR --format h5|npz \
    [--n-channels N] [--dtype uint32|uint16] [--metadata meta.json] \
    [--rebin N sum|mean]
```

API:

```python
from xrfraw import inspect_raw, read_raw, with_calibration, rebin
from xrfraw.io import write_dataset  # M3

report = inspect_raw("mappa11.txt")            # validazione, nessuna allocazione
ds = read_raw("mappa11.txt")                   # (NY, NX, NC) + assi + mask + metadati
ds = with_calibration(ds, 0.00259259, -0.0355556, provenance="xml")  # conteggi intatti
ds = rebin(ds, 2)                              # opzionale, esplicito (sum|mean)
write_dataset(ds, "mappa11.h5", fmt="h5")      # M3
```

## Verified vs UNVERIFIED

- **Verified (M0)**: grammatica degli input sui 2 file di esempio
  (`data_format.md` §4, 5 passate streaming: eventi 19 825 090 / 56 661 209,
  max canale 15902/15999, griglie, anomalie localizzate); audit del legacy
  (`legacy_audit.md`); crash legacy sul formato B riprodotto (ParseError,
  2026-11-17).
- **UNVERIFIED**: writer/CLI (M3); NC strumentale 16384 (N1); unità µm/µm/s
  (N4); deploy docker/apptainer/wslc (NOT TESTED, no daemon in questo
  ambiente); CI (M6, no push).

## Layout e repo map

Vedi `operational_plan.md` §3.

| path | ruolo |
| ---- | ----- |
| `AGENTS.md` | regole agent (leggere prima di tutto) |
| `operational_plan.md` | decisioni, milestone, criteri di accettazione, domande aperte |
| `legacy_audit.md` | problemi legacy verificati + differenze intenzionali |
| `data_format.md` | grammatica degli input (formati A/B, stream eventi, NC) |
| `output_schema.md` | schema comune NPZ/HDF5 |
| `scientific_notes.md` | calibrazione, conteggi, assi, precisione |
| `to_do.md` | Now/Next/Later/Blocked + verification log |
| `timeline.md` | storico append-only datato |
| `deploy/` | ricetta per backend con status verificato / NOT TESTED |
| `original_code/` | legacy di riferimento (gitignored, sola lettura) |
| `data_example/` | 2 file di esempio (gitignored, mai caricati in massa) |
