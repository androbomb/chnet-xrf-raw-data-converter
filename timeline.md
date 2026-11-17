# Timeline — raw-xrf-to-h5-opener-python

Append-only, dated decisions and changes. Entry format:

- YYYY-MM-DD — <decision/change> (evidence: commit / test / command).

- 2026-11-17 — M0 audit completato (sola lettura): 15 problemi legacy
  verificati (L1-L15), 10 differenze intenzionali proposte (D1-D10),
  grammatica input misurata sui 2 file di esempio; documenti creati
  (operational_plan, legacy_audit, data_format, output_schema,
  scientific_notes, README, AGENTS.md §3, to_do, timeline).
  (evidence: to_do.md verification log)
- 2026-11-17 — git init + .gitignore (`original_code/`, `data_example/`,
  build artifacts ignorati). Nessun push. (evidence: commit iniziale)
- 2026-11-17 — Risposte utente Q1-Q8 ("Piano ok"): converter CLI/package ora;
  UI nuova dopo; dtype opzione default uint32; formato B con griglia inferita +
  metadati esterni; unità µm/µm/s default da conferma; M4 sui file reali.
  (evidence: chat Telegram 2026-11-17)
- 2026-11-17 — Contratto kickstart assorbito (più restrittivo): NC esplicita
  mai max+1 (default strumentale 16384 UNVERIFIED); calibrazione come allegato
  energy[i]=m·i+q con conteggi element-identical (niente resampling/crop);
  ordine output (y, x, channel); maschera di acquisizione; niente auto-rebin /
  auto energy-crop; UI minimale Dash in milestone tardiva. Documenti aggiornati
  a v2; domande aperte N1-N4. (evidence: kickstart_thread_prompt.md;
  operational_plan.md §8-9)
- 2026-11-17 — Misure M0 v2 (awk mawk-safe, 5 passate read-only): max canale
  15902/15999; griglie osservate 285×76 / 215×145 step 1000 uniforme; 0 eventi
  orfani; anomalie localizzate: colonna x=290000 assente (mappa11, 76 px),
  marker X dangling (5000,265000) / (219000,149000) a 0 eventi.
  (evidence: to_do.md verification log)
- 2026-11-17 — N1-N4 risposte utente: NC=16384 default sovrascrivibile;
  UI minimale in M5 di questo repo (dopo M4); rebin esplicito (sum/mean)
  off di default, dichiarato nei metadati; unità X/Y=µm e Velocity=µm/s
  marcate "assumed" finché non confermate strumentalmente.
  (evidence: chat Telegram 2026-11-17)
- 2026-11-17 — M1 avvio: venv uv (numpy 2.5.5, h5py, tqdm, pytest); pacchetto
  `src/xrfraw` (reader 2-passate A/B, metadati XML riga-per-riga, griglia
  dichiarata/inferita, validazione, inspect_raw, Dataset); test sintetici +
  slow sui file reali. Riprova Python: scansione serpentina (Y-esterno/
  X-interno); mappa11 = missing_column x=290000 (76 px) + ultimo pixel
  ultima riga (5000,265000) non acquisito; Ragazzo = ultimo pixel ultima
  riga (219000,149000) non acquisito; entrambi finiscono con l'header X del
  pixel mancante (0 eventi). Documenti aggiornati.
  (evidence: tests/, data_format.md §4, to_do.md verification log)
- 2026-11-17 — M1 chiuso: suite verde (23 fast + 1 slow sui file reali),
  AGENTS.md sincronizzato al contratto kickstart (NC esplicita 16384,
  rebin esplicito off di default, unità assumed, UI M5, RAM ~1.9 GB),
  9 documenti allineati. Commit M1.
  (evidence: pytest output in to_do.md verification log)
- 2026-11-17 — M2 chiuso: processing `src/xrfraw/processing.py` —
  `with_calibration(ds, m, q, *, provenance)`: allegato puro
  `energy[i] = m·i + q` float64, conteggi bitwise-identici (F3, 10 canali a
  mano exact); `rebin(ds, size, how="sum")`: gruppi uniformi
  (`n_channels % size == 0`, errore esplicito), `sum` conserva i totali
  (accumulo esatto uint64, output uint32, overflow check rigoroso), `mean`
  = media per gruppo float64 (semantica legacy), asse `channel` = primo
  indice di ogni gruppo, `n_events` resta fisico, dichiarato in `transforms`
  (F4). Reader: m/q noti ma non applicati → `known_calibration`
  (`calibration` solo dopo `with_calibration`, secondo output_schema).
  Suite: 32 fast + 2 slow (76 s, file reali F2/F9, RAM peak ~3.3 GB).
  Commit M2. (evidence: tests/test_processing.py, test_real_slow.py)
- 2026-11-17 — M3 chiuso: io + CLI. `src/xrfraw/io.py`
  (`write_dataset`: schema output_schema, attributi root HDF5 / array
  `attrs` JSON in NPZ, `calibration_m/q` solo se calibrato, write atomico
  temp+rename, no-overwrite silenziosa → FileExistsError, `overwrite=True`
  esplicito). `src/xrfraw/cli.py` + entrypoint `xrf-raw-to-h5` (pyproject
  `[project.scripts]`, `python -m xrfraw`): file o directory batch,
  `--format h5|npz`, `--n-channels`, `--dtype`, `--metadata`, `--rebin N
  sum|mean`, `--overwrite`, exit 0/1/2, tqdm; calibrazione applicata come
  allegato quando m/q noti. F12 già presente dal reader M1
  (`merge_metadata` → MetadataConflictError con i due valori). Suite:
  43 fast + 2 slow; entrypoint verificato E2E su sintetico. Commit M3.
  (evidence: tests/test_io.py, tests/test_cli.py)
- 2026-11-17 — M4 chiuso: pipeline E2E sui 2 file reali (F1/F7, Q8).
  CLI single-thread: mappa11 99 MB → 17.1 s, RAM peak 1.40 GB, h5 1425 MB;
  Ragazzo 284 MB → 43.5 s, RAM peak 1.99 GB, h5 2043 MB. Incroci tutti
  verdi: sum(img)==n_events (19 825 090 / 56 661 209), mask 21 659/31 174
  (77/1 px non acquisiti), shape (76,286,16384)/(145,215,16384), energy
  [-0.035556..42.438846] keV su mappa11 (m/q dal XML, allegato), Ragazzo
  non calibrato senza energy (formato B, corretto), anomalies nei
  metadati (3/2) coerenti con M1, max_cell 17/1028 → uint16 safe
  (run proof: sum identico, 1022 MB, peak 2.97 GB per accumulo uint32 +
  downcast by design). No-overwrite rifiutato in uso reale. Commit M4.
  (evidence: to_do.md verification log M4; output/*.h5)
- 2026-11-17 — Emendamento contratto (utente): push verso GitHub
  (origin) consentito — push a ogni chiusura milestone; resta bloccato
  solo PyPI/TestPyPI. AGENTS.md/operational_plan/README/to_do aggiornati;
  prima push dell'intera history (M0-M4) verso origin.
- 2026-11-17 — M5 chiuso: UI minimale Dash `src/xrfraw/ui/app.py`
  (build_app: DARKLY, accent #4196B4; validazione, metadati,
  calibrazione nota/imposta, rebin, dtype, download .h5/.npz;
  embeddabile Jupyter `jupyter_mode="inline"` — example.ipynb). Pipeline
  condivisa `io.convert_file` tra CLI e UI; `inspect_raw` ora espone
  `known_calibration` nel report (mirror read_raw). Test headless
  (componenti/validate/convert h5+npz con cal e rebin) + server smoke
  (index 200, 2 callback registrati su /_dash-dependencies). Deps:
  dash>=4.5, dash-bootstrap-components>=2.0.4. Suite: 47 fast + 2 slow.
  Commit M5, push origin. (evidence: tests/test_ui.py, to_do.md
  verification log M5)
- 2026-11-17 — M6 chiuso: packaging + CI. `uv build` (hatchling) → wheel
  + sdist; wheel verificato in venv pulito (entrypoint
  `xrf-raw-to-h5 --version` → 0.1.0, `import xrfraw.ui` + build_app ok,
  runtime deps complete, dev-only escluso). `.github/workflows/ci.yml`
  creato (uv sync --dev, pytest -q fast; slow auto-skip senza data) e
  pushato — esecuzione **UNVERIFIED** (repo privato, no gh CLI in questo
  ambiente). Deploy recipe già in place con status onesti (docker/
  apptainer/wslc NOT TESTED). Nessun push PyPI/TestPyPI (contratto).
  Commit M6, push origin. (evidence: to_do.md verification log M6, dist/)
- 2026-11-17 — `example.ipynb` riscritto: demo CLI + UI embeddata (usa
  data_example/mappa11.txt reale se presente, altrimenti file sintetico
  formato B piccolo; CLI via `python -m xrfraw` con la stessa command line
  del terminale; verifica output con h5py — metadata_json è un attr della
  root; UI Dash inline). Logica verificata senza Jupyter in scratch
  (tiny 3×2: shape (2,3,16384), sum(img)=8==n_events, no-overwrite exit
  1). .gitignore += demo_out/, demo_tiny.txt.
- 2026-11-17 — Sezione deploy/ aggiornata (richiesta utente: UV è il
  percorso che userà): `how_to_deploy_uv.md` riscritto come percorso
  primario con istruzioni chiare (install uv, `uv sync`/`uv sync --dev`,
  uso CLI/Python/UI/Jupyter, kernel `xrf-raw` una-tantum con ipykernel,
  Windows) e result log con valori REALI verificati oggi (uv 0.13.7,
  Python 3.12.16, sync OK, 47 passed in 15 s, kernel NOT TESTED — no
  Jupyter in questo ambiente); `deploy/uv/README.md` allineato (rimossa
  sezione JAX/GPU residua dal template); `how_to_deploy_pip.md`: nomi
  reali (raw-xrf-to-h5-opener-python/xrfraw), kernel xrf-raw, nota
  contratto (PyPI/TestPyPI bloccati), nota license (campo pyproject
  mancante); docker/apptainer/wslc + Dockerfile/your-app.def:
  "CPU-only JAX" → "CPU-only (numpy)" (il progetto è CPU-only by design).
- 2026-11-17 — Kernel Jupyter `xrf-raw` (richiesta utente): `ipykernel`
  ora dipendenza runtime in `pyproject.toml` (entrate in `uv sync`,
  `uv lock` aggiornato, 47 passed); kernel registrato su questa macchina
  (`~/.local/share/jupyter/kernels/xrf-raw` → `.venv` del converter).
  Causa del fallimento osservato in un run dell'utente: notebook aperto
  col kernel `xrf-viz` di dash-xrf-visualizer (no `xrfraw` nel venv) →
  aprire `example.ipynb` col kernel `Python 3.12 (xrf-raw)`. Notebook
  ripulito (rimossi i output di esecuzione sbagliati commitati in
  0890542); docs UV aggiornati (ipykernel incluso da `uv sync`).
- 2026-11-17 — `example.ipynb` (sulla versione salvata dall'utente, run
  verde con kernel xrf-raw): aggiunta sezione "## 2. API Python" con
  `xrfraw.io.convert_file` (stessa chiamata della CLI, restituisce il
  `Dataset`); UI rinumerata a "## 3."; intro "tre percorsi". Cella API
  verificata su mappa11: shape (76,286,16384), sum(img)==n_events
  19 825 090, coerente con la run CLI.
- 2026-11-17 — Cella API del notebook: tutti i parametri espliciti
  (nome=valore con default, richiesta utente) — lista completa dei
  "knob" (fmt, n_channels, dtype, metadata, rebin_spec, cal,
  overwrite). Verificato sul sintetico (formato B): shape (2,3,16384),
  sum==n_events==8.
- 2026-11-17 — FIX notebook unreadable (segnalato utente: "File Load Error,
  missing expected key: metadata"): le due celle API inserite in a7cdb14
  mancavano della chiave `metadata` obbligatoria per cella (schema
  v4.5); `strip_transient` crashava su `cell.metadata` e il reader
  mascherava l'errore come "notebook senza metadata". Aggiunte
  `metadata: {}` + `id` (uuid) a tutte le 10 celle; write atomico
  (tmp+rename) contro read a metà. VALIDATO col Python del Jupyter di
  questo host (nbformat 5.11.1).
- 2026-11-17 — EMENDAMENTO contratto NC (segnalato utente: `n_channels=2048`
  → `XRFReadError: max observed channel 15902 >= n_channels 2048`): se il max
  canale osservato >= n_channels, invece dell'errore snap verso l'ALTO alla
  potenza di 2 successiva (profondità MCA = potenza di 2, es. 15902 →
  2^14 = 16384); valore esplicito rispettato se il dato ci sta dentro; snap
  dichiarato come anomalia `n_channels_snapped` {requested, effective,
  max_channel} + print. Helper `_next_pow2` in reader.py; help CLI, docstring,
  output_schema aggiornati. AGENTS.md aggiornato su approvazione utente
  (emendamento tracciato anche qui). Test: 49 passed
  (+3 snap, -1 vecchio raise). E2E mappa11 con n_channels=2048: shape
  (76,286,16384), sum==n_events==19 825 090, wall 17.1 s, RAM 1.44 GB.
  Notebook: outputs delle run (incl. quella fallita) rimossi, VALID.
- 2026-11-17 — NUOVO CONTRATTO NC + rebin_to + compressione (richiesta
  utente: "l'output è (h,w,n_channels) invece che 16383 (o quello trovato)"
  + keyword per rebinning efficiente N_orig → N_new): `n_channels` comanda
  la profondità ESATTA del cubo — l'output è sempre (h, w, n_channels);
  snap `n_channels_snapped` RIMOSso: read_raw → `XRFReadError` con
  suggerimento della potenza di 2 successiva (inspect_raw resta advisory).
  Rebin aggiornati: con calibrazione `m *= size`, `q` invariato (asse
  energia e metadati coerenti); nuova `rebin_to(ds, n_new)` per target
  {512,1024,2048,4096,8192}, solo sum (totali conservati), n_new < N e
  divisibilità uniforme. CLI: `--rebin-to`, `--compress 0-9`; output h5
  (gzip) e npz (zip-deflate) compressi, livello 4 di default, compress=0
  = none, dichiarato in attr `compression`. Test: 55 passed
  (+4 rebin_to, +3 compress, -2 snap; asserzioni m aggiornate).
- 2026-11-17 — dtype float (richiesta: l'output uint non è compatibile con
  dash-xrf-visualizer, la cui validate_cube_array richiede floating):
  _ALLOWED_DTYPES esteso a uint16/uint32/float32/float64 (reader, CLI
  --dtype, dropdown UI, README, AGENTS, deploy doc). Fix rebin: il branch
  sum trattava i float solo float64 (un float32 finiva castato a uint32)
  — ora ogni dtype floating preserva il proprio dtype (sum esatto per
  conteggi < 2^24 in float32). _populate invariato (+= 1 generico; solo
  uint16 ha safe-accumulate + overflow check). Test: +test_float_dtypes
  (read float32/float64 + float16 rifiutato), +test_rebin_sum_float32_keeps_dtype,
  test_cli: float32 ora valido, float16 → exit 2.
