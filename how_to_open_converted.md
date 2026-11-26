# Come aprire i file convertiti (NPZ, HDF5, OME-TIFF, FITS)

Spiega il notebook `example-open-converted.ipynb`: 4 esempi, uno per formato,
sullo stesso cubo (mappa11, rebin 512 canali, calibrato). Stesso contenuto in
tutti e 4: cubo `(y, x, canali)` di conteggi raw (uint32, lossless) + metadati
comuni (`output_schema.md`).

## Ambiente

```bash
uv pip install "chnet-xrf-raw-data-converter[fits]" h5py matplotlib
```

`h5py` e `matplotlib` servono a tutti gli esempi; l'extra `[fits]` (astropy)
solo per quello FITS. NPZ basta con numpy.

## Dove stanno i file

- **OME-TIFF e FITS**: share ownCloud, cartelle `512/` e `fits/512/`
  (stessa share dei file OME precedenti, rebin 512 e 1024 canali).
- **NPZ e HDF5**: non sono in share; dal raw in una riga (da questa repo):

```bash
xrf-raw-to-h5 mappa11.txt -o . --format npz --rebin-to 512 --overwrite
xrf-raw-to-h5 mappa11.txt -o . --format h5  --rebin-to 512 --overwrite
```

Metti i 4 file nella stessa cartella del notebook: `mappa11.npz`,
`mappa11.h5`, `mappa11.ome.tif`, `mappa11.fits`.

## I 4 esempi

Ogni esempio apre il file, stampa `(shape, dtype, totale eventi)` e disegna 3
pannelli: mappa totale eventi, media per pixel, spettro sommato. La griglia
(estensione µm) viene dai metadati, identica in tutti i formati.

### 1) NPZ — `np.load`

Un dizionario di array: `img`, `channel`, `x_axis`, `y_axis`, `mask`,
`energy_axis` (solo se calibrato) e `attrs`.

```python
import json, numpy as np
z = np.load("mappa11.npz")
img = z["img"]                          # (y, x, canali) uint32
energy = z["energy_axis"]               # presente solo se calibrato
attrs = json.loads(z["attrs"].item())   # attrs e' un ndarray 0-dim: .item()
meta = json.loads(attrs["metadata_json"])  # metadati completi (grid, ...)
```

Nota: `attrs` in NPZ e' un dizionario serializzato in JSON dentro un ndarray
0-dim — da cui `.item()` e il doppio `json.loads` (in HDF5 gli attrs sono
nativen, un solo livello).

### 2) HDF5 — `h5py`

Stessi dataset, attrs nativi sullo stesso schema:

```python
import h5py, json
with h5py.File("mappa11.h5", "r") as f:
    img = f["img"][...]                 # (y, x, canali) uint32
    energy = f["energy_axis"][...]      # presente solo se calibrato
    meta = json.loads(f.attrs["metadata_json"])
```

### 3) OME-TIFF — `read_ome`

Restituisce un `Dataset` pronto: `.img`, `.energy`, `.metadata`. La
calibrazione vive negli attributi OME (`CalibrationM`/`CalibrationQ`/
`Calibrated`), leggibile anche da qualsiasi reader OME:

```python
from xrfraw import read_ome
ds = read_ome("mappa11.ome.tif")        # ds.img, ds.energy, ds.metadata
```

### 4) FITS — `read_fits`

Lo stesso `Dataset`; la calibrazione e' WCS sull'asse energia
(`CTYPE3=ENERGY`, keV) + extension `XRF_META` (JSON) e `ENERGY` (asse),
leggibile da qualsiasi reader FITS. Richiede l'extra `[fits]`:

```python
from xrfraw import read_fits
ds = read_fits("mappa11.fits")
```

## Verifica

Il totale eventi deve coincidere col raw in tutti e 4 i formati (mappa11:
**19.825.090**); il notebook stampato in output conferma su tutti.

I file **non calibrati** non hanno `energy_axis`/`ds.energy`: l'asse 3 sono i
canali e la conversione in energia si fa a mano con la m/q nota.

Schema completo dei metadati e delle calibrazioni: `output_schema.md`.