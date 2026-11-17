# deploy/uv — ambiente e kernel Jupyter

Istruzioni complete in `../how_to_deploy_uv.md` (percorso primario,
verificato 2026-11-17). Qui i 3 comandi essenziali:

```bash
uv sync                              # crea .venv/ da uv.lock
.venv/bin/xrf-raw-to-h5 --version    # verifica
.venv/bin/python -m ipykernel install --user --name xrf-raw \
    --display-name "Python 3.12 (xrf-raw)"   # kernel Jupyter (una tantum)
```

Windows PowerShell:

```powershell
# installa uv se serve
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync
. .venv\Scripts\Activate.ps1
xrf-raw-to-h5 --version
python -m ipykernel install --user --name xrf-raw --display-name "Python 3.12 (xrf-raw)"
```

In Jupyter seleziona il kernel `Python 3.12 (xrf-raw)` e apri
`example.ipynb`. La UI si inlinizza con
`app.run(jupyter_mode="inline", debug=False, jupyter_height=800)`
(l'altezza predefinita dell'iframe Dash inline è 650 px; `jupyter_height`
è un int in pixel e serve solo a ingrandire l'iframe embeddato).

## Compute backend: CPU-only by design

Il converter è single-thread CPU (contratto: cap su risorse, nessuna
dipendenza GPU/JAX — vedi `scientific_notes.md`). `uv sync` è tutto;
non esiste variante GPU per questo progetto.