# Output schema — NPZ / HDF5 / OME-TIFF / FITS

Status: M3 (2026-11-17) — reader A/B + processing + writer NPZ/HDF5
(`io.write_dataset`) + CLI implementati e testati (43 fast + 2 slow). OME
(2026-11-25) — export/lettura OME-TIFF/BigTIFF (`ome.py`) integrato e testato.
FITS (2026-11-26) — export/lettura FITS multi-extension (`fits.py`, astropy
extra opzionale) integrato e testato. Principio:
l'output è la rappresentazione **fedele** (lossless) del raw: i conteggi
non vengono mai modificati dalla calibrazione (element-identical); niente
auto-rebinning né auto energy-crop. NPZ, HDF5, OME-TIFF e FITS portano gli
stessi campi logici.

## Pipeline core

```
raw (A/B) → inspect_raw      → report validazione (nessuna allocazione)
         → read_raw          → Dataset: img (NY,NX,NC) + assi + mask + metadati
         → with_calibration  → + energy[i] = m·i + q   (conteggi intatti)
         → write_dataset     → .h5 / .npz / .ome.tif / .fits
```

Opzionale, esplicito, non di default, **trasformativo** (documentato nei
metadati di output): `rebin(size, how=sum|mean)`.
`rebin_to(n_new)` mappa il cubo a una profondità target (potenza di 2).

## Campi comuni

| campo | forma/tipo | significato |
| ----- | ---------- | ----------- |
| `img` | (NY, NX, NC) uint32 | conteggi eventi per pixel e canale; ordine **(y, x, channel)** (float64 dopo `rebin(mean)` — dichiarato in `transforms`) |
| `channel` | (NC,) uint32 | indici ADC originali 0..NC−1 — sempre presente |
| `energy_axis` | (NC,) float64 | **solo se calibrato**: energia rappresentativa per canale; post-rebin: media delle energie dei bin aggregati (bin-mean), cioè `m_rebinned·i + q_rebinned` (per R=1 coincide con `m·i + q`) |
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
  calibrato (dopo `with_calibration`); dopo un rebin gli originali restano
  invariati e si affiancano `rebin_factor` (R totale), `rebin_uniform`
  (bool), `m_rebinned = R·m₀`, `q_rebinned = q₀ + (R−1)/2·m₀`,
  `convention: "bin-mean"`, `energy_unit: "keV"`.
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
- Asse `channel` in output = primo indice di ogni gruppo (`i·size`).
  `n_events` resta il conteggio fisico degli eventi.
- Calibrazione (se calibrato): gli originali `m₀`/`q₀` restano invariati in
  `calibration`; la calibrazione post-rebin è conservata come
  `m_rebinned = R·m₀`, `q_rebinned = q₀ + (R−1)/2·m₀` — energia rappresentativa
  = media delle energie del bin ("bin-mean", keV; per R=1 coincide con
  l'originale). `energy_axis` contiene le medie per gruppo (float64).
  `rebin` accetta solo gruppi uniformi (altrimenti errore esplicito): la
  formula lineare vale solo nel caso uniforme; un eventuale rebin non
  uniforme porterebbe `rebin_uniform: false` e la calibrazione va letta solo
  dal vettore `energy_axis`.
- Dichiarato in `transforms` come
  `{type: "rebin", size, how, n_channels_from, n_channels_to}`.

`rebin_to(ds, n_new)` — mappa (NY, NX, N) → (NY, NX, n_new) con n_new in
{512, 1024, 2048, 4096, 8192} (potenze di 2); solo `sum` (i totali sono
sempre conservati); richiede `n_new < N` e `N % n_new == 0`; m/q aggiornati
come in `rebin` (size = N/n_new). È il modo esplicito per ridurre la
profondità del cubo (es. 16384 → 2048) senza perdere eventi.

## HDF5 (`<nome>.h5`)

- dataset: `/img`, `/channel`, `/energy_axis` (se calibrato), `/x_axis`, `/y_axis`,
  `/mask`.
- attributi su `/`: `format`, `source_file`, `n_channels`, `dtype`,
  `n_events`, `metadata_json` (str), `calibration_m`, `calibration_q`
  (effettivi, post-rebin) + `calibration_m_original`,
  `calibration_q_original`, `rebin_factor`, `energy_unit` ("keV"),
  `bin_convention` ("bin-mean") (se calibrato), `software`, `created_utc`,
  `compression` (livello gzip 0-9, 0 = none).
- Compressione: tutti i dataset sono gzip (livello 4 di default, parametro
  `compress` di `write_dataset`); `compress=0` scrive senza compressione.

## NPZ (`<nome>.npz`)

Array: `img`, `channel`, `energy_axis` (se calibrato), `x_axis`, `y_axis`, `mask`,
più `attrs` (stringa JSON con gli stessi campi scalari dell'HDF5).

## OME-TIFF / OME-BigTIFF (`<nome>.ome.tif`)

Contenitore multidimensionale scientifico via `tifffile`: il datacube è
(C, Y, X) con **un IFD per canale spettrale** (`SizeC` = canali,
`DimensionOrder="XYZCT"`, `SizeZ=SizeT=1`). I canali XRF sono bande OME
`<Channel>` con `SamplesPerPixel="1"` — mai interpretati come campioni RGB.
I piani oltre l'IFD 0 NON portano metadati shaped (`shaped=False`):
`tifffile` deve vedere **un'unica serie OME CYX** (`tif.is_ome` e non
`tif.is_shaped`, `len(tif.series) == 1`, `axes == "CYX"` — testato).
L'OME-XML è **validato contro lo XSD ufficiale OME 2016-06** (conforme).

- Lossless: dtype preservato (uint16/uint32/float32/float64 → OME Type
  uint16/uint32/float/double), valori identici al round-trip (testati).
  Compressione lossless zlib (`compress` 0-9, default 4; 0 = nessuna).
- BigTIFF: `write_ome` passa a BigTIFF se i dati superano 4 GB (limite
  classic TIFF); esplicito con `bigtiff=True/False`.
- OME-XML (ImageDescription dell'IFD 0, namespace 2016-06, conforme allo
  XSD ufficiale — validato):
  - `Pixels` con `SizeX/SizeY/SizeC` + `PhysicalSizeX/Y` = passo di griglia,
    unità = metadata.units (campi spaziali OME standard).
  - `MapAnnotation` (sotto `OME.StructuredAnnotations`, collegata con
    `Image.AnnotationRef`; `ID="Annotation:0"`, `Namespace="urn:xrfraw:v1"`)
    con coppie chiave/valore `<M K="...">`:
    - `meta` = `metadata_json` completo (griglia, unità, calibrazione,
      campi raw, anomalie, transforms, provenienza);
    - `attrs` = attributi scalari (source_file, n_events, software,
      created_utc, compression) + se calibrato: `calibration_m`/
      `calibration_q` (effettivi, post-rebin), `calibration_m_original`/
      `calibration_q_original`, `rebin_factor`, `energy_unit` ("keV"),
      `bin_convention` ("bin-mean"), `energy_axis`: asse per canale (float64,
       post-rebin, identico a `/energy_axis` di H5/NPZ);
    - `mask` = byte bool compressi zlib+base64.
  - Il non-ASCII dell'XML va in numeric character references (i tag stringa
    TIFF sono 7-bit ASCII).
- Lettura: `xrfraw.read_ome(path)` ricostruisce `img` in (Y, X, C) e tutti
  i metadati; `energy` viene presa dall'asse esplicito `energy_axis` in
  `attrs` se presente (file 0.1.1: chiave `energy`), altrimenti ri-derivata
  da m/q (`energy = m·channel + q`, file scritti prima dell'asse esplicito).
- Interoperabilità: lettura verificata con `tifffile`; qualsiasi reader OME
  vede un'immagine C-stack valida. **La calibrazione custom vive nella
  MapAnnotation `urn:xrfraw:v1` e non è automaticamente comprensibile a
  software XRF generici**: l'interoperabilità della calibrazione con
  Bio-Formats non è verificata e non va dichiarata senza test.

## FITS (`<nome>.fits`)

Contenitore multidimensionale astronomico via `astropy.io.fits` (dipendenza
opzionale: `pip install chnet-xrf-raw-data-converter[fits]`; senza astropy
l'errore è esplicito). Il datacube in memoria è **(C, Y, X)** — convenzione
FITS `NAXIS1=X, NAXIS2=Y, NAXIS3=C`; la lettura lo restituisce (Y, X, C)
come gli altri formati. Nessun rebinning: nessun aggregazione aggiuntiva.

- **PRIMARY** (`ImageHDU`, non compresso): i conteggi.
  - Lossless: dtype preservato. uint16/uint32 → `BITPIX=32` +
    `BSCALE=1` e `BZERO=2^15`/`BZERO=2^31` (convenzione FITS per interi
    unsigned; lossless incluso il sentinela 2^32−1). float32 →
    `BITPIX=-32` (FITS big-endian; alla lettura i float sono convertiti
    in endianness nativa, come gli altri reader). float64 non esiste in
    FITS: il cubo è scritto come float32 (documentato); il JSON metadata
    resta invariato e dichiara ancora `dtype: "float64"`. Ogni altro
    dtype → errore esplicito.
  - **WCS**: per i file calibrati, l'asse energetico sull'asse 3:
    `CTYPE3="ENERGY"`, `CRPIX3=1`, `CRVAL3=q_rebinned`,
    `CDELT3=m_rebinned`, `CUNIT3="keV"` (lineare, esatto: `rebin` accetta
    solo gruppi uniformi; post-rebin l'energia rappresentativa è bin-mean).
    Assi spaziali: `CTYPE1/2="X"/"Y"`, `CRPIX=1`, `CRVAL=0`,
    `CDELT1/2` = passo di griglia, `CUNIT1/2` = unità dei metadati
    ("µm" → `um`, forma ASCII standard FITS). File non calibrati:
    nessuna `CTYPE3` e nessuna extension ENERGY.
  - Provenienza minima: `OBJECT` (basename del sorgente),
    `INSTRUME="MA-XRF"`, `DATE` (UTC), `SOFTWARE` (xrfraw + versione).
- **XRF_META** (`BinTableHDU`, 1 riga, 1 colonna stringa `JSON`):
  `metadata_json` completo e versionato, identico a NPZ/HDF5/OME — senza
  troncamenti. Fonte canonica dei metadati: l'header porta solo
  informazioni standard/ridondanti, mai l'unico posto di un campo.
- **MASK** (`ImageHDU`, `BITPIX=8`, Y×X): maschera di acquisizione, 0/1.
- **ENERGY** (`BinTableHDU`, colonna `E`, formato `D` = float64): asse
  esplicito (solo file calibrati; identico a `energy_axis` di H5/NPZ/OME).

Lettura: `xrfraw.read_fits(path)` ricostruisce il `Dataset` in (Y, X, C)
con metadati integrali (BZERO applicato, big-endian → nativo); da lì il
`Dataset` si converte a qualsiasi altro formato (NPZ/HDF5/OME ↔ FITS).
Compatibilità: il file si apre con qualunque reader FITS standard
(verificato con `astropy` e `h.verify()` strict); i reader non a conoscenza
di xrfraw vedono una C-stack valida con WCS energetico e ignorano le
extension custom.

Scalabilità: il cubo è scritto in un unico blocco non compresso (stessa
semantica di memoria degli writer OME/HDF5: cubo intero residente);
compressione lossless (`CompImageHDU`) non implementata in v0.1.3,
valutata come follow-up con verifica di compatibilità con reader
non-astropy.

## Convenzioni

- Nome output: basename dell'input + estensione; directory via CLI.
- **Nessun overwrite implicito**: file esistente → errore esplicito (salvo
  flag esplicito). Scrittura su file temporaneo + rename a successo
  (niente output parziali).
- Pixel non acquisiti: zero + `mask=False` (distinguibili da uno zero misurato).
- Output non calibrato: asse `channel` + (se m/q noti ma non applicati)
  m/q nei metadati — chi legge calcola `E = m·ch + q`.
- Semantica e invarianze: `scientific_notes.md` §8-14.
