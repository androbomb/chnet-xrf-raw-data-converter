# Data format — raw MA-XRF (Fi MA-XRF, INFN-CHNet)

Status: M1 (2026-11-17) — grammatica verificata su 2 file di esempio +
lettura del codice legacy + 5 passate streaming (awk, mawk-safe) + riprova
Python (M1) che fissa la struttura esatta delle anomalie (§4). I punti
marcati «ASSUNTO» richiedono conferma strumentale (operational_plan.md §9).

## 1. Varianti di file

- **Formato A — XML + dati**: riga 1 `<?xml version="1.2" encoding="UTF-8"?>`,
  root `<XRFanalysis>` con sezioni metadati, poi `<analysisData>` con lo stream
  eventi e chiusura `</analysisData></XRFanalysis>`.
  Esempio: `data_example/mappa11.txt` (99 MB).
- **Formato B — solo dati**: solo lo stream eventi, con possibile riga vuota di
  testa. Nei due esempi è presente anche la chiusura `</analysisData>
  </XRFanalysis>` (XML malformato: chiusura senza apertura). Nessun metadato,
  quindi **nessuna calibrazione** recuperabile dal file.
  Esempio: `data_example/Ragazzo-triste_area4_centrodx_38-80.txt` (284 MB).
- Il lettore legacy **crasha sul formato B** (vedi `legacy_audit.md` L1):
  `ET.fromstring` sul corpo di soli numeri non è protetto.
- Rilevamento formato: la prima riga non vuota inizia con `<?xml` → A,
  altrimenti → B. Il reader gestisce in entrambi i casi la presenza/assenza
  dei tag di chiusura (righe non numeriche ignorate).

## 2. Metadati XML (formato A)

XML non standard: i nomi dei tag contengono `()`, `/` e spazi; i valori sono
stringhe quotate. Il legacy riscrive i caratteri prima del parse
(`custom_escape_parser`, raw_reader.py:451-476); il nuovo reader parsea
**riga per riga** con regex sul pattern `<name>"value"</name>` (implementato
a M1 in `xrfraw/data/meta.py`; niente ET, niente riscrittura dei tag).

| sezione | campo | esempio mappa11 | significato |
| ------- | ----- | --------------- | ----------- |
| tube | tubeVoltage(kV) | "35" | tensione tubo |
| tube | tubeCurrent(uA) | "100" | corrente tubo |
| calibration | calibration_keV/ch | "0.00259259" | `m` di E = m·ch + q |
| calibration | calibration_Offset | "-0.0355556" | `q` di E = m·ch + q |
| tools | Telemeter(y/n) | "n" | flag |
| tools | Helium(y/n) | "n" | flag |
| coll | Collimator Diameter (mm) | "0.8" | diametro collimatore |
| analysisInfo | Xmin / Xmax | 5000 / 290000 | estensione X del piattino |
| analysisInfo | Ymin / Ymax | 190000 / 265000 | estensione Y del piattino |
| analysisInfo | Xstep / Ystep | 1000 / 1000 | passo di scan (il legacy usa Xstep per entrambi, L8) |
| analysisInfo | Velocity | 8000 | velocità di scan (unità ASSUNTA µm/s) |

Il XML **non dichiara** il numero di canali MCA né le unità di X/Y/Velocity.

## 3. Stream eventi (grammatica comune)

Un intero per riga, tre tipi:

1. **Header X**: numero a 8 cifre che inizia con `5` → `x = valore − 50_000_000`
2. **Header Y**: numero a 8 cifre che inizia con `6` → `y = valore − 60_000_000`
3. **Evento**: ogni altro numero → canale `c` (0-based); 1 evento rilevato
   nella posizione corrente `(x, y)` (ultima coppia X+Y vista)

Righe vuote e non numeriche (tag XML) sono ignorate. I dati grezzi sono
**eventi** (fotoni), non conteggi pre-accumulati: ogni riga evento incrementa
di 1 la cella `(y, x, c)` del datacube.

- Struttura stream (verificata su entrambi i file): ogni pixel =
  `header X, header Y, eventi…`; **0 eventi orfani** (eventi tra un header X e
  il successivo header Y) su entrambi i file.
- Ordine di scan (verificato M1): serpentina, Y esterno crescente da Ymin,
  X interno — crescente nelle righe dispari, decrescente nelle pari.
- **Anomalie di struttura** (osservate, §4) — il reader le riporta in
  `anomalies` e marca i pixel interessati con `mask=False`, senza correzioni
  silenziose:
  - `missing_row` / `missing_column`: pixel della griglia assente (mancano
    gli header Y/X) — caso osservato in entrambi i file;
  - `dangling_x_marker`: header X non seguito da header Y (duplicato
    intra-stream, difensivo, o a fine file — quest'ultimo è il caso reale
    osservato in Ragazzo); nessun evento gli viene attribuito.
- Vincoli (ASSUNTI): `x, y ≤ 99_999_999` (codifica a 8 cifre); canali
  realisticamente ≤ 16383 (MCA 16384 ch; nei due esempi max ≤ 15999).

## 4. Misure reali (M0, passate streaming, 2026-11-17)

| | mappa11.txt (A) | Ragazzo-…_38-80.txt (B) |
| --- | --- | --- |
| righe totali | 19 868 439 | 56 723 562 |
| righe numeriche | 19 868 409 | 56 723 558 |
| header X | 21 660 (285 distinti) | 31 175 (215 distinti) |
| header Y | 21 659 | 31 174 |
| **eventi** | **19 825 090** | **56 661 209** |
| X osservato | 5000..289000, step 1000 | 5000..219000, step 1000 |
| Y osservato | 190000..265000, step 1000 | 5000..149000, step 1000 |
| griglia dichiarata/inferita | 286×76 (XML) | 215×145 (inferita) |
| **canale max** | **15902** | **15999** |
| eventi/pixel | 915.3 | 1818.6 |
| eventi orfani | 0 | 0 |
| pixel acquisiti (coppia X+Y) | 21 659 | 31 174 |

Anomalie misurate (riprovate a M1 con sonda Python riga per riga):

- **mappa11**: la colonna dichiarata X=290000 (Xmax) è **assente** dallo scan
  → 76 pixel non acquisiti (`missing_column`, 1 riga di anomalia).
- **mappa11**: il pixel (5000, 265000) — ultimo pixel dell'ultima riga
  (riga y=265000 in ordine discendente x=289000→6000, stop a x=6000) — non
  è acquisito: vista per colonna, la colonna x=5000 ha 75 marker Y
  (190000..264000) → `missing_row`.
- **mappa11**: il file termina con il **marker X(5000) di quel pixel non
  acquisito** (ultima riga di dati `50005000`, poi riga vuota e tag di
  chiusura) — 0 eventi (`dangling_x_marker`, `at="eof"`): è l'header del
  pixel mancante, non un marker orfano.
- **Ragazzo**: il pixel (219000, 149000) — ultimo pixel dell'ultima riga
  (riga y=149000 in ordine ascendente x=5000→218000, stop a x=218000) — non
  è acquisito: vista per colonna, la colonna x=219000 ha 144 marker Y
  (5000..148000) → `missing_row`.
- **Ragazzo**: il file termina con il **marker X(219000) di quel pixel non
  acquisito** (ultima riga di dati, subito prima dei tag di chiusura) —
  0 eventi (`dangling_x_marker`, `at="eof"`).
- Entrambi: nessuna riga evento orfana; Ragazzo ha una riga vuota in testa.

Totale pixel non acquisiti: mappa11 **77/21 736** (76 colonna + ultimo
  pixel ultima riga); Ragazzo **1/31 175** (ultimo pixel ultima riga).

## 5. Profondità canali (NC)

- Il file non dichiara NC. Il legacy la deriva come
  `NC = max(canali osservati) + 1` (15903/16000 qui): **trunca i canali
  finali vuoti** del MCA (legacy_audit L7; `get_depth`).
- Regola nuova (kickstart): **NC è un parametro esplicito** (o dichiarato nei
  metadati), mai `max(observed)+1`.
- Default strumentale: **16384** (suggerito dal legacy
  `rebin_size = 16384//divisor` — lettura-codice, **UNVERIFIED**, conferma N1).
- I canali oltre il max osservato si conservano a zero (sono parte del MCA,
  possono aver avuto 0 eventi in questa acquisizione).
- Se un canale osservato ≥ NC → errore esplicito (l'utente alza NC).

## 6. Formato B: metadati mancanti

- Griglia (min/max/step di X e Y): **inferibile dagli header**; univoca solo se
  lo step è uniforme (altrimenti errore: griglia ambigua).
- Calibrazione (m, q) e metadati tubo/collimatore: **non recuperabili** dal
  file; fornibili via metadati esterni opzionali (JSON).
- Conflitti XML vs metadati esterni: **niente overwrite silenzioso** —
  confronto campo a campo; su disaccordo → errore esplicito con i due valori
  (test F12).

## 7. Unità

- L'XML non dichiara unità per Xmin/Xmax/Xstep/Ymin/Ymax/Ystep/Velocity.
- Default ASSUNTO: **µm** per X/Y, **µm/s** per Velocity (conferma N4).
  Finché non confermato, i valori escono marcati `units_status: assumed`.
