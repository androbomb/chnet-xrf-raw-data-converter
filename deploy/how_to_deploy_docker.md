# Deploy — Docker

**Status:** NOT TESTED (recipe is a template; run it and fill the result log).
CPU-only (numpy, no torch/pandas/JAX): no GPU passthrough.

## Steps

1. From the repository root (context must be the root so `COPY` resolves):

   ```bash
   docker build -t «app» -f deploy/docker/Dockerfile .
   ```

2. Run — with preloaded data (adjust path and filename):

   ```bash
   docker run --rm -p 8765:8765 \
       -v /home/<you>/«data-dir»:/data:ro \
       -e CUBE_PATH=/data/«file» \
       «app»
   ```

   (`CUBE_PATH` is the template name — rename it to match your app's
   `load_*` entry point.) Or empty (no env, no bind): the app starts with
   "no data loaded" and the user uploads a file or pastes a link in the UI.

3. Open `http://localhost:8765`.

## Notes

- `README.md` is copied alongside `pyproject.toml`: hatchling validates the
  declared `readme` during the editable build.
- `git was not found in the system` during the build is harmless
  (metadata only).
- Image: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` +
  `uv sync --frozen --no-dev` (no pytest/ipykernel inside).
- To iterate: rebuild, or run with a shell — app code lives at `/app`.
- GPU variant: NOT TESTED (a different base image would be needed); see
  `uv/README.md`.

## Checklist (fill per project)

- [ ] Build succeeds.
- [ ] Page loads at `http://localhost:8765` (main view left, detail right).
- [ ] Empty start (no `CUBE_PATH`) → upload/link in UI → data appears.
- [ ] Cross-selection works both directions (map→detail, detail→map).
- [ ] Numeric panels work; bad input shows an error message.
- [ ] Scale toggle (log/linear) and any calibration work.
- [ ] Export / PNG download works with the expected dimensions.

## Result log (fill in after your test)

| date | docker version | build | run | UI checks | notes |
| ---- | -------------- | ----- | --- | --------- | ----- |
|      |                |       |     |           |       |
