# Deploy with pip / PyPI

**Contract (2026-11-18, emendamento utente): la pubblicazione PyPI è
ABILITATA** e preparata con Trusted Publishing (OIDC). Distribution name:
`chnet-xrf-raw-data-converter`; import name: `xrfraw`; CLI:
`xrf-raw-to-h5`. Le versioni PyPI sono **immobili**: un numero pubblicato
non viene mai ripubblicato.

## End-user install (dopo la pubblicazione)

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "chnet-xrf-raw-data-converter[ui]"
python -m pip install ipykernel
python -m ipykernel install --user --name xrf-raw \
  --display-name "Python 3.12 (xrf-raw)"
```

- core: `numpy`, `h5py`, `tqdm` (CPU-only — nessun torch/pandas/JAX,
  vedi `scientific_notes.md`);
- extra `[ui]`: `dash>=4.5`, `dash-bootstrap-components>=2.0.4` (solo per
  `from xrfraw.ui import build_app` e `example.ipynb`);
- `ipykernel` si installa a parte solo se serve il kernel nominato `xrf-raw`
  in Jupyter.

Selezionare il kernel nominato in Jupyter, poi aprire `example.ipynb`
(§1 CLI, §2 API, §3 UI inline: `build_app()`,
`app.run(jupyter_mode="inline", debug=False, jupyter_height=800)`).

## Release workflow (Trusted Publishing, nessun token PyPI)

1. L'agent fa: bump versione in `pyproject.toml`, `uv lock`, test suite
   verde, commit `release: bump to X.Y.Z`, push `master`, tag `vX.Y.Z` sul
   commit di bump, push del tag.
2. Configurazione **una tantum** (utente, da web): PyPI → Project
   `chnet-xrf-raw-data-converter` → *Add a new publisher* con
   owner `androbomb`, repo `chnet-xrf-raw-data-converter`, workflow
   `publish.yml`; idem per TestPyPI con workflow `publish-testpypi.yml`.
   Su GitHub: *Settings → Environments* con gli ambienti `pypi` e
   `testpypi` (opzionale ma consigliato, per il gate di revisione).
   Guida: <https://docs.pypi.org/trusted-publishers/>.
3. Per ogni release l'utente invoca, da *Actions*:
   - `Publish to TestPyPI` (input: `vX.Y.Z`) → l'agent verifica su
     `https://test.pypi.org/pypi/chnet-xrf-raw-data-converter/json` e
     installa la wheel in venv pulito (con `--no-cache`, la cache uv
     globale può servire l'index stantio);
   - `Publish to PyPI` (input: `vX.Y.Z`) → l'agent verifica
     `https://pypi.org/pypi/chnet-xrf-raw-data-converter/json`, installa
     la versione esatta in venv pulito e fa lo smoke test (import +
     `convert_file` + `build_app`);
   - *Releases* → "Draft a new release" sul tag esistente.
4. I workflow `publish*.yml` sono **solo** `workflow_dispatch`: un push o
   un tag non pubblicano mai nulla da soli.

Nota TestPyPI: se un install da TestPyPI fallisce la risoluzione delle
dipendenze transitive, usare `--extra-index-url https://pypi.org/simple`
con `--index-strategy unsafe-best-match`.