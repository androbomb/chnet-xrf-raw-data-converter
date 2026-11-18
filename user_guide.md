# User guide — xrf-raw-to-h5

Guida operativa: cosa fare, cosa puoi fare, con i numeri reali.
Dettagli tecnici: `data_format.md` (input), `output_schema.md` (output),
`scientific_notes.md` (calibrazione/precisione).

## 1. Che cosa fa

Legge un raw MA-XRF (Fi MA-XRF / INFN-CHNet) — formato **A** (XML+dati) o
**B** (solo dati, 284 MB di eventi) — e scrive un cubo
`img (y, x, channel)` in `.h5` o `.npz`, con assi, maschera, metadati e
calibrazione energia come allegato. I conteggi **non** vengono mai
modificati: niente auto-rebin, niente auto-crop — tutto è esplicito.

## 2. I tre ingressi — quando usarne uno

| Ingresso | Quando | Come |
| -------- | ------ | ---- |
| **UI** | Esplorare un file, parametri a vista, output da scaricare col browser | notebook (`example.ipynb`) o terminale → browser |
| **CLI** | Batch, script, riproducibilità | `xrf-raw-to-h5 FILE_OR_DIR -o OUT_DIR [opzioni]` |
| **API** | Pipeline custom in Python | `from xrfraw import inspect_raw, read_raw, ...` |

Sono la stessa pipeline: stessa validazione, stesso output.

## 3. Input: come dai il file

- **Formato A o B**: non devi scegliere niente — il reader lo riconosce e
  valida *prima* di allocare il cubo (file rotto = errore subito, niente
  mezz'ora di lavoro buttato).
- **UI, tre modi**:
  - *Upload*: solo file **< ~48 MB** (il browser li base64-izza in memoria).
  - ***Load from link***: per file grandi — il server scarica direttamente
    (verificato a 99 MB in ~13 s e a 284 MB in ~64 s). Ogni link ha un nome
    file univoco; link interrotto = nessun file tronco.
  - *path_to_file*: il file è già sulla macchina del server (es.
    `C:\...\mappa11.txt` su Windows).
- **CLI**: un file, oppure una cartella (converte tutti i raw dentro).

## 4. Parametri: cosa devi / puoi impostare

**Cosa devi**: niente. I default sono gli default strumentali; per un file
normale converti senza toccare nulla.

**Cosa puoi** (UI: campo con tooltip; CLI: flag; API: keyword):

| Parametro | Default | Nota |
| --------- | ------- | ---- |
| `n_channels` | **16384** | profondità **esatta** del cubo. Canali oltre = errore esplicito (suggerisce la potenza di 2 successiva). *UNVERIFIED come default strumentale (N1)* |
| `dtype` | `uint32` | `uint16` (conteggi 16 bit), `float32`/`float64` per consumer che richiedono floating — **`float32` è il target di dash-xrf-visualizer** |
| `out_path` | vuoto | vuoto → `<temp>/xrfraw_ui/<nome>_<n_channels>.<fmt>` + tasto **Download file** |
| `fmt` | `h5` | `npz` = stessi campi logici, diverso contenitore |
| `rebin size/how` | off | rebinning spaziale esplicito (2 = somma 2×2) |
| `rebin_to` | off | profondità target {512…8192}, solo sum — es. `2048` per un cubo leggero |
| `cal m / cal q` | da XML | calibrazione energia `energy[i]=m·i+q`; se m/q ignoti l'output è *non calibrato* (asse `channel`) e lo dice in chiaro |
| `metadata` | off | `meta.json` per i file di formato B senza griglia |
| `compress` | 4 | gzip 0-9 (0 = nessuno) |
| `overwrite` | on (UI) / **off** (CLI) | la CLI non sovrascrive mai senza `--overwrite` |

## 5. Output: cos'hai in mano

`.h5`/`.npz` con: `img (NY,NX,NC)` — ordine **(y, x, channel)**,
**canale = indice ADC**, canali finali a zero se il file non li riempie —
+ `channel`, `x_axis`/`y_axis` (µm), `mask` (`False` = non acquisito),
`metadata_json` (origine, griglia, calibrazione, anomalie, transforms).
`energy` c'è **solo se calibrato**.

**Linea OK = controllo fatto**:
`OK: (145, 215, 16384) uint32, 56 661 209 eventi, non calibrato, 45.3 MB in 38.7 s`
— i conteggi totali del cubo sono confrontati con gli eventi letti:
coerente per costruzione, e il check è ripetuto nei test.

## 6. Workflow consigliato

1. **File piccolo/sconosciuto** → UI, *load from link* o path, Convert.
   ~20 s (mappa11) per vedere griglia, eventi, calibrazione, dimensione output.
2. **File grande** (ragazzo triste, 284 MB, 56.7 M eventi) → stesso
   flusso: ~1 min di conversione, **peak RAM ~2.1 GB**, output 45 MB
   (compress 4). Single-thread: su WSL/Windows metti in conto 1-2 min.
3. **Batch / riproducibile** → CLI (sezione 7).
4. **Per il visualizer** → `dtype float32` (UI: dropdown; CLI: `--dtype float32`).

## 7. CLI — quick reference

```bash
# il minimo (h5, 16384, uint32, compress 4)
xrf-raw-to-h5 mappa11.txt -o out/

# cartella intera
xrf-raw-to-h5 ./raws -o out/

# per dash-xrf-visualizer: float32, profondità ridotta
xrf-raw-to-h5 ragazzo_triste.txt -o out/ --dtype float32 --rebin-to 2048

# npz senza compressione, sovrascrittura esplicita
xrf-raw-to-h5 mappa11.txt -o out/ --format npz --compress 0 --overwrite
```

Exit code: `0` ok, `1` conversione fallita, `2` errore d'uso.
Exit 1 = problema nel file (report nella riga d'errore: anomalia, canale
oltre `n_channels`, …) — rileggi `data_format.md` §4 se serve il dettaglio.

## 8. UI — dove aprirla e i suoi limiti

```python
path_to_file = "./data_example/mappa11.txt"
from xrfraw.ui import build_app
app = build_app(src=path_to_file)
app.run(jupyter_mode="inline", debug=False, jupyter_height=800)  # notebook
# da terminale: app.run()  →  http://127.0.0.1:8050
```

- **Porta 8050 fissa** (tutte le app Dash inline della macchina). Se un
 'altra app inline è aperta, l'iframe mostra *quella* — chiudila o
  *Kernel → Restart*.
- **Schermo grigio** = il proxy del notebook non mostra l'app (l'app gira):
  apri `http://127.0.0.1:8050` in una tab normale — identica, e con F12.
  Se ancora no: `Kernel → Restart` + ri-esegui la cell; poi controlla chi
  occupa la 8050 (`netstat -ano | findstr :8050` → `taskkill /PID <pid> /F`).
- **Download file** serve l'output dall'app; il path completo del file è
  sempre nel messaggio di status (utile se la scaricata non arriva: il
  file c'è in `out_path`).
- Un solo Convert alla volta (lock); il click dà status immediato
  "conversione in corso" — se lo vedevi come "non fa nulla" era l'iframe
  morto di sopra, non il callback.

## 9. Numeri reali (WSL, single-thread)

| File | Dimensione | Eventi | Tempo | Peak RAM | Output |
| ---- | ---------- | ------ | ---- | -------- | ------ |
| mappa11 | 99 MB | 19.8 M | 18.1 s | 1.5 GB | 21.3 MB h5 c4 (calibrato) |
| ragazzo triste (area4) | 284 MB | 56.7 M | 46.6 s | 2.1 GB | 45.3 MB h5 c4 (non calibrato) |

Su Windows (C-drive + antivirus) metti in conto 2× sul tempo.

## 10. Limiti conosciuti

- `n_channels` 16384 è il default strumentale **UNVERIFIED** (domanda N1
  aperta) — se i tuoi raw hanno profondità diversa, il reader te lo dice
  subito (errore esplicito, non troncamento).
- Unità spaziali `µm` / velocità `µm/s` sono **assunte** (l'XML non le
  dichiara — N4); dichiarate `units_status: "assumed"` nei metadati.
- Single-thread (scelta di contratto: risorse contate, cap rispettato).
- `original_code/` è legacy di **riferimento**: mai importato, mai
  modificato, gitignored.