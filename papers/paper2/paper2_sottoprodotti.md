# Sottoprodotti del congelamento v1 — da citare nel Paper 2
### Registro aperto — 25 agosto 2026

Cose scoperte durante la Fase 0 che hanno valore scientifico proprio, non solo di igiene interna.
Ognuna costa poche righe nel manoscritto e toglie una domanda dalla bocca di un referee.

---

## S1 — Nessuna realizzazione duplicata in tutto l'ensemble v1 ★

**Il fatto.** Confronto SHA-256 esaustivo su **34 611 artefatti binari** dell'ensemble v1:

| tier | artefatti | hash distinti | duplicati |
|---|---|---|---|
| features (vettori a 8 feature per mock) | 12 189 | 12 189 | **0** |
| fields (campi δ a 128³) | 2 202 | 2 202 | **0** |
| diagrams (curve di Betti, diagrammi *H*₁) | 16 221 | 16 221 | **0** |
| superseded (diagrammi a scatola periodica) | 4 000 | 4 000 | **0** |

**Perché conta.** Il Paper 1 documenta un difetto di path-collision in cui *"mock indices 0–199 were
overwritten by a subsequent run with a different HOD"*, difetto che aveva prodotto la dispersione
errata di 445 poi corretta a 313.0. Nessuno aveva mai verificato se quel difetto avesse lasciato
residui altrove nell'ensemble.

Non li ha lasciati. Ogni campo δ, ogni vettore di feature, ogni diagramma è una realizzazione
distinta. Questo **chiude per esclusione** l'ipotesi che il deficit sia contaminato da realizzazioni
duplicate — un'ipotesi che riduce artificialmente la dispersione mock-to-mock e quindi gonfia
qualunque significatività calcolata contro di essa, incluso il residuo beyond-two-point a 6.8σ.

**Dove va.** Sezione metodologica del Paper 2, accanto al congelamento dell'ensemble. Due righe.
Formulazione possibile:

> An exhaustive SHA-256 comparison across the 34,611 binary artefacts of the frozen ensemble finds no
> byte-identical pair: every mock field, feature vector and persistence diagram is a distinct
> realisation. The path-collision defect reported in [Paper 1] left no residue elsewhere in the
> ensemble, which excludes duplicated realisations as a source of artificially deflated mock-to-mock
> dispersion.

---

## S2 — L'escursione ritirata 2.0/2.7 era la scala priva del livello *k* = 1

**Il fatto.** M26 R1 riporta *"complete-ladder excursion 6.8/9.8 percentage points, correcting the
submitted 2.0/2.7"*, senza spiegare l'origine dell'errore. Il confronto fra i record del 24 e del
26 luglio la spiega: il run precedente scandiva *R* = 10, 12, 15, 17 ai livelli di erosione {0, 2, 3}
— **senza *k* = 1**. Verificato aritmeticamente su entrambi gli emisferi:

| | scala | max | min | escursione | dichiarato |
|---|---|---|---|---|---|
| NGC | livelli {0,2,3} | 20.6 | 18.6 | **2.0** | *"submitted 2.0"* |
| | livelli {0,1,2,3} | 25.4 | 18.6 | **6.8** | *"corrected 6.8"* |
| SGC | livelli {0,2,3} | 20.0 | 17.3 | **2.7** | *"submitted 2.7"* |
| | livelli {0,1,2,3} | 27.1 | 17.3 | **9.8** | *"corrected 9.8"* |

**Perché conta.** Il massimo della scala di erosione **sta a *k* = 1**, e nel primo passaggio quel
livello non era stato calcolato. Non era un errore di calcolo: era un livello mancante. Per la
Componente C questo è direttamente rilevante — il picco che genera la tensione a fattore ~24 fra
§7.2 e §8.1 è stato scoperto tardi, in un run separato, il che rende la sua verifica su ensemble v2
più informativa e non meno.

**Dove va.** Sezione Componente C, come contesto sulla provenienza del numero che si va a rimisurare.

---

## S3 — Tre correzioni appaiate del Paper 1 riprodotte dai record congelati

Scansione automatica dei record contro le firme congelate, senza rieseguire nulla:

| record | campi | differenza | corrisponde a |
|---|---|---|---|
| `n6_fkp_NGC.jsonl` | `unit` 35 449.9 / `fkp` 35 372.0 | **77.9** | pesatura FKP, −78.0 ± 8.0 |
| `n7_nfw_NGC.jsonl` | `uniform` 35 454.7 / `nfw` 35 398.2 | **56.5** | profilo NFW, −56 ± 24 |
| `n9_res256_NGC.jsonl` | `n128` | 35 447.1 ± 276.7 | Tab. 11, esatto |
| `n2_persistence_NGC.jsonl` | `n_tot`, min | **31 226** | "lowest mock" di M26, esatto |

**Perché conta.** È una pre-esecuzione parziale del cancello 2.1, e passa. Non va nel manoscritto,
ma va nel record congelato del Paper 2 come evidenza che i numeri pubblicati sono ricostruibili dai
soli record archiviati, senza accesso ai 26 GiB di campi.

---

## S4 — Note di provenienza minori, da annotare e non correggere

**Due valori di σ_px fiduciale in circolazione.** I record per-mock riportano
`sigma_px = 0.32042249039652254`, che è esattamente 5.0/(1997.3629167166155/128) e quindi
autoconsistente col modulo. Ma `paper1_rev_n8_masks.py`, `paper1_rev_n8b_differential.py` e
`paper1_rev_v3b_pilot_box.py` hard-codano `SIGMA_FID = 0.3204385518606827`, che corrisponde a una
cella di 15.603616 invece di 15.604398.

Scarto relativo 5 × 10⁻⁵, cioè **~3 × 10⁻⁴ σ** sul sistematico σ_px di +8.42σ: numericamente nullo.
Ma sono due costanti che si dichiarano entrambe "σ_px fiduciale", e finiscono negli script che
producono il bias differenziale di maschera. Da uniformare quando si tocca quel codice, non prima.

**Tre precisioni del lato del box.** `1997.3629167166155` in `phase8_cutsky_mocks.py`, `1997.4` in
tre script di calibrazione, `1997.0**3` in `phase_r51_calibrate_mmin.py`. Differenze fino allo 0.02%,
irrilevanti per una calibrazione di densità.

---

## Ambiguità di provenienza — tutte chiuse

| | oggetto | diagnosi | esito |
|---|---|---|---|
| **A** | due CSV byte-identici | entrambi contengono il **refit HOD** (35 304.56 ± 1033.00, min 27 766, un mock sotto DESI) | **nome sbagliato**, non dato corrotto |
| **B** | quattro record di erosione | il `_bak` è lo stato **pre-correzione**: raggi ritirati ai livelli {0,2,3}, **senza *k*=1** | risolta, vedi S2 |
| **C** | otto `*_manifest.json` identici | sono **registri di completamento** `{indice: "done"}`: 30 890 byte = 2000 voci esatte, 311 byte = 20 voci esatte | **benigna per costruzione** |

Nessuna delle tre tocca i dati. Insieme a S1 (zero duplicati in 34 611 artefatti), l'ensemble v1 è
pulito: le anomalie erano tutte di etichettatura, in file di riepilogo, e nessuna raggiunge i numeri
pubblicati.

### Osservazione di documentazione, non di correttezza

I `*_manifest.json` sono registri di avanzamento, non manifest: descrivono *fin dove* un run è
arrivato, non *cosa* era. Nessuno di loro può quindi servire da provenienza —
`phase6_mock_manifest_z05_R10.json` non contiene nulla che lo leghi a un run a *R* = 10. I parametri
vivono nei `*_diagnostics.json`. `*_checkpoint.json` sarebbe un nome più onesto, quando si tocca
quel codice.

---

## Azioni residue

- [ ] **A1 — il nome.** `results/phase8_test2_permock.csv` afferma di essere il record per-mock del
      test2, e contiene il refit HOD a *N* = 200. Rimuoverlo con `git rm` documentando il motivo
      (il gemello `_hodfit.csv`, byte-identico, porta il nome corretto), oppure rinominarlo.
      In entrambi i casi il manifest `records` va **ricostruito da zero** — è append-only, `--force`
      lascerebbe la voce stantia — e il digest `e905d7fd…` cambierà. Da fare prima di citarlo in
      `REPRODUCIBILITY.md`.

- [ ] **A2 — il sottoinsieme etichettato.** Il file con le colonne (*w*₀, Ω_m, σ₈) ha la firma del
      refit HOD, non del baseline: media 35 304.56 contro 35 436.7, σ 1033.00 contro 313.0, minimo
      27 766 contro 31 226. Se M26 §5.5 legge da qui, la correlazione parziale *r* = −0.015 e la
      Fig. 5 poggiano su mock con **HOD ricalibrato**.

      Scelta difendibile — è l'occupazione preferita dai dati — ma la didascalia *"mocks (labelled)"*
      lascia intendere il baseline, e il testo dice che la risposta binned è piatta a ~35 400 contro
      i 35 305 di questo file. Da chiarire mentre M26 è in revisione: **quale script produce −0.015
      e da quale file legge.** Se è questo, basta una parola nella didascalia.

- [ ] **E — l'ensemble canonico.** `results/paper1/per_mock_NGC_R5.jsonl`, campo **`base.N_H1`**
      (annidato sotto `base`, accanto a `remap` e `null` dell'esperimento a un punto). Da confermare
      con `--only E` sulla sonda corretta: attesi media 35 436.7, σ 313.0, rango 1/2001. È il campo
      che il cancello 2.1 deve interrogare.
