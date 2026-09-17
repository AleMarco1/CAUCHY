# REPRODUCIBILITY

### Manoscritto → tag → DOI → digest — voce **R2** — 7 settembre 2026,
### rev. 17 settembre 2026 (record 69, 71, 72, 73)

Questo documento dice, per ogni manoscritto del programma CAUCHY, **quale stato del repository e
quale deposito** gli corrispondono, e come verificarli senza eseguire la pipeline.

Non introduce numeri nuovi. I digest dei tier congelati sono **ricalcolabili dai file
depositati**, e la regola per farlo è nel §3. I digest del **protocollo**, al §7, non lo sono — il
deposito non contiene quel documento — e si verificano contro il record 72 e il file su disco.

---

## 1. La mappa

| manoscritto | stato | tag | commit | deposito |
|---|---|---|---|---|
| **M26** — la misura del deficit | sottomesso, R1 in revisione | `v2.0-paper-c` | `18fcac8` | concept DOI |
| **Paper 1** — decomposizione del deficit | sottomesso, in revisione | `v2.1-phase9b` | `f2bdf39` | concept DOI |
| **Paper 2** — a cosa risponde il conteggio | Fasi 0–5 chiuse, Fase 6 in corso | `v3.0-paper2` | `5c54807` | **version DOI 10.5281/zenodo.22148444** — l'archivio della pipeline, **non** il protocollo: §7 |

**Concept DOI del programma:** `10.5281/zenodo.21128856` — identifica l'opera e punta sempre
all'ultima versione.

**Version DOI del deposito:** `10.5281/zenodo.22148444` — identifica i **sei file depositati**
il 28 agosto 2026, e non si muove. È quello contro cui la Fase 3 è registrata.
**Non contiene il documento di pre-registrazione**, in nessuna versione: misurato il 17
settembre aprendo ogni archivio di ogni versione del concept DOI (record 73). Il protocollo è
ancorato **per byte** dal record 72, e il §7 di questo documento dice come citare i due
ancoraggi senza confonderli.

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
| `352e024` | **rimozione** di `results/phase8_test2_permock.csv` e ricostruzione del manifest `records` (P-A1; §5) |
| `c13ccc3` | prima stesura di questo documento |
| `3e43e38` | disciplina dei fine riga: regole di cartella in coda in `.gitattributes`, `eol=lf` sui sorgenti, tre file del tier `records` riportati a `-text` con l'indice riletto (record 69) |
| `bfcb4a5` | contenuti di Fase 4–6: registri di misura, strumenti e verdetti; il record 70 dichiara la portata del rilascio |

Il **tag del Paper 2 per le Fasi 4–6 è `v3.1-paper2`** (record 70 §iv; non `v2.1-paper2`, che
si ordinerebbe prima del deposito del 28 agosto). `origin` si aggiorna **periodicamente** dal
17 settembre 2026 (record 73 §v); il deposito Zenodo, invece, **solo alla sottomissione**
(record 73 §vi), ed è lì che la v1.1 del protocollo entra nell'archivio citabile.

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

## 5. Quello che il lettore deve sapere

*(Il titolo portava «Quattro cose». Un conteggio in un'intestazione invecchia alla prima voce
aggiunta, come il «55 record» del §6: qui i conteggi stanno nelle righe, dove si verificano.)*

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

**Correzione del 17 settembre 2026 (record 71).** Questo paragrafo diceva che la copia
byte-identica segnalata da documenti interni precedenti **non esiste**. La copia esisteva:
`results/phase8_test2_permock.csv`, **rimossa per causa** dal commit `352e024`, che è la voce
`P-A1` — la rimozione per cui il tier `records` è passato a 224 file e all'aggregato
`5364cf2e…`, registrata dall'emendamento 11. Al momento in cui questo documento è stato
scritto il file non c'era più, e **«non esiste adesso» è stato scritto come «non è mai
esistito»**: una rimozione registrata letta come una negazione. Il sopravvissuto è il
`_hodfit` qui sopra, che ha un nome simile e non è la stessa cosa.

Gli unici digest ripetuti dentro `records` sono **otto manifest JSON** — sei
`phase*_manifest.json` con lo stesso digest e due `phase_r51_manifest` — e sono identici
**per costruzione**, non per errore.

### I fine riga del registro degli emendamenti

`src/paper2_v1_amendments.jsonl` ha sei righe — 8, 9, 10, 11, 13 e 14 — terminate da un LF solitario
dove le altre portano CRLF, e quattro di esse condividono un `utc` segnaposto. È registrato, è
**inerte**, e resta **non riparato**: il file è append-only, e normalizzare sei righe sarebbe la prima
modifica mai fatta a un registro che vale proprio per non essere stato toccato.

`.gitattributes` contiene `*.jsonl -text`, quindi git **non converte** quei fine riga in nessuna
direzione, nonostante `core.autocrlf = true`. Quell'attributo esiste dal 25 agosto 2026, dodici
giorni prima del record 47: il record 68 lo emenda su questo punto — cambia il meccanismo, non
l'esito.

**L'invariante sono le righe, non i conteggi** *(correzione del 17 settembre, record 69)*. Questo
paragrafo dava «49 CRLF e 6 LF» per il file committato. I totali crescono a ogni append — a 72
record sono 66 e 6, a 73 saranno 67 e 6 — quindi non sono un'ancora: la proprietà verificabile
è che le righe a LF siano **esattamente la 8, 9, 10, 11, 13 e 14 e nessun'altra**, e che i
primi byte del file non cambino mai. È ciò che `paper2_append_amend*.py` verifica prima e dopo
ogni append, e ciò che il censimento dei registri misura.

**E l'attributo di un file si legge, non si deduce dal commento in testa a `.gitattributes`.**
In quel file **vince l'ultima regola che combacia**: le due regole di cartella stavano in testa
e quelle di tipo in coda, quindi ogni `.md`, `.txt` e `.py` sotto `results/` era `text` — e tre
file del tier congelato `records` (`src_bundle_phase9.txt`,
`phase5_hod_variance_decomp_summary.md`, `env_versions.txt`) erano **normalizzabili**: i loro
byte erano riproducibili solo su Windows con `core.autocrlf=true`, e un checkout altrove li
avrebbe scritti a LF facendo uscire il congelamento MISMATCH. Il `CLEAN` non lo vedeva perché
la conversione non era ancora avvenuta. Corretto dal commit `3e43e38` (record 69): regole di
cartella in coda, `*.py` e `*.md` a `text eol=lf`, l'indice dei tre file riletto — la cache di
stat di git non si invalida da sé, e `git add` su un file il cui stat combacia con l'indice è
un no-op silenzioso. Si verifica con `git ls-files --eol`, non a occhio.

**Se un giorno si aggiungerà un digest del registro, lo si calcoli sui RECORD e non sui byte.** È
invariante ai fine riga, all'ordine delle chiavi — che dal record 50 non è più uniforme — e al BOM
che `results/revision/rev1_r11_tiling.json` porta e gli altri registri no.

### Due coperture per la cache di *P*(*k*), una sola per il suo asse *k*

| | percorso | byte | sha256 | chi lo copre |
|---|---|---:|---|---|
| cache | `results/phase7_pk_nwlh_cache.npz` | 880 272 | `d148f63f…` | il corpo del manifest `features` **e** il record 5 |
| asse *k* | `results/paper2/phase7_pk_nwlh_kref.npz` | 1 684 | `92679cbd…` | **solo** il record 61 |

L'asse *k* delle 110 colonne di `pk_matrix` non esisteva in nessun file: il codice che scrive la
cache ricava `k_ref` dalla prima realizzazione riuscita e **non lo salva**. Il kref è quell'asse,
rigenerato dalla realizzazione 0 e congelato nel record 61. Sta in `results/paper2/` e non nella
radice di `results/` per una ragione meccanica: lì cadrebbe **dentro** le regole del tier
`features` e il congelamento lo segnalerebbe come file extra. Chi verifica dall'esterno ha
bisogno di entrambi, e il kref ha una copertura sola: se si perde, l'asse va rigenerato con
`src/paper2_prov_pk_riproduci.py riproduci --out-kref` e riconfrontato col digest del record 61.

### Il pattern di ripresa che vale la pena copiare

`paper1_remap.py`, righe 512-516, riprende una corsa interrotta solo se esistono **sia** la riga
nel registro **sia** il file delle curve su disco. È l'unico runner del programma che verifica il
**prodotto laterale** e non solo il proprio registro, ed è la forma corretta: una riga scritta
prima di un file mancante fa saltare un lavoro che non è stato fatto. All'estremo opposto,
dichiarato e non riparato, `ensemble_v2_{NGC,SGC}.jsonl` non ha né ripresa né identificatore —
`--da` è un selettore di popolazione, non una ripresa — e una seconda corsa vi appenderebbe 2000
record indistinguibili dai primi per chi legge per unione. Quel runner non riparte: la Fase 4 è
chiusa. **I registri di misura si leggono per UNIONE, mai last-wins, e senza i record `smoke`.**

---

## 6. Il registro degli emendamenti

Append-only, in un file separato dal reference set, che resta byte-identico per sempre. **Il
conteggio corrente non si scrive qui**: lo dichiara `DOCUMENTED_AMENDMENTS` in
`src/paper2_freeze_verify.py`, e ogni esecuzione del verificatore confronta quella costante col
numero di record sul disco e rifiuta se divergono. *(Questo paragrafo diceva «55 record»: era
vero all'8 settembre e ha smesso di esserlo al primo append.)*

Il **§9 del protocollo** ne dichiara dodici alla data del deposito, e il verificatore asserisce
che il conteggio su disco non scenda mai sotto quella soglia. Il dodici ha una conferma
indipendente: `cauchy_code.zip` del deposito porta `src/paper2_v1_amendments.jsonl` con **dodici
record**, 12 670 byte (record 73).

Il numero di un emendamento è la sua **posizione** nel file, non un campo: due record possono
condividere `utc` e schema, e la numerazione posizionale è ciò che li distingue.

**Le predizioni falsificate restano falsificate**, con la ragione per cui la soglia era mal posta, e
non sono mai riparate a posteriori. Fra i record 39–55: due predizioni dichiarate e smentite, un
audit che ha **ritirato** una falsificazione precedente perché non decideva, e la registrazione di un
difetto che è costato otto ore di macchina.

---

## 7. Il protocollo: due ancoraggi, e cosa il DOI non contiene

Ogni record del registro porta, nel campo `document`, la stringa «`paper2_prereg_v1.md` v1.1 —
version DOI 10.5281/zenodo.22148444». È un **nome**, non un digest, e per 71 record non ce n'era
nessun altro.

| | valore | che cos'è |
|---|---|---|
| **v1.1, su disco** | `607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86`, 25 319 byte | il protocollo corrente, **ancorato per byte dal record 72** |
| **v1.0, in git** | `05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115`, 21 430 byte | recuperabile con `git show 900335e^:papers/paper2/paper2_prereg_v1.md` |
| **nel deposito** | — | **nessuna delle due**: il version DOI non contiene il protocollo |

**Perché la v1.1 non è in git.** `papers/` è uscito dal versionamento col commit `900335e` del 28
agosto alle 18:23:40 +0200 — i sorgenti dei manoscritti e la corrispondenza con editore e referee
non fanno parte del rilascio del codice (record 70 §i) — e la v1.1 è stata scritta alle 20:13:04,
dopo. Un file uscito dal versionamento smette di avere una storia nello stesso istante, e ciò che
si scrive dopo non ce l'ha mai avuta. **Ancorare non è versionare**: le due decisioni sono
indipendenti, e il record 72 fa la prima senza toccare la seconda.

**Perché la v1.1 non è nel deposito, e nemmeno la v1.0** *(record 73, misurato il 17 settembre
2026)*. Il concept DOI ha quattro versioni — v1.0 (2 luglio), v2.0-paper-c (3 luglio),
v2.1-phase9b (6 luglio), v3.0-paper2 (28 agosto). Ogni file di ognuna è stato scaricato e ogni
archivio aperto: **1068 membri in tutto, nessuno col protocollo**. Le prime tre versioni sono
archivi del repository a quei tag, e il protocollo non esisteva ancora; la quarta contiene sei
file — `README.md`, `MANIFEST.sha256` e quattro zip, i cui digest coincidono col manifest — e
`cauchy_code.zip` non porta `papers/` perché quell'albero era già fuori dal versionamento da
sedici minuti. **Il version DOI ancora l'archivio della pipeline, non il documento contro cui la
pipeline si dichiara.**

**Che cosa cambia fra v1.0 e v1.1, misurato riga per riga:** 8 righe tolte e 61 aggiunte, e le
aggiunte cadono nel preambolo, nel §2.1 (*Reference set*), nel §9 (*Amendment record*) e in tre
righe del §0. **Le sezioni che portano le regole dell'analisi sono identiche.** È la ragione per
cui depositare la v1.1 alla sottomissione non indebolisce la pre-registrazione: non c'è una
regola che sia stata cambiata dopo aver visto un risultato. È una condizione da **rimisurare** se
qualcuno tocca il documento, non da riaffermare.

**Una riga del protocollo che non è vera, e non è stata corretta qui.** La v1.1 dichiara in testa
«*Version 1.1 — 28 August 2026 (version 1.0 deposited 27 August 2026)*». Nessuna versione del
concept DOI è del 27 agosto: l'unico evento di quel giorno su quel percorso è il commit
`73c8213`. La parola «deposited» descrive lì un commit, non un deposito. Il protocollo **non si
riscrive per emendamento**: la correzione va nella versione che si deposita alla sottomissione,
dove sarà vera (record 73 §iii).

**Come citare i due ancoraggi.** Fino al deposito della Fase 7: il **DOI** per l'archivio della
pipeline, il **digest del record 72** per il documento. Dopo il deposito, il version DOI nuovo
coprirà entrambi, e questa sezione va riscritta con quel DOI al posto di questa distinzione.
