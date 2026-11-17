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
