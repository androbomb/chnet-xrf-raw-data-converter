# Deploy with uv (primary path)

1. From the repository root:

   ```bash
   uv sync                      # creates .venv/ from uv.lock
   .venv/bin/python -m pytest -q
   ```

2. Register the Jupyter kernel once:

   ```bash
   .venv/bin/python -m ipykernel install --user --name «pkg»-viz \
       --display-name "Python 3.12 («pkg»-viz)"
   ```

   Windows PowerShell: activate `.\.venv\Scripts\Activate.ps1` first and
   use `python -m ...` instead of `.venv/bin/python`.

3. In Jupyter, select the kernel `Python 3.12 («pkg»-viz)` and run the
   notebook pattern from `README.md`: load the data, `build_app(path)`,
   `app.run(jupyter_mode="inline", debug=False, jupyter_height=1000)`.
   (Dash's inline output defaults to 650 px; `jupyter_height` is an int in
   pixels and only stretches the embedded iframe.)

## Checklist

- [ ] `uv sync` succeeds on Python «3.12».
- [ ] `pytest -q` green.
- [ ] Kernel selectable in Jupyter; app runs inline without a separate
      browser server.
- [ ] Changing `path_to_file` requires rerunning the `build_app` cell.

## Result log (fill in after your test)

| date | python | uv | sync | tests | kernel | notes |
| ---- | ------ | -- | ---- | ----- | ------ | ----- |
|      |        |    |      |       |        |       |
