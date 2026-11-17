# Deploy with pip / PyPI

This is the pip-based alternative to the repository's `uv` workflow. It is a
deployment guide and release checklist; **the project is not published on
PyPI yet** — `pip install «package-name»` works only after the first release.

## End-user install (after publication)

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install «package-name»
python -m pip install ipykernel
python -m ipykernel install --user --name «pkg»-viz \
  --display-name "Python («package-name»)"
```

Select the named kernel in Jupyter, then follow the notebook pattern in
`README.md`: load the data, `build_app(path)`,
`app.run(jupyter_mode="inline", debug=False, jupyter_height=1000)`.

The default install uses the project's `jax` dependency (CPU). GPU JAX is
platform/CUDA-specific; use the current JAX installation instructions rather
than assuming the generic pip package enables a GPU. See
`deploy/uv/README.md` for the project's tested CPU path and the untested GPU
variant.

## Before the first release

1. Check the distribution name on PyPI's JSON endpoint
   (`https://pypi.org/pypi/«package-name»/json` — 404 = unlisted). This does
   NOT reserve the name; recheck immediately before publishing. The
   distribution name and the source import name may differ (`«package-name»`
   vs `«pkg»`), so the source directory does not need renaming.
2. MIT is recorded in `LICENSE` and `pyproject.toml`. Verify the copyright
   notice matches the actual rights holder before the first release, and
   review licenses of any material added to the package.
3. Confirm the project URLs and supported Python classifiers in
   `pyproject.toml`. Keep `requires-python` as the range CI actually tests.
4. Build wheel and sdist with Hatchling; inspect both archives to confirm
   any package data files ship with the package (CI already asserts this).
   Run `twine check`, install the wheel in a clean venv, and smoke-test the
   imports and the `build_app(...)` factory.
5. Run the test suite on each supported Python version and verify dependency
   resolution with pip.

## Release workflow

1. CI tests the supported Python versions and builds wheel + sdist on pushes
   and pull requests. Release only from a reviewed `v<version>` tag matching
   `[project].version`; PyPI releases are immutable — never reuse a published
   version.
2. Rehearse the artifact on TestPyPI (`publish-testpypi.yml`) and install it
   in a clean environment.
3. Configure PyPI Trusted Publishing: owner `<owner>`, repository
   `<repo>`, workflow `publish.yml`, GitHub environment `pypi` (and
   `testpypi` for the rehearsal). Use GitHub Actions OIDC and PyPA's
   supported publishing action — no long-lived PyPI token. See the
   [PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/).
4. For each release: build and validate artifacts, create/push the version
   tag, then manually run the protected `Publish to PyPI` workflow for that
   tag. It is intentionally not triggered by an ordinary push or tag push.
   Verify the project page and install the exact version with pip.

Publishing is a separate, explicit release action; preparing this guide does
not upload anything to PyPI.
