# Guida: chnet-xrf-raw-data-converter (ambiente con `uv`, UI, Python, CLI)

Questa guida ti porta da zero a un ambiente Python funzionante con **uv**, e ti
mostra le tre modalità d'uso del convertitore raw MA-XRF → HDF5/NPZ
(`chnet-xrf-raw-data-converter`, importato come `xrfraw`):

- **UI** — interfaccia web nel browser/notebook, per esplorare un file e
  scaricare l'output col click;
- **Python** — alcune righe in un notebook, per pipeline custom;
- **CLI** — comandi in terminale, per batch e riproducibilità.

Sono la stessa pipeline sotto il cofano: stessa validazione, stesso output.

> **Sei in fretta? I 5 comandi che servono** (dalla tua cartella di lavoro):
>
> ```bash
> uv venv xrfraw-env
> source xrfraw-env/bin/activate        # Windows: .\xrfraw-env\Scripts\Activate.ps1
> uv pip install "chnet-xrf-raw-data-converter[ui]" ipykernel jupyterlab
> python -m ipykernel install --user --name=xrfraw --display-name "Python (xrfraw)"
> jupyter lab
> ```
>
> Poi segui la sezione 5 (UI) o la 7 (Python). Il resto è il "come e perché".

---

## 0. Installare `uv` (una sola volta)

`uv` è un gestore di pacchetti e ambienti Python estremamente veloce, scritto
in Rust: sostituisce `pip`, `virtualenv` e gli step affini. Si installa una
volta sola sul sistema.

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verifica:

```bash
uv --version
```

Dovresti vedere `uv 0.xx.x`. Se il comando non viene trovato, riapri il
terminale o verifica che `~/.local/bin` (macOS/Linux) o
`%USERPROFILE%\.local\bin` (Windows) sia nel `PATH`.

---

## 1. Creare l'ambiente virtuale `xrfraw-env`

L'ambiente serve a isolare i pacchetti di questo lavoro dal resto del
sistema (niente conflitti di versioni, niente "ho rotto" il Python globale).

**Dove crearlo**: nella cartella in cui vuoi tenere raw file, output e
notebook — la tua cartella di lavoro (es. `C:\Misure\XRF` su Windows,
`~/misure/xrf` su macOS/Linux). Posizionati lì e crea l'ambiente:

```bash
uv venv xrfraw-env
```

Puoi fissare la versione di Python (consigliato 3.12 o 3.13):

```bash
uv venv xrfraw-env --python 3.12
```

Se la versione richiesta non c'è già, `uv` la scarica da solo. Nasce la
cartella `xrfraw-env/` con dentro l'interprete.

---

## 2. Attivare l'ambiente

**macOS / Linux:**

```bash
source xrfraw-env/bin/activate
```

**Windows (PowerShell):**

```powershell
.\xrfraw-env\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
xrfraw-env\Scripts\activate.bat
```

Dopo l'attivazione il prompt mostra il nome dell'ambiente
(`(xrfraw-env)`). **Da qui in poi tutti i comandi (uv, python, jupyter,
xrf-raw-to-h5) girano dentro l'ambiente**, finché non chiudi il terminale o
non lo disattivi (`deactivate`). Ogni volta che apri un terminale nuovo
riparti dall'attivazione — due secondi.

### ⚠️ 2.1 Correzione: errore "script non firmato" su PowerShell

Su Windows, al primo tentativo di attivazione potresti vedere:

```
.\xrfraw-env\Scripts\Activate.ps1 : Impossibile caricare il file ... non è
firmato digitalmente. Lo script non può essere eseguito nel sistema corrente.
    + CategoryInfo          : Errore di protezione: (:) [], PSSecurityException
```

PowerShell blocca di default gli script non firmati, e `Activate.ps1` lo è.
Soluzioni:

#### Permanente per il tuo utente (consigliata, una volta sola)

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Conferma con `Y`. Serve admin.

#### Temporanea (solo questo terminale)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Poi rilancia `.\xrfraw-env\Scripts\Activate.ps1`.

#### Dal pannello di Windows

**Impostazioni → Privacy e sicurezza → Per sviluppatori → sezione PowerShell**
→ attiva *"Modifica i criteri di esecuzione per consentire gli script locali
non firmati"* → **Applica**.

#### Ultima spiaggia: sblocca il file

Tasto destro su `xrfraw-env\Scripts\Activate.ps1` → **Proprietà** → in fondo
alla scheda Generale, se c'è la voce **"Sblocca"**, spuntala → OK.

| Metodo | Comando / Azione | Ambito |
| :--- | :--- | :--- |
| Sessione corrente (temporaneo) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` | solo il terminale aperto |
| Utente corrente (permanente) | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` | il tuo account |
| Pannello di Windows | Per sviluppatori → PowerShell → Applica | utente corrente |
| Sblocca file | Proprietà di `Activate.ps1` → "Sblocca" → OK | quel file |

---

## 3. Installare i pacchetti

Con l'ambiente attivo, in un solo colpo:

```bash
uv pip install "chnet-xrf-raw-data-converter[ui]" ipykernel jupyterlab
```

Cosa stai installando:

- **`chnet-xrf-raw-data-converter[ui]`** — il convertitore (il core funziona
  anche senza `[ui]`; l'extra `[ui]` aggiunge l'interfaccia web Dash).
  Installato **da PyPI**: prendi sempre l'ultima versione pubblicata.
- **`ipykernel`** — registra l'ambiente come kernel Jupyter.
- **`jupyterlab`** — l'interfaccia Jupyter per aprire i notebook.

Verifica che sia tutto a posto (ti deve rispondere `xrf-raw-to-h5 0.x.y`):

```bash
xrf-raw-to-h5 --version
```

In futuro, altri pacchetti si aggiungono allo stesso modo:
`uv pip install pandas seaborn ...`.

---

## 4. Registrare l'ambiente come kernel Jupyter

```bash
python -m ipykernel install --user --name=xrfraw --display-name "Python (xrfraw)"
```

- `--user`: installa il kernel nella cartella utente, senza privilegi admin.
- `--name=xrfraw`: nome interno del kernel.
- `--display-name`: quello che vedi nel menu a tendina di Jupyter.

Da ora in Jupyter, nel menu **Kernel** (in alto a destra) compare
**Python (xrfraw)**: selezionandolo, il notebook gira dentro `xrfraw-env`.

---

## 5. UI: la finestra web (per esplorare e scaricare)

La UI è una pagina web con l'upload, i parametri, il tasto **Convert** e il
**Download** del file prodotto. È il modo più comodo per la prima volta.

### 5.1 Avviarla dal notebook — codice copia-incolla

In Jupyter Lab crea un nuovo notebook, seleziona il kernel
**Python (xrfraw)** e incolla questa cella:

```python
# Il file da convertire: il percorso completo, oppure None per caricarlo
# dopo dalla UI (upload o link).
path_to_file = None   # es. "C:/Misure/XRF/mappa11.txt" oppure "~/misure/mappa11.txt"

from xrfraw.ui import build_app

app = build_app(path_to_file)
app.run(
    jupyter_mode="inline",   # l'app si apre dentro la cella (iframe)
    debug=False,
    jupyter_height=800,
)
```

Esegui la cella: **la UI si apre dentro la stessa cella** (iframe). Se
preferisci la UI in una tab del browser (meglio per lo schermo grigio, vedi
sotto): commenta `jupyter_mode="inline"` e usa `app.run()` — poi apri
`http://127.0.0.1:8050` nel browser.

> Se usi il repository, il notebook `example.ipynb` già contiene questa cella
> (più una cella che riattiva i log del server, comoda se qualcosa non parte).

### 5.2 Come si usa (user experience)

Lo schermo ha tre zone:

**1) Dare il file** — tre modi, usa quello che comodi:

- **Upload** (trascina il `.txt` nell'area): solo file **< ~48 MB**, il
  browser li carica in memoria.
- **Load from link** (incolla l'URL, tasto): per file grandi. Il server si
  scarica il file da solo (verificato: 99 MB in ~13 s, 284 MB in ~64 s).
  Ogni link ha un nome file univoco; link interrotto = nessun file tronco.
- **path_to_file**: il file è già sulla macchina — o lo hai messo nella cella
  della sezione 5.1, oppure lo scrivi nel campo dedicato.

**2) I parametri** (nessuno è obbligatorio: i default sono quelli
strumentali, per un file normale non tocchi nulla):

| Campo | Default | Cosa fa, in parole povere |
| :--- | :--- | :--- |
| `out_path` | vuoto | dove salvare l'output. **Vuoto = va in una cartella temporanea** e il tasto *Download file* sotto lo scarica col click. |
| `fmt` | `h5` | formato di output: `h5` (HDF5) o `npz` (NumPy). Stessi contenuti, contenitore diverso. |
| `n_channels` | `16384` | profondità **esatta** del cubo (numero di canali energia). Se il file ha canali oltre, errore esplicito: ti dice la potenza di 2 successiva. |
| `dtype` | `uint32` | tipo dei conteggi: `uint32`, `uint16`, `float32`, `float64`. Per il visualizer xrf usa `float32`. |
| `rebin size` / `rebin how` | off | rebinning spaziale esplicito (es. 2 = raggruppa 2×2 pixel, `sum` o `mean`). |
| `rebin_to` | off | riduci la profondità dei canali a un valore tondo (512/1024/2048/4096/8192), solo somma: es. `2048` per un cubo leggero. **Non si usa insieme a `rebin size/how`.** |
| `cal m` / `cal q` | dal file | calibrazione energia `energia[i] = m·i + q`; se il file non ce l'ha e non la dai, l'output resta "non calibrato" e lo dice in chiaro. |
| `metadata` | off | file `meta.json` esterno: serve ai file di formato B senza griglia dentro. |
| `compress` | 4 | compressione gzip 0-9 (0 = nessuna). Più alto = file più piccolo, CPU più alta. |
| `overwrite` | spuntato | se il file esiste già: sostituirlo (spuntato) o fermarsi (non spuntato). |

**3) Convert e Download:**

- Premi **Convert** → parte lo spinner, poi la riga di status.
- **Riga OK = conversione riuscita**, con i numeri:
  `OK: (145, 215, 16384) uint32, 56,661,209 eventi, non calibrato, 45.3 MB in 46.6 s`
  (forma, dtype, numero eventi, dimensione e tempo).
- **Download file**: scarica l'ultimo output riuscito (il percorso completo
  c'è sempre nella riga di status, utile se vuoi il file senza cliccare).

### 5.3 Problemi classici (due minuti, non di più)

- **Schermo grigio nell'iframe**: l'app gira, è il proxy del notebook che non
  la mostra. Apri `http://127.0.0.1:8050` in una **tab normale del browser**:
  è identica (e lì funziona anche F12 per i log).
- **La tab 8050 mostra un'altra app**: la porta 8050 è una sola per
  macchina — chiudi l'altra app o fai *Kernel → Restart* e ri-esegui la cella.
- **Click su Convert che non fa nulla**: guarda i log — nel notebook la cella
  diagnostica di `example.ipynb` li riattiva; cerca righe `[xrfraw-ui]
  CONVERT` (a ogni click) e `Converting file ... OK:` (il lavoro vero).
- **Testo bianco nei campi**: era il "dark mode" forzato del browser; l'app
  lo gestisce già — `git pull` (se usi il repo) e *Kernel → Restart*.

---

## 6. UI dal terminale (senza notebook)

Stessa UI, senza Jupyter:

```bash
xrf-raw-to-h5 --help        # i comandi della CLI
```

per l'UI vera e propria, da un terminale con l'ambiente attivo:

```bash
python -c "from xrfraw.ui import build_app; build_app().run()"
```

→ apre `http://127.0.0.1:8050` nel browser. Premi `Ctrl+C` nel terminale per
chiuderla.

---

## 7. Python: il notebook per l'uso senza UI

Per chi vuole le pipeline in Python (o verificare senza aprire l'UI).
Crea un notebook, kernel **Python (xrfraw)**, e copia queste celle in ordine.

### Cella 1 — versione e ambiente

```python
import sys
import xrfraw

print("Python:", sys.version.split()[0])
print("Eseguibile:", sys.executable)      # deve contenere "xrfraw-env"
print("xrfraw:", xrfraw.__version__)
```

Se `sys.executable` NON contiene `xrfraw-env`, hai sbagliato kernel: in alto
a destra seleziona **Python (xrfraw)** e ri-esegui.

### Cella 2 — ispezionare il raw PRIMA di convertire (niente da pagare)

```python
from xrfraw import inspect_raw

info = inspect_raw("mappa11.txt")   # percorso al tuo raw .txt
print(info)
```

Ti dice, **senza allocare nulla**: formato (A o B), griglia, numero eventi,
canale massimo, memoria stimata, eventuali anomalie. Se `ok: False`, il file
ha un problema — non convertire.

### Cella 3 — conversione minima

```python
from xrfraw.io import convert_file

ds = convert_file("mappa11.txt", "out/mappa11.h5", overwrite=True)
print(ds.img.shape, ds.img.dtype, ds.metadata["n_events"])
# es. (76, 286, 16384) uint32 19825090
```

`overwrite=True` così la seconda esecuzione non sbatte su file esistente.
Se non vuoi sovrascrivere: toglilo e, se il c'è già, ti risponde con un
errore esplicito (niente sorprese).

### Cella 4 — conversione con opzioni

```python
# cubo leggero per il visualizer: float32 + profondità canali 2048
ds = convert_file("ragazzo_triste.txt", "out/rt_2048.h5",
                  dtype="float32", rebin_to=2048, overwrite=True)
print(ds.img.shape, ds.img.dtype, ds.metadata["n_events"])
# es. (145, 215, 2048) float32 56661209   <-- totali conservati dal rebin (sum)
```

Le opzioni a disposizione (sono le stesse della UI, come keyword):
`fmt`, `n_channels`, `dtype`, `metadata`, `rebin_spec=(size, "sum"|"mean")`,
`rebin_to`, `cal={"m": ..., "q": ...}`, `compress`, `overwrite`.

### Cella 5 — leggere il file prodotto (verifica)

```python
import h5py

with h5py.File("out/mappa11.h5", "r") as f:
    print("dataset:", list(f.keys()))                 # img, channel, x_axis, y_axis, mask, ...
    print("attr:", {k: f.attrs[k] for k in ("format", "n_events", "dtype")})
    img = f["img"]
    print("cubo:", img.shape, img.dtype, "eventi totali:", int(img[...].sum()))
```

Se il totale eventi qui coincide con quello della Cella 3, il file è sano.

---

## 8. CLI: i comandi per batch e script

Tutto in terminale, ambiente attivo (`(xrfraw-env)` nel prompt).

```bash
# il minimo: h5, 16384 canali, uint32, compressione 4
xrf-raw-to-h5 mappa11.txt -o out/

# tutta una cartella di raw (converte ogni .txt dentro)
xrf-raw-to-h5 ./raws -o out/

# per il visualizer: float32 e profondità 2048 (file più leggero)
xrf-raw-to-h5 ragazzo_triste.txt -o out/ --dtype float32 --rebin-to 2048

# npz senza compressione, sovrascrittura esplicita
xrf-raw-to-h5 mappa11.txt -o out/ --format npz --compress 0 --overwrite
```

**Tutti i flag** (da `xrf-raw-to-h5 --help`):

| Flag | Default | Note |
| :--- | :--- | :--- |
| `input` (posizionale) | — | un `.txt`, o una cartella di `.txt` |
| `-o`, `--out-dir` | **obbligatorio** | cartella output (creata se manca) |
| `--format` | `h5` | `h5` o `npz` |
| `--n-channels` | 16384 | profondità esatta del cubo; canale oltre = errore |
| `--dtype` | `uint32` | `uint16`, `float32`, `float64` |
| `--metadata` | off | JSON esterno (formato B senza griglia) |
| `--rebin SIZE HOW` | off | es. `--rebin 2 sum`; `HOW` = `sum` o `mean` |
| `--rebin-to` | off | profondità target 512/1024/2048/4096/8192, solo sum. **Esclusivo** con `--rebin` |
| `--compress` | 4 | gzip 0-9 (0 = nessuna) |
| `--overwrite` | **off** | la CLI non sovrascrive mai senza questo flag |
| `--version` | — | la versione |

**Codici di uscita**: `0` ok, `1` uno o più file falliti (l'errore è sulla
riga, il batch continua), `2` errore d'uso (flag sbagliati).

---

## 9. Cos'hai in mano (l'output)

`.h5`/`.npz` con il cubo **`img (y, x, channel)`** — attenzione all'ordine
assi: righe, colonne, canali ADC — più:

- `channel`: gli indici dei canali;
- `x_axis`, `y_axis`: le posizioni in µm;
- `mask`: `False` = pixel non acquisito;
- `energy`: c'è **solo** se il file è calibrato;
- metadati (origine, griglia, calibrazione, anomalie) come attributo
  `metadata_json`.

I conteggi **non vengono mai** modificati in silenzio: niente auto-rebin,
niente auto-crop — ogni trasformazione è un tuo comando esplicito.

---

## 10. Numeri reali (WSL, single-thread)

| File | Input | Eventi | Tempo | Peak RAM | Output |
| :--- | :--- | :--- | :--- | :--- | :--- |
| mappa11 | 99 MB | 19.8 M | ~18 s | 1.5 GB | 21 MB h5 |
| ragazzo triste | 284 MB | 56.7 M | ~47 s | 2.1 GB | 45 MB h5 |

Su Windows (C-drive + antivirus) metti in conto il doppio del tempo.

---

## 11. Riepilogo dei comandi

| Passo | Comando |
| :--- | :--- |
| Installare `uv` (una volta) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) oppure `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` (Windows) |
| Creare l'ambiente | `uv venv xrfraw-env` |
| Attivare (macOS/Linux) | `source xrfraw-env/bin/activate` |
| Attivare (PowerShell) | `.\xrfraw-env\Scripts\Activate.ps1` |
| Correzione PowerShell (una volta) | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| Installare i pacchetti | `uv pip install "chnet-xrf-raw-data-converter[ui]" ipykernel jupyterlab` |
| Registrare il kernel | `python -m ipykernel install --user --name=xrfraw --display-name "Python (xrfraw)"` |
| Avviare Jupyter Lab | `jupyter lab` |
| Selezionare il kernel | nel menu Kernel di Jupyter: **Python (xrfraw)** |
| UI dal notebook | cella della sezione 5.1 (copia-incolla) |
| UI dal terminale | `python -c "from xrfraw.ui import build_app; build_app().run()"` |
| Conversione minima (CLI) | `xrf-raw-to-h5 FILE_OR_DIR -o out/` |
| Verifica install | `xrf-raw-to-h5 --version` |