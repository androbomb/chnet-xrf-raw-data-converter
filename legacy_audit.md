# Legacy audit — original_code/raw-xrf-to-h5-opener-python-master

Status: M0 v2, 2026-11-17. Tutto in **sola lettura**; il legacy resta
riferimento e non viene importato dal nuovo runtime. Stato di ogni voce:
verificato (esecuzione) / lettura-codice / da verificare.

## 1. Problemi verificati

| # | Problema | Evidenza | Stato |
| - | -------- | -------- | ----- |
| L1 | **Crash sul formato B (solo dati)**: `ET.fromstring` sul corpo numerico non protetto da try/except → `ParseError` in `__init__` | raw_reader.py:142-159; try a 145-156 copre solo l'escape parser; `ParseError` riprodotto con stdlib ET sul file di esempio | **verificato** |
| L2 | Memoria: file letto intero + `split('\n')` → lista di ~56.7M stringhe Python (picco multi-GB) + array int | raw_reader.py:142, 262-263 | lettura-codice |
| L3 | Calibrazione O(N²) in Python puro (doppio loop su ~15 903² elementi) | raw_reader.py:591-604 | lettura-codice |
| L4 | Calibrazione **perdente**: `cal[:, :, j] = xrf[:, :, i]` (overwrite) + `j` non azzerato → canali fuori E_range collassano su bin estremi (vince l'ultimo) | raw_reader.py:585, 603; quantificato in scientific_notes §5 | lettura-codice |
| L5 | CLI: parametro `E_range` di `from_raw_to_h5` ignorato, hardcoded (0.5, 38.5) | convert_raw_to_h5.py:21 vs 31 | lettura-codice |
| L6 | CLI batch: `os.walk` restituisce `root` ma il path costruito usa `raw_data_path + file` → sottocartelle rotte | convert_raw_to_h5.py:161, 169 | lettura-codice |
| L7 | `rebin_size = 16384//divisor` assume depth == 16384; negli esempi depth = 15903/16000 → con divisor=1 il rebin **non scatta** (condizione `rebin_size < depth` falsa). Evidenza che la profondità MCA strumentale sia 16384 | convert_raw_to_h5.py:30; raw_reader.py:438 | lettura-codice |
| L8 | `Ystep` letto ma ignorato: `Xstep` usato per entrambi gli assi | raw_reader.py:235, 285 | lettura-codice |
| L9 | Off-by-one latenti: `int(line) <= shape[-1]` per il canale e `pixelX <= shape[0]` → IndexError potenziali (non innescati dai dati di esempio) | raw_reader.py:330-332 | lettura-codice |
| L10 | Datacube uint16: overflow silenzioso > 65 535 eventi/cella | raw_reader.py:293-296 | lettura-codice |
| L11 | `torch` usato solo per `AdaptiveAvgPool1d`; `pandas` in requirements mai importato | raw_reader.py:22-24, 537; requirements.txt:2,4 | lettura-codice |
| L12 | Batch: eccezioni ingoiate con print, nessun riepilogo errori; submit non attesi | convert_raw_to_h5.py:39-40, 172-174 | lettura-codice |
| L13 | `np.float` (alias deprecato, rimosso in numpy ≥ 2) → legacy incompatibile con numpy moderni | raw_reader.py:540 | lettura-codice |
| L14 | Parse XML assume `analysisData` figlio diretto della root | raw_reader.py:260 | lettura-codice |
| L15 | Euristiche header hardcoded (prima cifra 5/6, valore > 17000): fragili se MCA > 16 384 ch o coordinate fuori range | utils.py:13-18 | lettura-codice |

## 2. Differenze intenzionali legacy → nuovo (contratto kickstart)

| # | Differenza | Motivo |
| - | ---------- | ------ |
| D1 | Supporto formato B + metadati esterni opzionali (JSON) per calibrazione/griglia | L1; entrambi gli esempi in data_example |
| D2 | Reader streaming 2-passate: passata 1 scan (griglia, max canale, validazione, memoria stimata) + passata 2 populate; memoria ~O(cubo) invece di O(file) | L2 |
| D3 | Calibrazione = **allegato del vettore energia**: conteggi element-identical; niente resampling/overwrite/crop | L3, L4, L5; contratto kickstart |
| D4 | **Niente auto-rebinning**; rebin solo opzione esplicita (sum/mean), off di default, dichiarata nei metadati | L11; contratto kickstart |
| D5 | Datacube uint32 di default; opzione uint16 con pre-check overflow | L10; decisione utente Q4 |
| D6 | **NC esplicita** (default strumentale 16384), mai `max(observed)+1`; canali finali a zero conservati | L7, `get_depth`; contratto kickstart |
| D7 | Ordine output **(y, x, channel)** + maschera di acquisizione `(NY,NX)` nell'output | differenza intenzionale dal legacy (x,y,channel) senza mask |
| D8 | `Ystep` usato; griglia validata contro gli header osservati; pixel non acquisiti → `mask=False` (non solo zero indistinguibile) | L8; anomalie in data_format §4 |
| D9 | Fuori-range / righe malformed / marker dangling → errore esplicito con numero di riga o anomalia riportata; niente skip silenziosi | L9, L15 |
| D10 | Dipendenze: numpy + h5py + tqdm; **niente** torch, pandas, JAX | L11 |
| D11 | CLI single-file + loop batch semplice (niente process pool); errori per-file riportati, non ingoiati | L6, L12 |
| D12 | Output NPZ aggiunto + schema comune (assi, mask, channel, metadata_json) | richiesta utente; output_schema.md |

## 3. Non verificato (manca in questo ambiente / richiede esecuzione)

- Valore strumentale NC = 16384: suggerito da L7, **da conferma utente (N1)**.
- Comportamento sui marker X dangling (mappati: (5000,265000) mappa11,
  (219000,149000) Ragazzo; 0 eventi): proposta "anomalia + mask=False",
  da conferma.
- Max conteggio per cella (pixel, canale) nei due esempi (rischio overflow
  uint16): da misurare a M4.
- Semantica esatta di `AdaptiveAvgPool1d` su split non uniformi (no torch qui).
- Se tutti i file reali del formato B portino la chiusura
  `</analysisData>` (i due esempi sì; il reader gestisce entrambi i casi).
- Unità di X/Y e Velocity (µm? µm/s?): da conferma utente (N4).
