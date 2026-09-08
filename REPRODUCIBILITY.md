# REPRODUCIBILITY

### Manoscritto → tag → DOI → digest — voce **R2** — 7 settembre 2026

Questo documento dice, per ogni manoscritto del programma CAUCHY, **quale stato del repository e
quale deposito** gli corrispondono, e come verificarli senza eseguire la pipeline.

Non introduce numeri nuovi: ogni digest qui sotto è ricalcolabile dai file depositati, e la regola per
farlo è nel §3.

---

## 1. La mappa

| manoscritto | stato | tag | commit | deposito |
|---|---|---|---|---|
| **M26** — la misura del deficit | sottomesso, R1 in revisione | `v2.0-paper-c` | `18fcac8` | concept DOI |
| **Paper 1** — decomposizione del deficit | sottomesso, in revisione | `v2.1-phase9b` | `f2bdf39` | concept DOI |
| **Paper 2** — a cosa risponde il conteggio | Fasi 0–3 chiuse | `v3.0-paper2` | `5c54807` | **version DOI 10.5281/zenodo.22148444** |

**Concept DOI del programma:** `10.5281/zenodo.21128856` — identifica l'opera e punta sempre
all'ultima versione.

**Version DOI della pre-registrazione:** `10.5281/zenodo.22148444` — identifica lo stato dei file
**pre-registrato**, e non si muove. È quello contro cui la Fase 3 è registrata.

### I tag non sono alias

`v2.0-paper-c` e `v2.1-phase9b` sono i nomi **veri** dei tag nel repository. Documenti interni
precedenti li chiamavano `v2.0-m26-r1` e `v2.1-paper1`: quei nomi **non esistono** e non sono stati
creati, perché due tag sullo stesso commit con nomi diversi confondono una citazione invece di
chiarirla. Si citano i nomi che ci sono.

### Lo stato dopo il tag

`v3.0-paper2` fotografa il repository al **deposito della pre-registrazione**, con dodici emendamenti.
Il lavoro delle Fasi 0–3 è proseguito oltre, e si cita **per sha**:

| commit | contenuto |
|---|---|
| `c3e8f93` | registro degli emendamenti fino al record 55 |
| `0dc0225` | toolchain della Fase 3: 43 appender, patcher, runner, strumenti d'analisi |
| `3858660` | registri di misura della Fase 3: griglia, mock, budget, ripattern, surrogati |

**Nessun tag nuovo è stato creato su questi commit.** Uno stato citato per sha è altrettanto
verificabile e non aggiunge un nome che dovrebbe poi essere spiegato.

---

## 2. L'ensemble di riferimento v1

Immutabile, e verificato **file per file** in quattro direzioni indipendenti: intestazione contro
corpo, corpo contro disco, regole del tier rigiocate sul disco per trovare file che le soddisfano e
non sono nel manifest, e ricostruzione dell'aggregato.

| tier | file | byte | aggregate_sha256 |
|---|---:|---:|---|
| diagrams | 16 221 | 4 488 929 201 | `3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929` |
| features | 12 189 | 24 326 788 | `b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc` |
| fields | 2 202 | 18 472 477 342 | `bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34` |
| records | 224 | 20 710 671 | `5364cf2ef1cac16c…` *(emendato: vedi §5)* |
| superseded | 4 000 | 5 739 175 578 | `f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764` |
| **totale** | **34 836** | **28 745 619 580** (26.771 GiB) | |

### Il reference, e le sue DUE grandezze

Sono due cose diverse e vanno citate come tali:

| | valore | che cos'è |
|---|---|---|
| **byte del file** | `332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d` | sha256 di `paper2_v1_reference.json` come sta sul disco |
| **contenuto canonico** | `865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc` | il `_self_sha256` che i cinque manifest dichiarano |

**Non sono due versioni**: il reference non è mai stato modificato. Il primo cambia se cambia un byte
del file, il secondo solo se cambia il contenuto che descrive.

---

## 3. Come verificare, senza la pipeline

L'aggregato di ogni tier è

```
sha256( "\n".join(sorted( "{rel}:{sha256}" )) )
```

calcolato sull'insieme dei percorsi **deduplicato** — last-wins, perché l'aggregato lavora su un
dizionario e non sulle righe. È quindi **ricalcolabile con qualunque strumento** e indipendente dalla
piattaforma. È stato verificato che i cinque aggregati sono **invarianti sotto ricongelamento
completo**: dipendono solo da percorsi e contenuti, non da metadati né dallo stato di git.

**Verifica completa** (26 GiB letti, qualche minuto):

```
python src/paper2_freeze_verify.py verify --jobs 4
```

**Verifica del solo tier `features` dal tarball depositato**, senza avere l'albero:

```
python src/paper2_tarball_features.py verify
```

---

## 4. Il tarball del tier `features`

| | |
|---|---|
| file | `results/paper2/ensemble_v1_features.tar.gz` |
| contenuto | 12 189 file, 24 326 788 byte |
| compresso | 5 611 494 byte |
| **sha256** | `febf93ed8ca745b6b9f9aedd8bd2acb64dc905125a6dcb26d082e9b30b24caf9` |

**Costruito dal manifest, non dall'albero**: prende ciò che il congelamento **dichiara**, e ogni
differenza rispetto al disco è un errore invece di finire dentro in silenzio.

**Deterministico**: membri in ordine di percorso, `mtime`/`uid`/`gid`/`uname`/`gname` azzerati, gzip
con `mtime=0`. Due ricostruzioni danno lo **stesso byte**, ed è la ragione per cui il suo sha256 è
citabile. Il file **non è tracciato in git**: si ricostruisce con lo strumento e si verifica contro
l'aggregato depositato.

---

## 5. Quattro cose che il lettore deve sapere

### Il tier `records` è emendato

L'aggregato dichiarato per `records` differisce da quello del primo congelamento: il tier è stato
ricongelato dopo aver spostato le curve del cancello 2.1 fuori da `results/paper1`. Il verificatore
lo riporta come `(emendato)` e la ragione sta negli emendamenti. **Gli altri quattro tier non sono
mai stati toccati.**

### `config_hash` non è un ancoraggio degli ingressi

Il campo `config_hash` che compare nei registri **non hasha gli ingressi**. Il nome suggerisce ciò
che non fa. Gli ancoraggi sono i digest di questo documento, non quel campo, e citarlo come garanzia
di provenienza sarebbe un errore.

### `phase8_test2_permock_hodfit.csv`

Il tier `records` contiene `results/phase8_test2_permock_hodfit.csv`, `ae733e1e2a74bfff`, 10 891 byte.
Documenti interni precedenti ne segnalavano una copia byte-identica: **non esiste**. Gli unici digest
ripetuti dentro `records` sono **otto manifest JSON** — sei `phase*_manifest.json` con lo stesso
digest e due `phase_r51_manifest` — e sono identici **per costruzione**, non per errore.

### I fine riga del registro degli emendamenti

`src/paper2_v1_amendments.jsonl` ha sei righe — 8, 9, 10, 11, 13 e 14 — terminate da un LF solitario
dove le altre portano CRLF, e quattro di esse condividono un `utc` segnaposto. È registrato, è
**inerte**, e resta **non riparato**: il file è append-only, e normalizzare sei righe sarebbe la prima
modifica mai fatta a un registro che vale proprio per non essere stato toccato.

`.gitattributes` contiene `*.jsonl -text`, quindi git **non converte** quei fine riga in nessuna
direzione, nonostante `core.autocrlf = true`. Il file committato porta 49 CRLF e 6 LF, cioè
l'anomalia com'è.

**Se un giorno si aggiungerà un digest del registro, lo si calcoli sui RECORD e non sui byte.** È
invariante ai fine riga, all'ordine delle chiavi — che dal record 50 non è più uniforme — e al BOM
che `results/revision/rev1_r11_tiling.json` porta e gli altri registri no.

---

## 6. Il registro degli emendamenti

**55 record**, append-only, in un file separato dal reference set, che resta byte-identico per sempre.
Il §9 del documento depositato ne dichiarava dodici al deposito, e il verificatore asserisce che il
conteggio su disco non scenda mai sotto quella soglia.

Il numero di un emendamento è la sua **posizione** nel file, non un campo: due record possono
condividere `utc` e schema, e la numerazione posizionale è ciò che li distingue.

**Le predizioni falsificate restano falsificate**, con la ragione per cui la soglia era mal posta, e
non sono mai riparate a posteriori. Fra i record 39–55: due predizioni dichiarate e smentite, un
audit che ha **ritirato** una falsificazione precedente perché non decideva, e la registrazione di un
difetto che è costato otto ore di macchina.
