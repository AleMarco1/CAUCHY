# Item 0.1 — CHIUSO
### Congelamento dell'ensemble v1 — 25 agosto 2026

---

## Stato

| | |
|---|---|
| dichiarazione scritta | ✅ |
| valori di riferimento raccolti e verificati | ✅ 10 controlli su 10 |
| strumento scritto e testato | ✅ 6 test in sandbox |
| manifest generati sui dati reali | ✅ 34 836 file, 26.771 GiB |
| `verify` pulito dopo il commit | ✅ `CLEAN` |

---

## I cinque digest definitivi

Ensemble v1 = `voxelize_mock` con **pesi unitari**. Immutabile. Ogni numero del Paper 2 porta
l'etichetta `v1` o `v2`; l'espressione *"ensemble fiduciale"* senza suffisso è ritirata.

| tier | file | dimensione | `aggregate_sha256` |
|---|---|---|---|
| **records** | 225 | 20.72 MB | `e905d7fd085b23e9a7e534e2583a4940a40904d1a6cf3bdc3a0e9011ffe882ce` |
| **features** | 12 189 | 24.33 MB | `b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc` |
| **fields** | 2 202 | 18.47 GB | `bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34` |
| **diagrams** | 16 221 | 4.49 GB | `3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929` |
| **superseded** | 4 000 | 5.74 GB | `f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764` |

Reference set: `src/paper2_v1_reference.json`, sha256 `865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc`.
Escluso: 4005 file / 32.10 GiB (Branch B: tau field, grafi GNN; più 2 `.bak`).

Questi sono i digest da citare nel protocollo congelato, nella pre-registrazione (item 0.6) e in
`REPRODUCIBILITY.md`.

---

## Cosa l'item ha trovato, che è la ragione per cui esiste

Un congelamento che non trova nulla è tempo perso. Questo ha trovato cinque cose.

**1. Un record v1 mancava dal disco.** `results/phase8_test2_permock.csv` era tracciato in git ma
cancellato dalla working tree, quindi fuori dal congelamento. Recuperato.

**2. L'intero corredo numerico del Paper 1 era fuori dal repository.** La regola `/results/*/`
nascondeva `paper1/` (75 record, 17.35 MB — **l'84% dell'intero tier records**), `revision/` (i
record della revisione di M26, §4.1, §5.2, §5.6), `paper2/` (i manifest di integrità stessi) e
`phase4_sr_runs/`. La Data Availability di M26 R1 dichiara che l'archivio *"adds the records
produced for the referee revision"*: prima di questa correzione non era vero.

**3. Il codice che ha prodotto i numeri del Paper 1 era untracked.** Venticinque script
`src/paper1_*.py`, mai aggiunti a git. Ora committati.

**4. La conversione EOL avrebbe distrutto il congelamento.** Con `core.autocrlf=true` un checkout
trasforma un file da 48 a 50 byte e ne cambia lo SHA-256: `verify` avrebbe segnalato drift su ogni
file di testo dopo ogni clone. Risolto con `.gitattributes` (`results/** -text`), verificato
sperimentalmente prima e dopo.

**5. Due file di record hanno nomi che si contraddicono.** Vedi sotto.

---

## Aperto: tre ambiguità di provenienza

Nessuna blocca il Paper 2, ma tutte vanno risolte prima di citare i numeri corrispondenti.

### A. I due CSV byte-identici — **da risolvere**

```
10 891 byte  ae733e1e…  results/phase8_test2_permock.csv          (ripristinato da git)
10 891 byte  ae733e1e…  results/phase8_test2_permock_hodfit.csv   (mai tracciato)
```

Stesso contenuto, nomi incompatibili: uno dei due mente. E 10 891 byte sono ~200 righe, non 2000 —
M26 Tab. 1 riporta il refit HOD a *N* = 200. L'ipotesi è che un run con HOD diverso abbia scritto sul
percorso base, la stessa famiglia di difetto già documentata nel Paper 1 (indici 0–199 sovrascritti,
σ da 445 a 313.0).

**Decisivo:** media ~35 305 con σ ~1033 → refit HOD; ~35 437 con σ ~313 → baseline.

### B. I record di erosione `_bak` — **priorità, è la Componente C**

```
5 645 byte  af80917abbc4  paper1_erosion_NGC_restrict_bak.json   24 lug 13:14
2 808 byte  57b80df172f0  paper1_erosion_NGC_restrict.json       26 lug 14:21
5 635 byte  3ae1a7c12eb6  paper1_erosion_SGC_restrict_bak.json   24 lug 13:30
2 868 byte  bc63a27eb79f  paper1_erosion_SGC_restrict.json       26 lug 14:17
```

**Non** sono copie: hash e dimensioni diversi. Il più vecchio è il più grande, cioè il più recente
contiene meno dati. La finestra 24→26 luglio è quella in cui l'escursione della scala è stata
corretta (M26 R1: *"complete-ladder excursion 6.8/9.8 percentage points, correcting the submitted
2.0/2.7"*).

Perché è prioritario: la scala di erosione *k* = 0–3 è la **Componente C del Paper 2**, la tensione a
fattore ~24 fra §7.2 (−78 loop dalla pesatura FKP) e §8.1 (+1840 loop dall'escursione *k* = 0→1). Il
Paper 2 dovrà ripetere quella scala su ensemble v2 e confrontarla con v1: sapere quale dei due file
sostiene Tab. 9–10 è un prerequisito, non un dettaglio. Si lega anche al chiarimento già in sospeso
fra `--k` e `n_mocks` in `paper1_mask_erosion.py`.

### C. Sei manifest di input identici — probabilmente benigno

`phase5_hod_b3_manifest.json`, `phase6_mock_manifest_z05.json`, `phase6_mock_manifest_z05_R10.json`,
`phase_b3_cal135_manifest.json`, `phase_b3_cal135_v2_manifest.json`, `phase_oc1_pk_hod_manifest.json`
— tutti 30 890 byte, stesso sha, da maggio a giugno. Più `phase_r51_manifest_v3.json` identico alla
versione base nonostante il "v3".

Plausibile se descrivono lo stesso elenco di 2000 simulazioni; sospetto se ciascuno doveva descrivere
un run distinto. Da guardare quando capita.

---

## Regole operative che discendono dal congelamento

Da mettere nel protocollo del Paper 2:

1. **Mai leggere `results/paper1/` per glob.** Esistono `per_mock_NGC_R{5,10,12,15,17,20,30}.jsonl`,
   ma solo **R = 5 è affidabile**: la scansione multi-scala è stata ritirata per contaminazione di
   bordo. Un `per_mock_NGC_R*.jsonl` mescolerebbe silenziosamente risultati validi e ritirati.
2. **`phase1_persistence_diagrams/` non è v1.** È la configurazione a scatola periodica di M26
   App. D. Contiene però `b2_birth`/`b2_death` con ~29 500 generatori *H*₂ per campo: è la misura di
   partenza per il **Paper 3-bis**, non cancellarla.
3. **La 4.2a non deve rigenerare in loco.** L'ensemble v2 scrive in percorsi nuovi. Il tier `fields`
   esiste per rendere rilevabile la violazione.
4. **Prima di ogni sessione di lavoro sul Paper 2**, un `verify` dei tier `records` e `features`
   (istantanei, 45 MB in totale).

---

## Ultimo passo, meccanico

I cinque summary registrano ancora `commit e9297d53, dirty: 146`, stato precedente al commit
`363c1d4`. Rilanciare i cinque `freeze`: non ricalcolano nulla, riscrivono i summary con
`dirty: false` e il commit corretto.

**I cinque digest devono restare identici.** Nessun file è stato aggiunto o rimosso dal disco: è
cambiato solo il tracciamento git. Se restano identici, è la dimostrazione che il congelamento è
indipendente da git — che è esattamente la proprietà per cui è stato costruito.

---

## Prossimo: item 0.5

Ispezione del codice, tre domande a risposta binaria. La prima decide se metà del Paper 2 esiste:

> Il cubo di embedding e Δ*x* sono **ricalcolati dal catalogo random** a ogni run, o hard-coded a
> `L = 1997.36`?

Se sono derivati, la Proposizione 2 si applica alla pipeline com'è e la componente isotropa dell'AP è
esattamente nulla per costruzione. Se sono hard-coded, non si applica e la Fase 1 va ripensata.

Due punti di partenza già identificati: `src/phase8_test2_masked.py` (la pipeline like-for-like) e
`results/paper1/src_bundle_phase9.txt` (132 KB di sorgenti raccolti dentro i risultati).
