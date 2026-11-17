# Scientific notes — raw MA-XRF

Ogni voce: affermazione — fonte — data. Stato: verificato / lettura-codice /
assunto / da verificare.

1. **Calibrazione energia**: `E(ch) = m·ch + q` con m = `calibration_keV/ch`,
   q = `calibration_Offset` (XML). — fonte: XML mappa11 + `calibrate_xrf`
   (raw_reader.py:556) — lettura-codice 2026-11-17; verifica numerica a M2.
2. **Semantica eventi**: ogni riga dello stream = 1 evento rilevato (fotone)
   nel canale c; il datacube è l'istogramma per pixel; totali conteggi =
   numero di righe conteggio (19 825 090 / 56 661 209 negli esempi, misurato).
   — fonte: `single_step_populate` (raw_reader.py:336) + awk M0 —
   verifica per conteggio a M4.
3. **Assi X/Y**: coordinate del piattino (motore). Unità **ASSUNTA µm**
   (l'XML non dichiara unità; step = 1000). — da conferma utente (N4).
4. **Velocity** = 8000, unità ASSUNTA µm/s → dwell per pixel = step/velocity
   = 0.125 s. — assunto (derivato da #3).
5. **Calibrazione legacy (riferimento)**: griglia uniforme su E_range con
   NC0 bin; assegnamento `cal[:, :, j] = xrf[:, :, i]` (**overwrite, non
   somma**) e `j` non azzerato per canale → canali fuori E_range collassano sui
   bin estremi: **~206 canali (basso) + ~1038 (alto) per pixel persi
   silenziosamente** per m=0.00259259, q=−0.0355556, E_range=(0.5, 38.5),
   NC0=15903. — calcolo dalla logica del codice (raw_reader.py:581-604),
   2026-11-17.
6. **Rebin legacy**: `torch.nn.AdaptiveAvgPool1d` = **media** per gruppo
   (non somma) → output float64 (`np.float`, rimosso in numpy ≥ 2: il legacy
   non gira su numpy moderni). — lettura-codice (raw_reader.py:537-544).
7. **dtype legacy**: datacube uint16; overflow se una cella (pixel, canale)
   supera 65 535 eventi. Max per cella negli esempi: **non misurato** —
   da M4. — lettura-codice (raw_reader.py:293-295).
8. **dtype nuovo (decisione Q4)**: datacube **uint32** di default
   (fino a 4.29e9 eventi/cella), opzione `uint16` per compatibilità
   (con pre-check: errore se max cella > 65 535). float64 per griglie
   energia e aritmetica. — test a M2.
9. **Calibrazione nuova (contratto kickstart)**: **allegato puro** — si
   produce il vettore `energy[i] = m·i + q` per i = 0..NC−1 e lo si allega al
   dataset. I conteggi restano **element-identical** (niente resampling,
   niente overwrite, niente crop). Invariante testata:
   `with_calibration(ds).img` bitwise-uguale a `ds.img`; `energy[i] == m*i+q`
   a 10 canali a mano. — test a M2.
10. **Rebin (contratto kickstart)**: **niente auto-rebinning**. Solo opzione
    esplicita, non di default (`sum` | `mean`), dichiarata come
    trasformazione nei metadati di output (`transforms`). `sum` conserva i
    totali; `mean` = media per gruppo (semantica legacy). — test a M2.
11. **Profondità canali (contratto kickstart)**: `NC` = parametro esplicito,
    default strumentale **16384** (suggerito dal legacy
    `rebin_size = 16384//divisor` — **UNVERIFIED**, N1). Mai
    `max(observed)+1`: i due esempi hanno max canale 15902/15999, quindi
    482/385 canali finali a zero si conservano (parte del MCA). — test F9 a M2.
12. **Ordine output**: **(y, x, channel)** — differenza intenzionale dal
    legacy (x, y, channel). Test orientamento asimmetrico (NY ≠ NX). — test F10.
13. **Maschera di acquisizione**: `mask (NY,NX) bool`. Pixel non acquisiti
    (colonna X=290000 assente in mappa11; marker dangling (5000,265000) e
    (219000,149000)) = `False` + zero, riportati in `anomalies`. — M0
    (misure awk), test a M1/M4.
14. **Unità**: µm / µm/s ASSUNTE (l'XML non le dichiara) → marcate
    `units_status: assumed` in output finché l'utente non conferma (N4).
