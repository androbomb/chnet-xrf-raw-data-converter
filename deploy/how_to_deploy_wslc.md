# Deploy — WSLC (WSL Container, Windows/WSL2)

**Status:** NOT TESTED (template; run it and fill the result log).
Same image as `../docker/`, built with the `wslc` CLI. CPU-only (numpy, no GPU).

## Build (context = repository root)

```powershell
wslc build --tag «app» --file deploy/wslc/Containerfile .
```

## Run

`CUBE_PATH` optional — without it the app starts empty and you upload a
file or paste a download link in the UI:

```powershell
wslc run --name «app»-viewer -p 8765:8765 `
    -v C:\Users\<you>\«data-dir»:/data:ro `
    -e CUBE_PATH=/data/«file» `
    «app»
```

One line:

```powershell
wslc run --name «app»-viewer -p 8765:8765 -v /abs/path/to/data:/data:ro -e CUBE_PATH=/data/«file» «app»
```

Flags follow Microsoft's WSLC docs (docker short-flag form: `-p`/`-v`/`-e`);
`-v` takes a Windows source path; drop `:ro` if your wslc version rejects it.

Then open `http://localhost:8765`.

## Result log (fill in after your test)

| date | wslc version | build | run | UI checks | notes |
| ---- | ------------ | ----- | --- | --------- | ----- |
|      |              |       |     |           |       |
