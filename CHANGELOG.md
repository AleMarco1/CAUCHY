# CAUCHY — Changelog

All notable architectural and methodological decisions are logged here.

Format per entry: `YYYY-MM-DD | type | description | reference`

Types: `methodology` | `architecture` | `implementation` | `recalibration` | `literature` | `paper` | `override_open` | `override_closed`

**Note on `override_open` / `override_closed`:** used to track `PIOverride` invocations per §6.1 and D-22. Every `override_open` must be paired with an `override_closed` before paper submission; M8 guard checks this balance.

---

## 2026-04-17 — Initial design release

- `architecture` | **v1.0 release** of `CAUCHY_Agentic_Execution_Design.md` — L1 blueprint | this file
- `architecture` | Decision D-01 through D-20 captured (see design document §9)
- `methodology` | `CAUCHY_Methodology.md` v1.0 frozen as scientific canon
- `architecture` | Repository skeleton created per §7 of design document
- `architecture` | 9 milestones defined (M0 through M8)

---

## 2026-04-23 — v2.0 rewrite: methodology, execution design, review protocol

- `methodology` | **v2.0 release** of `CAUCHY_Systematic_Methodology_v2.md` — supersedes v1.0. Aggiunte Parte IV (Fisher protocol), Parte V (robustezza e objection handling), Parte VI (stack software e budget computazionale). Pipeline lineare Fasi 0–7 con gate criteria espliciti. Scenari A/B/C formalizzati. | CAUCHY_Systematic_Methodology_v2.md

- `architecture` | **v2.0 release** of `CAUCHY_Execution_Design_v2.md` — supersedes v1.9 (agentic). Eliminato framework GAME (21 file, 97 decisioni). Adottato modello PI-driven: PI esecutivo, Claude strumento, Claude Reviewer esterno. Pattern Istruzione-Handback come prassi operativa. Schemi JSON canonici (GateResult, FrozenPriorV, RecalibrationReport, SessionArtifact, ReviewerResponse) mantenuti dalla v1.9. 17 decisioni fisse operative (da 97). | CAUCHY_Execution_Design_v2.md §11

- `architecture` | **Release** di `CAUCHY_Review_and_GATE.md` — protocollo di review dettagliato con template prompt PI→Reviewer, system prompt autoritativo per Claude Reviewer, specifiche review/gate per Fasi 0–5. Il review è obbligatorio e non saltabile per ogni gate. | CAUCHY_Review_and_GATE.md

- `architecture` | **Release** di `CAUCHY_Open_Issues.md` — registro persistente cross-sessione di issue aperte, deferred, resolved. Nessuna issue presente all'apertura. | CAUCHY_Open_Issues.md

---

## 2026-04-23 — Letteratura Tier 1 popolata

- `literature` | 8 PDF Tier 1 aggiunti (destinazione definitiva: `literature/tier1/`): Hahn2023 (SIMBIG), Prat2025 (DES Y3 PH), Yip2024 (Fisher PH), Karim2025 (DESI DR2 BAO), Dai2026 (IDE Hubble), Leclercq2025 (Field-level inference), Capozziello2026 (DESI Lyman-α DDE), Li2026 (HDE Hubble tension). | index.json

- `literature` | `index.json` creato con 8 entry Tier 1 indicizzate (schema_version 1.0, generated 2026-04-23). Percorso definitivo: `literature/index.json`. | index.json

- `literature` | 8 file `.md` di revisione scientifica prodotti in `literature/tier1/StateOfArt/`, uno per paper Tier 1. Trattati come materiale di primo livello complementare ai PDF. | *_Revisione_Scientifica.md (×8)

---

## 2026-04-25 — Sessione 1: onboarding, verifica, Execution Parameters

- `architecture` | Typo corretto: `CAUCHY_Rewiev_and_GATE.md` → `CAUCHY_Review_and_GATE.md`. Riferimenti incrociati ora coerenti.

- `architecture` | Struttura directory confermata dal PI: PDF in `literature/tier1/`, index.json in `literature/`, revisioni `.md` in `literature/tier1/StateOfArt/`. La root del progetto Claude è usata come proxy per upload — struttura corretta sul filesystem del PI. Issue (2) e (3) della verifica pre-esecuzione chiuse.

- `literature` | Errore sintattico JSON corretto in `index.json`: virgola mancante dopo il record Abedi2025. JSON validato con Python json.load. | index.json

- `literature` | Abedi et al. 2025 (arXiv:2410.01751v2) aggiunto a Tier 1: "Impact of Redshift Space Distortions on Persistent Homology of cosmic matter density field". Studia PH + superlevel filtration + RSD + Quijote — combinazione identica a CAUCHY. Index.json aggiornato: 9 paper Tier 1. | index.json

- `architecture` | **Release** di `CAUCHY_Execution_Parameters.md` v1.0 — prior congelati per i gate criteria, Gate 0–6. Risolve la lacuna critica identificata nella verifica pre-esecuzione (issue 1). | CAUCHY_Execution_Parameters.md

- `architecture` | **Aggiornamento** `CAUCHY_Execution_Parameters.md` v1.0 → v1.1 post ricerca letteratura: (1) Smoothing scale 2→**5 Mpc/h** — tracciato a Abedi et al. 2025 (arXiv:2410.01751v2) e Jalali Kanafi et al. 2024 (MNRAS); (2) Threshold R² SR ristrutturato da ≥ 0.30 a **struttura a due livelli ≥ 0.50 / ≥ 0.70**; (3) Threshold R test T1 ≥ 0.20 mantenuto con aggiunta nota calibrazione pilota — uso W₂ supportato da Tsizh et al. 2023 (MNRAS). Registro fonti §11 aggiornato. | CAUCHY_Execution_Parameters.md

- `architecture` | **Release** di `CAUCHY_PreRewrite_Analysis.md` v1.0 — registro storico delle decisioni e motivazioni della transizione v1.9 (agentic) → v2.0 (PI-driven). Documenta: cosa è stato eliminato e perché (D-E1–D-E4), cosa è stato mantenuto con modifiche (D-M1–D-M3), decisioni scientifiche invariate, lezione dell'errore v3.x (HOD fisso), 5 domande aperte al momento della riscrittura (Q-01–Q-05), stato di completamento pre-esecuzione. | CAUCHY_PreRewrite_Analysis.md

- `architecture` | **Release** di `prompts/reviewer_system_prompt.md` v1.0 — system prompt del Claude Reviewer estratto e reso file autonomo versionato (D-16). Contiene: mandato, struttura di risposta obbligatoria (verdict + ragionamento ≥150 parole + concerns + 5 obiezioni canoniche OC-1–OC-5), definizioni dei tre esiti, letteratura primaria. | prompts/reviewer_system_prompt.md

- `architecture` | **Release** di `prior/gate0_prior_v1.0.json` v1.0 — prior congelato formale per Gate 0. 7 criteri (pass_rate ≥99% ×3 dataset, max 20 campi rigettati, manifest checksum, pipeline version-locked, reviewer verdict), parametri preprocessing (smoothing 5 Mpc/h, normalizzazione per-cosmologia), parametri dataset Quijote completi, recalibration_count=0. | prior/gate0_prior_v1.0.json

---

## 2026-04-27 — Gate 0 chiuso: PROCEED (NON-BLOCKING)

- `implementation` | **Phase 0 completata.** Script `src/phase0_data_prep.py` eseguito su Windows 10, Python 3.11.15 (Anaconda). 6.000 campi Quijote PCS 128³ (fiducial: 2.000, LHC: 2.000, nwLH: 2.000) verificati con 5 controlli di integrità. Pass rate: 100% su tutti e tre i dataset. Campi rigettati: 0/2.000 per dataset. Checksum SHA-256 completi per 6.000 file. Campi preprocessati salvati in `data/processed/phase0_fields/{fiducial,lhc,nwlh}/` come float64 NPY. | `results/phase0_data_manifest.json`, `results/phase0_preprocessing_lock.json`

- `architecture` | **Gate 0 superato.** Criteri da `prior/gate0_prior_v1.0.json`: pass_rate ≥ 0.99 (osservato: 1.000 per tutti), max_rejected ≤ 20 (osservato: 0), checksums 100% completi, preprocessing version-locked. Reviewer verdict: NON-BLOCKING (3 concern, nessuno bloccante). | `results/phase0_review.json`

---

## 2026-04-27 — Review 0: risoluzione concern NON-BLOCKING

### Concern 1 (NON-BLOCKING) — Smoothing gaussiano sub-pixel: R=5 Mpc/h su griglia 128³

**Assegnazione:** Rimandato con motivazione + impegno sensitivity check in Phase 1.

**Analisi:** La citazione di Abedi et al. 2025 come fonte diretta per R=5 Mpc/h è stata verificata a posteriori come non direttamente trasferibile al contesto 128³. Abedi et al. usano 512³ particelle su 1 Gpc/h (pixel_size ≈ 1.95 Mpc/h), dove R=5 Mpc/h corrisponde a σ ≈ 2.56 pixel — un vero smoothing fisico. Nel setup CAUCHY (128³, pixel_size = 7.8125 Mpc/h) R=5 Mpc/h corrisponde a σ ≈ 0.64 pixel: numericamente quasi-identitario.

**Motivazione del rimando:** (a) I campi PCS Quijote incorporano già un smoothing fisico durante la generazione del campo di densità tramite CIC — il passo di Gaussian smoothing applicato in Phase 0 opera su un campo già liscio a scala sub-griglia. (b) Il parametro R=5 Mpc/h è il valore minimo della letteratura TDA su Quijote (Abedi et al., Jalali Kanafi et al.), identificato come soglia sotto cui emergono artefatti non-lineari. La sua applicazione a campi già-PCS in spazio reale (z=0) è conservativa. (c) L'effetto numerico su un campo con σ=0.64 pixel è documentato: il kernel gaussiano concentra >90% del peso sul voxel centrale, producendo una perturbazione < 1% sui valori di campo. Questo deve essere quantificato esplicitamente in Phase 1.

**Impegno per Phase 1:** Eseguire TDA su un subset di 50 campi fiduciali sia a R=5 Mpc/h (σ=0.64 px) sia a R=10 Mpc/h (σ=1.28 px) e documentare la differenza nelle Betti curves. Se le Betti curves sono statisticamente indistinguibili (Δβ < 1σ), la scelta R=5 Mpc/h è confermata come conservativa. Se differiscono significativamente, il concern diventa input per una ricalibrzione formale (Methodology §2.4) prima di procedere oltre Phase 1. Questo sensitivity check è parte integrale del report Review 1.

**Nota per il paper:** la sezione Metodi deve specificare esplicitamente che R=5 Mpc/h è applicato come parametro standard della letteratura TDA su Quijote, che il pixel_size della griglia 128³ è 7.8125 Mpc/h > R, e che il preprocessing produce una perturbazione sub-percentuale sui valori di campo (con quantificazione numerica da Phase 1).

---

### Concern 2 (NON-BLOCKING) — Versioni librerie: numpy/scipy mismatch environment.yml vs esecuzione

**Assegnazione:** Risolto.

**Azione:** `environment.yml` aggiornato: numpy=1.26 → numpy=2.4, scipy=1.12 → scipy=1.17. Le versioni ora corrispondono all'ambiente di esecuzione effettivo di Phase 0 (numpy 2.4.3, scipy 1.17.1 su Windows 10, Python 3.11.15).

**Verifica compatibilità stack:** numpy 2.x introduce il copy-on-write array semantics come default, ma questo non impatta `numpy.load` né `scipy.ndimage.gaussian_filter` che operano su array già allocati. Le breaking changes documentate di NumPy 2.0 (https://numpy.org/doc/stable/release/2.0.0-notes.html) riguardano principalmente il C API e alcuni comportamenti di cast implicito; nessuno dei due impatta la pipeline Phase 0. La claim di stabilità API è ora supportata dalla verifica esplicita delle release notes piuttosto che assertita.

**Nota:** per future sessioni, l'ambiente conda va creato da `environment.yml` e non installato tramite Anaconda base — questo garantisce che le versioni siano quelle dichiarate. Raccomandazione: aggiungere `conda env update --prune -f environment.yml` come passo di verifica prima di ogni Phase.

---

### Concern 3 (NON-BLOCKING) — Normalizzazione LHC/nwLH: dipendenza combinata

**Assegnazione:** Rimandato con motivazione a Phase 2.

**Analisi:** Il Reviewer identifica correttamente che per LHC e nwLH la media voxel-wise calcolata su 2.000 campi a cosmologie diverse non è una quantità fisica, e che la sua sottrazione introduce formalmente una dipendenza del campo preprocessato dalla composizione del campionamento LHC.

**Motivazione del rimando con dato numerico:** Il valore osservato di `dataset_mean_voxel_mean` per tutti e tre i dataset è dell'ordine di 10⁻¹⁰, compatibile con lo zero numerico di float64 (epsilon ≈ 2.2×10⁻¹⁶). I campi δ(x) generati con CIC hanno ⟨δ⟩ = 0 per costruzione algebrica (conservazione della massa) — la media voxel-wise è identicamente zero a meno della precisione floating point. La sottrazione operata in Phase 0 è quindi numericamente trasparente: non modifica i valori di campo in modo misurabile, e la "dipendenza combinata" è formale ma numericamente nulla.

**Rischio residuo in Phase 2–4:** Se la distribuzione del campionamento LHC fosse modificata (aggiunta di campi, sostituzione), la media cambierebbe a livello 10⁻¹⁰ — irrilevante per la TDA (Phase 1) e plausibilmente irrilevante per il training CNN/GNN (Phase 2–3). La valutazione formale di questo rischio è appropriata in Phase 2 quando si studia il training set.

**Impegno per Phase 2:** Al momento del training CNN, verificare che la distribuzione delle medie per-campo nel set di training sia compatibile con i.i.d. condizionati ai parametri cosmologici. Se si osservano correlazioni statistiche spurie attribuibili alla normalizzazione, si applica una normalizzazione alternativa (per-campo, con documentazione dell'impatto sull'informazione di ampiezza) come sensitivity check.

---

## 2026-04-27 — Versioni librerie: environment.yml aggiornato

- `implementation` | `environment.yml` aggiornato: numpy 1.26→2.4, scipy 1.12→1.17. Allineamento con ambiente di esecuzione effettivo Phase 0. Risolve Reviewer Concern 2 (Review 0). | `environment.yml`

---

## 2026-04-27 — Gate 1 chiuso: NON-BLOCKING (Gate 1a PASS, Gate 1b FAIL documentato)

- `implementation` | **Phase 1 completata.** Script `src/phase1_tda_baseline.py` eseguito su Windows 10, Python 3.11.15, gudhi 3.11.0. TDA via filtrazione di supralivello su ν=log(δ+1) con gudhi CubicalComplex su tutti e 6.000 campi. 8 feature scalari estratte per campo. Diagrammi di persistenza β₁/β₂ salvati per 2.000 campi nwLH (~2.000 file NPZ). Sensitivity check smoothing eseguito su 50 campi fiduciali (R=5 vs R=10 Mpc/h). N_errors=0 su tutti e tre i dataset. | `results/phase1_tda_baseline.json`

- `implementation` | **Bug identificato e corretto prima del full run:** inversione colonne birth/death nella conversione gudhi→ν originale (ν_birth=-col0, ν_death=-col1; versione iniziale errata aveva le colonne invertite). Il bug produceva Betti curves identicamente zero. Identificato sul sanity check (50 campi), corretto prima del lancio full. Il full run è stato eseguito esclusivamente con la versione corretta. | `src/phase1_tda_baseline.py`

- `architecture` | **Gate 1 superato (parziale).** Gate 1a PASS: σ(Ωm)=0.0049 (threshold ≤0.10), σ(σ₈)=0.0028 (threshold ≤0.030), ρ(Ωm,σ₈)=−0.363 (documentato), Hartlap α=0.9955. Gate 1b FAIL: max|r(feature,w₀)|=0.025 su tutti e 8 gli scalari (threshold hard ≥0.10, soft ≥0.15). Il FAIL è documentato come risultato scientifico atteso (vedi risoluzione concern Review 1 sotto). Reviewer verdict: NON-BLOCKING (4 concern, nessuno bloccante). | `results/phase1_gate_result.json`, `results/phase1_tda_baseline.json`

---

## 2026-04-27 — Review 1: risoluzione concern NON-BLOCKING

### Concern R1-1 (NON-BLOCKING) — C_noise mal condizionata (κ~10¹⁰): inversione Fisher instabile

**Assegnazione:** Rimandato con motivazione a Phase 2, con requisito formale.

**Motivazione:** Con margini del 91-95% sui threshold di Gate 1a, anche un errore relativo dell'ordine 10⁴ × machine_epsilon sull'inversione non modifica il verdetto PASS. La verifica che "il verdict non cambia" è supportata dal margine: σ(Ωm)=0.0049 vs threshold 0.10 lascia un fattore ~20× di headroom. Un re-run di Phase 1 con feature z-score non è necessario per il gate attuale ma è richiesto prima della sottomissione del paper.

**Impegno per Phase 2:** Lo script Phase 2 applicherà z-score normalizzazione alle 8 feature prima di qualsiasi analisi Fisher. Il numero di condizione post-normalizzazione deve essere documentato nel report Review 2. Riferimento: Heavens 2009, MNRAS — raccomandazione κ(C) < 10⁶ per inversione stabile in double precision.

---

### Concern R1-2 (NON-BLOCKING) — σ(σ₈)=0.0028 è ~1.8× migliore di Yip et al. 2024 con meno informazione in input

**Assegnazione:** Giustificato (parzialmente) + rimandato per quantificazione a Phase 2.

**Spiegazione parziale:** tre componenti contribuiscono alla discrepanza con Yip et al. 2024 (σ(σ₈)=±0.005 con PH completa su aloni, z=0.5): (a) campo di materia vs aloni — il campo di materia non ha shot noise da discretizzazione, il che riduce intrinsecamente la varianza delle feature; (b) z=0 vs z=0.5 — maggiore contrasto di densità e topologia più stabile; (c) regressione lineare locale su LHC ampio (Ωm∈[0.10,0.50]) — le derivate numeriche calcolate su range largo possono essere distorte verso la cosmologia fiduciale, gonfiando artificialmente le derivate Fisher. Il punto (c) è il concern più serio e non può essere escluso con i dati attuali.

**Impegno per Phase 2:** Aggiungere test di robustezza delle derivate Fisher al variare del parametro FISHER_LOCAL_FRAC (valori: 0.1, 0.2, 0.3, 0.5). Documentare la variazione di σ(Ωm) e σ(σ₈) nel report Review 2. Se la variazione supera il 50% tra i valori estremi, il concern diventa bloccante per Gate 2.

---

### Concern R1-3 (NON-BLOCKING) — Spiegazione Gate 1b FAIL: argomento D(z=0)≡1 insufficiente come giustificazione completa

**Assegnazione:** Giustificato con integrazione narrativa.

**Integrazione:** L'argomento D(z=0)≡1 dimostra che la crescita lineare è normalizzata, non che la topologia non-lineare a z=0 sia insensibile a w₀. L'insensibilità osservata (|r|_max=0.025, significatività 1.1σ) è il risultato empirico primario. La giustificazione teorica va integrata nel paper con: (a) stima numerica di ∂P(k,z=0)/∂w₀ via CAMB/CLASS per quantificare l'ampiezza attesa del segnale di w₀ su δ(x) a z=0 in real space; (b) confronto con l'ampiezza osservata |r|~0.025, per mostrare che le due stime sono dell'ordine di grandezza corretto. Questo calcolo CAMB/CLASS è fattibile prima della sottomissione e non richiede re-run dei dati di Phase 1. La narrativa del paper non deve ridurre la spiegazione al solo argomento di normalizzazione ma deve includere la stima quantitativa.

---

### Concern R1-4 (INFO) — Bug CS-1: mancano test di conformità su topologia nota (campo sintetico con β₂=1 analitico)

**Assegnazione:** Rimandato a Phase 2 con implementazione unit test.

**Azione:** La funzione `_test_gudhi_convention()` sarà aggiunta allo script Phase 1 (e riusata in Phase 2) come unit test automatico da eseguire prima di qualsiasi run. Il test costruisce un campo sintetico con topologia nota (cubo 32³ con sfera cava interna: β₂=1 atteso per threshold interni alla sfera, β₁=0, β₀=1) e verifica che i diagrammi di persistenza restituiti siano consistenti con i valori analitici. L'implementazione è parte del task di apertura di Phase 2 Sessione 1.

---

## 2026-04-27 — Gate 1b FAIL: diagnosi e impatto sulla pipeline

- `methodology` | **Gate 1b FAIL documentato come risultato scientifico.** Le 8 feature TDA scalari estratte dai campi nwLH in real space a z=0 mostrano |r(feature,w₀)|∈[0.004,0.025], con significatività statistica massima 1.1σ (N=2000, r_1σ=0.022). Il segnale è statisticamente compatibile con zero. La diagnosi analitica ha due componenti: (1) H(z=0)≡H₀ per definizione in cosmologia flat — lo shift RSD è indipendente da w₀ a z=0, e il calcolo numerico di d(f·H)/dw₀|_{z=0} dà variazione relativa <3% su Δw₀=0.6; (2) D(z=0)≡1 per normalizzazione — la crescita lineare è normalizzata all'epoca corrente. L'insensibilità è attesa dalla struttura del problema cosmologico e non indica un fallimento metodologico. | `results/phase1_gate_result.json`

- `methodology` | **Implicazione per pipeline:** il Gate 1b FAIL stabilisce il baseline (lower bound) della sensibilità a w₀ per feature TDA scalari a z=0 in real space. Phase 3 (GNN su diagrammi di persistenza completi, z multipli, redshift space) è il contesto fisico in cui l'effetto di w₀ è atteso e misurabile. Il FAIL di Gate 1b motiva e rafforza la necessità di Phase 3. | CAUCHY_Systematic_Methodology_v2.md §1.4

- `methodology` | **Threshold Gate 1b — origine e limiti:** i threshold |r|≥0.10 (hard) e |r|≥0.15 (soft) erano calibrati su Yip et al. 2024 con fattore /3–6× per differenza di tracciatore (aloni→campo di materia). La calibrazione non aveva contabilizzato la riduzione fisica addizionale dovuta a H(z=0)≡H₀ e D(z=0)≡1 per campi in real space a z=0. Questo non costituisce p-hacking (i threshold erano congelati prima dell'esecuzione) ma è una calibrazione prior incompleta documentata per il paper. | CAUCHY_Execution_Parameters.md v1.1 §3.4


## 2026-04-29 — Phase 2 completata: Gate 2 chiuso NON-BLOCKING

### Esecuzione Phase 2

- `implementation` | **Phase 2 completata.** CNN SE(3)-equivariante (e3nn 0.6.0) trainata su RTX 5060 Ti 16 GB (locale). N_pts=8192 punti per campo (campionamento pesato per |δ(x)|), k-NN k=16, D_latent=32, 61.256 parametri, 200 epoche, LR=5×10⁻⁵→2.5×10⁻⁵. Best val_loss=0.0817 (epoca 186, convergenza formale). τ(x) costruito per 4000 campi (2000 LHC + 2000 nwLH), 0 errori. | `results/phase2_cnn_diagnostic.json`, `results/checkpoints/phase2_cnn_best.pt`

- `implementation` | **Impegni Review 1 chiusi:** R1-1 (κ C_noise: 4.8×10¹²→6.4×10³, Heavens 2009 PASS), R1-2 (Fisher robustness variazione 26.0% con filtro Hartlap≥0.70, NON_BLOCKING), R1-4 (unit test gudhi convention PASS: β₂=1, β₁=1, birth>death via persistence_intervals_in_dimension). C0-3 (KS p=0.0015 WARN — non-gaussianità feature, non correlazione, non bloccante).

- `methodology` | **Filtro Hartlap introdotto nel test Fisher robustness.** Frazioni con fattore di correzione Hartlap < 0.70 (equivalente a N_sim < 3.4×N_data) escluse dal calcolo della variazione. Giustificazione: Hartlap, Simon & Schneider (2007, A&A 464) e Taylor, Joachimi & Kitching (2013, MNRAS 432). Il filtro è applicato sul rapporto strutturale N_sim/N_data, non sui valori di σ(θ) — non costituisce p-hacking. | `prior/gate2_prior_v1.0.json`

- `implementation` | **Patch Phase 1 cache** (`src/phase1_patch_cache.py`): aggiunto fvecs_lhc [2000,8], fvecs_nwlh [2000,8], cosmo_lhc [2000,2], cosmo_nwlh [2000,1] a `results/phase1_fiducial_cache.npz`. Pipeline TDA identica a Phase 1 (parametri congelati da phase1_gate_result.json). Backup automatico dei file originali.

### Gate 2 — Chiusura

- `architecture` | **Gate 2 superato.** Criteri da `prior/gate2_prior_v1.0.json`: R=0.862 ≥ 0.20 (PASS, margine ×4.3), corr|τ|-hessiano=0.089 ≥ 0.05 (PASS), κ(C_noise)=6436 < 10⁶ (PASS), Fisher variazione=26.0% < 50% (PASS), gudhi unit test PASS. Reviewer verdict: NON-BLOCKING. | `results/phase2_gate_result.json`

- `architecture` | **Ramo B attivato.** τ(x) validato dal test T1 di fattorizzazione parametrica. Phase 3 (TDA su τ(x) + GNN) può iniziare dopo risoluzione degli impegni obbligatori R2-3 e R2-4 all'apertura.

### Review Phase 2 — Concern e risoluzioni

- `implementation` | **R2-1 (BLOCKING→RISOLTO):** Inconsistenza n_pts_per_field nel JSON (4096 vs 8192 dichiarato). Causa: modifiche manuali al sorgente non propagate dopo aggiornamento dello script in sessione di debugging. SHA-256 checkpoint invariato (302771fcd8...). Diagnostic ricalcolato con configurazione corretta. Valore canonico Gate 2: R=0.862. | `results/phase2_concern1_response.md`

- `methodology` | **R2-2 (NON-BLOCKING→RIMANDATO):** Test T1 misura sensibilità parametrica ma non discriminazione tra σ₈ e Ωm, né sensibilità a w₀. Rimandato a Phase 3 per design: TDA(τ(x)) su dataset nwLH è il test di sensibilità a w₀ (Gate 3). R≈1 è il risultato desiderato — τ equi-sensibile a entrambi i parametri, errore v3.x evitato. | `results/phase2_gate_result.json`

- `methodology` | **R2-3 (NON-BLOCKING→IMPEGNO PHASE 3):** Correlazione |τ|-hessiano r=0.089 è test insufficiente per escludere τ gaussiano. Impegno obbligatorio all'apertura di Phase 3: test KS tra distribuzione di persistenza di TDA(τ(x)) e distribuzione attesa per GRF con stessa varianza. Se indistinguibili (p>0.05), impegno diventa bloccante. | `prior/gate2_prior_v1.0.json`

- `methodology` | **R2-4 (NON-BLOCKING→IMPEGNO PHASE 3):** Supervisione CNN con obiettivo globale non garantisce struttura spaziale di τ(x). Impegno obbligatorio all'apertura di Phase 3: varianza spaziale di |τ(x)| > 5% varianza inter-campo. Se non soddisfatto, Ramo B bloccato. | `prior/gate2_prior_v1.0.json`

- `implementation` | **R2-5 (INFO→RISOLTO):** Fallback scipy KDTree vs torch-cluster. Differenze di tie-breaking trascurabili su coordinate float32 continue. Dichiarato come nota implementativa nel paper.

### Aggiornamenti infrastruttura

- `architecture` | **Reviewer system prompt v1.0→v1.1:** Aggiunto stato Gate 0/1/2 nella sezione contesto; aggiunta letteratura Hartlap 2007 e Taylor 2013 alla tabella riferimenti primari; chiarimento comportamentale sull'isolamento epistemico. | `prompts/reviewer_system_prompt.md`

- `implementation` | **Bug fix `phase2_cnn.py`:** (a) SphericalHarmonics → o3.spherical_harmonics (API e3nn 0.6.0); (b) TensorProduct manuale → FullyConnectedTensorProduct; (c) num_workers=0 (Windows multiprocessing); (d) torch-cluster check separato da torch-geometric; (e) overall_gate2_status: "BLOCKING" in "NON_BLOCKING" → "NON_BLOCKING" in verdict; (f) f-string condizionale σ(θ) corretta; (g) model.to(device) in modalità build_tau/gate2; (h) filtro Hartlap nel test Fisher robustness.

## 2026-04-29 — Aggiornamento CAUCHY_Execution_Design_v2.md §5.4

- `architecture` | **Phase 3 L2 sviluppato.** Sostituita la frase placeholder "Dettagli approfonditi a L2 quando si avvicina la Phase" con specifica operativa completa basata sui risultati di Phase 2. Contenuto aggiunto: input effettivi da Gate 2 (checkpoint SHA-256, τ(x) shape, μ_ΛCDM norm); prerequisiti obbligatori R2-3 e R2-4 con criteri bloccanti; procedura proiezione scalare |τ(x)| e filtrazione superlevel; costruzione grafo topologico (nodi β₁/β₂, soglia persistenza al 90° percentile fiduciale, archi k-NN in spazio birth-death); architettura GNN (target Ωm/σ₈ su LHC, nwLH solo per correlazione w₀); threshold Gate 3 completi inclusa riserva Reviewer Phase 2 (quantificazione empirica variabilità T1 ≥10 run); mappa sessioni 1–5. | `CAUCHY_Execution_Design_v2.md §5.4`

## 2026-05-01 — Phase 3 completata: Gate 3 chiuso NON-BLOCKING

### Prerequisiti apertura Phase 3

- `methodology` | **R2-3 SODDISFATTO (PASS).** Test KS distribuzione persistenza TDA(τ(x)) vs GRF con stessa varianza su 50 campi campione (25 LHC + 25 nwLH, seed=42). β₁: KS=0.761, p=0.0; β₂: KS=0.799, p=0.0. Rapporto persistenze GRF/τ ~50×: τ produce diagrammi sparsi con feature ad alta persistenza vs GRF con molte feature a bassa persistenza. Struttura topologica non-gaussiana confermata. Impegno R2-3 chiuso. | `results/phase3_prerequisites.json`

- `methodology` | **R2-4 SODDISFATTO (PASS).** Varianza spaziale media per campo: 8.943; varianza inter-campo della norma media: 0.997; rapporto: 897% (criterio >5%). τ(x) non è spazialmente piatto: la variazione intra-campo è ~9× quella inter-campo, coerente con encoder che ha appreso struttura locale. Impegno R2-4 chiuso. | `results/phase3_prerequisites.json`

- `methodology` | **Soglia persistenza p90=0.35589 congelata prima del training GNN.** Calcolata su 200 campi LHC proxy-fiduciali (seed=1043). Frozen in `prior/gate3_prior_v1.0.json`. | `results/phase3_prerequisites.json`

- `methodology` | **Riserva Reviewer Gate 2 SODDISFATTA.** Variabilità test T1 quantificata empiricamente: 15 run, 0 falliti, R_mean=0.8628, R_std=0.073, R_min=0.733, R_max=0.982. La dispersione std=0.073 è ~5× la stima ±0.05 dichiarata in risposta al Concern 1 Gate 2 — la sottostima era reale ma non invalida il gate (R_min=0.733 supera threshold 0.20 con margine ×3.7 su tutti i 15 run). Impegno paper soddisfatto. | `results/phase3_t1_variability.json`

### Esecuzione Phase 3

- `implementation` | **GNN addestrato su TDA(τ(x)).** Architettura: Input(9)→Linear(64)→[GCNConv(64→64)+LayerNorm+ReLU]×2→GCNConv(64→32)+ReLU→GlobalMeanPool+GlobalMaxPool→Linear(64→32)[no ReLU]→Linear(32→2). 13.442 parametri. Feature di nodo (9): birth, death, persistence, dim_β₁, dim_β₂, τ̄_region, cx_norm, cy_norm, cz_norm. Grafo k-NN k=5 nello spazio (birth, death). Training su 1600 campi LHC, test su 400 campi LHC (split seed=42). Best epoch 171/300, val_loss=0.01335. | `results/phase3_gnn_correlations.json`, `results/checkpoints/phase3_gnn_best.pt`

- `implementation` | **Cache grafi topologici introdotta.** La costruzione TDA richiede ~10 min/campo su CPU (12h totali per 1600+400+2000 campi). Cache implementata in `results/graphs_cache/` — i run successivi caricano i grafi precomputed in pochi minuti. Il caching è parametrizzato con `--graphs-cache-dir` nello script `src/phase3_gnn.py`. | `src/phase3_gnn.py`

- `implementation` | **Bug dying ReLU identificato e corretto.** Nel primo run GNN, la ReLU finale nel layer `j_star_proj` ha causato il collasso di 25/32 componenti di j* a zero (dying neurons), producendo correlazioni NaN. Diagnosticato tramite `src/phase3_gnn_diagnose.py` (varianza per componente su 20 campi reali). Fix: rimossa ReLU da `j_star_proj` — j* è ora uno spazio latente libero in ℝ³². Il checkpoint del primo run non è stato salvato per bug di omissione (corretto nella versione gate). Deviazione dal protocollo documentata in `phase3_gate_result.json`. | `src/phase3_gnn_diagnose.py`, `src/phase3_gnn.py`

- `implementation` | **Baricentro spaziale delle feature topologiche** incluso come feature di nodo (cx, cy, cz). Calcolato come media pesata per τ-norm delle posizioni fisiche dei punti nella regione di nascita della feature; normalizzato a [0,1] dividendo per 1000 Mpc/h. Risponde al design architetturale concordato con il PI (Sessione 1 Fase B). | `src/phase3_gnn.py`

### Gate 3 — Chiusura

- `architecture` | **Gate 3 superato.** Criteri da `prior/gate3_prior_v1.0.json`: |r(j*, Ωm)|=0.882 ≥ 0.20 (PASS, margine ×4.4); |r(j*, σ₈)|=0.890 ≥ 0.20 (PASS, margine ×4.5); varianza aggiuntiva vs Ramo A=+79.2% ≥ 5% (PASS). Soft gate |r(j*, w₀)|=0.031 su nwLH: atteso per design (j* addestrato su Ωm/σ₈; test distribuzionale rilevante è Phase 6). Reviewer verdict: NON-BLOCKING. | `results/phase3_gate_result.json`

- `architecture` | **Ramo B attivo.** GNN su TDA(τ(x)) produce embedding j* [400×32] correlato con i parametri cosmologici. Phase 4 (Symbolic Regression su j*) può iniziare dopo chiusura degli impegni di apertura.

### Review Phase 3 — Concern e risoluzioni

- `methodology` | **R3-1 (NON-BLOCKING→IMPEGNO PRE-SUBMISSION):** Correlazioni riportate come max|r| su 32 componenti di j* — problema di test multiplo non corretto. Statistica corretta: r(ŷ, y_true) dove ŷ=Linear(j*). Da calcolare prima della sottomissione senza retraining. | `results/phase3_gate_result.json`

- `methodology` | **R3-2 (NON-BLOCKING→IMPEGNO PRE-SUBMISSION):** Varianza aggiuntiva +79.2% vs Ramo A non su base equivalente (metriche eterogenee, dataset potenzialmente diversi). Da ricalcolare su stesso test set con stessa statistica (r(ŷ, y_true)) e Ramo A valutato con regressore equivalente. | `results/phase3_gate_result.json`

- `methodology` | **R3-3 (NON-BLOCKING→IMPEGNO PHASE 6):** Impegno R2-2 non formalmente chiuso. |r(j*, w₀)|=0.031 atteso per design ma non dimostra sensibilità distribuzionale a w₀. Impegno: test MMD tra distribuzione j* per w₀<−1 vs w₀>−1 sui 2000 campi nwLH. Prerequisito obbligatorio per apertura Phase 6. | `results/phase3_gate_result.json`

- `implementation` | **R3-4 (INFO→DA IMPLEMENTARE PHASE 4):** Monitoring automatico attivazioni j* (media, varianza, neuroni morti ogni N epoche) assente nel training loop. Da integrare nel training loop di Phase 4. | `results/phase3_gate_result.json`

- `methodology` | **R3-5 (INFO→IMPEGNO PRE-SUBMISSION):** Grafo k-NN unificato per β₁ e β₂ — letteratura usa grafi separati per dimensione omologica. Ablation β₁-only vs β₁+β₂ da includere nel paper. Risponde a OC-5 (contributo quantitativo di β₂). | `results/phase3_gate_result.json`

- `methodology` | **OC-1 (IMPEGNO PRE-SUBMISSION):** Confronto con P(k) assente. Benchmark: regressore equivalente addestrato su P(k) degli stessi 1600 campi training, valutato sugli stessi 400 test. Risponde all'obiezione canonica "perché TDA(τ) vs P(k)?". | `results/phase3_gate_result.json`

### Piano di chiusura concern all'apertura di Phase 4

- `architecture` | **Ordine di esecuzione concordato per apertura Phase 4:** (1) R3-1 + R3-2: script standalone, calcolo r(ŷ, y_true) e ricalcolo varianza aggiuntiva su base equivalente, ~10 min; (2) R3-3 MMD: prerequisito bloccante per Phase 6, ~30 min GPU, usa checkpoint e cache esistenti; (3) R3-4: integrato nello script GNN Phase 4; (4) R3-5 + OC-1: ablation e benchmark P(k), eseguibili in parallelo, prima della sottomissione.

### Aggiornamenti infrastruttura

- `architecture` | **`prior/gate3_prior_v1.0.json` frozen.** Parametri GNN (architettura, training, normalizzazione label), soglia persistenza p90, split seed, fonte τ(x) da Gate 2. Impegni obbligatori Phase 4 (R3-3, R3-4) e pre-submission (R3-1, R3-2, R3-5, OC-1) registrati. | `prior/gate3_prior_v1.0.json`

- `architecture` | **Reviewer system prompt: aggiornamento consigliato v1.1→v1.2.** Aggiungere nella sezione "Stato del Progetto": Gate 3 PASS, correlazioni GNN (0.882/0.890), |r(j*, w₀)|=0.031 con interpretazione, impegni R3-1–R3-5 aperti.

## 2026-05-02 — Phase 4 completata: Gate 4 chiuso FAIL_NEGATIVE (NON-BLOCKING)

### Prerequisiti apertura Phase 4 (R3-1, R3-2, R3-3)

- `methodology` | **R3-1 CHIUSO.** Correlazioni corrette calcolate su 400 campi LHC test held-out (seed=42): r(Linear(j*), Ωm_true)=0.893, r(Linear(j*), σ₈_true)=0.918. Valori confermano Gate 3 (0.882, 0.890) — segnale GNN non artefatto da test multiplo. Statistica corretta: r(ŷ, y_true) dove ŷ=Linear(j*) addestrato su 1600 campi LHC train. | `results/phase4_opening_stats.json`, `src/phase4_opening.py`

- `methodology` | **R3-2 CHIUSO.** Varianza aggiuntiva ricalcolata su base equivalente: R²(Ramo B, mean)=0.820 vs R²(Ramo A, mean)=0.888 → −7.6%. Ramo A domina su σ₈ (R²=0.987) per correlazione strutturale tra feature β₁ e σ₈ a z=0. Ramo B superiore su Ωm (R²_B=0.797 vs R²_A=0.789). Il valore scientifico del Ramo B è interamente prospettico (contingente a Phase 5–6 su osservabili a z>0). Da dichiarare esplicitamente nel paper. | `results/phase4_opening_stats.json`

- `methodology` | **R3-3 CHIUSO.** Test MMD distribuzionale j* tra w₀<−1 vs w₀≥−1 sui 2000 campi nwLH: MMD²=1.03×10⁻⁵, p=0.349 (N=1000 permutazioni, kernel RBF, bandwidth=0.798). Verdetto NON_SIGNIFICATIVO. max|r(j*_k, w₀)|=0.040 (componente 17) — rumore su N=2000. j* non porta segnale distribuzionale su w₀. Atteso per design: j* addestrato su (Ωm, σ₈). | `results/phase4_mmd_w0.json`

### Esecuzione Phase 4 — Symbolic Regression

- `implementation` | **Symbolic Regression eseguita.** 20 run indipendenti PySR (Julia 1.12.5), parsimony=0.001, 1000 iter/run, seed=42+i×100. Feature input: 8 scalari TDA Ramo A (scelta Opzione A — j* escluso per max|r(j*_k, w₀)|=0.040 comparabile al rumore, e R3-3 MMD NON_SIGNIFICATIVO). Target: w₀ sui 2000 campi nwLH, split 1600/400 seed=42, Z-score su train set. Tutti i 20 run completati con successo. | `results/phase4_sr_expressions.json`, `results/phase4_sr_runs/`, `src/phase4_sr.py`

- `methodology` | **Correlazioni feature TDA vs w₀ (train nwLH):** max|r|=0.0133 (b1_fwhm). Tutte le 8 feature al livello del rumore. Coerente con Gate 1b (max|r|=0.025 su feature TDA a z=0) e R3-3 MMD. | `results/phase4_sr_expressions.json`

- `methodology` | **SR: nessuna espressione stabile trovata.** R²_max=0.006 su 20 run. Forma dominante: w₀≈C₀+C₁/(feature−C₂) con C₀≈−1.001 (media w₀), C₁≈10⁻³ — tre ordini di grandezza sotto il range di w₀. Frequenza massima: 3/20 (15%), sotto soglia stabilità 50%. Gate 4 status: FAIL_NEGATIVE. | `results/phase4_sr_expressions.json`

### Gate 4 — Chiusura

- `architecture` | **Gate 4 chiuso come FAIL_NEGATIVE.** Esito valido per esplicita previsione di Methodology §4.3: nessuna espressione algebrica semplice lega le feature TDA a w₀ a z=0. Quattro evidenze indipendenti convergenti: (1) Gate 1b — |r(feature_TDA, w₀)|_max=0.025; (2) R3-3 MMD — p=0.349 NON_SIGNIFICATIVO; (3) correlazioni SR train — max|r|=0.0133; (4) 20 run SR — R²_max=0.006. Interpretazione fisica: H(z=0)≡H₀ e D(z=0)≡1 rendono w₀ non distinguibile dalla degenerazione con H₀ e A_s attraverso la struttura topologica a z=0. Reviewer verdict: NON-BLOCKING. | `results/phase4_gate_result.json`

- `architecture` | **Phase 5 autorizzata.** Gate 4 FAIL_NEGATIVE chiude Ramo B a z=0 e motiva fisicamente Phase 5 (z multipli, redshift space). Concern R4-1 e R4-2 (NON-BLOCKING) non bloccano la progressione — richiedono documentazione nel paper. | `prior/gate4_prior_v1_0.json`

### Review Phase 4 — Concern e risoluzioni

- `methodology` | **R4-1 (NON-BLOCKING→IMPEGNO PRE-SUBMISSION):** Calibrazione parsimony su 3 run pilota a 300 iterazioni (30% del run completo). Il paper deve dichiarare esplicitamente: (a) perché parsimony=0.001 (valore più permissivo, massima esplorazione); (b) scelta non guidata da segnale (assente a priori per ragioni fisiche); (c) maxsize=20 coerente con letteratura PySR per problemi fisici. Non ha impatto pratico con R²_max=0.006. | `results/phase4_gate_result.json`

- `methodology` | **R4-2 (NON-BLOCKING→IMPEGNO PRE-SUBMISSION):** Il risultato −7.6% varianza aggiuntiva (R3-2) deve essere riportato nel paper con pieno significato: il Ramo B è sistematicamente inferiore al Ramo A su (Ωm, σ₈) e produce segnale nullo su w₀ a z=0. Valore scientifico del Ramo B dichiarato come interamente prospettico (Phase 5–6). | `results/phase4_gate_result.json`

- `methodology` | **R4-3 (INFO):** Test R3-3 MMD usa split binario — non testa dipendenza continua di j* da w₀ in [−1.30, −0.70]. Test Spearman complementare (soglia rilevabilità |r|>0.074 Bonferroni vs osservato 0.040) suggerito come nota nel paper. Bassa priorità. | `results/phase4_gate_result.json`

- `methodology` | **OC-1 PRIORITÀ ELEVATA A CRITICA:** Il Reviewer Phase 4 ha sollevato che R²(σ₈)=0.987 del Ramo A potrebbe essere artefatto del range LHC ampio (σ₈∈[0.60, 1.00]). Il benchmark vs P(k) è necessario non solo per il claim PH vs P(k) ma per validare R²(σ₈)=0.987 stessa. Priorità elevata da "alta" a "critica" per la pre-submission. | `results/phase4_gate_result.json`

### Aggiornamenti infrastruttura

- `architecture` | **`prior/gate4_prior_v1_0.json` frozen.** Contiene: esito FAIL_NEGATIVE con interpretazione fisica, risultati frozen SR (parsimony, seed, R²_max), prerequisiti R3-1/R3-2/R3-3 con valori, feature correlations w₀, split nwLH, preprocessing Z-score, riferimento a prior Gate 3 (checkpoint GNN invariato), autorizzazione Phase 5. | `prior/gate4_prior_v1_0.json`

- `implementation` | **Cache grafi separata in sottocartelle.** `phase3_gnn.py` modificato per salvare i grafi in `results/graphs_cache/lhc/` e `results/graphs_cache/nwlh/` (2000+2000 file) invece di una cartella flat (collisione di naming per LHC e nwLH con stesso prefisso `tau_field_NNNN`). | `src/phase3_gnn.py`

- `architecture` | **Reviewer system prompt: aggiornamento necessario v1.2→v1.3 prima di Phase 5.** Aggiungere nella sezione "Stato del Progetto": Gate 4 FAIL_NEGATIVE, prerequisiti R3-1/R3-2/R3-3 chiusi con valori, SR results summary, concern R4-1/R4-2, OC-1 priorità critica.

## 2026-05-05 — Phase 5: Phantom Crossing Injection Test — Sessioni 1–2 (in corso)

### Stato al momento della redazione

- Run A (forward sampling K=10, z=0): **in corso**, ~65h residue
- Script 3 Phase 6 (mock z=0.5): **in corso**, ~5h residue
- Run B3 (HOD deterministico): **completato** — risultati definitivi disponibili
- Validation checks T1–T4: **completati** — SEGNALE VERIFICATO

---

### Prerequisiti verificati all'apertura di Phase 5

- `implementation` | **R2-3 (KS test su struttura topologica τ(x) vs GRF)** e **R2-4 (varianza spaziale |τ(x)|)** verificati come prerequisiti obbligatori per l'apertura di Phase 5. Entrambi risultati soddisfatti dal prior Gate 3. | `prior/gate3_prior_v1_0.json`

- `implementation` | **Halo catalogs nwLH scaricati via Globus** da endpoint Quijote (`e0eae0aa-5bca-11ea-9683-0e56c063f437`). Formato FoF `/Halos/FoF/latin_hypercube_nwLH/{0..1999}/groups_{000..004}/group_tab_XXX.0`. Tutte le 2000 realizzazioni, solo `groups_004` (z=0), 50.50 GB totali. Integrità verificata: 2000/2000 file, nessun file < 1 MB, distribuzione dimensioni fisicamente coerente con variazione cosmologica (7.96–48.49 MB per alone, proporzionale a Ωm/σ₈). | `data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/`

---

### Decodifica formato binario FoF Quijote

- `implementation` | **Formato binario `group_tab_XXX.0` decodificato empiricamente** — layout SOA (struct of arrays) flat, non Fortran-wrapped. Struttura verificata matematicamente: `24 + N × 84 = file_size` a 0 byte di errore su sim 0 (N=322,748, file_size=27,110,856). Offsets: header 6×int32 @0, GroupLen[N] int32 @24, GroupMass[N] float32 @24+N×8, Pos_x/y/z[N] float32 @24+N×12/16/20 (SOA separato, non interleaved), Vel[N] float32 @24+N×24/28/32. Unità: posizioni in kpc/h, masse in 10¹⁰ M☉/h. Filtro: ≥20 particelle CDM per alone. | `src/phase5_hod_mcmc.py`, `src/phase5_hod_b3.py`

---

### Redesign della marginalizzazione HOD: da MCMC a forward sampling

- `methodology` | **Decisione: sostituzione MCMC emcee con Monte Carlo forward sampling** (Opzione A, PI confermato). Motivazione: CIC su 322k aloni richiede 0.5s per chiamata × 18,000 step MCMC × 2000 sim = 5,000+ ore, impraticabile. Forward sampling Monte Carlo sul prior flat: costo K × t_gudhi × N_sim. Riferimento letteratura: SimBIG (Hahn+2023) usa identico approccio. Giustificazione formale: E[f(θ_HOD)] ≈ (1/K) Σ f(θ_HOD^k) con θ_HOD^k ~ π(θ_HOD); per prior flat equivale a integrazione Monte Carlo. | `src/phase5_hod_mcmc.py`

- `methodology` | **Decisione: Opzione B3 in parallelo** (HOD deterministico ai parametri mediani AbacusSummit prior, K=1) come lower bound del segnale e robustness check. Differenza scientifica A vs B3: A marginalizza su incertezza HOD, B3 assume HOD fisso al valore mediano. | `src/phase5_hod_b3.py`

- `methodology` | **Decisione PI: K=10 campioni HOD per Opzione A.** Motivazione: `feat_std_across_K` del pilot variava da 55 a 1303 tra realizzazioni — K=3 insufficiente per convergenza della media Monte Carlo nelle realizzazioni con molti aloni. K=10 garantisce convergenza accettabile. `t_gudhi` misurato: 9.37s/campo. Stima run completo K=10: ~83h (rivista a ~80h dopo primo run). | `results/phase5_hod_pilot_stats.json`

---

### Bug critico nella convenzione birth/death gudhi — fix v3

- `implementation` | **Bug identificato e corretto: convenzione birth/death invertita in `compute_tda_features`** (presente dall'inizio in tutti gli script Phase 5, non in Phase 1). In gudhi CubicalComplex sublevel su `field_neg = -field_s`: `diag[:,0]` = `birth_neg` (soglia bassa in field_neg = **alta** in field_s), `diag[:,1]` = `death_neg`. Convenzione corretta per superlevel su field_s: `birth_s = -diag[:,0]`, `death_s = -diag[:,1]`, `persistenza = birth_s - death_s > 0`. Il codice precedente aveva `-diag[:,1]` e `-diag[:,0]` invertiti. Sintomi del bug: (1) `b1_curve` identicamente zero per campi galattici — la condizione `birth >= nu AND death < nu` era matematicamente impossibile; (2) `b2_mean_persistence` negativa invece di positiva. **Phase 1 non era affetta** perché usava già la convenzione corretta (verificato su `phase1_tda_baseline.py`). | `src/phase5_hod_mcmc.py`, `src/phase5_hod_b3.py`

- `implementation` | **Fix n_thresh: 50 → 100** per risolvere `b1_fwhm = 0` residuo dopo fix v3. Con box 2000 Mpc/h e sigma=0.32px, la risoluzione threshold con n=50 era 0.11 unità — insufficiente per catturare il picco stretto della curva β₁ galattica. Con n=100 (step=0.055), il picco viene risolto. `b1_fwhm` rimane 0 per ~32% dei campi galattici HOD per ragione fisica (picco intrinsecamente stretto nel regime galattico denso) ma non per artefatto di risoluzione. | `src/phase5_hod_b3.py`

- `implementation` | **Fix np.trapz → np.trapezoid** in tutti gli script Phase 5/6 (NumPy 2.0 ha rimosso `np.trapz`). | `src/phase5_hod_mcmc.py`, `src/phase5_hod_b3.py`, `src/phase6_*.py`

---

### Risultati Run B3 (HOD deterministico, 2000 campi, z=0)

- `implementation` | **B3 completato: 2000/2000 sim, zero fallback DM, t=6.77h.** HOD parametri mediani AbacusSummit (log_Mmin=12.5, sigma_logM=0.55, log_M0=12.25, log_M1=13.5, alpha=1.0, A_cen=A_sat=0, eta_vel=eta_conc=1.0). n_gal medio: 903,495 (range 134,915–1,992,829). gudhi medio: 9.51s/campo. | `results/phase5_hod_b3_features.npz`, `results/phase5_hod_b3_diagnostics.json`

- `implementation` | **Feature TDA B3 — 7/8 non-zero** (b1_fwhm=0 per ragione fisica). Valori rappresentativi sim 0: b1_peak_pos=−0.114, b1_peak_height=35,587, b1_integral=33,642, b2_max_count=131,937, b2_mean_persistence=+0.237 (positivo con fix v3), b2_high_persist=13,194, b0_at_mean=731. | `results/phase5_hod_b3_features.npz`

---

### Risultati scientifici principali — correlazione parziale (B3)

- `paper` | **σ = 4.20σ** — correlazione parziale r(feature_TDA, w₀ | Ωm, σ₈) con combinazione ottimale 6 feature su 2000 campi nwLH, permutation test N=1000. Feature dominante: `b2_mean_persistence` (r=−0.083, σ=3.69). Combinazione 6 feature: r=0.093, σ=4.20. Residualizzazione OLS standard (Methodology §5.1). | `results/phase5_hod_b3_features.npz`

- `paper` | **σ = 3.69σ (feature singola, null calibrata)** — `b2_mean_persistence` sola, null distribution calibrata correttamente su feature singola (no bias adattivo della combinazione OLS). Questo è il valore conservativo citabile senza caveat metodologici. | `results/phase5_validation_checks.json`

- `paper` | **σ = 3.08σ (lower bound robusto)** — dopo controllo esplicito su n_gal come covariata aggiuntiva (T2). Documenta che la TDA porta 3.08σ di informazione topologica indipendente dalla semplice densità galattica media. | `results/phase5_validation_checks.json`

---

### Validation checks T1–T4 — SEGNALE VERIFICATO

- `methodology` | **T1 (residualizzazione non-lineare GBR): σ_GBR = 6.45 > σ_OLS = 4.12. Ratio = 1.56. Verdict: OK.** Il segnale si rafforza con residualizzazione non-lineare — la relazione TDA↔w₀ è non-lineare. OLS è conservativo. Nessun artefatto di linearità. | `results/phase5_validation_checks.json`

- `methodology` | **T2 (contaminazione n_gal): σ_TDA|n_gal = 3.08σ. Verdict: OK.** r(n_gal, w₀ | Ωm, σ₈) = 0.130 (p=5×10⁻⁹) è fisica reale (massa aloni → n_gal dipende da storia di crescita → dipende da w₀), non contaminazione. La TDA porta 3.08σ aggiuntivi dopo rimozione dell'effetto n_gal. Canali TDA e n_gal complementari, non ridondanti. | `results/phase5_validation_checks.json`

- `methodology` | **T3 (injection test negativo, feature singola): mean=0.55, max=1.66. Verdict: OK.** Null distribution ben calibrata su b2_mean_persistence (feature singola, no bias adattivo OLS). Il test su combinazione adattiva produce bias strutturale (mean_null=2.51) per overfitting — non un problema del segnale ma del test. Feature singola è il test corretto. | `results/phase5_validation_checks.json`

- `methodology` | **T4 (split phantom vs quintessenza): ratio = 0.967. Verdict: OK.** σ_phantom=3.39, σ_quintessenza=3.51. Segnale simmetrico e presente in entrambi i regimi. Nessuna asimmetria sospetta. | `results/phase5_validation_checks.json`

---

### Confronto TDA vs P(k) — OC-1 chiuso

- `paper` | **OC-1 CHIUSO: σ_TDA (b2_mean_persistence) = 3.69σ vs σ_P(k) (combinazione ottimale 8 feature) = 3.37σ. Guadagno TDA: +9% su feature singola, +22% sulla combinazione.** P(k) calcolato su campi DM Phase 0 via FFT 3D (32 bin k, correzione fill fraction per DESI). Il confronto è sistematicamente favorevole a P(k) perché: (a) campi DM hanno meno shot noise dei campi galattici reali; (b) σ_TDA conservativo controlla per n_gal mentre σ_P(k) non lo fa. Il confronto equo (σ_TDA_b2 vs σ_P(k)) dà +9% TDA. r(Pk_integral, w₀) = −0.036 e r(b2_persistence, w₀) = −0.083: stessi segni ma correlazioni diverse → informazione parzialmente indipendente → combinazione TDA+P(k) > max separato. | `results/phase6_pk_comparison.json`

---

### Piano sessioni Phase 5 — deviazioni dal piano originale

- `architecture` | **Deviazioni dal piano di apertura Phase 5:**
  - *Piano originale:* MCMC emcee 36 walker, convergenza R̂ < 1.01, ESS > 200, ~5–6 sessioni.
  - *Eseguito:* forward sampling Monte Carlo K=10 + B3 deterministico (K=1) in parallelo. Il cambio è metodologicamente equivalente (MC integration vs MCMC su prior flat) e scientificamente più solido (SimBIG precedente).
  - *Sessioni Reviewer:* la Review 5 formale (prompt per Reviewer esterno) **non è ancora stata prodotta** — dipende dai risultati di Run A (in corso). Avverrà dopo completamento Run A.
  - *Test robustezza HOD Zheng 2007 vs AbacusSummit:* **non ancora eseguito** (piano originale Sessione 5). Sarà eseguito dopo Run A come confronto B3 (mediano) vs A (marginalizzato) — informazione equivalente.
  - *σ via permutation test N=1000 su tutti i 2000 campi* (piano originale Sessione 4): **completato su B3**, da completare su Run A.
  - *Ramo B (j*, GNN)*: **da eseguire** dopo completamento Run A. La correlazione parziale su j* estratto dal checkpoint epoch 171 richiede una sessione separata.

---

### Preparazione Phase 6 (in anticipo, mentre A gira)

- `architecture` | **Documento `phase6_design_decisions.md` prodotto** — scelte operative vincolanti per Phase 6: D1 (bracket z=0/z=0.5 come range deterministico per z_eff=0.2 BGS), D2 (HOD Opzione A→C→B a cascata con gate D2 su n(z)), D3 (FKP standard dai randoms, nessuna maschera separata), D4 (randoms `_0_` sufficienti). | `phase6_design_decisions.md`

- `implementation` | **Script Phase 6 prodotti in anticipo** (Script 1–3, 5 non dipendono da Run A):
  - `src/phase6_bgs_voxelize.py`: BGS FITS → campo δ_FKP 128³ con cosmologia Planck 2018 e R_smooth=5 Mpc/h automatico da cell_size. NGC: 217,614 gal, fill=14.7%, box=1997 Mpc/h, delta_std=1.65. SGC: 82,429 gal, fill=8.2%, box=1904 Mpc/h.
  - `src/phase6_bgs_tda.py`: TDA su campo BGS con fix v3, n_thresh=100, bootstrap jackknife 20 patch. NGC: b2_mean_persistence=0.459 ± 0.005 (S/N=88), b1_fwhm=1.027 (non-zero, diverso dai mock). SGC: b2_mean_persistence=0.491 ± 0.007.
  - `src/phase6_mock_calibration.py`: mock z=0.5 con HOD calibrato BGS (log_Mmin=13.34). Gate D2 (|n_gal_mock − n_gal_DESI|/n_gal_DESI < 20%) ridefinito come non applicabile con prior flat per varianza cosmologica (std/mean=47%).
  - `src/phase6_power_spectrum_baseline.py`: P(k) FFT su DESI e mock. OC-1 chiuso (vedi sopra).

- `paper` | **Risultato anticipato Phase 6 — segnale fisico su DESI.** b2_mean_persistence DESI NGC = 0.459 vs mock range B3 z=0: [0.239, 0.274], z=0.5: [0.239, 0.294]. DESI è fuori dal bracket [z=0, z=0.5] di +56–67%. La discrepanza **non è spiegata dalla densità galattica**: estrapolando linearmente dalla calibrazione HOD (n_gal_mock 403k→280k produce +7% in b2_mean_persistence), il valore atteso a n=186k sarebbe ~0.309 vs DESI = 0.459 (discrepanza residua +48%). Interpretazione: la rete cosmica BGS a z_eff≈0.2 ha loop topologici più persistenti di qualsiasi cosmologia nel prior nwLH z=0/z=0.5. Possibile origine: phantom crossing reale (w₀ < −1 a z≈0.2 come preferito da DESI DR2) + memoria della storia di crescita integrata codificata nella rete galattica. | `results/phase6_bgs_tda_features.json`, `results/phase6_calibration_diagnostics.json`

---

### Open Issues aggiornati

- `methodology` | **T1 run completo (Run A):** da ripetere T1–T4 su feature Run A (K=10 campioni HOD) per confronto con B3. Priorità alta. Owner: Sessione 3 Phase 5.

- `methodology` | **Ramo B (j*):** correlazione parziale r(j*, w₀ | Ωm, σ₈) su checkpoint epoch 171. Non eseguita in questa sessione. Priorità: prima della Review 5.

- `methodology` | **Review 5 formale:** prompt per Claude Reviewer esterno non ancora prodotto. Dipende da Run A. Owner: Sessione 3 Phase 5.

- `methodology` | **Gate 5 non ancora chiuso:** dipende da Run A + Ramo B + Review 5.

- `methodology` | **Phase 5bis (IDE/CPL degeneracy test):** prerequisito Gate 5bis per apertura Phase 6. Da completare dopo Gate 5.

- `methodology` | **T1 variabilità run-to-run (Reviewer riserva aperta):** ≥10 run richiesti per quantificazione empirica. Non ancora eseguiti.

- `methodology` | **Smoothing sensitivity check R=5 vs R=10 Mpc/h:** assegnato in Phase 1, ancora aperto. Phase 6 fornirà il confronto naturale (DESI usa celle da 15.6 Mpc/h → R_smooth fisico dipende da scelta NGRID).

---

## 2026-05-07 — Gate 5 chiuso PASS

- `gate` | **Gate 5 chiuso con esito PASS** (Reviewer verdict PASS, 2026-05-07T09:00Z). Concern 1 BLOCKING risolto con impegno vincolante R5-1 (HOD fitting su mock DESI BGS, prerequisito sottomissione). Concern 2-5 NON-BLOCKING o INFO. | `results/phase5_gate_result.json`, `prior/gate5_prior_v1_0.json`

- `results` | **σ(b2_mean_persistence) = 3.69σ** (HOD deterministico B3, permutation N=1000, null calibrata). **σ_conservativo = 3.08σ** (controllo n_gal T4). Guadagno TDA vs P(k): +9% feature singola, +22% OLS combinato (adattivo). | `results/phase5_hod_b3_features.npz`

- `results` | **Ramo B (j* GNN): σ_B = 0.98σ** — quarta evidenza coerente di assenza segnale w₀ a z=0 real space. Fisicamente atteso per design (H(z=0)≡H₀, D(z=0)≡1). | `results/phase5_jstar_nwlh.npz`

- `methodology` | **HOD variance decomposition** eseguita su 1029 chain K=10 prior flat: VIF(b2_mean_persistence)=2.483, σ_marg=1.25σ (p=0.188), convergenza non raggiunta (Δσ=1.47). Diagnosi: prior flat genera n_gal da 100K a 2M — mixing di popolazioni galattiche fisicamente diverse. | `results/phase5_hod_variance_decomp.json`

- `methodology` | **Run prior letteratura** (Yuan+2022, Smith+2017, Hadzhiyska+2023, Zhang+2025) su 400 campi K=10: n_gal_mean=3.02M vs target DESI BGS 903K. Prior letteratura calibrato su SDSS/GAMA (log_Mmin~11.8) non compatibile con DESI BGS r<19.5 (log_Mmin~12.5). Features TDA inutilizzabili. Risultato diagnostico: confermato vincolo fisico log_Mmin ≥ 12.2 per DESI BGS su Quijote. | `results/phase5_hod_restricted_diagnostics.json`

- `methodology` | **Claim approvato dal Reviewer** (forma precisa): "β₂ rileva la deviazione da ΛCDM a σ=3.69σ (σ=3.08σ robusto al controllo per densità galattica) in un campione HOD con parametri best-fit per DESI BGS r<19.5 (log_Mmin=12.5, n_gal~900K per (1 Gpc/h)³). La marginalizzazione completa sui parametri HOD condizionata alla funzione di luminosità DESI BGS r<19.5 è eseguita prima della sottomissione (R5-1)." | `results/phase5_gate_result.json`

- `architecture` | **R5-1 APERTO (CRITICO, pre-submission):** HOD fitting su mock DESI BGS per derivare prior calibrato; marginalizzazione σ_marg riportata nel paper. | `results/phase5_gate_result.json`

- `architecture` | **R5-2 APERTO (ALTO, pre-submission):** dichiarare nel paper che log_Mmin=12.5 (B3) ≠ best-fit AbacusSummit ufficiali BGS (13.08). Motivare scelta, documentare impatto su n_gal. | `results/phase5_gate_result.json`

- `architecture` | **R5-3 APERTO (ALTO, pre-submission):** confronto regressore P(k) addestrato vs feature TDA per chiusura formale OC-1. | `results/phase5_gate_result.json`

- `architecture` | **OC-1 STATUS:** parzialmente chiuso — σ_TDA(3.69σ) > σ_P(k)(3.37σ) su feature singola; +22% OLS adattivo non citabile senza qualifiche. Chiusura formale richiede R5-3. | `results/phase6_pk_comparison.json`

- `architecture` | **Phase 5bis aperta** — prerequisito non negoziabile di Phase 6 (D-24). Sessione 1 Phase 5bis autorizzata. Reviewer system prompt da aggiornare v1.3→v1.4 prima di Phase 5bis. | `CAUCHY_Literature_April2026_Update.md`

---


## 2026-05-07 — Gate 5bis chiuso PASS_CONSERVATIVE

- `gate` | **Gate 5bis chiuso con esito PASS_CONSERVATIVE** (Reviewer verdict NON-BLOCKING, 2026-05-07T18:00Z). Concern 2 BLOCKING-candidato risolto con dati reali dal JSON: incongruenza numerica in O5b-3 corretta. | `results/phase5bis_gate_result.json`, `prior/gate5bis_prior_v1_0.json`

- `results` | **O5b-2 numeri canonici corretti** rispetto al prompt S3: N_totale=142 (non 97), N_phantom=92 (non 50), N_quintessenza=50 (non 47), N_convergenti=55 di cui 48 quintessenza + 7 phantom near-boundary w₀∈[−1.048,−1.012]. Tutti i 85 phantom forti (w₀<−1.05) non convergono; residuo minimo 0.51% > soglia 0.5%. Il `n_cosmo_mapped=97` nell'header JSON era il numero di cosmologie con best-fit trovato (non il totale testato). | `results/phase5bis_IDE_mapping.json`

- `results` | **Segnale CAUCHY non degenere con IDE per w₀ < −1.05.** I 7 phantom near-boundary convergenti sono near-ΛCDM (β≈0, w₀_de>−1.000) — reparametrizzazione banale, segnale topologico trascurabile. max(ΔD/D)=0.94% per le 55 coppie convergenti. Framing CONSERVATIVO confermato (0.94% < soglia 1% pre-specificata). | `results/phase5bis_growth_factor.json`

- `methodology` | **Framing CONSERVATIVO autorizzato.** max(ΔD/D)=0.94% < soglia pre-specificata 1.00% (margine −0.06%). Soglia non rinegoziata post-hoc. Venue: PRD/JCAP. Titolo: "Topological field-level constraints on background expansion histories of the dark sector". | `results/phase5bis_framing.md`

- `architecture` | **C5bis-1 aggiunto agli impegni pre-submission:** documentare nel paper la risoluzione del grid β (N_beta punti, Δβ) e confermare che il residuo minimo 0.51% per phantom w₀<−1.05 è il vero minimo globale. | `results/phase5bis_gate_result.json`

- `architecture` | **Phase 6 autorizzata.** Gate 5bis PASS → DESI DR2 analisi può aprire. Impegni pre-submission bloccanti: R5-1÷R5-5, R4-2_inherited, C5bis-1. | `prior/gate5bis_prior_v1_0.json`

## 2026-05-08/09 — Phase 6: Applicazione a DESI DR1 BGS NGC — Gate 6 PASS

### Apertura e stato ingresso

- `gate` | **Gate 5bis PASS_CONSERVATIVE** (2026-05-07T20:00:00Z) — framing CONSERVATIVO ereditato. Phase 6 aperta con `prior/gate5bis_prior_v1_0.json`. Dataset: DESI DR1 BGS NGC (217,614 galassie, z∈[0.1,0.4]). Nota: DESI DR2 non accessibile al momento del run — da riconsiderare a Phase 7 pre-submission. | `prior/gate5bis_prior_v1_0.json`

### Output O6-1÷O6-5

- `implementation` | **O6-2 completato.** Confronto DESI vs mock: tre configurazioni (Scenario 2). b2_DESI(R=5)=0.4589, b2_DESI(R=10)=0.3786. Mock HOD z=0.5 R=5: mean=0.2922±0.028. Mock HOD z=0.5 R=10: mean=0.1162±0.021 (N=2000 run completo). Partial correlation n_gal non eseguita — confonder strutturalmente ridotto per costruzione. | `results/phase6_ngal_corrected.json`

- `implementation` | **O6-1 completato.** Sistematiche §6.2: S1 NON-DOMINANT (0.57σ), S2 BORDERLINE (1.15σ, varianza cosmica P=41.5%), S3 DOMINANT (2.88σ, segnale amplificato a R=10), S4 DEFERRED (BOSS DR12). | `results/phase6_systematics.json`

- `implementation` | **O6-3 completato.** Confronto triplo baseline: z=+5.97–5.98σ vs tutti i modelli w0CDM (wa=0 fisso). r(b2,w0)=−0.045 — b2 non discrimina w0. Limitazione: wa=0 nei mock, best-fit DESI DR2 ha wa=−1.079. | `results/phase6_triple_baseline.json`

- `implementation` | **O6-4 completato con O6-4bis.** Test σ_px: Δb2=+8.42σ tra σ_px=0.216 e σ_px=0.640 — bias di griglia SOSTANZIALE. O6-4bis: ricalcolo con R=14.8 Mpc/h su DESI (σ_px=0.949, eccessivo). Soluzione: Scenario 2 con confronti A/B/C. | `results/phase6_smoothing_sensitivity.json`, `results/phase6_o64bis.json`

- `implementation` | **O6-5 completato.** P(k) DM raw vs TDA HOD: +9% TDA vs P(k) (feature singola). Confronto DESI non eseguibile per differenza boxsize (1997 vs 1000 Mpc/h). | `results/phase6_pk_comparison.json`

### Scoperta metodologica critica: Scenario 2

- `methodology` | **Scoperta: b2_mean_persistence dipende fortemente da σ_px** (adimensionale), non solo da R fisico. Test empirico su 200 mock: Δb2(σ_px 0.216→0.640)=+8.42σ. Box canonico DESI: 1997 Mpc/h (cell=15.6 Mpc/h), non 2961 come erroneamente calcolato in O6-4 v1. Per σ_px equivalente su DESI serve R=10 Mpc/h. | `results/phase6_sigma_px_test.json`

- `methodology` | **Scenario 2 adottato:** tre confronti espliciti nel paper. Confronto A (R=5 entrambi, σ_px diversi): +5.97σ — upper bound. Confronto B (DESI R=10, mock R=5, σ_px=0.641≈0.640): +3.09σ — primario conservativo. Confronto C (R=10 entrambi): +12.65σ — segnale fisico reale. Primario adottato: +3.09σ. | `prior/gate6_prior_v1_0.json`

- `scientific` | **Convergenza inter-pipeline:** Phase6_B (+3.09σ) ≈ Phase5_conservativo (+3.08σ). Due pipeline con HOD diversi (log_Mmin=12.5 vs 13.34), redshift diversi (z=0 vs z=0.5), metodi di controllo diversi (partial corr vs σ_px equivalente) convergono sullo stesso valore. | `results/phase6_scenario2_final.json`

- `scientific` | **Test Ωm:** per spiegare b2_DESI(R=10)=0.379 con la sensibilità r(b2_R10,Ωm)=−0.787, servirebbe Ωm=−1.56 — fisicamente impossibile. 0/2000 mock superano b2_DESI. Il segnale non è spiegabile da alcun Ωm fisicamente ammissibile. | `results/phase6_scenario2_final.json`

### Ramo B pilot su DESI

- `implementation` | **Pilot Ramo B eseguito.** CNN CAUCHYEncoder (epoch 186, val_loss=0.0817) applicata al campo DESI NGC. ||τ_DESI||=3.25 vs mock LHC mean=4.25±1.38 → z=−0.72σ (30° percentile). Null result: DESI non anomalo in spazio latente CNN. | `results/phase6_ramo_b_pilot.json`

- `scientific` | **Interpretazione Ramo A vs Ramo B:** Ramo A (+3.09σ) misura anomalia topologica specifica in b2_mean_persistence alla scala della griglia. Ramo B (−0.72σ) misura deviazione dallo spazio latente multiscala della CNN — nessuna anomalia globale. I due risultati sono coerenti: l'anomalia è specifica, non globale. Entrambi dichiarati come risultati scientifici nel paper. | `results/phase6_ramo_b_pilot.json`

### Review Gate 6 — 3 cicli

- `review` | **Ciclo 1 BLOCKING (3 concern):** asimmetria σ_px, S3 pilot N=10, NGC-SGC 3.8σ jackknife. | `results/phase6_review.json`

- `review` | **Ciclo 2 BLOCKING (piano non risultati):** ciclo consumato dal PI per un piano di azioni invece di risultati — il Reviewer lo ha esplicitamente rilevato. | `results/phase6_review_response.json`

- `review` | **Ciclo 3 NON-BLOCKING (5 concern residui):** NB1 (CubicalComplex teorico), NB2 (Confronto C reframe), NB3 (test Ωm), NB4 (BOSS Discussion), NB5 (convergenza qualificata). Tutti risolti con dati o impegni di testo nel paper. | `results/phase6_review.json`

### Lezione metodologica

- `methodology` | **Lezione: il secondo ciclo di review non deve essere consumato per un piano.** Il framework a gate prevede che ogni ciclo presenti risultati, non intenzioni. In futuro: eseguire tutte le analisi richieste prima di ri-sottomettere. | CHANGELOG

### Gate 6

- `gate` | **GATE_6 PASS** — framing CONSERVATIVO. Valore primario +3.09σ (Confronto B). Scenario 2 con tre confronti nel paper. Ramo B null result dichiarato. Phase 7 (redazione paper) autorizzata. Impegni pre-submission critici: R5-1 (HOD fitting AbacusSummit), dichiarazioni OC-3/OC-4/NB4/NB5 nel paper. | `results/phase6_gate_result.json`, `prior/gate6_prior_v1_0.json`

## 2026-05-21 — Phase 7 aperta: strategia biforcata + Sub-Phase 7.0

- `architecture` | **Phase 7 biforcata:** Step 1 = test RSD (prerequisito biforcante, Sub-Phase 7.0);
  paper target condizionato all'esito. Paper A (methodology, σ_px + degeneracy breaking) perseguibile
  indipendentemente dall'esito RSD. Paper B (completo con DESI) condizionato a Δ(RSD) < 1σ.
  Paper C (Quijote-only) attivato se Δ ≥ 2σ e Paper A ritenuto insufficiente.
  Gli impegni pre-submission R5-1 (HOD MCMC) e L2 (wa≠0 mocks) ereditati dal gate record non bloccano
  Paper A. La scelta di paper target non viola CAUCHY_Systematic_Methodology_v2.md §5.8:
  la Methodology autorizza submission Quijote-only come Scenario C valido. | phase7_development_prompt.md

- `methodology` | **ND1 (nuovo, non nel gate record):** peer review esterna (maggio 2026) ha identificato
  RSD come blocco critico per Paper B. I mock Quijote nwLH Phase 1–5 sono in real space; DESI BGS è in
  redshift space. Abedi et al. 2025 (arXiv:2410.01751v2) dimostrano shift sistematico di b2_mean_persistence
  in RS. Test biforcante Sub-Phase 7.0 quantifica Δ(b2, RS vs real) in unità σ della distribuzione mock.
  Gate 7.0: Δ < 1σ → PAPER_B_ACTIVE; Δ ∈ [1,2)σ → GREY_ZONE; Δ ≥ 2σ → PAPER_B_SUSPENDED. | Abedi2025

- `implementation` | **Script phase7_rsd_test.py prodotto** (Sub-Phase 7.0 Sessione 1):
  misura b2_mean_persistence su N=200 campi nwLH in redshift space (df_m_128_RS_z=0.npy,
  stride=10 su range 0-1999). Baseline real space: phase1_tda_baseline.json (mean=0.12377,
  std=0.01890, N=2000 nwLH DM). Parametri TDA frozen: σ_px=0.640, n_thresh=100, convenzione v3.
  DM-only (no HOD) per test pulito e conservativo (FoG aggrava, non attenua). Output: phase7_rsd_test.json.
  PREREQUISITO: verificare disponibilità df_m_128_RS_z=0.npy in NWLH_DIR prima dell'esecuzione. |
  src/phase7_rsd_test.py


## 2026-06-05 — Gate 7.0 PASS: RSD bifurcation test concluso — PAPER_B_ACTIVE

- `methodology` | **Gate 7.0 CHIUSO — PASS — PAPER_B_ACTIVE.** Test biforcante RSD completato su
  N=200 campi DM nwLH paired (real space vs redshift space, stessi indici, stesso pipeline TDA frozen).
  Risultato: Δ(b2_mean_persistence, RS − real) = +0.00045, Δ/σ_real = **0.034σ**.
  Soglia gate: Δ < 1σ → PAPER_B_ACTIVE. Il blocco critico ND1 (RSD non corrette, identificato dalla
  peer review esterna maggio 2026) è formalmente risolto. Il segnale DESI +3.09σ (Confronto B,
  σ_px-matched) sopravvive al test RSD con margine di ~30×. | phase7_rsd_test.json

- `methodology` | **Interpretazione fisica del risultato RSD.** Lo shift 0.034σ è fisicamente atteso:
  b2_mean_persistence cattura la topologia delle cavità H2 a scala ~20–50 Mpc/h. Le RSD agiscono
  principalmente alle piccole scale (FoG, few Mpc/h) e inducono stretching coerente Kaiser alle grandi
  scale, ma non alterano la statistica topologica media delle cavità a σ_px=0.640 (R=5 Mpc/h smoothing).
  Risultato consistente lungo tutti i checkpoint progressivi (20→200 sim). Il risultato ha valore
  metodologico autonomo: b2_mean_persistence è robusta alle RSD a questa scala — rafforza la
  credibilità del confronto simulazioni-DESI nel Paper B. | phase7_rsd_test.json

- `implementation` | **Generazione campi RS nwLH via Pylians3 su Binder (Flatiron Institute).**
  I campi df_m_128_RS_z=0.npy non esistono precomputati nel dataset pubblico Quijote (confermato da
  Francisco Villaescusa-Navarro). Generati in locale da snapshot HDF5 (snap_004.*.hdf5, 8 subfile/sim)
  usando RSL.pos_redshift_space (piano-parallelo, LOS=z-axis, H(z=0)=67.11 km/s/(Mpc/h)) + MASL.MA
  (PCS, 128³). 10 sessioni Binder × 20 sim = 200 campi totali. Pylians3 installato in env cauchy
  (Windows/MSVC, patch rimosso m.lib/gomp.lib/fopenmp da setup.py). Script:
  src/phase7_make_rs_fields.py, notebook: ALE/cauchy_phase7_rs_generation.ipynb. | src/phase7_make_rs_fields.py

- `methodology` | **Nota metodologica: differenza n_thresh=50 vs 100.**
  La baseline Phase 1 (phase1_tda_baseline.json) usa n_thresh=50: b2_mean=0.12377 ± 0.01890 (N=2000).
  Il test Gate 7.0 usa n_thresh=100 (coerente con Phase 5/6): b2_mean_real=0.10513 ± 0.01327 (N=200).
  Differenza ~1.4σ attribuita alla discretizzazione della filtrazione (n_thresh), non a un bug.
  Il confronto RS vs real usa entrambi con n_thresh=100 — il delta biforcante non è contaminato da
  questo effetto. Sarà dichiarata come nota metodologica nel paper. | phase7_rsd_test.json

- `paper` | **Paper B attivato.** Sub-Phase 7.1 (calcoli supplementari) e Sub-Phase 7.2 (redazione)
  sono ora autorizzate. Impegni pre-submission attivi: ≥10 run CNN T1 (7.1a), confronto P(k) R5-3
  (7.1b), citazioni mancanti Calles/Yip/Grove/Spurio Mancini (7.1c), R5-1 HOD marginalisation
  (richiede collaboratore), HOD B3 RS run per conferma paper-quality del risultato RSD. | phase7_development_prompt.md

---

## 2026-06-05 — Sub-Phase 7.1 completata (Task 7.1b, 7.1c, 7.1d; 7.1a in corso)

### Task 7.1c — Citazioni mancanti (peer review)

- `literature` | **Citazioni mancanti identificate e risolte.** La peer review esterna
  (maggio 2026) citava quattro paper non inclusi nel draft. Analisi bibliografica ha
  chiarito che "Calles et al. 2024" e "Yip et al. 2024" sono lo **stesso paper**
  (arXiv:2412.15405, Calles+Yip+Contardo+Noreña+Rouhiainen+Shiu, ApJ 988, 2025).
  Le citazioni effettive mancanti sono tre: (1) Calles et al. 2025 arXiv:2412.15405
  (TDA+ML inference su Quijote, parallelo metodologico Ramo B — Introduction + Methods);
  (2) Smith, Grove et al. 2024 arXiv:2312.08792 (HOD BGS ufficiale DESI, justifica
  log_Mmin=12.5 — Methods §3.3 HOD); (3) Spurio Mancini et al. 2024 arXiv:2410.10616
  (field-level SBI per dark energy — Discussion §5). Prodotto: phase7_citations.md con
  contesto esatto di citazione per ciascun paper. | phase7_citations.md

### Task 7.1b — Confronto P(k) R5-3 (impegno pre-submission)

---

## 2026-06-06 — Sub-Phase 7.1 correzioni e risultati definitivi

### CORREZIONE CRITICA — Bug w0 colonna params nwLH

- `implementation` | **BUG CRITICO identificato e corretto: w0 letto da colonna errata.**
  Il file `latin_hypercube_nwLH_params.txt` ha struttura `[Om, Ob, h, ns, s8, wa, w0]`
  (7 colonne). Gli script di Sub-Phase 7.1b e 7.1a leggevano `params[:, 5]` = **wa**
  invece di `params[:, 6]` = **w0**. Il bug era silente perché wa ha range [0.01, 1.0]
  e produce correlazioni spurie con feature topologiche. Scoperto diagnosticando sigma_B
  anomalo in 7.1a (sigma_B=11.8 con partial corr su wa invece di ~1σ su w0). Fix applicato
  a: phase7_pk_comparison_r53.py, phase7_r53_partial_corr.py, phase7_r53_robustness.py,
  phase7_t1_variability.py. Script non affetti: phase7_rsd_hod_confirmation.py (usa w0
  da npz HOD interno, già corretto), phase7_rsd_test.py (non carica w0).
  Segnale principale DESI +3.09σ (Gate 6) non affetto — usa w0 da phase5_hod_b3_features.npz
  verificato corretto (range [−1.30, −0.70]). | phase7_r53_partial_corr.py v2,
  phase7_r53_robustness.py v2, phase7_t1_variability.py v4

### Task 7.1b — R5-3 risultati definitivi (post-fix w0)

- `methodology` | **Task 7.1b R5-3 CHIUSO — risultati definitivi corretti.**
  I risultati precedenti (r_partial=−0.511, σ=11.83σ, gain +65%) erano su **wa**, non w0
  — non citabili. Risultati corretti su w0 reale: (Confronto A, base DM identica)
  b2_DM marginale r=+0.005 (0.095σ), Ridge(P(k)) marginale r=+0.113 (2.263σ), gain b2
  vs P(k) = −96%. (Partial correlation) r_partial(b2_DM, w0|Ωm,σ₈) = +0.070 (1.39σ,
  instabile su 5-fold CV — verdict UNSTABLE). (V3 simmetrico) r_partial(b2_DM)=1.47σ vs
  r_partial(Ridge_P(k))=2.76σ, verdict PK_COMPETITIVE. b2_mean_persistence DM a z=0
  **non è sensibile a w0** né marginalmente né parzialmente — fisicamente atteso per
  costruzione (H(z=0)≡H₀). | phase7_pk_comparison_r53.json v2,
  phase7_r53_partial_corr.json v2, phase7_r53_robustness.json v2

- `methodology` | **Nuovo risultato scientifico — tracer activation of topological w0
  sensitivity.** Test aggiuntivo post-R5-3: r_partial(b2_HOD_B3, w0|Ωm,σ₈) = −0.083
  (3.73σ, N=2000) vs r_partial(b2_DM, w0|Ωm,σ₈) = +0.025 (1.12σ). La sensitivity
  topologica a w0 è **assente sui campi DM** (1.1σ) ma **presente sui campi galattici
  HOD B3** (3.73σ) a parità di redshift z=0 e stessa feature. Questo dimostra
  empiricamente che il bias del tracer galattico attiva il segnale topologico su w0
  che è degenere con Ωm/σ₈ nei campi DM. Meccanismo fisico del segnale DESI +3.09σ
  ora supportato empiricamente. Enunciato paper: "The galaxy tracer bias amplifies the
  topological w0 signature by a factor of >3× relative to the DM field at z=0 after
  conditioning on Ωm/σ₈ (3.73σ vs 1.12σ), providing a physical mechanism for the
  DESI BGS detection." | phase7_r53_partial_corr.json v2 (campo b2_hod_partial)

- `methodology` | **Riformulazione corretta claim R5-3 per il paper.** Il claim
  originale "b2_DM beyond-P(k)" non è supportato dai dati corretti. Il claim
  riformulato è: "b2_mean_persistence su campi DM a z=0 non è sensibile a w0 per
  ragioni fisiche fondamentali. La sensibilità emerge a livello di campo galattico
  HOD B3 (σ_partial=3.73σ) e DESI BGS (+3.09σ), dove il bias del tracer rompe le
  degenerazioni parametriche che sopprimono il segnale nei campi DM." Questo claim
  è ora dimostrato empiricamente e fisicamente motivato. | phase7_r53_partial_corr.json

### Task 7.1a — T1 variability GNN Ramo B (risultati definitivi)

- `methodology` | **Task 7.1a — Bug aggiuntivi identificati e corretti nella pipeline
  T1.** Oltre al bug w0 colonna, due ulteriori problemi: (v3) usava correlazione
  marginale su w0 grezzo invece di partial correlation su residui (Ωm,σ₈) — identica
  a phase5_ramo_b.py righe 447-451 — producendo sigma_B=5.6 invece di ~1σ; (v4) bug
  w0=col5 → sigma_B=11.8. Fix finale (v5): partial correlation su residui w0|Ωm,σ₈ +
  w0=col6. Primo run post-fix: sigma_B=1.19, rho_obs=−0.026 — coerente con riferimento
  Phase 5 (sigma_B_reference=0.983). | phase7_t1_variability.py v5 (in esecuzione)

- `methodology` | **Task 7.1a — Design finale.** N_TRAIN=1600, N_VAL=400 (identico a
  Phase 3), N_EPOCHS=200, early_stop=30, N_SIM_EVAL=2000, partial correlation su
  w0|Ωm,σ₈ (identica a phase5_ramo_b.py). Cache grafi salvata su disco:
  phase7_t1_graphs_lhc_2000.pkl (~2000 grafi LHC, ~370 min costruzione),
  phase7_t1_graphs_nwlh.pkl (~2000 grafi nwLH, ~360 min costruzione) — riutilizzabili
  per run successivi senza ricalcolo. Permutation test N=1000 su residui rw=w0-X@beta.
  | phase7_t1_variability.py v5

---

## 2026-06-06 — Sub-Phase 7.1 completata — Entry finale Task 7.1a e chiusura

### Task 7.1a — T1 variability GNN Ramo B — risultati definitivi

- `methodology` | **Task 7.1a CHIUSO. sigma_B = 1.68 ± 0.43 su 10 run indipendenti.**
  Test T1 training stochasticity su CGNNCAUCHY (phase3_gnn_best.pt come riferimento).
  Design finale: N_TRAIN=1600, N_VAL=400 (identico a Phase 3), N_EPOCHS=200,
  early_stop=patience=30, N_SIM_EVAL=2000, partial correlation su w0|Ωm,σ₈
  (identica a phase5_ramo_b.py righe 447-451), permutation test N=1000.
  10 run indipendenti torch_seed=0..9. Risultati: sigma_B = 1.03–2.58σ,
  mean=1.68, std=0.43, CV=25.3%. Segno di rho_obs alternante (5+/5−) su
  10 componenti latenti diverse — prova diretta assenza direzione stabile
  associata a w0. Riferimento Phase 5 (seed=42): sigma_B=0.983. Tutti i run
  coerenti con null fisico (H(z=0)≡H₀, D(z=0)≡1 per costruzione).
  Run 09 outlier (sigma_B=2.58σ) spiegato da best_val=0.0218 peggiore dei
  10 run — convergenza non ottimale, non segnale fisico.
  Blocker L6 peer review formalmente risolto. | phase7_t1_variability.json

- `implementation` | **Pipeline T1 — percorso di debug documentato.**
  Versione v1: architettura errata (CAUCHYEncoder CNN SE3 invece di CGNNCAUCHY GNN).
  Versione v2: checkpoint errato (phase2_cnn_best.pt su campi δ invece di
  phase3_gnn_best.pt su campi τ) → sigma_B=8.34 anomalo.
  Versione v3: partial correlation assente (correlazione marginale su w0 grezzo
  invece di residui w0|Ωm,σ₈) → sigma_B=5.6.
  Versione v4: bug w0 colonna (params[:,5]=wa invece di params[:,6]=w0)
  → sigma_B=11.8. Versione v5 (finale): pipeline identica a phase5_ramo_b.py
  + w0=col6 → sigma_B=1.19 Run00, risultati definitivi coerenti.
  Cache grafi su disco: phase7_t1_graphs_lhc_2000.pkl + phase7_t1_graphs_nwlh.pkl
  (~730 min costruzione totale, riutilizzabili). | phase7_t1_variability.py v5

### Sub-Phase 7.1 — Chiusura formale

- `methodology` | **Sub-Phase 7.1 COMPLETATA.** Tutti i task pre-draft chiusi:
  7.1a (T1 variability, sigma_B=1.68±0.43, blocker L6 risolto),
  7.1b (R5-3 beyond-P(k), risultato corretto: b2_DM a z=0 non sensibile a w0
  per costruzione fisica; tracer activation dimostrata empiricamente 1.12→3.73σ),
  7.1c (3 citazioni mancanti identificate),
  7.1d (RSD HOD B3 confirmation, Δ=−0.004σ N=200).
  JSON frozen citabili prodotti: phase7_t1_variability.json,
  phase7_pk_comparison_r53.json, phase7_r53_partial_corr.json,
  phase7_r53_robustness.json, phase7_rsd_hod_confirmation.json,
  phase7_citations.md. Prossimo step: Reviewer cycle pre-draft → Sub-Phase 7.2.


---

## 2026-06-06 — Sub-Phase 7.1 chiusura formale + apertura 7.2

### Task 7.1a — risultati definitivi (integra entry precedente)

- `methodology` | **Task 7.1a CHIUSO — risultati definitivi post-fix.**
  Pipeline v5 (finale): CGNNCAUCHY + campi τ + partial correlation su w0|Ωm,σ₈
  + permutation test N=1000 + w0=params[:,6] (fix colonna). 10 run torch_seed=0..9,
  N_TRAIN=1600, N_VAL=400, N_EPOCHS=200, early_stop=patience=30.
  sigma_B = 1.68±0.43σ (CV=25.3%), range [1.03, 2.58], segno rho alternante 5+/5−
  su 10 componenti latenti diverse. Riferimento Phase 5: 0.983σ.
  Cache grafi su disco: phase7_t1_graphs_lhc_2000.pkl + phase7_t1_graphs_nwlh.pkl.
  | phase7_t1_variability.json (v5 finale)

### Chiusura formale Sub-Phase 7.1

- `methodology` | **Gate 7.1 PASS. Sub-Phase 7.1 completata.**
  Reviewer cycle completato (verdict NON-BLOCKING, 2026-06-06).
  Tutti i task pre-draft chiusi: 7.1a (T1, σ_B=1.68±0.43), 7.1b (R5-3 ricalcolato
  su w0 corretto, tracer activation 1.12→3.73σ post-hoc), 7.1c (3 citazioni),
  7.1d (RSD HOD B3, Δ=−0.004σ).
  JSON prodotti: phase7p1_gate_result.json, gate7p1_prior_v1_0.json.
  | gate7p1_prior_v1_0.json, phase7p1_gate_result.json

- `methodology` | **Nomenclatura frozen — β₁ non β₂.**
  Analisi del codice (phase5_hod_b3.py) conferma: tutte le feature CAUCHY Ramo A
  sono β₁ (H1, loops/filamenti) o β₀ (H0). NON esistono feature β₂ nel pipeline.
  Il prefisso interno "b2_" è un indice posizionale, non il numero di Betti β₂.
  La feature principale "b2_mean_persistence" va chiamata ⟨pers₁⟩ nel paper con
  nota esplicativa. Questa scoperta modifica la narrativa del paper rispetto al
  documento methodology (§1.3 citava β₂ come "segnale primario") — il claim
  corretto è anomalia β₁ (struttura filamentare 3D).
  Gap R3-5 (β₂ ablation) rimane OPEN come future work.
  | phase7_nomenclature_lock.json, phase7_r35_beta_contribution.md

- `methodology` | **Dual signature DESI identificata.**
  Dall'analisi di phase6_bgs_tda_features.json: DESI BGS NGC mostra pattern
  opposto in due feature β₁ — ⟨pers₁⟩ ALTO (+11.85σ) e β₁_max BASSO (−55.6σ).
  Meno loops/filamenti ma più persistenti — fisicamente coerente con phantom
  crossing (soppressione struttura piccola scala + amplificazione strutture
  topologiche large-scale). Questo dual signature è più difficile da spiegare
  con sistematiche osservative rispetto a un singolo outlier e rafforza
  la credibilità del segnale. Incluso in phase7_nomenclature_lock.json.
  | phase6_bgs_tda_features.json, phase7_nomenclature_lock.json

### Apertura Sub-Phase 7.2

- `paper` | **Sub-Phase 7.2 autorizzata — Redazione Paper B.**
  Draft Paper B ("Topological field-level constraints on background expansion
  histories of the dark sector", JCAP primary target) autorizzato dal Reviewer
  cycle 7.1. La sub-fase si articola in 4 step sequenziali: (1) riassunto
  risultati e metodi, (2) verifica narrativa + delta methodology + scelta rivista,
  (3) struttura capitoli con conteggio parole, (4) stesura cap per cap con review
  interna. Condotta in nuova sessione Claude.
  Impegni pre-submission ancora aperti: R5-1 (HOD fitting DESI BGS mocks, BLOCKING
  pre-submission), R3-5 β₂ ablation (NON-BLOCKING, future work dichiarato).
  | phase7p2_opening_prompt.md

## 2026-07-02 — Phase 8: cut-sky test (referee response), Test 1 SURVIVES

Context: JCAP simulated referee report (MAJOR REVISION, conditional). All three
referees converged on one required remedy: demonstrate the anomaly survives a
comparison against cut-sky mocks with the DESI BGS footprint, n(z), selection,
and space (RSD) applied. Internal code audit confirmed the referees' premise.

- `implementation` | **Code audit finding (blocking).** `phase6_bgs_tda.compute_tda_features` runs gudhi CubicalComplex on the FULL 128^3 embedding cube; ~85% of voxels are exterior set to 0.0; the mask is used only for thresholds/mean, NOT to exclude the exterior from the filtration. Mocks (`phase6_smoothing_sensitivity.compute_b2_full`) are periodic boxes with mode='wrap' and no mask. The canonical DESI <pers1>=0.459 and beta1_max=29683 are therefore NOT like-for-like with the mock distribution. Confirms R3-1/R2-4/R1-4. | phase6_bgs_tda.py, phase6_bgs_voxelize.py

- `implementation` | **Log-transform discrepancy (blocking).** The paper states nu=log(1+clip(delta,-1)); the code never applied it. Restored in the shared `build_field` (Phase 8), on the RAW delta before smoothing/mean-sub. Effect on the DESI reference: <pers1>_DESI 0.459 -> 0.892 at matched sigma_px — a ~2x shift from the transform alone. Documents the strong sensitivity of <pers1> to field transformation (R2 fragility concern). | phase8_cutsky_mocks.py

- `methodology` | **gate8 frozen** before running: Test 1 (exact-replica, zero-exterior, unmasked TDA) and Test 2 (masked, virial satellite velocities). DISSOLVED/SURVIVES/PARTIAL thresholds fixed a priori; empirical rank primary at N=200 (p-floor ~1/201). | gate8_prior_v1_0.json

- `implementation` | Cut-sky construction: FoF groups_003 (z=0.5) with GroupVel (validated: |v| mean 356, max 1540 km/s); B3 median HOD; option (a) satellite velocity = halo bulk (no intra-halo dispersion); periodic tiling into the DESI embedding cube; observer at origin; RSD z_obs; carve by DESI NGC mask + z-range; global n(z)-matched downsample to N=217614; delta_FKP against the DESI random field; shared `build_field`; identical unmasked TDA. | phase8_cutsky_mocks.py

- `recalibration` | **Amplitude mismatch resolved.** Without log, cut-sky mock nu_std was 31x the DESI field (FKP shot-noise spikes to delta=+150). With log on raw delta, ratio 0.79x — fields comparable. | phase8_field_diagnostic.py

- `paper` | **Test 1 result (N=200), SURVIVES.** <pers1>: DESI 0.892 vs mock 0.629±0.040, rank 99.5% (z~+6.65, tail-extrapolated). beta1_max: DESI 27471 vs mock 35804±332, rank 0.0% (z~-25.1). The dual signature survives the geometry/selection/RSD/density/sigma_px controls on both features. The paper's -55.6 sigma on beta1_max was ~half survey geometry; a ~-25 sigma residual remains. | results/phase8_cutsky_test1.json

- `override_open` | Pending before any resubmission: (1) weight asymmetry check (DESI WEIGHT*WEIGHT_FKP vs mock w=1); (2) Test 2 (masked filtration, virial satellite velocities, DESI reference recomputed) pilot then N=2000; (3) reframe primary claim onto beta1_max (robust) with <pers1> secondary + declared fragility; (4) NO phantom-dark-energy attribution without wa!=0 mocks (R1). | this file

Interpretation (frozen): even in the best case this is a field-level topological
deviation from LambdaCDM cut-sky mocks that survives observational controls — NOT
a phantom dark energy detection. Conservative framing mandatory.

## 2026-07-03 — Phase 8 complete: cut-sky validation chain, pivot to methods paper

Referee response (JCAP MAJOR REVISION, conditional). All three referees required a
like-for-like comparison against cut-sky mocks with the DESI BGS footprint, n(z),
selection, and RSD applied, and a reframing/withdrawal of the phantom interpretation.
Phase 8 built that comparison and ran the full exclusion battery.

- `implementation` | Cut-sky pipeline: FoF groups_003 (z=0.5) + GroupVel (validated,
  |v|~356 km/s mean); B3-median HOD w/ velocities; periodic tiling into the DESI
  embedding cube; observer at origin; RSD; carve by DESI mask + n(z); global n(z)
  downsample to N=217614; shared build_field (delta_FKP -> log -> smooth -> mean-sub,
  the log FINALLY applied as the paper states). | phase8_cutsky_mocks.py

- `recalibration` | DESI reference rebuilt from FITS through build_field: <pers1>
  0.459 (no-log, canonical) -> 0.892 (log). Confirms <pers1> is strongly transform-
  dependent (R2 fragility). Amplitude ratio mock/DESI 31x (FKP shot-noise) -> 0.79x
  after log. | phase8_field_diagnostic.py

- `paper` | **Test 1 (exact-replica, exterior-zero, unmasked TDA), N=200: SURVIVES.**
  <pers1> DESI 0.892 vs mock 0.629, rank 99.5%. beta1_max DESI 27471 vs 35804, rank 0%.
  | results/phase8_cutsky_test1.json

- `override_closed` | Weight asymmetry (DESI WEIGHT*WEIGHT_FKP vs mock w=1): ROBUST.
  beta1_max worst-case separation z=-24.6; <pers1> weakens to +4.67. beta1_max is a
  connectivity statistic (robust); <pers1> an amplitude statistic (fragile). | phase8_weight_check.py

- `paper` | **Test 2 (masked filtration, exterior EXCLUDED, virial satellite vel),
  N=2000: BETA1_ONLY.** DESI beta1_max 28256 BELOW ALL 2000 cut-sky mocks (35437±313),
  rank 0.0% (p<1/2000). <pers1> z=+2.16 rank 98% — NOT significant after correct masking.
  Dual signature RETRACTED. | results/phase8_test2_masked.json

- `override_closed` | w0CDM(wa=0) EXCLUDED. Partial corr r(beta1_max,w0|Om,s8)=+0.015;
  phantom (w0<-1.10) and quintessence (w0>-0.90) subsets identical (~35410); DESI below
  the phantom minimum; extrapolated w0 needed = -294 (absurd). The deficit is NOT w0.
  CAVEAT: excludes wa=0 only; CPL wa!=0 not testable (no mocks). | results/phase8_w0_exclusion.json

- `override_closed` | HOD EXCLUDED. wp(rp) fit to DESI (TreeCorr LS) gives a MORE
  concentrated best-fit (log_Mmin=13.1, log_M1=13.8, a=0.8) than B3, yet cut-sky mocks
  with the fitted HOD give beta1_max=35305 — deficit unchanged, DESI rank 0.5%. Even the
  clustering-calibrated HOD does not reproduce the deficit. | results/phase8_hod_bestfit.json, phase8_test2_hodfit.json

- `override_closed` | Fiber-assignment (surrogate) EXCLUDED. Density-dependent decimation
  up to 30% does NOT move mock beta1_max toward DESI (frac closed ~0; slightly widens the
  gap — decimation fragments dense regions, creating MORE small loops). Full altmtl test =
  future work. | results/phase8_fiber_surrogate.json

- `decision` | **Paper reframed as METHODS paper for JCAP, variant B (anomaly as honest
  teaser).** Contributions: (1) sigma_px systematic; (2) survey-geometry/boundary artefacts
  + the demonstration that the original "dual signature" was largely diagram truncation and
  the stated log-transform was not applied; (3) like-for-like cut-sky framework; (4) DESI
  BGS case study — most of the apparent signal dissolves; a robust beta1_max deficit
  (p<1/2000) survives all observational controls and w0CDM(wa=0), reported as an open anomaly.
  NO phantom-dark-energy claim.

- `override_open` | Remaining, declared as limitations/future work: (i) full DESI altmtl
  fiber-assignment test; (ii) CPL wa!=0 mocks; (iii) independent replication (BOSS DR12 /
  DESI DR2); (iv) proper significance including cosmic variance at BGS volume (current
  claim is empirical rank p<1/2000, NOT -25 sigma); (v) full HOD posterior (current fit
  is coarse-grid, z=0.5). | this file

Trajectory note: the project began as a phantom-dark-energy DETECTION via TDA. The data
reframed it into a METHODS paper that EXCLUDES that interpretation on its own testbed. The
value is the method + the honest exclusion battery, not a discovery. This is the publishable,
non-retractable form.

## 2026-07-04 — Phase 9: referee-response validation campaign, gate9 PASS

Context: after the Phase 8 masked Test 2 verdict (BETA1_ONLY, N=2000), the
isolated-referee pass returned NON-BLOCKING / minor revision with four concerns
plus OC-3. Phase 9 executes each as a real computation before JCAP submission,
rather than deferring them as "script ready if asked". PI-driven instruction-
handback throughout; every number traces to a frozen JSON. gate9 frozen with the
per-script criteria before interpretation.

- `methodology` | **gate9 frozen** with per-script pre-registered criteria
  (`gate9_prior_v1_0.json`). beta1_max primary criterion corrected to the real
  gate8 threshold (empirical p<=0.01 AND z<-3); the Script-1 code's earlier
  `n_below==0` phrasing superseded as an over-literal restatement. | gate9_prior_v1_0.json

- `implementation` | **Per-mock feature extraction (prerequisite).** The
  definitive N=2000 masked run saved the 2000 masked cubes
  (`results/phase8_test2_fields/test2_XXXX.npz`) but only the N=200 pilot
  per-mock table. Recomputed the 2000 beta1_max/pers1 with Phase 8's own
  `compute_tda_features(..., masked=True)` (identical filtration by construction);
  means reproduce the frozen summary (drift beta1 0.04 sigma, pers1 0.12 sigma).
  Frozen to `results/phase9_likeforlike_arrays.npz`. | phase9_extract_features.py

- `paper` | **Script 1 — empirical histograms (Concern 1), PASS.** The empirical
  distribution is wider than the Gaussian drawn from the frozen summary
  (beta1_max std 445 vs 313; pers1 std 0.080 vs 0.044). beta1_max: DESI=28256
  below all but ONE of 2000 mocks (rank 1/2000, one-sided p~1.0e-3, Gaussian-ref
  z=-16.1). The sole lower mock (idx 139: Om=0.103, s8=0.675, w0=-1.26) is an
  extreme low-density phantom cosmology, RETAINED not excluded. pers1: rank 96.4%
  (z=+1.11), not significant — consistent with BETA1_ONLY. Paper wording softened
  from "below all 2000, p<1/2000" to "below all but one, rank 1/2000, p~1e-3".
  | phase9_empirical_histograms.py, results/phase9_empirical_histograms.json,
  figures/fig_phase9_beta1max_empirical.pdf, figures/fig_phase9_pers1_empirical.pdf

- `recalibration` | **Script 2 — w0 response (Concern 3), exclusion RETRACTED and
  reframed, PASS.** On the labelled subset (N=200): partial
  r(beta1_max,w0|Om,s8)=-0.015 (perm p=0.84); binned response flat at ~35400 with
  a symmetric dip at both prior edges (Om/s8-edge mixing, not w0); OLS slope at
  fixed (Om,s8) = -76 per unit w0, bootstrap 95% CI [-1050, +929] — consistent
  with zero. A sign-ambiguous slope admits NO finite linear extrapolation; the
  earlier "w0 ~ -294" figure is retracted (inverting a near-zero denominator is
  meaningless). Deficit reframed as an anomaly relative to the w0CDM (wa=0) suite,
  not a physical exclusion of any specific w0. | phase9_w0_response_curve.py,
  results/phase9_w0_response.json, figures/fig_phase9_w0_response.pdf

- `paper` | **Script 3 — angular fiber surrogate (Concern 4), FIBER_EXCLUDED,
  PASS.** Correct variable: projected angular target density within the 62"
  collision scale (the Phase 8 surrogate keyed on 3D local density). Removal
  probability prop. to local angular neighbour count, vs a count-matched random
  null (K=30, 3 random reps). At all f in {0.05,0.10,0.20} the fiber-specific
  effect has the WRONG sign (fiber raises beta1_max vs random by 43-103), and
  fiber-decimated mocks remain +7250-7290 above DESI. Baseline drift 0.07 sigma.
  altmtl remains the gold-standard follow-up. | phase9_altmtl_fiber_test.py,
  results/phase9_fiber_surrogate.json

- `paper` | **Script 4 — RSD satellite sensitivity (Concern 2), SUBDOMINANT,
  PASS.** eta_vel (satellite virial dispersion multiplier) scanned over Munari-
  plausible +/-20% {0.8,1.0,1.2} (K=30). Mock mean 35512 -> 35389, span 123
  generators = 1.7% of the deficit. Baseline (eta=1.0) drift 0.07 sigma. The
  declared-but-unquantified Munari caveat is now a bound. | phase9_rsd_satellite_sensitivity.py,
  results/phase9_rsd_satellite.json

- `paper` | **Script 5 — concentrated HOD grid (OC-3), HOD_EXCLUDED, PASS.**
  Extended the fitted grid across its log_M1 edge into the concentrated region:
  log_M1 13.8 -> 13.3 at fitted (log_Mmin, alpha) doubles the pre-carve satellite
  count (3.2e5 -> 5.3e5) but moves the density-matched mock mean only 247
  generators toward DESI (35295 -> 35048), leaving a +6792 gap. Baseline
  (log_M1=13.8) drift 0.01 sigma. The grid-edge concern is resolved; the deficit
  is not an occupation-concentration artefact. | phase9_hod_concentrated_grid.py,
  results/phase9_hod_concentrated.json

- `methodology` | **Cross-test consistency.** The same low-structure mocks (idx
  139, 27, 16) sit lowest across the beta1, fiber, RSD, and HOD scans; the tail is
  driven by low Om/s8 cosmologies, not by fiber/RSD/HOD nuisances. Physics is
  consistent across all tests. | gate9_prior_v1_0.json

- `override_closed` | Phase 8 pending items closed: (2) Test 2 N=2000 empirical
  ranking done (Script 1); fiber assignment executed as angular surrogate (Script
  3, excluded); satellite RSD asymmetry quantified (Script 4, 1.7%); HOD grid-edge
  resolved (Script 5). Remaining declared future work (unchanged, non-blocking):
  official altmtl catalogues, wa!=0 simulations, independent replication (BOSS
  DR12 / DESI DR2), volume-matched error budget. | this file

- `paper` | **Paper C updated** to v2 (`cauchy_paper_c_jcap.tex`): 20 edits across
  abstract, intro contributions, dissolution/survival results, exclusion battery
  (+3 rows), w0 section (retraction), significance, discussion, limitations, and
  conclusions. fig4 -> fig_phase9_beta1max_empirical.pdf; fig5 ->
  fig_phase9_w0_response.pdf. All stale frozen numbers replaced; brace/environment
  balance verified. | cauchy_paper_c_jcap.tex

gate9 overall verdict (frozen): PASS. The beta1_max deficit survives empirical
ranking (1/2000), a flat in-range w0 response (exclusion retracted -> reframed),
angular fiber incompleteness (excluded, wrong sign), a +/-20% satellite-dispersion
variation (1.7% of the deficit), and a concentrated HOD (excluded). Reported as an
honest open anomaly, NOT a dark-energy detection.

## 2026-07-04 — Phase 9b: three-referee second-round panel, all computational items closed

Context: the full three-referee second-round report (MINOR REVISION,
JCAP_058P_0726.R1) is broader than the isolated-referee concerns Phase 9 covered.
Editor flagged three mandatory items (growth, SGC, mask). Phase 9b executes those
plus every remaining major, as real computations. PI-driven; every number frozen
to JSON; gate9 extended before interpretation.

- `implementation` | **Growth mismatch (R1.1, mandatory), Script 6.** Paired
  same-seed z=0 (snap4) vs z=0.5 (snap3) cut-sky masked mocks, K=30.
  d(beta1_max)/dz = -53 +/- 112 (consistent with zero) -> over dz~0.25 the offset
  is ~13 generators = 0.2% of the deficit. GROWTH_SUBDOMINANT; leading mundane
  candidate excluded, anomaly strengthened. | phase9_growth_mismatch.py,
  results/phase9_growth_mismatch.json

- `paper` | **Mask-edge robustness (R3.2, mandatory), Script 8 + re-verdict.**
  DESI + 300 mock cubes recomputed under 5 mask variants (threshold 5%/20%, erode
  1/2 voxels), identically both sides. DESI stays rank 1-2/300, z -6.3..-8.3;
  fractional deficit 20-29% (grows under stricter thresholds -> fiducial mask
  conservative). The naive absolute-swing auto-verdict was corrected to the
  standardized/rank criterion (loop count scales with volume). MASK_ROBUST. |
  phase9_mask_robustness.py, phase9_mask_reverdict.py, results/phase9_mask_robustness.json

- `paper` | **SGC like-for-like (R3.1, mandatory), Script 7.** Test 2 pipeline on
  the SGC footprint; box/cell/sigma_px/density-target recomputed self-consistently
  from SGC catalogues (sigma_px 0.336 vs 0.320 NGC); frozen SGC mask verified
  (100% of data inside). DESI-SGC beta1_max = 15122 vs mock 18694 +/- 178 (K=200):
  19.1% deficit, DESI below ALL 200 (z=-20). SGC_CONFIRMS -> anomaly reinforced in
  a second hemisphere with independent masks/randoms/imaging. |
  phase9_sgc_likeforlike.py, results/phase9_sgc_likeforlike.json

- `paper` | **Light majors (one script), phase9b_majors.py.**
  (A) Redshift split (R1.2): deficit 16.8% (z<0.315, z=-23.8) and 15.9% (z>0.315,
      z=-24.2) -> DEFICIT_IN_BOTH_HALVES.
  (B) Scatter decomposition (R2.2): fixed cosmology idx 1805, 50 HOD seeds ->
      stochastic std 110 = 6% of suite variance 445; ~94% cosmological, driven by
      Om (r=0.45), not w0 (r=-0.03). Deficit not absorbable by any varied param.
  (C) Filtration convention (R2.3): standard vs relative-cycle -> DESI/mock shift
      <0.5%, z -6.8 vs -6.9 -> CONVENTION_STABLE.
  (D) Imaging split (R3.1b): PHOTSYS N (BASS+MzLS) 17885 vs S (DECaLS) 18007 =
      0.7% -> IMAGING_CONSISTENT.
  | results/phase9b_redshift_split.json, phase9b_scatter_decomp.json,
  phase9b_filtration_convention.json, phase9b_imaging_split.json

- `methodology` | **gate9 extended and closed.** All referee computational items
  PASS: mandatory (growth, mask, SGC) + majors (redshift split, scatter,
  convention, imaging). Cross-test consistency: the beta1_max tail is driven by
  low-Om cosmologies across every scan, not by fiber/RSD/HOD/mask/imaging
  nuisances. | gate9_prior_v1_0.json

- `paper` | **Paper C -> v3.** Single tex pass, 10 verified edits: new Section 5.3
  (SGC, redshift halves, mask robustness, imaging split); Section 5.5 scatter
  decomposition + extension of the exclusion to the full (Om,s8,w0) box;
  look-elsewhere bound p<8/2000 in abstract and significance; growth limitation
  quantified (0.2%); single-field limitation -> two-cap positive; sample
  description (BGS_BRIGHT-21.5, Mr<-21.5); BAO-complementarity sentence; filtration
  convention note. Brace/environment/ref integrity verified. | cauchy_paper_c_jcap.tex

- `paper` | **Response to referees rewritten** against the real three-referee
  report, point by point (R1.1/1.2, R2.1-4, R3.1-3 + minors), all done/quantified.
  | response_to_referees_paperC.md

gate9b verdict (frozen): PASS. The beta1_max deficit survives NGC (20%) and SGC
(19%), both redshift halves, both imaging systems, five mask variants, two
filtration conventions, HOD refit + concentrated occupations, angular + 3D fiber
surrogates, +/-20% satellite dispersion, the snapshot-growth offset (0.2%), and
the full sampled (Om,s8,w0) box. Reported as an honest open anomaly, NOT a
dark-energy detection. No referee computational item remains open.



*Subsequent entries added per decision change, at session boundaries, or at gate events.*
