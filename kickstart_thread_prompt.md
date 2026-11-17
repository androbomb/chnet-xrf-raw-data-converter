# Kickstart thread — first prompt example

Voglio aggiornare il progetto `raw-xrf-to-h5-opener-python`, usando il template generico corretto come base organizzativa. Il codice legacy fornito è un riferimento da preservare, non un'implementazione scientificamente corretta da replicare automaticamente.

IMPORTANTE: la tua working directory è SOLO
`/workspace/exchange/xrf-raw-converter`
Il codice originale, da gitignorare dopo averlo analizzato, è in 
`/workspace/exchange/xrf-raw-converter/original_code`
in 
`/workspace/exchange/xrf-raw-converter/data_example`
trovi due files di esempio, uno XML con metadati e uno “solo data”. 

Leggi i file del progetto e le regole applicabili. Inizia con un M0 in sola lettura e restituisci un piano concreto. Dopo l'approvazione, implementa autonomamente entro lo scope concordato, senza richiedere conferme per ogni modifica ordinaria.

## Obiettivi obbligatori

1. Creare un pacchetto Python installabile da wheel e predisposto per PyPI, con API pubblica, CLI e layout `src/`. La pubblicazione effettiva richiede un'autorizzazione separata.
2. Fornire un notebook `.ipynb` che usi l'API pubblica per validazione, lettura, calibrazione dei metadati ed esportazione.
3. Correggere i bug verificati del legacy con test mirati.
4. Consentire output NPZ e HDF5, con gli stessi dati e la stessa semantica.
5. Preservare i canali ADC originali e i conteggi: nessuna interpolazione, redistribuzione, media, rebinning o ritaglio energetico automatico.
6. Fornire una UI minima per caricare TXT/XML, verificare il contenuto, vedere i metadati, impostare o confermare la calibrazione, scegliere il formato e scaricare l'output.
7. Validare gli input prima di allocare il cubo o iniziare la conversione. Supportare XML con metadati e dati, e dati senza metadati XML; riconoscere il contenuto senza richiedere di rinominare artificialmente le estensioni.
8. Scrivere un README dettagliato, con esempi realmente eseguibili per API, CLI, notebook e UI, installazione, formati, calibrazione, errori e limiti.

## Contratto scientifico

Nel legacy, il contenuto numerico viene interpretato come una sequenza di eventi: un valore di canale incrementa un conteggio, mentre specifici marker aggiornano le coordinate spaziali. Non confondere questa sequenza con una matrice di conteggi già aggregata.

Verifica la grammatica con file reali. Dal codice emergono marker basati su 50.000.000 e 60.000.000, ma non generalizzare la classificazione usando soltanto la prima cifra del numero.

La calibrazione è esclusivamente:
    energy[i] = m * i + q

Questa formula vale quando m e q sono riferiti ai canali ADC effettivamente salvati. Verifica la convenzione dello strumento e l'indice iniziale: non introdurre fattori 32, 16384/500 o altri adattamenti senza evidenza.

Salva coefficienti, unità, provenienza della calibrazione e vettore energetico. Applicare o cambiare calibrazione deve lasciare l'array dei conteggi identico elemento per elemento.

Se la calibrazione manca, conserva l'asse ADC e indica esplicitamente lo stato non calibrato. Non inventare m, q o un intervallo energetico predefinito.

Non ricavare il numero totale di canali dal massimo evento osservato: i canali finali possono avere zero eventi. Usa un valore dichiarato dai metadati o un parametro esplicito; qualsiasi default strumentale deve essere documentato e verificato.

## Input senza XML e metadati incompleti

Non assumere che “solo data” significhi necessariamente XML con il solo tag analysisData: verifica anche il formato testuale puro.

Ricava coordinate e geometria dai marker soltanto quando non ambiguo. Non inventare dimensioni, passo spaziale o coordinate mancanti. Se un'informazione necessaria non è disponibile, indica esattamente quale parametro deve fornire l'utente.

Se la UI permette un file di metadati separato, definisci esplicitamente come associarlo ai dati e come gestire conflitti; non sovrascrivere silenziosamente i valori.

## Schema output proposto, da formalizzare

- `img`: cubo di conteggi interi, ordine `(y, x, channel)`.
- `channel`: indici ADC originali.
- `energy`: vettore dei centri energetici, presente soltanto quando calibrato.
- `calibration_m`, `calibration_q`: coefficienti effettivi, presenti soltanto quando calibrato.
- `metadata_json`: metadati serializzati senza pickle, comprensivi di versione dello schema, unità, provenienza e convenzioni.
- Coordinate spaziali e maschera di acquisizione, se necessarie per distinguere pixel non acquisiti da pixel con zero conteggi.

Documenta l'orientamento rispetto al legacy, che indicizza prima x e poi y. Verifica con una fixture rettangolare asimmetrica.

NPZ e HDF5 devono conservare le stesse informazioni. Non usare array object NPZ. Non convertire i conteggi in floating point soltanto per soddisfare un visualizzatore precedente: segnala e tratta esplicitamente l'eventuale incompatibilità del lettore a valle.

## Architettura minima

Usa un unico nucleo condiviso:
    validazione → lettura → costruzione conteggi → metadati calibrazione → export

CLI, notebook e UI devono chiamare questa stessa API. Proponi pochi entry point chiari, ad esempio `inspect_raw`, `read_raw`, `with_calibration` e `write_dataset`, senza creare wrapper superflui.

NumPy è sufficiente come prima scelta. HDF5 richiede h5py. Non mantenere Torch, pandas o JAX senza una necessità dimostrata. La UI può usare Dash con DARKLY e accento #4196B4; adatta il layout al flusso di conversione.

## Robustezza e test

- Errori con posizione/riga e causa; nessuno scarto silenzioso di record.
- Conteggi senza overflow e verifica del totale degli eventi accettati.
- Limiti di input e memoria stimata prima dell'allocazione.
- Output scritto tramite file temporaneo e finalizzazione; nessuna sovrascrittura implicita.
- CLI con exit code non zero in caso di errore e riepilogo dei file riusciti/falliti.
- Elaborazione sequenziale come default; parallelismo solo se necessario e limitato.

Testa almeno: XML completo, dati senza XML, calibrazione assente, input malformato, coordinate fuori limite, canali finali vuoti, oltre 65.535 eventi nello stesso bin, orientamento spaziale, identità dei conteggi dopo calibrazione e round-trip NPZ/HDF5.

Verifica la UI anche con una breve sequenza browser quando disponibile. Non presentare test sintetici come validazione del formato strumentale reale.

## Documenti e milestones

Prepara:
- AGENTS.md: regole stabili e invarianti scientifiche.
- operational_plan.md: decisioni, dubbi e criteri di accettazione.
- legacy_audit.md: problemi verificati e differenze intenzionali dal legacy.
- data_format.md: grammatica degli input.
- output_schema.md: schema comune NPZ/HDF5.
- scientific_notes.md: calibrazione, conteggi, assi e precisione.
- README.md: guida completa.
- to_do.md e timeline.md: attività aperte ed evidenze, senza duplicazioni.

M0 deve distinguere ciò che è dimostrato dal codice da ciò che richiede esempi o conferma dell'utente. Non pubblicare su PyPI, non fare push e non eliminare il legacy.