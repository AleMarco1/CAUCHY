# Chiusura del congelamento ensemble v1 — 28 agosto 2026

Registro della sessione. Sostituisce, sui punti che tocca, quanto scritto in
`paper2_item01_closed.md`, `paper2_stato.md` (P-A1) e nella consegna del 27 agosto.

---

## 1. Esito

Il congelamento è **verificato per file in quattro direzioni indipendenti** e i cinque
aggregate sono **ricalcolabili senza lo strumento che li ha prodotti**.

```
paper2_freeze_verify.py verify  ->  CLEAN
```

| tier | file | byte | aggregate_sha256 |
|---|---:|---:|---|
| records | 224 | 20 710 671 | `5364cf2ef1cac16c66e2f80dcd897bee8d14324100f15d0c9b471085f4b876f0` |
| features | 12 189 | 24 326 788 | `b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc` |
| fields | 2 202 | 18 472 477 342 | `bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34` |
| diagrams | 16 221 | 4 488 929 201 | `3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929` |
| superseded | 4 000 | 5 739 175 578 | `f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764` |
| **totale** | **34 836** | **28 745 619 580** | = 26.77144 GiB, arrotonda a 26.771 |

Zero MISMATCH, zero MISSING, zero UNREADABLE. Unione dei percorsi = somma dei tier =
somma delle intestazioni = 34 836: nessun percorso appartiene a due tier.

### La regola dell'aggregate

Da `paper2_freeze_v1.py:235-238`:

```python
lines = sorted(f"{r['rel']}:{r['sha256']}" for r in records)
sha256("\n".join(lines).encode()).hexdigest()
```

Nessun newline finale; l'ordinamento è sulla stringa composta, non sul solo percorso;
l'insieme è deduplicato per percorso (last-wins) perché `records` è un dizionario.
Verificata sui dati veri, aggancia sia sui `rel` normalizzati sia su quelli grezzi:
**i percorsi nel manifest sono già con slash, quindi il digest è indipendente dalla
piattaforma.** Un revisore su Linux ottiene gli stessi cinque valori.

### Il cancello di invarianza

I cinque tier sono stati ricongelati da zero — 34 836 record riscritti con `mtime_utc` e
`scanned_at` nuovi — e i cinque aggregate sono rimasti identici. Il congelamento **non
dipende da git né dai metadati**, solo da `rel:sha256`. È il passo che
`paper2_item01_closed.md` chiamava «ultimo, meccanico» e che non era mai stato eseguito.

Su `diagrams` il confronto è chiuso in entrambe le direzioni: con i due file di troppo
l'aggregate vale `18f233708dc9afb75e3a3de63dd1bb65f10bf2383872b5ae5f9fa0bf3e87d3ac`
(16 223 file), senza vale `3a746c95…` (16 221).

---

## 2. Cosa è cambiato

### Commit

| commit | contenuto |
|---|---|
| `fea1037` | patch a `paper2_freeze_v1.py`; aggiunti `paper2_freeze_verify.py` e `paper2_refreeze.py` |
| `7c759d3` | ricongelamento di `features` e `fields` |
| `b44f28d` | ricongelamento di `diagrams`, `superseded`, `records` dopo lo spostamento delle curve del gate 2.1 |

### Modifiche a `paper2_freeze_v1.py`

1. **`exclude_dirs` dichiarato nell'intestazione.** `iter_files(..., exclude_dirs=[out])`
   esclude sempre la directory di output, ma la riga 341 registrava solo `args.exclude`.
   Un terzo che rigiocasse le regole dichiarate otteneva 262 file invece di 224 su
   `records`. Ora l'intestazione porta `"exclude_dirs": ["results/paper2"]`.
2. **Stato git misurato all'inizio, non alla fine.** `git_provenance` era chiamata mentre
   si costruiva `doc`, cioè dopo che il freeze aveva riscritto il proprio manifest, che è
   un file tracciato. Lo strumento sporcava l'albero e poi lo guardava: `dirty: false` era
   **irraggiungibile per costruzione**, e nessun numero di rilanci l'avrebbe prodotto.
3. **Directory di output esclusa dal conteggio del dirty**, con il campo
   `excluded_from_dirty` che lo dichiara. I manifest non sono né codice né artefatti: sono
   il registro che il run sta scrivendo. Controprova eseguita: una modifica vera a
   `src/` dà ancora `dirty: true` con il file elencato.

Rimossa anche una chiave `"exclude_pat"` duplicata.

### Strumenti nuovi

**`paper2_freeze_verify.py`** (16 controlli nel selftest). Verifica in quattro direzioni:
intestazione vs corpo; corpo vs disco; **disco vs corpo**, rigiocando `roots` +
`include_ext` + `exclude_pat` + `exclude_dirs` per trovare i file che soddisfano le regole
e non sono nel manifest; e ricostruzione dell'aggregate con ~20 costruzioni candidate.
Applica il last-wins sul JSONL accodato e sovrappone gli emendamenti ai valori documentati,
come prescrive l'item 0.12. Rifiuta di scrivere il proprio output dentro `results/`.

**`paper2_refreeze.py`** (15 controlli). Ricongelamento guardato: i cinque aggregate sono
costanti nel file, il preflight rifiuta di partire se lo stato iniziale non è quello, ogni
tier ha backup di intestazione e corpo, e su aggregate diverso ripristina e si ferma al
primo fallimento. Il corpo viene **rimosso** prima del freeze, non riusato.

---

## 3. Difetti trovati

### Corretti

| difetto | dove | stato |
|---|---|---|
| `exclude_dirs` non dichiarato nell'intestazione | `paper2_freeze_v1.py:341` | corretto, `fea1037` |
| `dirty` misurato dopo la propria scrittura | `paper2_freeze_v1.py`, `cmd_freeze` | corretto, `fea1037` |
| `curves_DESI_{NGC,SGC}_g21.npz` dentro il tier `diagrams` | `results/paper1` | spostati in `results/paper2` (182 416 e 99 124 byte; non tracciati da git, coperti da `.gitignore`) |

### Aperti

**`paper1_remap.py:710` riscriverà le curve in `results/paper1`.** Al prossimo run del
gate 2.1 i due `.npz` tornano dov'erano e `diagrams` risale a 16 223. `out_dir` (riga 659)
**non** può essere dirottato in blocco: alla riga 488 ci sta `per_mock_{region}_{tag}.jsonl`,
che è il file di ripresa, e alle 449-450 la scala nulla riusata. Correzione stretta:
aggiungere `--curves_dir` (default `None` → `out_dir`, quindi retrocompatibile) e usarlo
alle sole righe 540 e 710; il gate 2.1 lo passa nel `cmd` di riga 392 puntando a
`results/paper2`. Con `--stage selfcheck` scatta solo la 710.

**La scala nulla può sovrascrivere quattro artefatti congelati, in due tier.**

| file | tier | sha256 | byte |
|---|---|---|---|
| `results/paper1/null_ladder_NGC_n2000.npy` | diagrams | `cb207797573a2433a7d1a4b22aa9fa18c0ddaf57ac3454ee7a7570d412e50e20` | 2 462 568 |
| `results/paper1/null_ladder_SGC_n2000.npy` | diagrams | `1604f560e29debd8f50df985a7e606724ce063655f2fbb293fd4dfe1aeb621df` | 1 377 928 |
| `results/paper1/null_ladder_NGC_n2000.json` | records | `51cdfff65ce94c167a5cffc844e98d278c1c4c5a97231f993fa94374f7f29f2b` | 167 |
| `results/paper1/null_ladder_SGC_n2000.json` | records | `e9987adbe78fe1cc0567c52f2a6ee203196ceff31603cb2fd5614c4b5344ac8c` | 167 |

Il nome contiene `n{len(files)}`, ma la condizione di riuso (riga 453) richiede **anche**
`Q.size == mask.sum()`, che nel nome non c'è. Con la stessa cache da 2000 mock e una
maschera di conteggio diverso il percorso resta identico, il ramo stampa *«scala nulla su
disco incoerente - ricalcolo»* e `atomic_save_npy` sovrascrive. Una maschera erosa ha meno
voxel per definizione: **qualunque test di erosione riscriverebbe un artefatto di v1.**
Sarebbe un `MISMATCH`, non un `EXTRA` — l'unico percorso noto capace di alterare v1 invece
di aggiungervi. E il meta contiene `"created": _now()`, quindi anche un ricalcolo
numericamente identico cambierebbe il `.json`: il danno a `records` è garantito, non
probabile.

Mettere `n_voxels` nel nome sarebbe la correzione conforme al principio enunciato dal
commento della riga 444, ma oggi romperebbe il congelamento per ripararne la protezione:
i file congelati non verrebbero più trovati e nascerebbero due `.npy` nuovi. La via senza
costi è il fallimento rumoroso: `force` è parametro ma alla riga 504 non viene mai passato,
quindi un ricalcolo *voluto* non esiste nel codice e l'unico raggiungibile è quello
involontario. Sostituire il ramo di ricalcolo con `sys.exit` e aggiungere
`--force_null_ladder`. Nessuno scenario oggi funzionante cambia.

**La guardia `PROTECTED` del gate 2.1 è cieca alle aggiunte.** Confronta i digest di sette
percorsi prima e dopo: perfetta contro le modifiche, inerte contro i file creati. I due
`curves_DESI_*_g21.npz` sono stati creati, quindi la guardia è passata pulita mentre
`diagrams` diventava irriproducibile. Aggiungere i quattro percorsi della scala nulla a
`PROTECTED`, e far girare `paper2_freeze_verify.py verify --tier diagrams` dopo ogni gate
che invochi remap: costa 3.5 s e vede le aggiunte, che nessun confronto di digest può
vedere.

---

## 4. Correzioni documentali

1. **«sha256» indica due grandezze diverse dello stesso file.**
   `paper2_v1_reference.json` ha `_self_sha256` = `865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc`,
   che è il digest del **contenuto** riserializzato in forma canonica
   (`json.dumps(indent=2, sort_keys=True, ensure_ascii=False)` dopo aver estratto il campo
   stesso) — è ciò che `load_reference` verifica come cancello e ciò che i cinque manifest
   registrano in `reference_sha256`. Lo sha256 dei **byte del file** è
   `332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d`, 11 306 byte, ed è
   quello citato da consegna e pre-registrazione §2.1.
   **Il reference non è mai stato modificato** e l'immutabilità non è mai stata violata.
   I due documenti vanno disambiguati prima del deposito: la stessa parola per due
   quantità costa ore a chi legge.

2. **Conteggio degli emendamenti: 11 sul disco**, 12 nella consegna, 10 nel §9 della
   pre-registrazione. Il §9 va allineato al conteggio al momento del deposito.

3. **`paper2_amend_freeze.py`**: la docstring dice «mai committato» del freeze n. 2, che è
   stato committato in `6522204`; e attribuisce la rimozione di
   `results/phase8_test2_permock.csv` a `312218b`, mentre `git log --diff-filter=D` la
   assegna a `352e024`. `312218b` era HEAD al momento dello scatto. Il file è append-only:
   si appende un record di rettifica, non si riscrive quello esistente. Diventerebbe
   l'emendamento n. 12, e a quel punto la consegna torna corretta.

4. **`paper2_stato.md`, P-A1**: la nota diceva che `--force` lascerebbe la voce stantia, e
   **aveva ragione**, per un motivo diverso da quello che sembrava. `--force` azzera
   `existing`, che è l'accumulatore in memoria, non il file: `append_jsonl` (riga 324)
   accoda sempre. Un file rimosso dal disco non riceve un record nuovo, la sua vecchia riga
   resta sola nel JSONL e vince il last-wins. **Per ricostruire un tier il corpo va rimosso
   prima**, ed è così che fu fatto il ri-freeze delle 14:43 del 25 agosto (il corpo ha 224
   righe, non 449).

5. **`paper2_item01_closed.md`**: la tabella per tier riporta `records` a 225 file con
   aggregate `e905d7fd…`. È lo stato pre-P-A1, già coperto dall'emendamento; i totali
   34 836 / 26.771 GiB erano invece già quelli post-ricostruzione. Il sottoprodotto **S1**
   dichiara 34 611 artefatti binari mentre i quattro tier binari sommano a **34 612**, e
   sono disgiunti per costruzione (`features` esclude `paper1/`, `revision/`,
   `phase1_persistence`, `phase8_`, che sono le radici degli altri tre). La frase è già
   scritta per il manoscritto: va corretta prima che ci entri.

---

## 5. Cosa NON era un problema

Registrato perché durante la sessione è stato affermato il contrario, e la prossima
sessione non deve riaprirlo.

- Il reference **non** è stato modificato dopo il congelamento (vedi §4.1).
- Il freeze n. 2 di `records` **è** stato committato, in `6522204`.
- I record del Paper 1 (`m2_*`, `n1_*`, `n6_fkp`, `n8_masks`…) **sono** dentro il
  congelamento: comparivano come EXTRA solo perché il corpo risultava vuoto per un difetto
  del verificatore (la chiave `rel` non era fra quelle riconosciute).
- Il glob `curves_*.npz` di `paper1_step6_onepoint_betti.py:138` **non** può raccogliere le
  curve del gate 2.1: rastrella la sottocartella `curves_{region}_{tag}`, non `out_dir`.
- I 38 file sotto `results/paper2` esclusi da `records` sono **corretti**: è la `--out`,
  esclusa per disegno. Mancava solo la dichiarazione, ora aggiunta.

---

## 6. Prossimo passo

**Manifest dei prodotti Paper 2** — la quarta zip del deposito, oggi inesistente. Sono 40
file sotto `results/paper2` (i 38 di prima più i due `curves_DESI_*_g21.npz`), ma la
composizione richiede una scelta:

| gruppo | file | dimensione |
|---|---:|---:|
| `inventory.json` (output di `cauchy_inventory.py`) | 1 | 23.1 MiB |
| `ensemble_v1_*` (5 intestazioni + 5 corpi) | 10 | ~7.9 MiB |
| numeri del Paper 2 (`compD_*`, `dmed_*`, `gate21`, `gate25`, `fase2`, `item12a/b_*`, `probe_randoms2_*`, curve g21) | 29 | ~1.0 MiB |

Congelarli insieme renderebbe il manifest instabile per costruzione: `inventory.json`
cambia a ogni audit e i dieci `ensemble_v1_*` a ogni ricongelamento, operazioni che con i
numeri del Paper 2 non c'entrano. Tre insiemi con vite indipendenti:

- **`paper2_products`** — i 29 file dei risultati. È la quarta zip.
- **`v1_manifests`** — i dieci `ensemble_v1_*`, che per disegno si rigenerano.
- **`inventory.json` e `results_inventory.json`** — strumenti di audit, non risultati.
  Nessuno script li **legge** (`cauchy_inventory.py:201` e `paper2_inspect_results.py:240`
  li scrivono soltanto, ed entrambi hanno `--out`), quindi spostarli non rompe niente.

`--out` va **fuori da `results`**: sotto `results` cadrebbe nel territorio di `records` e
lo romperebbe al prossimo ricongelamento; in `logs/` resterebbe fuori dal deposito. Una
cartella `manifests/` in radice sta fuori da ogni tier ed è tracciabile.

`paper2_freeze_verify.py` accoppia i corpi al tier dichiarato dall'intestazione, non a una
lista fissa di nomi, quindi verifica i tier nuovi senza modifiche.

---

## 7. Ordine per la prossima sessione

1. `--curves_dir` in `paper1_remap.py` + passaggio dal gate 2.1 (l'unico difetto ancora
   attivo).
2. Fallimento rumoroso sulla scala nulla + quattro percorsi in `PROTECTED`.
3. `paper2_products` e `v1_manifests`, con `--out manifests/`.
4. Le cinque correzioni documentali del §4, incluso l'emendamento n. 12.
5. Deposito Zenodo, tag, version DOI nel §9 della pre-registrazione → chiude la 0.6.

Prima di ogni sessione, e dopo ogni gate che invochi `paper1_remap.py`:

```powershell
python src\paper2_freeze_verify.py verify --jobs 4 --out logs\fv.jsonl
```

Deve dare CLEAN. Se non lo dà, `logs\fv.jsonl` contiene il record completo del run
precedente per il confronto.
