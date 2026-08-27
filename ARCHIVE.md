# CAUCHY — riordino dell'archivio

**27 agosto 2026.** Disegno basato sul censimento di `results/paper2/inventory.json`
(59 723 file, 352.7 GiB) e sull'audit di `results/paper2/remote_audit.json`.

---

## 1. Lo stato di fatto

| | |
|---|---|
| repo git | `AleMarco1/CAUCHY`, branch `main`, HEAD `312218b` (25 ago 2026) |
| tracciati | **434** file |
| modificati non committati | **7** |
| **non tracciati** | **52** — di fatto l'intera Fase 2 (`src/paper2_*.py`, `results/paper2/*.jsonl`) |
| `D:\projects\cauchy_3.0` | **51 file, nessun git**: pre-registrazione, checklist, canovacci, item |
| Zenodo, concept 21128856 | **un solo file**, `AleMarco1/CAUCHY-v2.1-phase9b.zip`, 3.84 MB |

**Il rischio immediato non è l'ordine, è la perdita.** Il codice e i risultati di Fase 2,
la pre-registrazione e la checklist non hanno cronologia né copia remota. Questo va
sistemato prima di qualunque riorganizzazione, perché una riorganizzazione su file non
versionati è irreversibile.

---

## 2. Il principio: si divide per DIMENSIONE, non per paper

Il codice è condiviso: `phase8_cutsky_mocks` è usato da M26, dal Paper 1 e dal Paper 2.
Spezzare `src/` per paper significherebbe duplicarlo o rompere gli import. La struttura
per paper la danno invece gli **indici** `papers/<nome>/README.md`, che mappano ogni
figura e tabella del manoscritto allo script che l'ha prodotta e al file di risultato che
la contiene. È questo che rende l'archivio auto-riparante quando si aggiunge un paper: la
struttura cresce senza toccare il codice.

### Quattro livelli

| livello | cosa | quanto | dove |
|---|---|---|---|
| **A. git** | codice, documenti, manoscritti, risultati testuali | ~600 file, ~35 MiB | GitHub + zip su Zenodo |
| **B. Zenodo dati** | binari congelati non rigenerabili in tempi ragionevoli | ~2–4 GiB | Zenodo, stessa versione |
| **C. rigenerabile** | prodotto da noi, riproducibile da seme documentato | ~160 GiB | **non si archivia**: ricetta nel README |
| **D. esterno** | dato di terzi | ~169 GiB | **non si rideposita**: si cita col suo DOI |

### Perché il livello C è difendibile, e non una scorciatoia

Il cancello 2.5 ha verificato che i campi delta dei mock sono **bit-identici** se rigenerati
da `seed + kk`: 40 su 40, in entrambi gli emisferi, con `np.array_equal` vero. I 31.3 GiB
di `paper1_mock_deltas` non vanno depositati perché sono **dimostrabilmente** rigenerabili,
non perché sono scomodi. Il README riporta il comando e rimanda a `results/paper2/gate25.jsonl`.

Lo stesso argomento non è ancora stato verificato per `phase0_fields` (93.8 GiB) e
`phase2_tau_fields` (31.0 GiB): finché non lo è, vanno dichiarati «rigenerabili, non
verificati», che è una cosa diversa e va scritta così.

---

## 3. Struttura proposta

```
cauchy/                          UN repo, UN concept DOI
  README.md                      cos'e', quale paper sta dove, come si riproduce
  CITATION.cff                   con ORCID e il concept DOI
  ARCHIVE.md                     questo documento
  .gitignore  .gitattributes

  src/                           159 file, PIATTO. Condiviso fra i paper.
  papers/
    m26/       README.md         <- da paper0/paper B, paper0/paper C
    paper1/    README.md         <- da paper1/
    paper2/    README.md         <- da D:\projects\cauchy_3.0  (51 file)
      prereg/paper2_prereg_v1.md
      checklist_paper2.md, canovacci, item docs
  results/                       SOLO testo: json, jsonl, csv, txt
    paper1/  paper2/  revision/  ...
  MANIFESTS/                     manifest congelati per tier
  docs/prompts/                  35 file di sessione (valutare se pubblici)

  literature/                    FUORI da git: PDF di terzi, 131 MiB, diritti altrui
  data/                          FUORI da git: livelli C e D
```

**`cauchy_3.0` non diventa un secondo repository.** I suoi 51 file vanno in
`papers/paper2/` del repo esistente. Un repo, un DOI, nessuna divergenza da riconciliare
più avanti — che è la ragione per cui il concept DOI unico è stato scelto.

---

## 4. Cosa va nel livello B, nominalmente

| | file | spazio | perché |
|---|---|---|---|
| `results/paper1/curves_NGC_R5` | 2000 | 1.3 GiB | prodotto primario del Paper 1 |
| `results/paper1/curves_SGC_R5` | 2000 | 736 MiB | idem |
| `data/processed/phase6_fields/bgs_{ngc,sgc}_mask_128.npy` | 2 | 4.0 MiB | nodo condiviso da ~30 script |
| `results/paper1/null_ladder_{NGC,SGC}_n2000.npy` + `.json` | 4 | 3.7 MiB | bersaglio congelato del Paper 1 |
| `results/paper1/per_mock_{NGC,SGC}_R5.jsonl` | 2 | 3.1 MiB | l'anomalia |
| `src/paper2_v1_reference.json` + amendments | 2 | 19 KiB | il set congelato |

Totale ≈ **2.1 GiB**. Le scale `curves_NGC_R10..R30` (2.1 GiB) sono la scansione di
smoothing: si depositano solo se una figura le usa, altrimenti livello C.

---

## 5. Ordine di esecuzione

Ogni passo è reversibile finché non si arriva al 4.

1. **Mettere in sicurezza.** `.gitignore` e `.gitattributes` nuovi, poi committare i 52
   non tracciati e i 7 modificati. **Prima** di spostare qualunque cosa: `git mv` conserva
   la cronologia solo di ciò che è già tracciato.
2. **Importare `cauchy_3.0`** in `papers/paper2/`. Verificare che `mnras.bst` e `mnras.cls`,
   presenti in entrambi gli alberi e byte-identici, non vengano duplicati.
3. **Riorganizzare** con `git mv`: `paper0/` → `papers/m26/`, `paper1/` → `papers/paper1/`.
   `src/` non si tocca.
4. **Scrivere i tre `README.md`** per paper: indice figura → script → file di risultato.
   È il passo che richiede più giudizio e meno tempo macchina.
5. **Tag e deposito.** `v3.0-paper2`, versione nuova del concept 21128856, con lo zip del
   codice **e** i file del livello B.
6. **Aggiornare il DOI di versione** nel §9 della pre-registrazione e nelle dichiarazioni
   di disponibilità dei manoscritti.

---

## 6. Il nodo Zenodo, da decidere prima del passo 5

L'integrazione GitHub crea una versione a ogni release e vi mette **solo lo zip dei file
tracciati**: non può includere i binari del livello B. Aggiungerli a mano creando una
versione manuale funziona una volta, ma la release GitHub successiva genera un'altra
versione col solo zip, e il record alterna versioni con e senza dati.

- **Opzione 1 — deposito manuale, integrazione disattivata.** Un concept DOI; ogni versione
  contiene zip del codice e dati. Più lavoro per rilascio, ma il DOI significa sempre la
  stessa cosa. *Coerente con la ragione per cui il concept DOI unico è stato scelto.*
- **Opzione 2 — due record**, uno automatico per il codice e uno manuale per i dati,
  incrociati nei metadati `related_identifiers`. Meno lavoro, ma rinuncia al DOI unico.

---

## 7. Da verificare, non assumere

- **Cosa contiene davvero `CAUCHY-v2.1-phase9b.zip`.** Se il Paper 1 cita il concept DOI
  come archivio della pipeline e lo zip è fermo a phase9b, la dichiarazione di
  disponibilità del Paper 1 va corretta **nella revisione in corso**, non dopo.
- **Se `results/paper2/inventory.json` (21 MiB) e `inventory_report.json` (7.5 MiB)
  vadano committati.** Sono artefatti rigenerabili: propendo per il no, con lo script in
  git e l'output in `.gitignore`.
- **Se `docs/prompts/` debba essere pubblico.** 35 file di sessione: utili alla
  riproducibilità del *processo*, ma è una scelta, non un obbligo.
