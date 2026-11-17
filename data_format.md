# Data format — raw MA-XRF (Fi MA-XRF, INFN-CHNet)

Status: M0 — grammatica verificata su 2 file di esempio + lettura del codice
legacy (2026-11-17). I punti marcati «ASSUNTO» richiedono conferma utente.

## 1. Varianti di file

- **Formato A — XML + dati**: riga 1 `<?xml version="1.2" encoding="UTF-8"?>`,
  root `<XRFanalysis>` con sezioni metadati, poi `<analysisData>` con lo stream
  eventi e chiusura `</analysisData></XRFanalysis>`.
  Esempio: `data_example/mappa11.txt` (99 MB).
- **Formato B — solo dati**: solo lo stream eventi, con possibile riga vuota di
  testa. Nei due esempi è presente anche la chiusura `</analysisData>
  </XRFanalysis>` (XML malformato: chiusura senza apertura). Nessun metadato,
  quindi **nessuna calibrazione**.
  Esempio: `data_example/Ragazzo-triste_area4_centrodx_38-80.txt` (284 MB).
- Il lettore legacy **crasha sul formato B** (vedi `legacy_audit.md` L1):
  `ET.fromstring` sul corpo di soli numeri non è protetto.

## 2. Metadati XML (formato A)

XML non standard: i nomi dei tag contengono `()`, `/` e spazi; i valori sono
stringhe quotate. Il legacy riscrive i caratteri prima del parse
(`custom_escape_parser`, raw_reader.py:451-476); il nuovo reader deve fare
equivalente (decisione implementativa a M1: regex o stessa riscrittura).

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
| analysisInfo | Xstep / Ystep | 1000 / 1000 | passo di scan |
| analysisInfo | Velocity | 8000 | velocità di scan (unità ASSUNTA µm/s) |

## 3. Stream eventi (grammatica comune)

Un intero per riga, tre tipi:

1. **Header X**: numero a 8 cifre che inizia con `5` → `x = valore − 50_000_000`
2. **Header Y**: numero a 8 cifre che inizia con `6` → `y = valore − 60_000_000`
3. **Evento**: ogni altro numero → canale `c` (0-based); 1 evento rilevato
   nella posizione corrente `(x, y)`

Righe vuote e non numeriche (tag XML) sono ignorate. Ogni evento incrementa di
1 la cella `(x, y, c)` del datacube: i dati grezzi sono **eventi** (fotoni),
non conteggi pre-accumulati.

- Datacube: `(NX, NY, NC)` con `NC = max_canale + 1` per file.
- Ordine di scan (verificato su entrambi gli esempi): X esterno crescente da
  Xmin; Y interno crescente da Ymin.
- Vincoli (ASSUNTI): `x, y ≤ 99_999_999` (codifica a 8 cifre); canali
  realisticamente ≤ 16383 (MCA 16384 ch; nei due esempi max ≤ 15999).

## 4. Misure reali (M0, passata streaming su file interi, 2026-11-17)

| | mappa11.txt | Ragazzo-…_38-80.txt |
| --- | --- | --- |
| variante | A | B |
| righe totali | 19 868 439 | 56 723 562 |
| header X | 21 660 (285 distinti) | 31 175 (215 distinti) |
| header Y | 21 659 | 31 174 |
| eventi (righe conteggio) | 19 825 090 | 56 661 209 |
| X osservato | 5000..289000 | 5000..219000 |
| Y osservato | 190000..265000 | 5000..149000 |
| griglia dichiarata/inferita | 286×76 | 215×145 |
| canale max | 15902 (depth 15903) | 15999 (depth 16000) |
| eventi/pixel | 915.3 | 1818.6 |

Anomalie osservate:

- mappa11: X=290000 (Xmax dichiarato) **assente** dallo scan; un blocco X ha
  75 header Y invece di 76 (1 pixel mancante).
- Ragazzo: un blocco X ha 144 header Y invece di 145 (1 pixel mancante).
- Entrambi: righe vuote iniziali/finali; Ragazzo termina con un header senza
  eventi.

Comportamento scelto (come legacy): i pixel mancanti restano **zero** sulla
griglia completa dichiarata (A) o inferita (B).

## 5. Formato B: metadati mancanti

- Griglia (min/max/step di X e Y): **inferibile dagli header**.
- Calibrazione (m, q) e metadati tubo/collimatore: **non recuperabili** dal
  file; vanno forniti esternamente (JSON o blocco XML di un formato A) —
  decisione D1, in attesa di conferma.
