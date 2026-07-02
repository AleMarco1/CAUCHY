# CAUCHY — Riassunto Risultati e Metodi per Paper B
## Sub-Phase 7.2 — Step 1
## Prodotto: 2026-06-07

---

## AVVISO DI TRACCIABILITÀ

**Nessun numero in questo documento è "a memoria."**
Ogni cifra numerica riporta la fonte JSON frozen tra parentesi quadre.
Il documento è il reference interno per tutta la stesura del Paper B.

---

## 1. RISULTATO PRINCIPALE

| Quantità | Valore | Fonte frozen |
|---|---|---|
| Anomalia topologica ⟨pers₁⟩ | **+3.09σ** | `phase6_gate_result.json` Confronto B |
| Convergenza indipendente Phase 5 | +3.08σ | `phase5_gate_result.json` |
| Framing | CONSERVATIVO (Confronto B σ_px-matched) | `gate7p1_prior_v1_0.json` |

La feature rilevante è **⟨pers₁⟩** (β₁ mean persistence, H1), chiamata internamente `b2_mean_persistence`. Il prefisso "b2_" è un indice posizionale nel vettore di feature (posizione 5), **non** il numero di Betti β₂. Nota a piè di pagina obbligatoria nel paper. [Fonte: `phase7_nomenclature_lock.json`]

---

## 2. FEATURE DESI BGS vs MOCK ΛCDM (TABELLA COMPLETA)

### 2.1 Feature DESI NGC — z-score vs mock nwLH z=0

| Feature interna | Nome paper | Gruppo H | z-score NGC | z-score SGC | In prior 3σ? |
|---|---|---|---|---|---|
| b1_peak_pos | ν₁_peak | H1/β₁ | −0.19 | −0.29 | ✓ |
| b1_peak_height | β₁_peak | H1/β₁ | −2.25 | −2.75 | ✓ |
| b1_fwhm | Δν₁ | H1/β₁ | +1.36 | +1.38 | ✓ |
| b1_integral | ∫β₁ | H1/β₁ | −2.08 | −2.81 | ✓ |
| **b2_mean_persistence** | **⟨pers₁⟩** | **H1/β₁** | **+11.85** | **+13.58** | **✗** |
| b2_max_count | β₁_max | H1/β₁ | −55.59 | −62.90 | ✗ |
| b2_high_persist | β₁_high | H1/β₁ | −55.59 | −62.90 | ✗ |
| b0_at_mean | β₀(ν̄) | H0/β₀ | −0.85 | −0.88 | ✓ |

Fonte: `phase6_bgs_tda_features.json`, `phase7_r35_beta_contribution.md`

### 2.2 Valori assoluti ⟨pers₁⟩

| Quantità | Valore | Fonte |
|---|---|---|
| DESI NGC ⟨pers₁⟩ | 0.4589 | `phase6_bgs_tda_features.json` |
| DESI SGC ⟨pers₁⟩ | 0.4910 | `phase6_bgs_tda_features.json` |
| Mock nwLH mean (z=0) | 0.2385 | `phase6_bgs_tda_features.json` |
| Mock nwLH std (z=0) | 0.01859 | `phase6_bgs_tda_features.json` |
| Mock z=0.5 HOD mean | 0.2922 | `phase6_systematics_final.json` |
| Mock z=0.5 HOD std | 0.0279 | `phase6_systematics_final.json` |
| N mock nwLH | 2000 | `phase0_data_manifest.json` |
| DESI BGS NGC galassie | 217,614 | `phase6_gate_result.json` |

### 2.3 Tre Confronti (Scenario 2, Confronto B primario)

| Confronto | DESI R | Mock R | σ_px DESI | σ_px mock | z-score | Bias |
|---|---|---|---|---|---|---|
| A (R fisico) | 5 Mpc/h | 5 Mpc/h | 0.321 | 0.640 | +5.97σ | Favorisce DESI |
| **B (σ_px matched)** | **10 Mpc/h** | **5 Mpc/h** | **0.641** | **0.640** | **+3.09σ** | **Neutro** |
| C (R identico 10) | 10 Mpc/h | 10 Mpc/h | 0.641 | 1.280 | +12.65σ | Favorisce DESI |

Valore primario citabile: **+3.09σ** (Confronto B). Framing conservativo obbligatorio.
Fonte: `phase6_gate_result.json`, `phase6_sigma_px_test.json`

---

## 3. SISTEMATICA σ_px (SCOPERTA METODOLOGICA CENTRALE)

| Quantità | Valore | Fonte |
|---|---|---|
| Δz-score per mismatch σ_px | +8.42σ | `phase6_sigma_px_test.json` |
| Verdetto | DOMINANT | `phase6_systematics_final.json` |
| Implicazione | Confronto R fisico senza correzione σ_px è non-valido | `phase6_gate_result.json` |

**Nota paper:** ⟨pers₁⟩ dipende da σ_px = R/cell_size (adimensionale), non da R fisico in Mpc/h. Il Confronto B è il confronto neutro corretto: σ_px(DESI R=10) ≈ σ_px(mock R=5) = 0.640–0.641. Questa dipendenza è una scoperta metodologica inattesa non pianificata nel documento methodology — è il fondamento di Paper A (methodology σ_px) e della robustezza di Paper B.

---

## 4. ROBUSTEZZA RSD

| Test | Risultato | Fonte |
|---|---|---|
| Kaiser DM (N=200 nwLH) | Δ = +0.034σ | `phase7_rsd_test.json` |
| Kaiser+FoG HOD B3 (N=200) | Δ = −0.004σ | `phase7_rsd_hod_confirmation.json` |
| Verdetto | RSD non sposta ⟨pers₁⟩ a livello sub-σ | `phase7p1_gate_result.json` |

Entrambi i test blindati prima dell'esecuzione. Il risultato RSD DM (Gate 7.0) è il prerequisito biforcante che ha attivato PAPER_B_ACTIVE. Il test HOD (Task 7.1d) è la conferma con tracciatore realistico.

**Caveat:** Velocità satelliti = velocità alone (no dispersione intra-alone). Approssimazione conservativa → lower bound sul sistematico RSD. Da dichiarare nel paper.

---

## 5. SISTEMATICHE S1–S3 (TABELLA FINALE)

| Sistematica | Δ | Threshold | Verdetto |
|---|---|---|---|
| S1 — redshift mock (z=0 vs z=0.5) | 0.57σ | 1.0σ | NON_DOMINANT |
| S2 — NGC vs SGC | 1.15σ (1.154 esatto) | 1.0σ | BORDERLINE |
| S3 — smoothing σ_px | 8.42σ | — | DOMINANT (risolto Confronto B) |

- S2 BORDERLINE: da dichiarare nel paper. Test varianza cosmica: P(|diff mock pairs| > 0.032) = 41.5% — differenza NGC-SGC ordinaria per varianza cosmica. Fonte: `phase6_systematics_final.json`
- S3 è la sistematica dominante; il Confronto B la corregge per costruzione.

---

## 6. RAMO B (NULL RISULTATO DICHIARATO)

| Quantità | Valore | Fonte |
|---|---|---|
| σ_B Phase 5 (seed 42) | 0.983σ | `phase5_gate_result.json` |
| σ_B T1 mean (N=10 run) | 1.68σ | `phase7_t1_variability.json` |
| σ_B T1 std | ±0.43σ | `phase7_t1_variability.json` |
| σ_B T1 CV | 25.3% | `phase7_t1_variability.json` |
| σ_B T1 range | [1.03, 2.58]σ | `phase7_t1_variability.json` |
| Segno ρ_obs | Alternante 5+/5− su 10 run | `phase7_t1_variability.json` |

**Interpretazione:** Null fisicamente atteso a z=0. H(z=0) ≡ H₀ e D(z=0) ≡ 1 per costruzione — il campo di densità a z=0 non può rivelare w₀ attraverso la storia di espansione. La variabilità σ_B = 1.68±0.43 con segno alternante è prova diretta dell'assenza di direzione stabile associata a w₀. Il null è un risultato scientifico dichiarato, non un fallimento.
Framing Reviewer C1: "null con varianza spiegata", non "null stabile".

---

## 7. BEYOND P(k) — TRACER ACTIVATION

| Test | σ parziale | Fonte |
|---|---|---|
| ⟨pers₁⟩ DM z=0 (marginale) | 0.095σ | `phase7_pk_comparison_r53.json` |
| ⟨pers₁⟩ DM z=0 (parziale) | 1.39σ | `phase7_r53_partial_corr.json` |
| P(k) ridge DM z=0 (marginale) | 2.26σ | `phase7_pk_comparison_r53.json` |
| P(k) ridge DM z=0 (parziale) | 2.76σ | `phase7_r53_partial_corr.json` |
| ⟨pers₁⟩ HOD (parziale) | **3.73σ** | `phase7_r53_partial_corr.json` |
| Tracer activation ratio | 3.33× (DM 1.12σ → HOD 3.73σ) | `phase7_r53_partial_corr.json` |

**Interpretazione corretta (Delta 3):** TDA non batte P(k) sui campi DM a z=0 (P(k) competitivo). TDA supera P(k) **sui campi galattici** grazie al tracer bias che rompe la degenerazione H(z=0) ≡ H₀. Il gain emerge dal tracciatore galattico, non dalla TDA intrinsecamente.

**Nota Reviewer C2:** La tracer activation è post-hoc (non pre-specificata). Da dichiarare esplicitamente nel paper.
**Nota Reviewer C3:** Riportare entrambi i confronti (DM e HOD) nel paper.

---

## 8. DEGENERAZIONE IDE (Phase 5bis)

| Quantità | Valore | Fonte |
|---|---|---|
| Max ΔD/D (IDE vs CPL) | 0.94% | `phase5bis_gate_result.json` |
| Threshold PASS_CONSERVATIVE | < 1% | `gate5bis_prior_v1_0.json` |
| Verdetto | PASS_CONSERVATIVE | `phase5bis_gate_result.json` |

**Implicazione paper:** Il segnale topologico CAUCHY è in linea di principio degenere con cosmologie IDE equivalenti a livello di background — limite strutturale condiviso con qualsiasi probe basato sulla storia di espansione (BAO, SNe). Da dichiarare come limitazione esplicita in Discussion.

---

## 9. DATI OSSERVATIVI — DESI BGS DR1

| Quantità | Valore | Fonte |
|---|---|---|
| Survey | DESI BGS DR1 | `phase6_gate_result.json` |
| Regione primaria | NGC | idem |
| Galassie NGC | 217,614 | idem |
| Intervallo z | [0.1, 0.4] | idem |
| z_eff approx | ~0.2 | `phase6_systematics.json` |
| Box size NGC (Mpc/h) | ~1997 | `phase6_gate_result.json` |
| Cell size NGC (Mpc/h) | 15.6 | idem |
| σ_px DESI R=10 | 0.641 | `gate6_prior_v1_0.json` |

**Delta 5:** Il documento methodology prevedeva DESI DR2. Alla data di esecuzione (maggio 2026), DR2 non era accessibile. Usato DR1. Da dichiarare come limitazione. Karim et al. 2025 (DR2) conferma w₀ < −1 da BAO — rafforza la motivazione.

---

## 10. SIMULAZIONI MOCK — QUIJOTE nwLH

| Quantità | Valore | Fonte |
|---|---|---|
| Suite | Quijote nwLH Latin Hypercube | `phase0_data_manifest.json` |
| N cosmologie | 2000 | idem |
| w₀ range | [−1.30, −0.70] | idem |
| Griglia | 128³ voxel | idem |
| Smoothing mock primario | R = 5 Mpc/h | `phase6_gate_result.json` |
| σ_px mock | 0.640 | `gate6_prior_v1_0.json` |
| Cell size mock (Mpc/h) | 7.8125 | idem |
| HOD log_Mmin | 12.5 | `phase5_hod_b3_manifest.json` |
| Mock redshift riferimento | z = 0.5 | `phase6_mock_manifest_z05.json` |

---

## 11. PIPELINE TDA (RAMO A) — SPECIFICHE

| Componente | Valore | Fonte |
|---|---|---|
| Libreria | gudhi CubicalComplex | `phase0_preprocessing_lock.json` |
| Tipo filtrazione | Superlevel su ν = log(1+δ) | idem |
| Convenzione birth/death | birth = −diag[:,0], death = −diag[:,1] | `phase7_nomenclature_lock.json` |
| Log-transform | log1p(clip(δ, −1)) | `phase0_preprocessing_lock.json` |
| N threshold | 100 | `phase6_bgs_tda_features.json` |
| σ_px Confronto B | 0.640–0.641 | `gate6_prior_v1_0.json` |
| Omologia calcolata | H0 (β₀), H1 (β₁) | `phase7_nomenclature_lock.json` |
| H2 (β₂) calcolata? | **NO** | `phase7_nomenclature_lock.json` |
| N feature per campo | 8 (β₁ × 7, β₀ × 1) | `phase7_r35_beta_contribution.md` |

**Bug critico storico (documentare nel paper):** Log-transform errata `log1p(clip(δ, 0))` invece di `log1p(clip(δ, −1))` produceva b2_mean ≈ 0.008 invece di ≈ 0.105. Rilevato e corretto durante Gate 7.0.

**Convenzione birth/death:** Bug storico di inversione (birth=+col0) produceva curve β₁ identicamente zero. Rilevato in early development. Fonte: CHANGELOG.

---

## 12. PIPELINE CNN+GNN (RAMO B) — SPECIFICHE

| Componente | Valore | Fonte |
|---|---|---|
| CNN encoder | SE(3)-equivariant (e3nn 0.6.0) | `phase2_gate_result.json` |
| Campo τ(x) | Residuo spazio latente CNN vs ΛCDM | idem |
| GNN embedding | j* (fase3) | `phase3_gate_result.json` |
| Checkpoint GNN | phase3_gnn_best.pt, epoch 171 | `gate5_prior_v1_0.json` |
| N training | 1600 (LHC) | `phase7_t1_variability.json` |
| N validation | 400 (LHC) | idem |
| N eval (nwLH) | 2000 | idem |
| Partial corr | r(j*, w₀ \| Ωm, σ₈) | `phase5_ramo_b_results.json` |
| Permutation test | N = 1000 | `phase7_t1_variability.json` |

---

## 13. IMPEGNI PRE-SUBMISSION (NON BLOCCANO IL DRAFT)

| Item | Descrizione | Status |
|---|---|---|
| **R5-1** | HOD fitting su mock DESI BGS (Smith & Grove 2024) | NOT STARTED — BLOCKING pre-submission |
| R3-5 | β₂ ablation (β₂ non presente nel pipeline) | OPEN → future work dichiarato nel paper |
| OC-3 | Wang & Wang SNe calibration review | OPEN |
| OC-4 | Triple baseline comparison Phase 6 | OPEN |

---

## 14. CITAZIONI OBBLIGATORIE

### 14.1 Da aggiungere (peer review esterna)

| Paper | Sezione paper | Note |
|---|---|---|
| Calles, Yip et al. 2025 (arXiv:2412.15405) | Introduction + Methods Ramo B | Confermata da `phase7p1_gate_result.json` |
| Smith & Grove et al. 2024 (arXiv:2312.08792) | Methods §HOD | DESI BGS mock HOD |
| Spurio Mancini et al. 2024 (arXiv:2410.10616) | Discussion | SBI field-level |

### 14.2 Già nel progetto (Tier 1)

| Paper | Sezione | Ruolo |
|---|---|---|
| Karim et al. 2025 (DESI DR2 BAO) | Introduction | Motivazione + contesto |
| Yip & Biagetti 2024 (arXiv:2403.13985) | Introduction | Fisher PH |
| Hahn et al. 2023 (SimBIG) | Introduction/Discussion | Field-level inference benchmark |
| Prat et al. 2025 (DES Y3 PH) | Introduction | Distinzione 2D vs 3D β₁ |
| Abedi et al. 2025 (arXiv:2410.01751) | Methods/Discussion | RSD + PH reference |
| Neumann et al. 2026 (arXiv:2604.22970) | Methods | Metodologia PH |
| Gavela et al. 2009 (IDE doom factor) | Discussion | IDE degeneracy |
| Artola et al. 2026 | Discussion | IDE context |
| Dai et al. 2026 | Discussion | IDE context |

---

## 15. DELTA METODOLOGIA vs RISULTATI — FLAG ESPLICITI

Questi 5 delta devono essere discussi e risolti nello Step 2 prima della stesura.

### ⚠️ DELTA 1 — β₂ non implementato [IMPATTO: ALTO]
**Methodology §1.3 afferma:** β₂ è il "segnale primario per il phantom crossing."
**Risultato effettivo:** Pipeline calcola solo H1 (β₁) e H0 (β₀). H2 (β₂, vuoti 3D) non è calcolato.
**Il segnale +3.09σ è interamente β₁** (loop/filamenti cosmici), non β₂.
**Decisione necessaria:** Ricalibrazione della narrativa. La claim è "anomalia nella topologia filamentare 3D (β₁)", non "topologia dei vuoti (β₂)". La distintività 3D di β₁ vs analisi 2D (Prat et al.) rimane valida.
Fonte: `phase7_nomenclature_lock.json`, `phase7_r35_beta_contribution.md`

### ⚠️ DELTA 2 — Ramo B null [IMPATTO: MEDIO]
**Methodology:** Ramo B come contributo parallelo a Ramo A con segnale positivo.
**Risultato:** σ_B = 1.68±0.43σ, null fisicamente atteso a z=0, segno alternante.
**Decisione necessaria:** Presentare il null come risultato scientifico corretto e coerente. Spiegazione fisica: H(z=0) ≡ H₀ per costruzione → nessuna sensibilità a w₀ attraverso la storia di espansione. La CNN τ(x) non può rivelare quello che la fisica non consente a z=0.
Fonte: `phase7_t1_variability.json`, `gate7p1_prior_v1_0.json`

### ⚠️ DELTA 3 — Beyond-P(k) riformulato [IMPATTO: MEDIO]
**Claim originale:** "TDA batte P(k)" in generale.
**Risultato corretto:** TDA non batte P(k) su campi DM a z=0 (P(k) marginal 2.26σ vs TDA marginal 0.095σ). TDA supera P(k) su campi galattici HOD (tracer activation: 1.12σ DM → 3.73σ HOD).
**Decisione necessaria:** Claim deve essere fisicamente preciso — il gain TDA emerge dal tracer bias che rompe H(z=0)≡H₀, non dalla TDA per sé stessa.
**Dichiarazione post-hoc obbligatoria** (Reviewer C2, C3).
Fonte: `phase7_pk_comparison_r53.json`, `phase7_r53_partial_corr.json`

### ⚠️ DELTA 4 — σ_px come scoperta metodologica centrale [IMPATTO: ALTO]
**Methodology:** Non menzionava σ_px.
**Risultato:** ⟨pers₁⟩ dipende criticamente da σ_px (adimensionale), non da R fisico in Mpc/h. Questa scoperta è l'unico fondamento che rende valido il Confronto DESI vs mock. L'impatto σ_px è +8.42σ — dominante.
**Decisione necessaria:** Presentare come scoperta metodologica positiva nel Methods. È anche il nucleo di Paper A (methodology σ_px separabile).
Fonte: `phase6_sigma_px_test.json`, `phase6_gate_result.json`

### ⚠️ DELTA 5 — DESI DR1 invece di DR2 [IMPATTO: BASSO]
**Methodology:** Prevedeva DESI DR2.
**Risultato:** Usato DR1 (217,614 galassie, z∈[0.1,0.4], NGC).
**Decisione necessaria:** Dichiarare come limitazione esplicita. Notare che Karim et al. 2025 (DR2) conferma w₀ < −1 — rafforza la motivazione del paper, non lo indebolisce.
Fonte: `phase6_gate_result.json`, `Karim2025_DESI_DR2_BAO_Revisione_Scientifica.md`

---

## 16. PHYSICAL INTERPRETATION — DUAL SIGNATURE

Il segnale DESI NGC mostra un pattern fisicamente distintivo su due feature β₁:

| Feature | z-score NGC | Direzione | Interpretazione |
|---|---|---|---|
| ⟨pers₁⟩ (b2_mean_persistence) | +11.85 | DESI > mock | Loop più persistenti |
| β₁_max (b2_max_count) | −55.59 | DESI << mock | Meno loop in totale |

Interpretazione fisica [fonte: `phase7_nomenclature_lock.json`]: DESI ha meno loop filamentari del previsto sotto ΛCDM (~5× meno al picco: 29,683 vs mock 133,786), ma quelli presenti sono significativamente più persistenti. Questo pattern è fisicamente coerente con phantom crossing w₀ < −1: l'accelerazione espansiva accelerata sopprime la formazione di loop transitori a piccola scala (β₁_max basso) mentre amplifica le strutture topologiche large-scale (⟨pers₁⟩ alto). Il dual signature anti-correlato rafforza la credibilità del segnale rispetto a un singolo outlier.

---

## 17. ANOMALIA GEOMETRIA GRIGLIA (DESI vs MOCK)

| Quantità | DESI | Mock Quijote |
|---|---|---|
| Box size (Mpc/h) | ~1997 | 1000 |
| Cell size (Mpc/h) | 15.60 | 7.81 |
| σ_px @ R=5 Mpc/h | 0.321 | 0.640 |
| σ_px @ R=10 Mpc/h | 0.641 | 0.640 |

La differenza di cell_size (2×) è la causa del mismatch σ_px nel Confronto A. Il Confronto B corregge per costruzione portando σ_px a 0.641 ≈ 0.640.

---

*Documento completato — Step 1 Sub-Phase 7.2.*
*Nessun numero è "a memoria". Ogni cifra traccia al JSON frozen indicato.*
*Pronto per verifica PI prima di Step 2.*
