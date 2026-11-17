# raw-xrf-to-h5-opener-python

Convertitore raw MA-XRF (Fi MA-XRF, INFN-CHNet) → NPZ/HDF5 comuni: datacube
di eventi per pixel in ordine **(y, x, channel)**, indici canale ADC, assi
spaziali, maschera di acquisizione, metadati serializzati, con calibrazione
energia come **allegato** (`energy[i] = m·i + q`, conteggi element-identical).

**Status: M6 (2026-11-17) — converter + UI completi (49 test: 47 fast +
2 slow); packaging locale verificato (wheel in venv pulito); CI workflow
pushato ma esecuzione UNVERIFIED (repo privato); PyPI/TestPyPI fuori
contratto. Tutte le milestone chiuse.**

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
- UI minimale Dash (DARKLY, accent #4196B4, embeddabile in Jupyter):
  `from xrfraw.ui import build_app` (sezione UI).

## Setup (uv)

```bash
uv sync
.venv/bin/python -m pytest -q
```

## Uso

CLI (exit code 0 ok / 1 errori di conversione / 2 usage; nessuna overwrite
silenziosa — `--overwrite` per sostituire):

```bash
xrf-raw-to-h5 FILE_OR_DIR -o OUT_DIR --format h5|npz \
    [--n-channels N] [--dtype uint32|uint16] [--metadata meta.json] \
    [--rebin N sum|mean] [--overwrite]
```

Se m/q sono noti (XML o JSON esterni) la calibrazione viene applicata come
allegato (`with_calibration`); altrimenti l'output è non calibrato (asse
`channel`, nessun `energy`).

API:

```python
from xrfraw import inspect_raw, read_raw, with_calibration, rebin
from xrfraw.io import write_dataset

report = inspect_raw("mappa11.txt")            # validazione, nessuna allocazione
ds = read_raw("mappa11.txt")                   # (NY, NX, NC) + assi + mask + metadati
ds = with_calibration(ds, 0.00259259, -0.0355556, provenance="xml")  # conteggi intatti
ds = rebin(ds, 2)                              # opzionale, esplicito (sum|mean)
write_dataset(ds, "mappa11.h5", fmt="h5")      # o fmt="npz"; overwrite=False di default
```

UI minimale (Dash, DARKLY, accent #4196B4):

```python
from xrfraw.ui import build_app

app = build_app()
app.run()                          # browser
app.run(jupyter_mode="inline")     # dentro un notebook (vedi example.ipynb)
```

Carica raw (formato A o B), mostra report validazione + metadati +
calibrazione nota, permette di impostare m/q esplicitamente (provenance
`user`), sceglie dtype/rebin/formato e scarica l'output `.h5`/`.npz`.

## Verified vs UNVERIFIED

- **Verified (M0)**: grammatica degli input sui 2 file di esempio
  (`data_format.md` §4, 5 passate streaming: eventi 19 825 090 / 56 661 209,
  max canale 15902/15999, griglie, anomalie localizzate); audit del legacy
  (`legacy_audit.md`); crash legacy sul formato B riprodotto (ParseError,
  2026-11-17).
- **UNVERIFIED**: NC strumentale 16384 (N1); unità µm/µm/s (N4); deploy
  docker/apptainer/wslc (NOT TESTED, no daemon in questo ambiente);
  esecuzione CI (workflow pushato, repo privato — da verificare su
  GitHub Actions).

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
| `example.ipynb` | notebook demo: CLI + UI embeddata (Jupyter) |
| `deploy/` | ricetta per backend con status verificato / NOT TESTED |
| `original_code/` | legacy di riferimento (gitignored, sola lettura) |
| `data_example/` | 2 file di esempio (gitignored, mai caricati in massa) |
