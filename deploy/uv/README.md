# deploy/uv — environment and Jupyter kernel

Only instructions live here; the actual manifest/lock are at the repository
root (`pyproject.toml`, `uv.lock`).

## Setup

```bash
uv sync
.venv/bin/python -m pytest -q
.venv/bin/python -m ipykernel install --user --name «pkg»-viz \
    --display-name "Python 3.12 («pkg»-viz)"
```

Windows PowerShell:

```powershell
# install uv if needed
powershell -c "irm https://astral.sh/uv/install.ps1 | more"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m ipykernel install --user --name «pkg»-viz --display-name "Python 3.12 («pkg»-viz)"
```

In Jupyter select the kernel `Python 3.12 («pkg»-viz)`.

Dash's inline output defaults to 650 px high; to reduce scrolling pass a
larger integer pixel height, e.g.
`app.run(jupyter_mode="inline", debug=False, jupyter_height=1000)`.

## Compute backend: CPU by default (verified), GPU opt-in (NOT TESTED)

- The default install is **CPU-only JAX** (plain `jax`, no CUDA plugin).
  On a host with a visible GPU, `import jax; jax.devices()` still prints
  `CpuDevice(0)` and `nvidia-smi` shows no new CUDA process — importing JAX
  does not pre-allocate GPU memory in this setup.
- Keep reductions in float64 (see `scientific_notes.md`); CPU is also the
  fast path for interactive sizes (no CPU↔GPU transfer per callback).

### GPU variant (NOT TESTED — validate on your WSL2/Blackwell host)

```bash
uv add "jax[cuda12]"         # replaces plain jax; pulls jax-cuda12 + NVIDIA wheels
```

Known behavior to check (NOT TESTED by default):

- On first GPU use the XLA allocator pre-reserves a fraction of VRAM
  (default ~75%). Cap it before launching the kernel:

  ```bash
  export XLA_FLAGS=--xla_gpu_global_memory_fraction=0.3
  ```

- Verify a `CudaDevice` is actually usable:
  `.venv/bin/python -c "import jax; print(jax.devices())"`. A host-visible
  GPU is not a working JAX backend (Blackwell sm_120 needs a recent
  `jax-cuda12` build). The app reports the selected device and never falls
  back silently.
- WSL2/Blackwell quirk to check before relying on GPU for large transforms:
  `cuFFT` rfft at non-power-of-2 lengths can be pathological for larger
  batches (seconds instead of milliseconds, multi-GB allocations).
  Workaround if hit: smaller batches (≤8) or a per-forward decomposition.
