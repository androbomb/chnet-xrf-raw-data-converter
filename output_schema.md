# Output schema — NPZ / HDF5 / OME-TIFF comuni

Status: M3 (2026-11-17) — reader A/B + processing + writer NPZ/HDF5
(`io.write_dataset`) + CLI implementati e testati (43 fast + 2 slow). OME
(2026-11-25) — export/lettura OME-TIFF/BigTIFF (`ome.py`) integrato e testato.
Principio:
l'output è la rappresentazione **fedele** (lossless) del raw: i conteggi
non vengono mai modificati dalla calibrazione (element-identical); niente
auto-rebinning né auto energy-crop. NPZ, HDF5 e OME-TIFF portano gli stessi
campi logici.

## Pipeline core

```
raw (A/B) → inspect_raw      → report validazione (nessuna allocazione)
         → read_raw          → Dataset: img (NY,NX,NC) + assi + mask + metadati
         → with_calibration  → + energy[i] = m·i + q   (conteggi intatti)
         → write_dataset     → .h5 / .npz / .ome.tif
```

Opzionale, esplicito, non di default, **trasformativo** (documentato nei
metadati di output): `rebin(size, how=sum|mean)`.
`rebin_to(n_new)` mappa il cubo a una profondità target (potenza di 2).

## Campi comuni

| campo | forma/tipo | significato |
| ----- | ---------- | ----------- |
| `img` | (NY, NX, NC) uint32 | conteggi eventi per pixel e canale; ordine **(y, x, channel)** (float64 dopo `rebin(mean)` — dichiarato in `transforms`) |
| `channel` | (NC,) uint32 | indici ADC originali 0..NC−1 — sempre presente |
| `energy` | (NC,) float64 | **solo se calibrato**: `energy[i] = m·i + q` |
| `x_axis` | (NX,) float64 | coordinate spaziali X (unità dai metadati) |
| `y_axis` | (NY,) float64 | coordinate spaziali Y |
| `mask` | (NY, NX) bool | maschera di acquisizione: `False` = non acquisito (zero, non misurato) |
| `metadata_json` | str (JSON) | vedi sotto — no pickle |

## Contenuto di `metadata_json`

- `schema_version` (int) — versione di questo documento.
- `format`: "xml" \| "data-only".
- `source_file`: basename del file sorgente.
- `n_channels` (int, profondità ESATTA del cubo — l'output è sempre
  (NY, NX, n_channels)), `dtype` (str), `n_events` (int).
- `units`: `{x: "µm", y: "µm", velocity: "µm/s"}` + `units_status:
  "assumed"\|"confirmed"` (l'XML non le dichiara — conferma N4).
- `grid`: `{x_min, x_max, x_step, y_min, y_max, y_step,
  source: "xml"\|"inferred"\|"external"}`.
- `known_calibration`: `{m, q, provenance}` — solo se m/q noti ma non
  applicati (dopo `read_raw`, senza `with_calibration`).
- `calibration`: `{m, q, provenance: "xml"|"external"|"user"}` — solo se
  calibrato (dopo `with_calibration`).
- `raw`: tutti i campi XML (A) o i campi esterni (B).
- `anomalies`: lista delle anomalie di validazione (dangling marker, colonne
  mancanti, …) — nessuna viene corretta silenziosamente. Un canale che
  supera `n_channels` NON è un'anomalia: errore esplicito al read
  (`XRFReadError`, con suggerimento della potenza di 2 successiva);
  `inspect_raw` lo riporta come `channel_exceeds_n_channels` senza raise.
- `transforms`: lista delle trasformazioni applicate post-read — vuota nella
  pipeline core (vedi §Rebin).
- `software`, `created_utc`.

## Rebin (esplicito, opzionale)

`rebin(ds, size, how="sum")` — sull'asse canale, **mai automatico**
(`rebin_to(ds, n_new)` è la variante a profondità target, vedi sotto):

- Gruppi uniformi: richiede `n_channels % size == 0` (errore esplicito, mai
  troncamento silenzioso).
- `sum`: conserva i totali; accumulo esatto in uint64 (safe-accumulation
  numpy), output uint32; errore esplicito se un gruppo supera 4 294 967 295.
- `mean`: media per gruppo (semantica legacy `AdaptiveAvgPool1d`), output
  float64; i totali diventano `n_events/size`.
- Asse `channel` in output = primo indice di ogni gruppo (`i·size`); se
  calibrato, `energy` segue gli stessi indici e m/q vengono aggiornati
  (`m *= size`, `q` invariato), così asse energia e metadati restano
  coerenti. `n_events` resta il conteggio fisico degli eventi.
- Dichiarato in `transforms` come
  `{type: "rebin", size, how, n_channels_from, n_channels_to}`.

`rebin_to(ds, n_new)` — mappa (NY, NX, N) → (NY, NX, n_new) con n_new in
{512, 1024, 2048, 4096, 8192} (potenze di 2); solo `sum` (i totali sono
sempre conservati); richiede `n_new < N` e `N % n_new == 0`; m/q aggiornati
come in `rebin` (size = N/n_new). È il modo esplicito per ridurre la
profondità del cubo (es. 16384 → 2048) senza perdere eventi.

## HDF5 (`<nome>.h5`)

- dataset: `/img`, `/channel`, `/energy` (se calibrato), `/x_axis`, `/y_axis`,
  `/mask`.
- attributi su `/`: `format`, `source_file`, `n_channels`, `dtype`,
  `n_events`, `metadata_json` (str), `calibration_m`, `calibration_q`
  (se calibrato), `software`, `created_utc`, `compression` (livello gzip
  0-9, 0 = none).
- Compressione: tutti i dataset sono gzip (livello 4 di default, parametro
  `compress` di `write_dataset`); `compress=0` scrive senza compressione.

## NPZ (`<nome>.npz`)

Array: `img`, `channel`, `energy` (se calibrato), `x_axis`, `y_axis`, `mask`,
più `attrs` (stringa JSON con gli stessi campi scalari dell'HDF5).

## OME-TIFF / OME-BigTIFF (`<nome>.ome.tif`)

Contenitore multidimensionale scientifico via `tifffile`: il datacube è
(C, Y, X) con **un IFD per canale spettrale** (`DimensionOrder="CYX"`,
`DimensionType="C"`). I canali XRF sono bande OME `<Channel>` con
`SamplesPerPixel="1"` — mai interpretati come campioni RGB.

- Lossless: dtype preservato (uint16/uint32/float32/float64 → OME Type
  uint16/uint32/float/double), valori identici al round-trip (testati).
  Compressione lossless zlib (`compress` 0-9, default 4; 0 = nessuna).
- BigTIFF: `write_ome` passa a BigTIFF se i dati superano 4 GB (limite
  classic TIFF); esplicito con `bigtiff=True/False`.
- OME-XML (ImageDescription dell'IFD 0, namespace 2016-06):
  - `Pixels.PhysicalSizeX/Y` = passo di griglia, unità = metadata.units
    (campi spaziali OME standard).
  - `MapAnnotation` con chiave namespaced e versionata `urn:xrfraw:v1`:
    - `meta` = `metadata_json` completo (griglia, unità, calibrazione,
      campi raw, anomalie, transforms, provenienza);
    - `attrs` = attributi scalari (source_file, n_events, software,
      created_utc, compression);
    - `mask` = byte bool compressi zlib+base64.
  - Il non-ASCII dell'XML va in numeric character references (i tag stringa
    TIFF sono 7-bit ASCII).
- Lettura: `xrfraw.read_ome(path)` ricostruisce `img` in (Y, X, C) e tutti
  i metadati; se calibrato, `energy` è ri-derivata da m/q
  (`energy = m·channel + q`).
- Interoperabilità: lettura verificata con `tifffile`; qualsiasi reader OME
  vede un'immagine C-stack valida. **La calibrazione custom vive nella
  MapAnnotation `urn:xrfraw:v1` e non è automaticamente comprensibile a
  software XRF generici**: l'interoperabilità della calibrazione con
  Bio-Formats non è verificata e non va dichiarata senza test.

## Convenzioni

- Nome output: basename dell'input + estensione; directory via CLI.
- **Nessun overwrite implicito**: file esistente → errore esplicito (salvo
  flag esplicito). Scrittura su file temporaneo + rename a successo
  (niente output parziali).
- Pixel non acquisiti: zero + `mask=False` (distinguibili da uno zero misurato).
- Output non calibrato: asse `channel` + (se m/q noti ma non applicati)
  m/q nei metadati — chi legge calcola `E = m·ch + q`.
- Semantica e invarianze: `scientific_notes.md` §8-14.
