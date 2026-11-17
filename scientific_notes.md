# Scientific notes — raw MA-XRF

Ogni voce: affermazione — fonte — data. Stato: verificato / lettura-codice /
assunto / da verificare.

1. **Calibrazione energia**: `E(ch) = m·ch + q` con m = `calibration_keV/ch`,
   q = `calibration_Offset` (XML). — fonte: XML mappa11 + `calibrate_xrf`
   (raw_reader.py:556) — lettura-codice 2026-11-17; verifica numerica a M2.
2. **Semantica eventi**: ogni riga dello stream = 1 evento rilevato (fotone)
   nel canale c; il datacube è l'istogramma per pixel; totali conteggi =
   numero di righe conteggio (19 825 090 / 56 661 209 negli esempi). —
   fonte: `single_step_populate` (raw_reader.py:336) — lettura-codice;
   verifica per conteggio a M4.
3. **Assi X/Y**: coordinate del piattino (motore). Unità **ASSUNTA µm**
   (l'XML non dichiara unità; step = 1000). — da conferma utente.
4. **Velocity** = 8000, unità ASSUNTA µm/s → dwell per pixel = step/velocity
   = 0.125 s. — assunto.
5. **Calibrazione legacy (riferimento)**: griglia uniforme su E_range con
   NC0 bin; assegnamento `cal[:, :, j] = xrf[:, :, i]` (**overwrite, non
   somma**) e `j` non azzerato per canale → tutti i canali con E < E0 finiscono
   nel bin 0 e tutti quelli con E > E1 nell'ultimo bin: **~206 canali
   (basso) + ~1038 (alto) per pixel persi silenziosamente** per m=0.00259259,
   q=−0.0355556, E_range=(0.5, 38.5), NC0=15903. — calcolo dalla logica del
   codice (raw_reader.py:581-604), 2026-11-17.
6. **Rebin legacy**: `torch.nn.AdaptiveAvgPool1d` = **media** per gruppo
   (non somma) → valori = conteggio medio per canale originale; output float64
   (`np.float`, rimosso in numpy ≥ 2: il legacy non gira su numpy moderni). —
   lettura-codice (raw_reader.py:537-544).
7. **dtype legacy**: datacube uint16; overflow se una cella (pixel, canale)
   supera 65 535 eventi. Max per cella negli esempi: **non misurato** — non
   verificato. — lettura-codice (raw_reader.py:293-295).
8. **Precisione nuova (decisione)**: datacube uint32 (fino a 4.29e9
   eventi/cella), float64 per griglie energia e aritmetica. — AGENTS.md §4.
9. **Calibrazione nuova (proposta)**: binning che **conserva l'energia**
   (somma nei bin, `searchsorted`); E_range = crop opzionale, default nessuna
   crop. Invariante: `sum(out) == sum(in)` sui canali dentro E_range. — test a M2.
10. **Rebin nuovo (proposta)**: default **sum** (conserva i conteggi totali);
    opzione `mean` per compatibilità legacy (valori medi per gruppo). — test a M2.