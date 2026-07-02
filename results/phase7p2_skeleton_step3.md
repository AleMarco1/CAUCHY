# CAUCHY — Skeleton Paper B
## Sub-Phase 7.2 — Step 3
## Target: JCAP | Prodotto: 2026-06-07

---

## CALIBRAZIONE LUNGHEZZA

**Riferimento JCAP:** nessun limite di pagine esplicito per articoli di ricerca
(Research Articles). La lunghezza tipica per paper di cosmologia osservativa con
metodi computazionali è 25–35 pagine LaTeX (2-colonne), corrispondenti a ~8,000–12,000
parole escluse figure/tabelle/appendici. Precedenti diretti:
- Yip & Biagetti 2024 (JCAP 09 034): ~35 pagine, ~10,000 parole
- Prat et al. 2025 (MNRAS 545): ~30 pagine, ~12,000 parole

**Target Paper B:** ~9,500 parole corpo principale + ~1,500 parole appendici.
Totale stimato: **~11,000 parole** (esclusi titolo, abstract, riferimenti, tabelle,
didascalie figure).

---

## STRUTTURA COMPLETA

### Titolo
"Cosmology with Persistent Homology: a topological anomaly in the DESI BGS galaxy field"

### Autori
[Alessandro + eventuali collaboratori — da definire dal PI]

### Abstract
~250 parole. **Da redigere dopo la stesura dei capitoli principali.**
Elementi obbligatori: anomalia +3.09σ, σ_px matching, RSD robustezza, Ramo B null,
tracer activation, limitazione wₐ=0, implicazione metodologica σ_px.

---

## SEZIONI PRINCIPALI

---

### 1. Introduction
**Target: ~1,200 parole | ~4 pagine**

Struttura interna:

**1.1 Motivazione: evidenze per dark energy dinamica (~300 parole)**
- Karim et al. 2025 (DESI DR2): w₀ < −1 a 2.8–4.2σ, best-fit w₀=−0.838
- Tensione con ΛCDM — cosa può aggiungere una probe topologica?
- Phantom crossing come target specifico: w(z) attraversa −1

**1.2 Omologia persistente in cosmologia (~350 parole)**
- TDA come statistica non-gaussiana: β₀, β₁, β₂
- Precedenti: Yip & Biagetti 2024 (Fisher su aloni DM), Prat et al. 2025 (2D
  lensing), Calles et al. 2025 (inference ML) — posizionamento di CAUCHY
- Gap: nessuna analisi PH 3D su campo galattico per w₀ phantom crossing
- Distinzione da Prat et al. 2025: 3D vs 2D proiettato, w₀ vs S₈, dual signature
  inaccessibile alla proiezione (argomento forte D1)

**1.3 Questo lavoro (~350 parole)**
- CAUCHY: pipeline duale Ramo A (TDA su δ(x)) + Ramo B (CNN τ(x) + GNN j*)
- Dataset: DESI BGS DR1 NGC + Quijote nwLH (2000 cosmologie, w₀∈[−1.30,−0.70])
- Scoperta metodologica: dipendenza σ_px — Confronto B come contributo originale
- Struttura del paper (roadmap)

**Citazioni obbligatorie in §1:**
Karim et al. 2025, Yip & Biagetti 2024, Prat et al. 2025, Calles et al. 2025,
Hahn et al. 2023 (SimBIG), Leclercq 2025, Abedi et al. 2025

---

### 2. Data
**Target: ~600 parole | ~2 pagine**

**2.1 Osservazioni: DESI BGS DR1 (~300 parole)**
- Descrizione survey DESI BGS, footprint NGC
- N = 217,614 galassie, z∈[0.1,0.4], z_eff~0.2
- Procedura voxelizzazione: griglia 128³, box ~1997 Mpc/h, cell_size = 15.6 Mpc/h
- Campo δ(x): CIC weighting, mean subtraction
- Geometria griglia: σ_px(R=5)=0.321, σ_px(R=10)=0.641
- Limitazione D5a: DR1 usato (DR2 non accessibile)
- Fonte: `phase6_gate_result.json`

**2.2 Simulazioni: Quijote nwLH (~200 parole)**
- Suite nwLH: 2000 cosmologie, w₀∈[−1.30,−0.70], altri parametri fiduciali
- Griglia 128³, box 1000 Mpc/h, cell_size = 7.8125 Mpc/h, σ_px(R=5)=0.640
- HOD: modello Zheng 2007, log_Mmin=12.5, n_gal~9×10⁵ (Gpc/h)⁻³
- Redshift mock: z=0.5 come riferimento principale
- Fonte: `phase0_data_manifest.json`, `phase5_hod_b3_manifest.json`
- Citazioni: Villaescusa-Navarro et al. 2020 (Quijote), Smith & Grove et al. 2024 (HOD)

**2.3 Limitazione strutturale wₐ=0 (~100 parole)**
- Mock hanno wₐ=0 fisso — testo D5b
- Best-fit DESI DR2+CMB+DESY5: wₐ=−1.079 non testabile
- Claim ristretto a w₀CDM con wₐ=0

---

### 3. Methods
**Target: ~2,200 parole | ~7 pagine**

**3.1 Pipeline TDA — Ramo A (~600 parole)**
- Log-transform: ν = log(1+δ), convenzione log1p(clip(δ,−1))
- gudhi CubicalComplex: superlevel filtration su ν
- Convenzione birth/death: birth=−diag[:,0], death=−diag[:,1]
- N_thresh=100 livelli di soglia
- 8 feature estratte: 7 da H₁ (β₁), 1 da H₀ (β₀) — tabella nomenclatura
- Dichiarazione esplicita: NO H₂ (β₂) features — testo D1 Methods
- Footnote obbligatoria ⟨pers₁⟩ = b2_mean_persistence (indice posizionale)
- Feature primaria: ⟨pers₁⟩ — mean persistence H₁ generators
- Citazioni: Cohen-Steiner et al. 2007, Neumann et al. 2026

**3.2 Scoperta σ_px e Confronto B (~500 parole)**
- Paragrafo σ_px — testo D4 Methods §1
- DESI vs mock: cell_size diverso → σ_px diverso a parità di R fisico
- Quantificazione: +8.42σ tra σ_px=0.216 e σ_px=0.640 su N=200 mock
- Motivazione Confronto B — testo D4 Methods §2
- Tabella tre confronti A/B/C — tabella D4 Results
- Valore primario: Confronto B, +3.09σ

**3.3 HOD e campionamento galattico (~250 parole)**
- HOD Zheng 2007: log_Mmin=12.5 calibrato su DESI BGS r<19.5 (Phase 5)
- Differenza log_Mmin=12.5 vs best-fit AbacusSummit 13.08 — dichiarata
- HOD fitting completo (R5-1) come impegno pre-submission
- Citazioni: Smith & Grove et al. 2024, Zheng et al. 2007

**3.4 Robustezza RSD (~250 parole)**
- Test Kaiser DM (N=200 nwLH): Δ=+0.034σ — testo e fonte
- Test Kaiser+FoG HOD B3 (N=200): Δ=−0.004σ — testo e fonte
- Caveat: velocità satelliti = velocità alone (lower bound su RSD)
- Citazioni: Abedi et al. 2025, Kaiser 1987

**3.5 Pipeline Ramo B CNN+GNN (~350 parole)**
- Architettura Ramo B — testo D2 Methods
- CNN SE(3)-equivariante: campo τ(x), checkpoint phase3_gnn_best.pt (epoch 171)
- GNN CGNN: embedding j* 32-dimensionale
- Partial correlation r(j*, w₀|Ωm,σ₈), permutation test N=1000
- Citazioni: e3nn (Geiger & Smidt 2022), Calles et al. 2025

**3.6 Confronto P(k) vs TDA (~250 parole)**
- Descrizione confronto — testo D3 Methods
- Ridge e MLP su P(k) estratto con Pylians3
- Confronto A (clean DM) + Confronto B (post-hoc HOD, tracer asimmetrico dichiarato)

---

### 4. Results
**Target: ~2,000 parole | ~6 pagine**

**4.1 Anomalia topologica principale (~450 parole)**
- Tabella tre confronti A/B/C — tabella D4
- Valore primario: ⟨pers₁⟩(DESI NGC)=0.379, mock mean=0.292±0.028, z=+3.09σ
- Convergenza Phase 5: +3.08σ (configurazione indipendente)
- NGC vs SGC: concordanza segnale (sistematica S2 BORDERLINE dichiarata)
- Numeri: tutti da `phase6_gate_result.json`, `phase6_scenario2_final.json`

**4.2 Dual signature e interpretazione fisica (~400 parole)**
- ⟨pers₁⟩ NGC: +11.85σ raw (z=0 mock), +5.97σ (Confronto A z=0.5 mock)
- β₁_max NGC: −55.6σ — DESI ha ~5× meno loop al picco (29,683 vs mock 133,786)
- Pattern anti-correlato: {⟨pers₁⟩ HIGH, β₁_max LOW}
- Interpretazione phantom crossing: soppressione loop transitori + amplificazione
  strutture topologiche large-scale persistenti
- Dual signature più difficile da spiegare con sistematiche rispetto a singolo outlier
- Fonte: `phase6_bgs_tda_features.json`, `phase7_nomenclature_lock.json`

**4.3 Robustezza RSD (~250 parole)**
- Risultati Kaiser DM e Kaiser+FoG HOD — con numeri frozen
- Tabella RSD: Δ Kaiser=+0.034σ, Δ FoG HOD=−0.004σ
- Verdetto: RSD sub-σ su entrambi i test
- Caveat lower bound dichiarato
- Fonte: `phase7_rsd_test.json`, `phase7_rsd_hod_confirmation.json`

**4.4 Ramo B: null fisicamente atteso (~350 parole)**
- Sezione Results Ramo B — testo D2 Results
- σ_B=1.68±0.43σ, CV=25%, segno alternante 5+/5−
- Null fisico: H(z=0)≡H₀, D(z=0)≡1
- Rafforza Ramo A: due pipeline indipendenti, nessun artefatto condiviso
- Fonte: `phase7_t1_variability.json`

**4.5 Confronto P(k) vs TDA (~350 parole)**
- Tabella confronto — tabella D3
- Confronto A clean: P(k) 2.26σ marginale, TDA 0.095σ marginale
- Confronto B post-hoc†: TDA HOD 3.73σ parziale vs DM 1.12σ parziale
- Tracer activation ×3.33 — dichiarazione post-hoc esplicita
- Fonte: `phase7_pk_comparison_r53.json`, `phase7_r53_partial_corr.json`

**4.6 Sistematiche (~200 parole)**
- S1 (redshift z=0 vs z=0.5): 0.57σ < 1σ threshold — NON_DOMINANT
- S2 (NGC vs SGC): Δ=1.15σ — BORDERLINE, test varianza cosmica P=41.5%
- S3 (σ_px): DOMINANT — risolto per costruzione da Confronto B
- Fonte: `phase6_systematics_final.json`

---

### 5. Discussion
**Target: ~2,000 parole | ~6 pagine**

**5.1 Interpretazione fisica del segnale (~400 parole)**
- Dual signature in contesto phantom crossing w₀ < −1
- Confronto con previsioni teoriche qualitative: accelerazione espansiva →
  soppressione struttura piccola scala → β₁_max basso, ⟨pers₁⟩ alto
- Confronto con triple baseline CPL DESI DR2 (w₀CDM wₐ=0): z-score ~5.97σ
  invariante tra ΛCDM, DESI+CMB, DESI+CMB+DESY5 — ⟨pers₁⟩ insensibile a
  variazioni w₀ a wₐ=0 (interpretazione: segnale non riproducibile variando
  solo w₀ nei mock correnti)
- Implicazione wₐ≠0: motivazione per simulazioni future

**5.2 Tracer activation come meccanismo fisico (~300 parole)**
- Testo D3 Discussion tracer activation
- Meccanismo HOD: aloni massicci, funzione di massa, storia di crescita integrata
- Connessione con il segnale DESI: lo stesso meccanismo che attiva TDA su HOD
  spiega perché DESI (campo galattico reale) mostra il segnale mentre i campi DM non lo fanno
- Dichiarazione post-hoc ribadita

**5.3 Ramo B null: sanity check e prospettive (~250 parole)**
- Testo D2 Discussion interpretazione null
- Testo D2 Discussion future work Ramo B (z>0 light cone)

**5.4 Degenerazione IDE (~300 parole)**
- IDE non degenere con phantom CPL per w₀<−1.05: max ΔD/D=0.94%<1%
- Limitazione: solo near-ΛCDM IDE testati (55 coppie convergenti)
- Gavela et al. 2009: doom factor constraint
- Artola et al. 2026, Dai et al. 2026: contesto IDE recente
- Fonte: `phase5bis_gate_result.json`

**5.5 Confronto con la letteratura (~300 parole)**
- Yip & Biagetti 2024: Fisher PH su aloni DM — CAUCHY estende a galassie + w₀ + DESI
- Prat et al. 2025: PH 2D lensing — distinzione 3D vs 2D (argomento D1 richiamato brevemente)
- Hahn et al. 2023 (SimBIG): field-level inference — CAUCHY complementare (TDA vs CNN)
- Spurio Mancini et al. 2024: SBI field-level — confronto approcci
- Abedi et al. 2025: RSD su PH — conferma robustezza RSD di CAUCHY

**5.6 Limitazioni e future work (~450 parole)**
- Testo D5 Discussion limitazioni (quattro punti: i–iv)
- Limitazione strutturale wₐ=0: principale, dichiarata con nota che il segno
  dell'effetto wₐ≠0 su ⟨pers₁⟩ è sconosciuto
- Future work prioritario:
  1. DESI DR2 replication (straightforward)
  2. Simulazioni con wₐ≠0 (richiede nuove N-body)
  3. BOSS DR12 cross-validation (indipendente)
  4. HOD fitting su DESI BGS mocks (R5-1, pre-submission)
  5. β₂ (H2) features — testo D1 Discussion FW
  6. Ramo B su light-cone z>0 — testo D2 Discussion FW
- Implicazioni σ_px per la comunità TDA — testo D4 Discussion
  (rimando a Paper A companion)

---

### 6. Conclusions
**Target: ~500 parole | ~1.5 pagine**

Struttura:
- Sintesi del risultato principale: +3.09σ anomalia ⟨pers₁⟩ DESI BGS NGC vs
  2000 mock w₀CDM (wₐ=0), dual signature fisicamente coerente con w₀<−1
- Robustezza: RSD sub-σ (×2 test), convergenza con stima indipendente +3.08σ,
  concordanza NGC-SGC, non-degenerazione IDE
- Contributo metodologico: σ_px matching come standard per confronti TDA
  cross-survey — Paper A companion
- Ramo B null come sanity check (non fallimento)
- Prospettiva: le limitazioni strutturali (wₐ=0, DR1, HOD R5-1) sono tutte
  indirizzabili con estensioni dirette della pipeline

---

## APPENDICI

### Appendix A — Tabella nomenclatura feature
**Target: ~300 parole + tabella**

Tabella completa 8 feature: nome interno, nome paper, gruppo H, z-score NGC,
z-score SGC, in mock 3σ. Fonte: `phase7_nomenclature_lock.json`.
Spiegazione prefisso "b2_" = indice posizionale.

### Appendix B — Debug path pipeline T1 (Ramo B)
**Target: ~400 parole**

Documentazione trasparente del percorso di debug:
- v1: architettura errata (CNN invece di GNN)
- v2: checkpoint errato → σ_B=8.34
- v3: correlazione marginale invece di parziale → σ_B=5.6
- v4: bug colonna w₀ (col5=wₐ invece di col6=w₀) → σ_B=11.8
- v5: pipeline corretta → σ_B=1.68±0.43
Questo livello di trasparenza è standard in letteratura per pipeline ML
(cfr. Hahn et al. 2023 §Appendix, discussione robustezza CNN).

### Appendix C — Sistematica σ_px: dati completi
**Target: ~300 parole + tabella**

Tabella completa test σ_px su N=200 mock:
σ_px=0.216 (R=1.7), 0.640 (R=5.0), 1.280 (R=10.0) — mean, std, z-score DESI.
Fonte: `phase6_sigma_px_test.json`.
Nota: la caratterizzazione completa è in Paper A.

### Appendix D — Degenerazione IDE: dettagli numerici
**Target: ~300 parole**

N=142 cosmologie testate, N=55 coppie convergenti, max ΔD/D=0.94%.
Equazioni di crescita lineare (Gavela et al. 2009). Fonte: `phase5bis_gate_result.json`.

---

## FIGURE PIANIFICATE

| # | Contenuto | Sezione | Dati |
|---|---|---|---|
| 1 | Mappa DESI BGS NGC voxelizzata + esempio campo δ(x) | §2.1 | `phase6_bgs_voxelize_diagnostics.json` |
| 2 | Curva β₁(ν): DESI NGC vs distribuzione mock (banda 1σ/2σ/3σ) | §4.1 | `phase6_bgs_tda_features.json` |
| 3 | Diagramma di persistenza H₁: DESI NGC vs mock rappresentativo | §4.2 | da generare |
| 4 | Tabella/heatmap feature DESI vs mock: z-score 8 feature, NGC + SGC | §4.1 | `phase6_bgs_tda_features.json` |
| 5 | Distribuzione ⟨pers₁⟩ mock (istogramma N=2000) + valore DESI per confronti A/B/C | §4.1 | `phase6_scenario2_final.json` |
| 6 | RSD test: distribuzione Δ su N=200 run + valore osservato | §4.3 | `phase7_rsd_test.json`, `phase7_rsd_hod_confirmation.json` |
| 7 | Ramo B: distribuzione σ_B su 10 run + segno ρ_obs | §4.4 | `phase7_t1_variability.json` |
| 8 | P(k) vs TDA: scatter plot confronto A + B con errori | §4.5 | `phase7_pk_comparison_r53.json` |

**Nota:** figure 2 e 5 sono le più importanti per la narrativa principale e
devono essere prodotte in alta qualità. Figure 3 richiede script dedicato.

---

## TABELLE PIANIFICATE

| # | Contenuto | Sezione | Fonte |
|---|---|---|---|
| 1 | Tre confronti A/B/C con σ_px e z-score | §3.2 / §4.1 | `phase6_scenario2_final.json` |
| 2 | Feature DESI NGC/SGC vs mock: valori assoluti + z-score | §4.1 | `phase6_bgs_tda_features.json` |
| 3 | P(k) vs TDA: σ marginale e parziale per confronto A e B | §4.5 | `phase7_pk_comparison_r53.json`, `phase7_r53_partial_corr.json` |
| 4 | RSD: Δ Kaiser DM e Kaiser+FoG HOD | §4.3 | `phase7_rsd_test.json`, `phase7_rsd_hod_confirmation.json` |
| A1 | Nomenclatura feature (Appendix A) | App. A | `phase7_nomenclature_lock.json` |

---

## CONTEGGIO PAROLE TARGET

| Sezione | Parole | % del totale |
|---|---|---|
| Abstract | 250 | — |
| §1 Introduction | 1,200 | 12.6% |
| §2 Data | 600 | 6.3% |
| §3 Methods | 2,200 | 23.2% |
| §4 Results | 2,000 | 21.1% |
| §5 Discussion | 2,000 | 21.1% |
| §6 Conclusions | 500 | 5.3% |
| App. A (nomenclatura) | 300 | 3.2% |
| App. B (debug T1) | 400 | 4.2% |
| App. C (σ_px dati) | 300 | 3.2% |
| App. D (IDE dettagli) | 300 | — (spesso non conteggiato) |
| **Totale corpo** | **9,500** | **100%** |
| **Totale con appendici** | **~11,000** | — |

---

## ORDINE DI STESURA (Step 4)

Stesura sequenziale con review interna prima di procedere. Ordine proposto
per minimizzare le dipendenze:

1. **§3 Methods** — base di tutti i risultati; risolve le ambiguità prima di Results
2. **§4 Results** — dipende da §3; produce i testi principali citabili
3. **§2 Data** — breve, dipende da §3 solo per cell_size/σ_px
4. **§5 Discussion** — dipende da §3 + §4
5. **§1 Introduction** — si scrive meglio dopo aver scritto Methods + Results
6. **§6 Conclusions** — dipende da tutto
7. **Appendici** — parallele a §3-4, producibili mentre si scrivono i capitoli
8. **Abstract** — ultimo, dopo tutto il corpo

---

*Step 3 completato. Skeleton approvato dal PI → Step 4 (stesura §3 Methods).*
