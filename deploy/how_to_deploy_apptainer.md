# Deploy — Apptainer (SIF)

**Status:** NOT TESTED (template; run it and fill the result log).
CPU-only JAX: no GPU passthrough. The SIF boots from the Docker image, so
you need Docker only for the build step.

## Steps

1. Build the base image (from the repository root):

   ```bash
   docker build -t «app» -f deploy/docker/Dockerfile .
   ```

2. Build the SIF:

   ```bash
   apptainer build «app».sif deploy/apptainer/«app».def
   ```

   (the `.def` uses `Bootstrap: docker / From: «app»:latest`)

3. Run — with preloaded data (adjust path and filename), or empty (no
   bind, no env — the app starts with "no data loaded"):

   ```bash
   apptainer run --bind /home/<you>/«data-dir»:/data \
       -e CUBE_PATH=/data/«file» \
       «app».sif
   ```

4. Open `http://localhost:8765`. First request compiles the JAX reductions.

## Notes

- Apptainer bind syntax differs from Docker (`--bind src:dst`, no `:ro` in
  older versions — check `apptainer run --help`).
- If Apptainer cannot reach the local Docker daemon for the bootstrap,
  export the image: `docker save «app»:latest -o «app».tar` and point
  `From:` at the tar (or use `Bootstrap: localimage`).
- GPU variant: NOT TESTED; see `uv/README.md`.

## Checklist (fill per project)

- [ ] `apptainer build` succeeds.
- [ ] Page loads at `http://localhost:8765` (main view left, detail right).
- [ ] Empty start (no `CUBE_PATH`) → upload/link in UI → data appears.
- [ ] Cross-selection works both directions.
- [ ] Numeric panels / scale toggle / export work.

## Result log (fill in after your test)

| date | apptainer version | build | run | UI checks | notes |
| ---- | ----------------- | ----- | --- | --------- | ----- |
|      |                   |       |     |           |       |
