# raw-xrf-to-h5-opener-python

Convertitore raw MA-XRF (Fi MA-XRF, INFN-CHNet) → NPZ/HDF5 comuni: datacube
(X, Y, C) di eventi per pixel, assi coordinati, metadati, con calibrazione
energia opzionale (`E = m·ch + q`) e rebin opzionale.

**Status: M0 completato (2026-11-17) — piano in attesa di approvazione;
nessun codice nuovo ancora** (`src/your_app/` è lo scheletro di template e
verrà sostituito da `src/xrfraw/` a M1).

## Cosa fa

- Legge le due varianti di file raw (XML+dati e solo-dati) —
  grammatica in `data_format.md`.
- Costruisce il datacube (istogrammi di eventi per pixel), uint32.
- Calibrazione energia opzionale: binning conservativo (i conteggi non si
  perdono; il legacy ne perdeva silenziosamente — `legacy_audit.md` L4).
- Rebin opzionale: default `sum` (conserva i totali), `mean` per
  compatibilità legacy.
- Scrive `.h5` o `.npz` con lo stesso schema logico — `output_schema.md`.

## Setup (uv, path primario — da verificare a M1)

```bash
uv sync
.venv/bin/python -m pytest -q
```

Pip: `pip install raw-xrf-to-h5-opener-python` (dopo M5).

## Uso (target M3 — firme esatte a M1/M2)

CLI:

```bash
xrf-raw-to-h5 FILE_OR_DIR -o OUT_DIR --format h5|npz \
    [--rebin none|sum|mean --rebin-size N] [--E-range LO HI] [--metadata meta.json]
```

API:

```python
from xrfraw.data import read_raw          # formato A o B, streaming
from xrfraw.processing import populate, calibrate, rebin
from xrfraw.io import write_h5, write_npz

raw = read_raw("mappa11.txt")             # eventi + metadati
cube = populate(raw)                      # (NX, NY, NC0) uint32
cube = calibrate(cube, raw.m, raw.q)      # opzionale
write_h5("mappa11.h5", cube, raw)
```

## Verified vs UNVERIFIED

- **Verified (M0)**: grammatica degli input sui 2 file di esempio
  (`data_format.md` §4, misurazioni a flusso); audit del legacy
  (`legacy_audit.md`); crash legacy sul formato B riprodotto (ParseError,
  stdlib ET, 2026-11-17).
- **UNVERIFIED**: tutto il codice (non esiste ancora); deploy
  docker/apptainer/wslc (NOT TESTED, no daemon in questo ambiente); CI
  (preparata a M5, no push); unità µm di X/Y (Q7).

## Layout e repo map

Vedi `operational_plan.md` §2.

| path | ruolo |
| ---- | ----- |
| `AGENTS.md` | regole agent (leggere prima di tutto) |
| `operational_plan.md` | decisioni, milestone, criteri di accettazione, domande aperte |
| `legacy_audit.md` | problemi legacy verificati + differenze intenzionali |
| `data_format.md` | grammatica degli input (formati A/B, stream eventi) |
| `output_schema.md` | schema comune NPZ/HDF5 |
| `scientific_notes.md` | calibrazione, conteggi, assi, precisione |
| `to_do.md` | Now/Next/Later/Blocked + verification log |
| `timeline.md` | storico append-only datato |
| `deploy/` | ricetta per backend con status verificato / NOT TESTED |
| `original_code/` | legacy di riferimento (gitignored, sola lettura) |
| `data_example/` | 2 file di esempio (gitignored, mai caricati in massa) |