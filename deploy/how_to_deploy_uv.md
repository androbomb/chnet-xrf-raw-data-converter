# Deploy con uv (percorso primario — verificato)

L'ambiente del progetto è gestito con `uv`: un solo comando crea `.venv/`
da `uv.lock` (versioni pinnate) e mette a disposizione la CLI
`xrf-raw-to-h5`. Percorso primario per uso e sviluppo: i backend
docker/apptainer/wslc restano NOT TESTED (vedi i rispettivi documenti).

## 1. Installa uv (una tantum)

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Python: il progetto richiede `>=3.12,<3.14` (`pyproject.toml`); se Python
non c'è, uv se lo scarica da solo.

## 2. Crea l'ambiente (dalla root del repo)

```bash
uv sync            # .venv/ con le dipendenze runtime (numpy, h5py, tqdm, dash, dbc)
uv sync --dev      # stessa cosa + pytest, se vuoi anche la suite di test
```

Verifica:

```bash
.venv/bin/xrf-raw-to-h5 --version    # -> xrf-raw-to-h5 0.1.0
.venv/bin/python -m pytest -q        # suite fast (solo dopo uv sync --dev)
```

## 3. Usalo

### CLI

```bash
.venv/bin/xrf-raw-to-h5 FILE_O_DIR -o OUT_DIR --format h5
```

Opzioni: `--n-channels N` (default 16384), `--dtype uint32|uint16`,
`--metadata JSON` (griglia/calibrazione per il formato B),
`--rebin SIZE sum|mean`, `--overwrite` (default: rifiuta di sovrascrivere).
Exit code: 0 ok, 1 conversione fallita, 2 errore d'uso.

### Python

```bash
.venv/bin/python
>>> from xrfraw import read_raw, with_calibration, write_dataset
>>> from xrfraw.io import convert_file      # pipeline condivisa CLI/UI
```

### UI (browser)

```python
from xrfraw.ui import build_app
app = build_app()
app.run()        # apre su http://127.0.0.1:8050
```

### Jupyter (`example.ipynb`)

Il notebook gira con qualsiasi kernel in cui `xrfraw` sia importabile.
Per usare la `.venv` del progetto come kernel Jupyter (una tantum):

```bash
uv pip install ipykernel          # aggiunge ipykernel solo nella .venv, non in pyproject
.venv/bin/python -m ipykernel install --user --name xrf-raw \
    --display-name "Python 3.12 (xrf-raw)"
```

Poi in Jupyter: seleziona il kernel `Python 3.12 (xrf-raw)` e apri
`example.ipynb` — la sezione 1 mostra la CLI, la sezione 2 mostra la UI
embeddata (`jupyter_mode="inline"`).

Windows PowerShell: attiva prima l'ambiente
(`. .venv\Scripts\Activate.ps1`) e poi usa `python -m ...` /
`xrf-raw-to-h5` senza prefisso `.venv/bin/`.

## Checklist

- [x] `uv sync` OK (Python 3.12.16, uv 0.13.7).
- [x] `xrf-raw-to-h5 --version` → `xrf-raw-to-h5 0.1.0`.
- [x] `pytest -q` suite fast verde (47 passed, 2 slow deselected).
- [ ] Kernel Jupyter: comando documentato, NOT TESTED in questo ambiente
      (nessun Jupyter installato).

## Result log

| date | python | uv | sync | tests | kernel | notes |
| ---- | ------ | -- | ---- | ----- | ------ | ----- |
| 2026-11-17 | 3.12.16 | 0.13.7 | OK | 47 passed (fast, 15 s) | NOT TESTED | percorso primario; wheel 0.1.0 verificato anche in venv pulito (M6) |