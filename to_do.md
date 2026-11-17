# To-do — raw-xrf-to-h5-opener-python

## Now
- [ ] Approvazione piano M0 v2 (domande N1-N4, operational_plan.md §9)

## Next
- [ ] M1: scheletro `src/xrfraw` + layer dati (reader A/B 2-passate, metadati,
      inferenza griglia B, inspect_raw, validazione, regole conflitto) + test

## Later
- [ ] M2: processing (populate / with_calibration / rebin esplicito) + invarianze
- [ ] M3: io NPZ/HDF5 (schema v2) + round-trip + CLI
- [ ] M4: verifica sui 2 file reali (time/RAM/incroci) — Q8
- [ ] M5: UI minimale Dash (DARKLY, #4196B4, JupyterDash)
- [ ] M6: packaging + deploy recipe (no PyPI, no push)

## Blocked
- (in attesa) risposte N1-N4 — nulla di bloccante sul codice M1

## Verification log (append; do not rewrite history)
| date | check | result |
| ---- | ----- | ------ |
| 2026-11-17 | M0: profiling a flusso dei 2 file di esempio (awk, 1 passata) | mappa11: 19 868 439 righe, 19 825 090 eventi, depth 15903; Ragazzo: 56 723 562 righe, 56 661 209 eventi, depth 16000; 1 pixel mancante per file |
| 2026-11-17 | M0: crash legacy su formato B (stdlib ET sul corpo del file) | `ParseError: syntax error: line 2, column 0` — confermato (legacy_audit L1) |
| 2026-11-17 | M0: ambiente | Python 3.12.16, uv 0.13.7; numpy/h5py assenti da system python (ok: venv uv a M1) |
| 2026-11-17 | M0 v2: passate awk mawk-safe (5 totali) sui 2 file | max canale 15902/15999; griglie osservate 285×76 / 215×145 (step 1000 uniforme); eventi confermati 19 825 090 / 56 661 209; **0 eventi orfani** in entrambi |
| 2026-11-17 | M0 v2: localizzazione anomalie (awk per colonna) | mappa11: colonna x=290000 (Xmax) assente (76 px) + marker X dangling (5000, 265000); Ragazzo: marker X dangling (219000, 149000); entrambi 0 eventi → pixel non acquisiti 77/21 736 e 1/31 175 |
| 2026-11-17 | M0 v2: contratto kickstart assorbito | NC esplicita (default 16384 UNVERIFIED), calibrazione element-identical, ordine (y,x,channel), mask, niente auto-rebin/crop, UI minimale in milestone tardiva; 9 documenti aggiornati |
