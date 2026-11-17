# Output schema — NPZ / HDF5 comuni

Status: M0 — proposta, in attesa di approvazione. NPZ e HDF5 portano gli
stessi campi logici; l'output è il datacube **dopo i passi scelti** dalla
pipeline, con gli attributi che documentano esattamente cosa è stato fatto.

## Pipeline

```
eventi → (NX, NY, NC0) uint32   [populate]
       → (NX, NY, NC1) uint32   [calibrate, opzionale]
       → (NX, NY, NCout)        [rebin, opzionale]  uint32 (sum) | float64 (mean)
```

## HDF5 (`<nome>.h5`)

- dataset `/xrf` — cubo finale.
- dataset `/x_axis_um` — float64[NX] = xmin + i·step_x.
- dataset `/y_axis_um` — float64[NY].
- dataset `/channel_index` (uint32[NC0]) se non calibrato, altrimenti
  `/energy_keV` (float64[NC], griglia uniforme usata per il binning).
- attributi su `/`:

| attributo | tipo | contenuto |
| --------- | ---- | --------- |
| `format` | str | "xml" \| "data-only" |
| `source_file` | str | basename del file sorgente |
| `metadata_json` | str | tutti i campi XML (A) o metadati esterni (B) |
| `calibration_m`, `calibration_q` | f64 | assenti se non disponibile |
| `E_range` | str (JSON) | assente se nessuna crop |
| `original_depth` | int | NC0 |
| `rebin_mode` | str | "none" \| "sum" \| "mean" |
| `rebin_size` | int | NCout (0 se "none") |
| `software` | str | "xrfraw <version>" |
| `created_utc` | str | ISO 8601 |

## NPZ (`<nome>.npz`)

Array: `xrf`, `x_axis_um`, `y_axis_um`, `channel_index` **o** `energy_keV`,
più `attrs` (stringa JSON con gli stessi campi scalari dell'HDF5).

## Convenzioni

- Nome output: basename dell'input + estensione; directory di output via CLI.
- Pixel mancanti: zero sulla griglia completa (come legacy).
- Asse energia non calibrato: si conservano l'asse canale + m/q negli
  attributi (chi legge calcola E = m·ch + q); la griglia uniforme esiste solo
  se si applica la calibrazione.
- Semantica dei passi: `scientific_notes.md` §9 (conservazione dei conteggi).
