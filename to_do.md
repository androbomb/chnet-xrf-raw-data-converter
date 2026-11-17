# To-do — raw-xrf-to-h5-opener-python

## Now
- [ ] Approvazione piano M0 (domande Q1-Q8, operational_plan.md §8)

## Next
- [ ] M1: scheletro `src/xrfraw` + layer dati (reader A/B streaming, metadati, validazione) + test
- [ ] M2: processing (populate / calibrate / rebin) + test invarianze
- [ ] M3: io NPZ/HDF5 + round-trip + CLI

## Later
- [ ] M4: verifica sui 2 file reali (time/RAM/incroci) — Q8
- [ ] M5: packaging + deploy recipe (no PyPI, no push)

## Blocked
- (in attesa) risposte Q1-Q8 — nulla di bloccante sul codice

## Verification log (append; do not rewrite history)
| date | check | result |
| ---- | ----- | ------ |
| 2026-11-17 | M0: profiling a flusso dei 2 file di esempio (awk, 1 passata) | mappa11: 19 868 439 righe, 19 825 090 eventi, depth 15903; Ragazzo: 56 723 562 righe, 56 661 209 eventi, depth 16000; 1 pixel mancante per file |
| 2026-11-17 | M0: crash legacy su formato B (stdlib ET sul corpo del file) | `ParseError: syntax error: line 2, column 0` — confermato (legacy_audit L1) |
| 2026-11-17 | M0: ambiente | Python 3.12.16, uv 0.13.7; numpy/h5py assenti da system python (ok: venv uv a M1) |