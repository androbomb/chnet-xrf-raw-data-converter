# chnet-xrf-raw-data-converter (import: `xrfraw`)

Converter for raw MA-XRF files (Fi MA-XRF, INFN-CHNet) to **NPZ / HDF5 /
OME-TIFF / FITS**: a per-pixel event datacube in **(y, x, channel)** order,
ADC channel indices, spatial axes, acquisition mask, serialized metadata —
with the energy calibration carried as an *attachment*
(`energy[i] = m·i + q`), so the raw counts are never modified.

## What it does

- Reads both raw variants (XML+data, data-only); validates before allocating
  the cube (`inspect_raw`).
- Builds the datacube `(Y, X, n_channels)` with a choice of dtype: `uint32`
  (default), `uint16`, `float32`, `float64` — **exact** depth: the output is
  always `(Y, X, n_channels)`, trailing channels zero-filled.
- Energy calibration as attachment: counts are element-identical before and
  after (the legacy converter silently lost this).
- No auto-rebinning / auto energy-crop. Explicit rebin (sum/mean) and
  rebin-to-target-depth (`rebin_to`, sum-only, totals preserved) on demand.
- Writes `.h5`, `.npz`, `.ome.tif` (OME-TIFF/BigTIFF) or `.fits` (FITS
  multi-extension; requires the optional `[fits]` extra → astropy) with the
  same logical schema.
- Minimal Dash UI, embeddable in Jupyter: `from xrfraw.ui import build_app`
  (requires the `[ui]` extra).

## Install

```bash
python -m pip install chnet-xrf-raw-data-converter             # core
python -m pip install "chnet-xrf-raw-data-converter[ui]"       # + Dash UI
python -m pip install "chnet-xrf-raw-data-converter[fits]"     # + FITS read/write (astropy)
```

The core works without astropy: FITS read/write then raises an explicit
`ImportError` telling you to install the `[fits]` extra, and the FITS option
simply does not appear in the UI.

## Usage

### CLI

`xrf-raw-to-h5` — exit code 0 ok / 1 conversion error / 2 usage; no silent
overwrite (use `--overwrite`):

```bash
xrf-raw-to-h5 FILE_OR_DIR -o OUT_DIR --format h5|npz|ome|fits \
    [--n-channels N] [--dtype uint32|uint16|float32|float64] [--metadata meta.json] \
    [--rebin N sum|mean] [--rebin-to 512|1024|2048|4096|8192] \
    [--compress 0-9] [--overwrite]
```

When m/q are known (XML header or external JSON) the calibration is applied
as attachment (`with_calibration`); otherwise the output is uncalibrated
(channel axis, no `energy`). `--compress` applies to h5/npz/ome (FITS is
uncompressed in 0.1.x).

### Python

```python
from xrfraw import inspect_raw, read_raw, read_ome, read_fits, with_calibration, rebin, rebin_to
from xrfraw.io import write_dataset, convert_file

report = inspect_raw("mappa11.txt")   # validation, no allocation
ds = read_raw("mappa11.txt")          # (NY, NX, NC) + axes + mask + metadata
ds = with_calibration(ds, 0.00259259, -0.0355556, provenance="xml")  # counts untouched
ds = rebin(ds, 2)                     # optional, explicit (sum|mean)
ds = rebin_to(ds, 2048)               # optional: target depth, sum-only
write_dataset(ds, "out.h5", fmt="h5") # fmt: "h5" | "npz" | "ome" | "fits"

# one-liner: raw -> calibrated -> rebinned -> file (same pipeline as CLI/UI)
ds = convert_file("mappa11.txt", "out/mappa11.fits", fmt="fits", rebin_to=512)
```

### Reading back the converted files

Same cube + metadata in all four formats; the total event count must match
the raw in every one of them:

```python
# NPZ — plain numpy (attrs is a 0-dim ndarray: .item(); metadata_json inside)
import json, numpy as np
z = np.load("mappa11.npz")
img = z["img"]                                   # (y, x, channels) uint32
energy = z["energy_axis"]                        # only present if calibrated
meta = json.loads(json.loads(z["attrs"].item())["metadata_json"])

# HDF5 — h5py (native attrs, single JSON level)
import h5py
with h5py.File("mappa11.h5", "r") as f:
    img = f["img"][...]
    meta = json.loads(f.attrs["metadata_json"])

# OME-TIFF / FITS — xrfraw readers, return a ready Dataset (.img, .energy, .metadata)
from xrfraw import read_ome, read_fits
ds = read_ome("mappa11.ome.tif")
ds = read_fits("mappa11.fits")      # requires the [fits] extra
```

Uncalibrated files have no `energy_axis`/`ds.energy`: axis 3 is the channel
index; convert to energy by hand with the known m/q. OME-TIFF and FITS carry
the calibration in standard containers (OME attributes / FITS WCS
`CTYPE3=ENERGY`, keV) plus the full metadata JSON, readable by any
OME/FITS reader. Runnable examples for all four formats:
`example-open-converted.ipynb` + `how_to_open_converted.md` (in the repo).

### UI (Dash)

```python
from xrfraw.ui import build_app
app = build_app(src="./mappa11.txt")
app.run()                                        # browser
app.run(jupyter_mode="inline", jupyter_height=800)  # notebook
```

Every `convert_file` parameter is exposed as an input; the FITS option is
enabled only when astropy is installed. Upload is limited to ~48 MB (the
browser base64-encodes the file in memory) — use `src=` for bigger files.

## Docs (in the repo)

`output_schema.md` — shared metadata schema (incl. FITS HDU/WCS technical
note) · `data_format.md` — raw file grammar · `scientific_notes.md` —
calibration, counts, precision · `simple_guide.md` — from-scratch guide
(uv, UI, Python, CLI) · `user_guide.md` — operational guide.