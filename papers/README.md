# `papers/` — indice dei manoscritti

Questa cartella organizza il materiale editoriale del progetto CAUCHY. Il **codice resta in
`src/`, piatto e condiviso**: `phase8_cutsky_mocks` è usato da tutti e tre i lavori, e separarlo per
paper significherebbe duplicarlo o rompere gli import. La struttura per paper la danno questi
indici, non l'albero dei sorgenti.

## Cosa c'è qui, e cosa no

| | in questo repository | dove |
|---|---|---|
| **M26** — MN-26-2100-P | **no** | locale, `papers/m26/` |
| **Paper 1** — MN-26-2388-P | sorgenti **no**, record di lavoro **sì** | `papers/paper1/` |
| **Paper 2** — in preparazione | tutto sì | `papers/paper2/` |

**I manoscritti in revisione, i rapporti dei referee e le lettere editoriali non sono versionati
qui.** I rapporti di peer review sono confidenziali e i due manoscritti sono sotto valutazione. Il
materiale esiste sul disco dell'autore ed è escluso via `.gitignore`; verrà depositato su Zenodo al
momento della pubblicazione, non prima.

Quello che resta versionato è ciò che rende il lavoro verificabile: i **record di provenienza**, le
**pre-registrazioni**, le **checklist**, e la **mappa figura → script**.

## File

- **`FIGURE_PROVENANCE.md`** — provenienza delle dodici figure di M26 e Paper 1: quale script
  produce quale figura, quali sono rigenerabili dal dato congelato, e quale è esclusa
  deliberatamente. Nessuna figura è senza spiegazione.
- **`paper1/README.md`** — indice dei record del Paper 1.
- **`paper2/README.md`** — indice della pianificazione e della pre-registrazione del Paper 2.

## Riproducibilità

Il record congelato dell'ensemble v1 è `src/paper2_v1_reference.json`
(sha256 `332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d`, immutabile), con gli
emendamenti in `src/paper2_v1_amendments.jsonl`, append-only. I cinque tier del freeze sommano a
**34 836 file e 26.771 GiB**; i manifest sono in `results/paper2/ensemble_v1_freeze_*.json`.

I dati di terzi (DESI DR1, BOSS DR12, cataloghi Quijote) non sono ridepositati: si citano con i
propri DOI. I campi delta dei mock non sono archiviati perché **dimostrabilmente rigenerabili**: il
cancello 2.5 (`results/paper2/gate25.jsonl`) verifica che siano bit-identici se ricalcolati da
`seed + kk`, 40 su 40 nei due emisferi.
