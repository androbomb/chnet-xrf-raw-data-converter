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
- 2026-11-17 — UI riscritta: CLI grafica per convert_file (richiesta
  utente: "rifacciamo totalmente la UI — minimale per usare la CLI,
  template grafico della app, via tutto ciò che non serve").
  build_app(src=None): template dash-xrf-visualizer — upload | load from
  link | path_to_file (src precompila, come build_app(cube) laggiù) + un
  input per ogni parametro di convert_file (out_path, fmt, n_channels,
  dtype, metadata, rebin_spec via size+how, rebin_to, cal m/q, compress,
  overwrite) + Convert + Download file. Via il tasto Valida e le card
  report (inspect_raw resta API pubblica, usata da CLI/test). Upload/link
  scrivono in $TMPDIR/xrfraw_ui e riempiono path_to_file; dispatch su
  ctx.triggered_id (audit 1 del visualizer); fix run_convert: mkdir della
  dir di destinazione (write_dataset fa rename atomico su .part).
  test_ui.py riscritto: 21 ids, prefill src, run_convert h5/npz
  roundtrip, outpath default in xrfraw_ui.
- 2026-11-17 — `example.ipynb` fix post-riscrittura UI: markdown "3. UI embeddata" aggiornato (testo vecchio pre-rewrite: report validazione / m-q provenance user -> input convert_file + Convert + Download file); nota sulla **porta fissa 8050** di dash inline: se un'altra app inline (es. l'example del visualizer) e' ancora viva, l'iframe della cell mostra quella -> Kernel -> Restart prima di eseguire la cell; output iframe salvato (127.0.0.1:8050) rimosso dalla cell UI + execution count azzerate; bullet Note troncato/duplicato riparato. Smoke test: `app.run(port=8051)` serve il layout completo (path_to_file, Load from link, Convert, Download file, tutti i campi convert_file). Causa del "visualizer sotto la cella": dash 4.5 `_jupyter.run_app` usa port=8050 di default per TUTTE le app inline della macchina; l'iframe salvato puntava a 8050 dove girava ancora l'app del visualizer.
- 2026-11-17 — fix `build_app(src=Path)`: il notebook passa RAW come WindowsPath e Dash serializza il layout in JSON per il client -> `TypeError: Object of type WindowsPath is not JSON serializable` / "Error loading layout". Fix alla radice: `value=str(src)` in app.py + hint `str | Path | None`; test di regressione (Path prefill + json.dumps del layout con PlotlyJSONEncoder, lo stesso encoder del serving). Verificato E2E: `build_app(src=Path(...))` servito su 8051, GET /_dash-layout 200 con value str.
- 2026-11-17 — UI: root cause dello "schermo grigio" + UX. Il campo rebin_to parte VUOTO (value "", placeholder "off" solo visivo) e il callback faceva int("") -> ValueError -> HTTP 500 su OGNI click di Convert -> UI bloccata. Fix alla radice: campi vuoti gestiti ("", "off" -> None) + try/except difensivo su tutto il parsing (ogni errore = alert rosso, mai 500); compress: int(compress or 4) fixato (0 e' valido). Nuova UX (richieste utente): dcc.Loading (spinner su ogni callback); callback immediato al click su Convert (status "conversione in corso: <file> (<MB>) - puo richiedere minuti" + tasto disabilitato fino al termine); lock threading anti doppio-convert; upload limitato a ~48 MB raw (il browser base64-izza il file in memoria: 284 MB = gray screen) con messaggio che indica path_to_file; tooltip dbc su tutti i campi. Test: nuovo test_convert_callback_http_roundtrip — E2E headless via POST /_dash-update-component (body "inputs" plurale, chiave multi-output "..id.prop...id.prop.." come dash._utils.create_callback_id, response annidata response[id][prop]): click Convert -> file scritto + riabilitazione, click -> feedback immediato. 58 passed. Timing file grande (ragazzo triste, 56 661 209 eventi, nc=16384 uint32): 46.6 s, peak RAM 2094 MB su WSL — l'app era ROTTA, non lenta.
- 2026-11-18 — UI: diagnosi schermo grigio e feedback. Repro end-to-end del flusso utente via POST /_dash-update-component (stesso protocollo del browser) con i link ownCloud REALI: load mappa11 (99 MB) 200 in ~13 s, load ragazzo triste (284 MB) 200 in 64 s, Convert ragazzo triste 200 in 39 s (OK 56 661 209 eventi, 45.3 MB) — il backend e' corretto: le risposte contengono in-path.value e lo status. I sintomi utente (campo path_to_file vuoto con status ok, Convert che "non fa nulla", iframe grigio dopo re-run) sono tutti lato frontend/iframe del notebook: l'inline di Dash 4.5 usa un iframe via /proxy/8050/ del server notebook; se il proxy e' stantio il frame e' grigio e tutto dopo sembra morto. Fix lato app (indipendenti dal frontend): (a) messaggi di load autocontenuti "Caricato: <path> (<MB>)" — il path si vede SEMPRE anche se il campo non si aggiorna; (b) nome file unico per URL (download_<sha1[:8]>.txt, idempotente per lo stesso link) — prima ogni link sovrascriveva lo stesso "download"; (c) download atomico (.part + os.replace): un link interrotto non lascia file tronco; (d) label/tooltip out_path senza jargon "<stem>". example.ipynb: sezione 3 estesa con la diagnostica schermo grigio (apri 127.0.0.1:8050 diretto, kernel restart, netstat/taskkill per la 8050) + alternativa da terminale. 58 passed.
- 2026-11-18 — UI: fix bianco-su-bianco (testo invisibile nei campi). L'utente ha confermato: il valore di path_to_file c'era (selezionabile), ma il testo si rendeva invisibile — "bianco su bianco". Causa: forced dark mode del browser (es. Chrome auto-dark) che inverte testo/sfondi della pagina. Fix in build_app: app.index_string dichiarata color-scheme:light (disattiva l'inversione) + colori espliciti input,select (scudo). Test di regressione test_index_declares_light_color_scheme (pagina servita deve contenere la dichiarazione). user_guide.md §8: voce di troubleshooting. 59 passed.
- 2026-11-18 — UI: dropdown ancora "scritti in bianco" + Download muto + Convert muto. (a) Dropdown: il fix color-scheme aveva reso visibili gli input, ma i 4 dcc.Dropdown (react-select, styling interno proprio) restavano testo bianco su fondo scuro/trasparente — letti dall'utente come "alcuni campi bianchi". Fix: className="xrfraw-dd" sui 4 dropdown + CSS scoped in index_string (fondo bianco + testo scuro su tutti gli elementi interni, border esplicito). (b) Download muto: la causa era lo stato client-side — il tasto dipendeva da dcc.Store(file-store) scritto dalla risposta di Convert; in un iframe instabile lo stato si perde -> no_update = zero feedback. Fix: Download è ora un link reale alla route /xrfraw-download che serve l'ultimo output di run_convert (globale _LAST_OUT) con send_file as_attachment; 404 con messaggio esplicito se non c'è output. Via dcc.Download + file-store + callback _on_download. (c) Bug latente trovato dai test: senza file-store, _on_convert_start e _on_convert finivano con gli STESSI (outputs, inputs) -> stesso callback id in Dash -> 500 al dispatch. Fix: outputs distinti (start: disabled+children "⏳ in corso"; convert: disabled+children+status; il dcc.Loading dà lo spinner durante il POST lungo). E2E live su 8051 con mappa11: Convert 17.8 s (OK 19 825 090 eventi, 21.3 MB, calibrato) + GET /xrfraw-download 200 attachment, sha256 IDENTICO al file su disco. user_guide §8 aggiornato. 60 passed.

- **2026-11-18 (round 3: Convert "bloccato")** — Screenshot: campi tutti
  leggibili (fix CSS ok) ma click su Convert senza reazione (nessuno
  spinner/status; Load from link invece aveva funzionato nello stesso
  iframe). Causa: Convert = DUE callback sullo stesso click (feedback
  immediato + conversione) = due round-trip sul proxy iframe instabile;
  uno perso → tasto apparentemente morto, e il `disabled` del primo
  poteva restare bloccato senza reset. Fix: **un solo callback** (stessa
  forma di Load): output solo `out-status.children`, feedback "in corso"
  via spinner di `dcc.Loading` (lato client, zero round-trip), doppio
  click coperto da `_CONVERT_LOCK` ("già in corso"). Il tasto non viene
  mai disabilitato → non esiste stato bloccabile. Test: 60 passed
  (nuovo assert sul lock; fix helper `_update`: il body Dash 4 usa
  `outputs` come target singolo per i callback single-output, lista per i
  multi — `types.CallbackExecutionBody`). E2E live 8051: convert
  mappa11 18.4 s OK → download 21.3 MB byte-identico (sha256 uguale).

## PyPI packaging prep (2026-11-18)

Contratto emendato dall'utente: PyPI sbloccato, "iniziamo a preparare la
strada verso un push su PyPI, con nome chnet-xrf-raw-data-converter".
Nome disponibile su PyPI (404 su pypi.org/pypi/chnet-xrf-raw-data-converter/json).
Cambi: `pyproject.toml` riscritto (dist name `chnet-xrf-raw-data-converter`,
license MIT PEP 639, autori, classifiers, project.urls, UI come extra
`[ui]`, `ipykernel` → dev group); `LICENSE` copyright Alessandro Bombini;
`xrfraw.__version__` da importlib.metadata (no drift, test dedicato);
CI → matrix 3.12/3.13 + `uv sync --locked` + `uv build` + twine check +
smoke wheel in venv pulito + artifact; nuovi workflow `publish.yml` /
`publish-testpypi.yml` (solo workflow_dispatch, OIDC Trusted Publishing,
environment `pypi`/`testpypi`, pattern dash-xrf-visualizer);
`deploy/how_to_deploy_pip.md` riscritta (blocco rimosso, procedura
release); `CITATION.cff` aggiunto; README/operational_plan/to_do al nuovo
nome. Resterà all'utente (web): configurazione Trusted Publishing su
PyPI/GitHub + dispatch dei workflow — i push e i tag non pubblicano mai
da soli.

## Release v0.1.0 (2026-11-18)

Pubblicato su **TestPyPI** e **PyPI**: `chnet-xrf-raw-data-converter` 0.1.0
(wheel 27.3 KB + sdist 121 KB), via workflow `publish-testpypi.yml` /
`publish.yml` (OIDC Trusted Publishing, dispatch manuale). Fix di percorso:
tag input `v.0.1.0`→`v0.1.0` (utente) e glob wheel non espanso nel smoke
(`7f762f8`, tag `v0.1.0` spostato sul fix). Verifica agent su entrambi gli
index: JSON endpoint con 0.1.0, install `--no-cache` in venv pulito, CLI
`--version`, conversione reale `(2,2,4096)` uint32 4 eventi, `build_app` ok,
versione == metadati dist.

## Guida utente da zero (2026-11-20)

Nuovo file `simple_guide.md`: guida "molto nabbo" su modello della
guida uv+Jupyter dell'app xrf-visualizer. Struttura: install `uv` (una
volta), venv `xrfraw-env`, attivazione (incl. fix "script non firmato"
PowerShell), `uv pip install "chnet-xrf-raw-data-converter[ui]" ipykernel
jupyterlab`, kernel, poi le 3 modalità d'uso con codice copy-paste: UI
(cella notebook + UI dal terminale, sezione UX con tabella parametri e
troubleshooting), notebook Python (5 celle: versione, inspect_raw,
convert_file minima, opzioni, lettura h5py), CLI (quick ref + tabella flag +
exit code). Link nel README. **Verifica**: le celle Python e l'UI
(terminale, HTTP 200 + `<title>xrf-raw-to-h5</title>`) eseguite in locale su
un mini raw sintico.

## Audit public-readiness (2026-11-20)

- `CITATION.cff`: aggiunto `date-released: 2026-11-18` (come in dash-xrf-visualizer).
- `LICENSE`: già MIT — Copyright (c) 2026 Alessandro Bombini (identica a dash-xrf-visualizer).
- `README.md`: status aggiornato (v0.1.0 pubblicato su PyPI/TestPyPI; CI verde; rimosso "repo privato").
- Audit secret/path: nessun token, URL ownCloud, `/home/dev` o path personale nei file
  tracciati né nella storia git; nessun `.env`/chiavi/dati tracciati; workflow senza
  `secrets.*` (solo OIDC Trusted Publishing).
- Struttura file allineata a dash-xrf-visualizer (repo pubblica): stessi tipi di docs
  (AGENTS.md, operational_plan.md, timeline.md, to_do.md, scientific_notes.md, deploy/).
- Restante: cambio visibilità a pubblica da GitHub (Settings → General → Danger zone).

## OME-TIFF / BigTIFF export (2026-11-25)

- `src/xrfraw/ome.py` (nuovo): `write_ome` (un IFD per canale, OME-XML CYX
  nell'IFD 0, MapAnnotation `urn:xrfraw:v1` con meta/attrs/mask, zlib 0-9,
  BigTIFF auto >4 GB) + `read_ome` (round-trip → Dataset (Y,X,C) + metadati,
  energy ri-derivata da m/q). Dip: `tifffile` (core).
- Integrazione: `write_dataset(fmt="ome")` (atomico, estensione `.ome.tif`),
  CLI `--format ome`, UI (dropdown fmt, nome default `.ome.tif`),
  `xrfraw.read_ome` exportato. Comportamenti NPZ/HDF5 invariati.
- Test: `tests/test_ome.py` (13 fast: round-trip lossless uint16/uint32/
  float32/float64, calibrato/non calibrato, formato B, OME-XML struttura
  canali/Dimension/PhysicalSize/MapAnnotation, BigTIFF magic, 256 canali,
  compressione 0/9 lossless, TIFF senza OME-XML → ValueError, CLI) +
  `test_ome_round_trip_real` (slow, mappa11: 16384 IFD, cubo identico).
- Nota: i tag stringa TIFF sono 7-bit ASCII → il non-ASCII dell'OME-XML
  (es. unità µm) va in numeric character references.
- Fix conformità (stesso giorno): validazione contro l'XSD ufficiale OME
  2016-06 ha rivelato 13 violazioni (XML scritto a convenzioni 2008-02:
  elemento `<Dimension>`, `DimensionOrder="CYX"`, `DimensionType`,
  `SamplesPerPixel` su Pixels, booleani "False", `StructuredAnnotations`
  sotto Pixels). Corretti: attributi `SizeX/SizeY/SizeC/SizeZ/SizeT`,
  `DimensionOrder="XYZCT"`, booleani lowercase, `StructuredAnnotations`
  sotto `OME` + `Image.AnnotationRef`. Ora **XSD-VALID**; i file sul share
  ownCloud rigenerati e riscaricati.
- Fix single-OME-series (2026-11-25, da audit interoperabilità): `tifffile`
  vedeva **512 serie shaped YX** invece di un'unica serie OME CYX —
  `TiffWriter` di default (`kind=shaped`) allega un JSON
  `{"shape": [Y, X]}` a ogni piano 2D, che `TiffFile` interpreta come
  metadati shaped per-IFD. Fix: `TiffWriter(..., shaped=False)` (l'arg `kind`
  è troppo recente per il range di tifffile supportato). Aggiunti test:
  `tif.is_ome`, `not tif.is_shaped`, `len(tif.series) == 1`,
  `series[0].axes == "CYX"`, counts/annotazioni conservati.
- Calibrazione energetica post-rebin registrata esplicitamente: `attrs`
  nell'OME-XML ora include `energy` (asse float64 per-canale, post-rebin,
  come `/energy` in H5/NPZ) oltre a `calibration_m/q`; `read_ome` usa
  l'asse esplicito se presente, altrimenti ri-deriva da m/q (compat file
  0.1.1). `output_schema.md` aggiornato.
- Calibrazione energetica post-rebin distinguibile (2026-11-25, feature
  request): il rebin non modifica più la calibrazione originale.
  `metadata["calibration"]` conserva m₀/q₀ intatti; la calibrazione
  post-rebin va in un blocco `rebinning` = `{factor, uniform, m, q,
  convention: "bin-mean", energy_unit: "keV"}` con `m' = R·m₀`,
  `q' = q₀ + (R−1)/2·m₀` (energia rappresentativa = media delle energie dei
  bin aggregati, keV; per R=1 coincide con l'originale). `energy` è ora la
  media per gruppo (float64). Schema v2: NPZ/H5/OME espongono gli attributi
  scalari `calibration_m_original`, `calibration_q_original`, `rebin_factor`,
  `energy_unit`, `bin_convention` accanto a `calibration_m/q` (effettivi);
  retrocompatibile (i reader ri-derivano sui file 0.1.1). Aggiunti test
  round-trip dei 3 formati + esempio di riferimento (m=0.00373862,
  q=-0.0340262, R=32 → m'=0.11963584, q'=0.02392241).
