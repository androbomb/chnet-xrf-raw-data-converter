# To-do — raw-xrf-to-h5-opener-python

## Now
- [x] M1: reader A/B 2-passate + metadati + griglia + validazione + test
      (24 passed: 23 fast + 1 slow sui file reali)
- [x] M2: processing (with_calibration / rebin esplicito) + invarianze
      (34 passed: 32 fast + 2 slow sui file reali, 76 s, RAM peak ~3.3 GB)

## Next
- [ ] M3: io NPZ/HDF5 (schema v2) + round-trip + CLI

## Later
- [ ] M4: verifica sui 2 file reali (time/RAM/incroci) — Q8
- [ ] M5: UI minimale Dash (DARKLY, #4196B4, JupyterDash)
- [ ] M6: packaging + deploy recipe (no PyPI, no push)

## Blocked
- (nessuno)

## Verification log (append; do not rewrite history)
| date | check | result |
| ---- | ----- | ------ |
| 2026-11-17 | M0: profiling a flusso dei 2 file di esempio (awk, 1 passata) | mappa11: 19 868 439 righe, 19 825 090 eventi, depth 15903; Ragazzo: 56 723 562 righe, 56 661 209 eventi, depth 16000; 1 pixel mancante per file |
| 2026-11-17 | M0: crash legacy su formato B (stdlib ET sul corpo del file) | `ParseError: syntax error: line 2, column 0` — confermato (legacy_audit L1) |
| 2026-11-17 | M0: ambiente | Python 3.12.16, uv 0.13.7; numpy/h5py assenti da system python (ok: venv uv a M1) |
| 2026-11-17 | M0 v2: passate awk mawk-safe (5 totali) sui 2 file | max canale 15902/15999; griglie osservate 285×76 / 215×145 (step 1000 uniforme); eventi confermati 19 825 090 / 56 661 209; **0 eventi orfani** in entrambi |
| 2026-11-17 | M0 v2: localizzazione anomalie (awk per colonna) | mappa11: colonna x=290000 (Xmax) assente (76 px) + marker X dangling (5000, 265000); Ragazzo: marker X dangling (219000, 149000); entrambi 0 eventi → pixel non acquisiti 77/21 736 e 1/31 175 |
| 2026-11-17 | M0 v2: contratto kickstart assorbito | NC esplicita (default 16384 UNVERIFIED), calibrazione element-identical, ordine (y,x,channel), mask, niente auto-rebin/crop, UI minimale in milestone tardiva; 9 documenti aggiornati |
| 2026-11-17 | N1-N4 risposte utente | NC=16384 default sovrascrivibile; UI M5 repo; rebin esplicito off di default; unità µm/µm/s marcate assumed |
| 2026-11-17 | M1: riprova Python struttura anomalie (sonda riga per riga) | scansione serpentina Y-esterno/X-interno (righe dispari X asc., pari X disc.); mappa11: colonna x=290000 assente (76 px) + ultimo pixel ultima riga (5000,265000) non acquisito; Ragazzo: ultimo pixel ultima riga (219000,149000) non acquisito; in entrambi il file termina con l'header X di quel pixel mancante (0 eventi) |
| 2026-11-17 | M1 close: suite verde + docs + AGENTS.md | `uv run pytest -q` → 23 passed (0.7 s) + `pytest -m slow` → 1 passed (~20 s, file reali); fix: `_to_number` fallback stringa per flag non numerici XML (es. "n"); dangling_x_marker = header del pixel mancante a fine file in entrambi (mappa11 X(5000) y_prev=265000; Ragazzo X(219000) y_prev=149000); AGENTS.md sync (goal, invarianti NC/rebin/unità, test M5, RAM ~1.9 GB, §8 UI M5) |
| 2026-11-17 | M2 close: processing (`with_calibration` F3, `rebin` F4, F2/F9/F10) | `uv run pytest -q` → 32 passed (0.9 s) + `pytest -m slow` → 2 passed (76 s, file reali: F2 `sum(img)==n_events` 19 825 090 / 56 661 209, F9 canali oltre max a zero, shape (76,286,16384)/(145,215,16384), mask 21 659/31 174; RAM peak ~3.3 GB); fix: `np.add.reduceat` su uint32 accumula in uint64 (numpy safe-accumulation) → overflow check rigoroso su somme esatte; reader: m/q noti ma non applicati → `known_calibration` (schema: `calibration`/`energy` solo dopo `with_calibration`) |
