# CAUCHY — Execution Parameters
## Gate Thresholds and Numerical Priors

**Classification:** Operational Parameters — Frozen Priors  
**Version:** 1.1 — Aprile 2026 (revisione post-ricerca letteratura)
**Status:** Pre-execution — da convalidare dal PI prima della Phase 0  
**Autorità:** CAUCHY_Systematic_Methodology_v2.0 §2.4 — questo documento è citato come destinazione dei threshold numerici dei gate.

---

## Avvertenza Metodologica

Questo documento fissa i **prior congelati** per i gate criteria di CAUCHY. Ogni threshold è derivato dalla letteratura Tier 1 tramite argomento di scaling esplicito — non fitting al valore atteso. I threshold sono **immutabili** salvo applicazione del Protocollo di Ricalibrzione Formale (Methodology §2.4, max N=2 per gate).

Ogni numero fisico riportato è tracciato alla fonte primaria nella sezione §7 (Registro delle Fonti). Affermazioni prive di fonte sono marcate esplicitamente `[VALORE NON VERIFICATO]`.

Il PI deve leggere e approvare questo documento prima dell'inizio della Phase 0. L'approvazione è registrata nel CHANGELOG.

---

## 1 — Parametri Globali e Dataset di Riferimento

### 1.1 Cosmologia Fiduciale

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| Ωm | 0.3175 | Methodology §0.1 ← Quijote suite (Villaescusa-Navarro et al. 2020) |
| σ₈ | 0.834 | idem |
| w₀ | −1.0 | idem |
| h | 0.6711 | idem |
| Ωb | 0.049 | idem |
| ns | 0.9624 | idem |

### 1.2 Dataset Operativi

| Dataset | N campi | Uso | Range parametri |
|---------|---------|-----|-----------------|
| Fiduciali PCS 128³ | 2.000 (di 15.000) | Matrice covarianza, μ_ΛCDM | cosmologia fissa |
| LHC PCS 128³ | 2.000 | Gate 1a, Fasi 2-4 | Ωm ∈ [0.10, 0.50], σ₈ ∈ [0.60, 1.00] |
| nwLH PCS 128³ | 2.000 | Gate 1b, Fase 5 | w₀ ∈ [−1.30, −0.70] |

**Volume di riferimento:** (1 Gpc/h)³ per campo. Fonte: Methodology §0.1.

---

## 2 — Gate 0: Integrità Dati e Preprocessing

### 2.1 Criteri di Integrità

| Criterio | Threshold | Motivazione |
|----------|-----------|-------------|
| Tasso di superamento controlli integrità | ≥ 99% dei campi per dataset | Soglia operativa standard — meno dell'1% di perdita è accettabile per artefatti di I/O |
| Campi rigettati (max) | ≤ 20 per dataset (1% di 2000) | Coerente con la riserva di robustezza — le 13.000 fiduciali rimanenti assorbono la perdita |
| Checksum SHA-256 | 100% dei file verificati | Integrità assoluta richiesta per l'audit trail del paper |

### 2.2 Pipeline di Preprocessing

| Parametro | Valore | Fonte/Motivazione |
|-----------|--------|-------------------|
| Scala di smoothing | 5 Mpc/h (Gaussian kernel) | Consenso della letteratura TDA su campi di densità 3D con superlevel filtration su Quijote: Abedi et al. 2025 (arXiv:2410.01751v2) e Jalali Kanafi et al. 2024 (MNRAS) usano entrambi R = 5 Mpc/h. Abedi et al. mostrano che l'impatto delle RSD sul segnale topologico dipende fortemente dalla scala di smoothing e che scale < 5 Mpc/h amplificano artefatti non-lineari da finger-of-god. |
| Normalizzazione | Per-cosmologia (non per-campo) | Methodology §0.2: preserva il segnale di ampiezza necessario per β₁ e β₂ |
| Griglia | 128³ punti, scatola (1 Gpc/h)³ | Input nativo dei campi PCS Quijote |

**Nota:** Abedi et al. 2025 (arXiv:2410.01751v2) è il paper di riferimento primario per questa scelta: studia esattamente la combinazione PH + superlevel filtration + RSD + simulazioni Quijote. Il paper mostra (Fig. 5) che R = 5 Mpc/h produce Betti curves stabili in entrambi gli spazi (reale e redshift) e che scale più piccole amplificano gli effetti non-lineari delle RSD su β₂ — il segnale di interesse primario per CAUCHY.

---

## 3 — Gate 1: TDA Baseline (Ramo A)

### 3.1 Stime di Riferimento dalla Letteratura

Il benchmark primario è **Yip et al. 2024** (arXiv:2403.13985), omologia persistente su cataloghi di aloni Quijote, volume (1 Gpc/h)³.

Risultati Fisher estrapolati di Yip et al. 2024 (Tabella 1 della revisione scientifica, valori estrapolati):

| Parametro | σ_PH (estrapolato) | σ_P₀+P₂+B₀ (estrapolato) | Dataset |
|-----------|-------------------|--------------------------|---------|
| Ωm | ±0.014 | ±0.010 | Aloni Quijote, (1 Gpc/h)³ |
| σ₈ | ±0.005 | ±0.009 | idem |
| w | ±0.062 | ±0.113 | idem |

Fonte: Yip2024_PersistentHomology_Fisher_Revisione_Scientifica.md §3.1 ← Yip et al. 2024 Tabella 1.

### 3.2 Scaling al Contesto CAUCHY

CAUCHY differisce da Yip et al. 2024 su tre assi:

**Asse 1 — Tracciatori:** Yip usa aloni di materia oscura; CAUCHY usa campi di densità PCS (particle-centered smoothed). L'effetto atteso è che i campi PCS portano meno informazione degli aloni (che includono la funzione di massa degli aloni come segnale aggiuntivo), ma più informazione rispetto ai campi di griglia lisci. Fattore di correzione: non quantificabile a priori — la ricalibrzione del gate è **prevista e attesa**.

**Asse 2 — Spazio reale vs spazio di redshift:** Yip opera in spazio reale; CAUCHY opera in spazio di redshift (PCS). Le RSD allungano le strutture lungo la linea di vista (finger-of-god, Kaiser effect), modificando sistematicamente le Betti curves. L'effetto netto sulla sensibilità a w₀ è non banale — l'analisi Fischer di Li & Zhao (2025) [arXiv:2512.07236, citato in Revisione Yip §4.4] mostra che includere RSD **migliora** la sensibilità ai parametri di crescita.

**Asse 3 — Statistica (α-DTMℓ vs superlevel filtration):** Yip usa la filtrazione α-DTMℓ su cataloghi di punti; CAUCHY usa la filtrazione di supralivello su campi di densità (gudhi `CubicalComplex`). I due approcci non sono direttamente comparabili in termini di informazione estratta.

**Formula di scaling applicata (Methodology §2.4):**

```
σ(θ)_CAUCHY_prior = σ(θ)_Yip × f_tracciatore × f_RSD
```

dove f_tracciatore e f_RSD sono fattori di correzione che **non possono essere quantificati a priori** senza eseguire l'analisi. Il protocollo corretto è:

1. Si esegue la Fase 1.
2. Si confronta il risultato osservato con σ_Yip.
3. Se il risultato è fuori dal range [0.5×, 3×] × σ_Yip, si apre il Protocollo di Ricalibrzione.

### 3.3 Gate 1a — Threshold Numerici

| Criterio | Threshold | Tipo | Fonte |
|----------|-----------|------|-------|
| σ(Ωm) dal Fisher TDA su LHC | ≤ 0.10 (1σ marginalizzato) | Soglia massima ammissibile | 3× degradazione rispetto a Yip ±0.014 — oltre questo limite il metodo non è competitivo |
| σ(σ₈) dal Fisher TDA su LHC | ≤ 0.030 (1σ marginalizzato) | Soglia massima ammissibile | 6× degradazione rispetto a Yip ±0.005 — margine largo per differenze di tracciatore |
| σ(w₀) dal Fisher TDA su LHC | da documentare | Documentazione | Non threshold di pass/fail — valore registrato come baseline per Gate 5 |
| Convergenza della matrice Fisher | ≥ 2 direzioni ben convergenti | Qualitativo | Ouellette & Holder (2025) citati in Revisione Yip §4.3: con 2.000 realizzazioni, convergenza parziale è attesa |
| Correlazione ρ(Ωm, σ₈) | da documentare e confrontare con ρ_Pk ≈ −0.95 | Documentazione | Methodology §1.3: correlazione diversa = risultato pubblicabile |

**Interpretazione:** i threshold su σ(Ωm) e σ(σ₈) sono volutamente larghi (fattori 3-6× rispetto a Yip) per tenere conto delle differenze strutturali tra i setup. Il gate non misura la performance assoluta: misura che l'analisi abbia prodotto un risultato significativo e documentabile.

### 3.4 Gate 1b — Threshold Numerici

| Criterio | Threshold | Tipo | Fonte |
|----------|-----------|------|-------|
| \|r(b1_peak_position, w₀)\| su nwLH | ≥ 0.10 | Soglia minima | Correlazione non nulla al 95% richiede \|r\| > 2/√N ≈ 0.045 per N=2000; soglia 0.10 = 2.2× questa stima per robustezza |
| \|r(b2_mean_persistence, w₀)\| su nwLH | ≥ 0.10 | Soglia minima | idem — β₂ è il segnale primario per phantom crossing (Methodology §1.3) |
| Almeno una feature con \|r\| ≥ 0.15 | sì/no | Soft gate | Segnale sufficiente per motivare il Ramo B — se nessuna feature raggiunge 0.15, documentare come Scenario C parziale |

**Nota statistica:** per N=2.000 campioni, il threshold di significatività al 99% per correlazione di Pearson è |r| > 3/√N ≈ 0.067. Il threshold scelto di 0.10 corrisponde a ~4.5σ statistici — sufficientemente conservativo da escludere fluttuazioni casuali.

---

## 4 — Gate 2: CNN e Test T1 di Fattorizzazione Parametrica

### 4.1 Architettura CNN

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| Architettura | SE(3)-equivariante, e3nn | Methodology §2.1 |
| Target di supervisione | Betti curve features di Fase 1 | Methodology §2.1 — non i parametri cosmologici diretti |
| Numero campi fiduciali per μ_ΛCDM | 2.000 | Methodology §2.2 |
| Split training/test | 80% / 20% (LHC) | Prassi standard |
| Seed globale | 42 | environment.yml `CAUCHY_GLOBAL_SEED` |

### 4.2 Test T1 — Threshold Numerico

Il rapporto R è definito come:

```
R = W₂(stesso-σ₈, Ωm-diverso) / W₂(stesso-Ωm, σ₈-diverso)
```

dove W₂ è la distanza di Wasserstein del 2° ordine tra le distribuzioni di τ nei quadranti del piano (σ₈, Ωm).

| Criterio | Threshold | Motivazione |
|----------|-----------|-------------|
| R (rapporto Wasserstein) | ≥ 0.20 | Se R < 0.20, le distribuzioni di τ non distinguono Ωm da σ₈ meglio di un fattore 5 — il campo τ è dominato da σ₈ e il Ramo B non porta informazione indipendente |
| Correlazione \|τ(x)\| vs hessiano locale di δ(x) | ≥ 0.05 (soft) | Sanity check: τ deve catturare struttura non-lineare. Valore non derivato da letteratura specifica — da convalidare |

**⚠️ Nota PI:** il threshold R ≥ 0.20 è una stima del PI basata sulla fisica del problema, non derivato direttamente da un paper. È il primo candidato alla ricalibrzione se il test T1 produce valori di R sistematicamente diversi. La motivazione per 0.20 è: R = 1.0 indicherebbe piena fattorizzazione (CNN equamente sensibile a entrambi i parametri); R < 0.05 indicherebbe collasso totale su σ₈; R = 0.20 è una soglia minima di informazione su Ωm.

---

## 5 — Gate 3: GNN su TDA(τ(x))

### 5.1 Architettura GNN

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| Framework | e3nn + torch-geometric | Methodology §3.2, environment.yml |
| Split training/test | 80% / 20% (LHC) | Prassi standard |
| Target | (Ωm, σ₈, w₀) | Methodology §3.2 |
| Persistenza minima per selezione nodi | da determinare in Fase 1 | Methodology §3.1: "derivata dalla distribuzione di persistenza nei campi fiduciali" |

### 5.2 Threshold Gate 3

| Criterio | Threshold | Motivazione | Fonte |
|----------|-----------|-------------|-------|
| \|r(GNN_j*, Ωm)\| sul test set | ≥ 0.20 | Il GNN deve essere più informativo di una correlazione casuale su Ωm | Coerente con significatività ~9σ per N=400 (20% di 2000) |
| \|r(GNN_j*, σ₈)\| sul test set | ≥ 0.20 | idem per σ₈ | idem |
| Miglioramento su baseline TDA (Ramo A) | varianza aggiuntiva spiegata ≥ 5% | Il Ramo B deve portare informazione genuinamente nuova rispetto al Ramo A | Motivazione operativa — soglia minima per pubblicabilità del contributo |
| \|r(GNN_j*, w₀)\| su nwLH | da documentare (soft) | Precursore della Fase 5 — non threshold di pass/fail | Methodology §3.3 |

---

## 6 — Gate 4: Symbolic Regression

### 6.1 Configurazione PySR

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| Backend | Julia 1.10, PySR 0.18 | environment.yml, Methodology §4.2 |
| N run indipendenti | 20 | Methodology §4.2 |
| Metrica di selezione | AIC/BIC (non solo MSE) | Methodology §4.2 — previene overfitting |

### 6.2 Threshold Gate 4

| Criterio | Threshold | Fonte |
|----------|-----------|-------|
| Stabilità espressione | ≥ 10/20 run (50%) | Methodology §4.3 — verbatim |
| R² sul test set held-out | struttura a due livelli: ≥ 0.50 (soglia minima) / ≥ 0.70 (soglia forte) | La letteratura PySR su applicazioni scientifiche opera con R² >> 0.90 per recupero di leggi fisiche note. Per il contesto CAUCHY — SR come strumento interpretativo su segnali topologici rumorosi — si adotta una struttura a due livelli: R² ≥ 0.50 = relazione parziale documentabile; R² ≥ 0.70 = espressione fisicamente interpretabile pubblicabile. Soglie derivate da considerazioni operative, non da una singola fonte. |
| Interpretabilità fisica | sì/no (qualitativo) | Methodology §4.3: "no polinomi arbitrari senza motivazione" — valutato dal PI e dal Reviewer |

**Tabella di interpretazione Gate 4:**

| R² | Interpretazione | Azione |
|----|-----------------|--------|
| < 0.50 | Nessuna relazione analitica stabile | Scenario C su SR del Ramo B — documentare come risultato negativo |
| 0.50 – 0.70 | Relazione debole, struttura parziale | Documentare con caveat esplicito nel paper |
| ≥ 0.70 | Espressione fisicamente interpretabile | Gate 4 superato, procedere con interpretazione fisica |

---

## 7 — Gate 5: Phantom Crossing Injection Test

### 7.1 Valori di Injection

I valori di w₀ testati corrispondono alle regioni best-fit di DESI DR2 (Karim et al. 2025):

| Scenario | w₀ | wₐ | Best-fit DESI DR2 | Fonte |
|----------|----|----|-------------------|-------|
| Quintom-B moderato | −0.7 | −0.8 | w₀ ≈ −0.75, wₐ ≈ −0.86 (DESI+CMB+DESY5) | Karim2025, eq. (28): w₀ = −0.752±0.057, wₐ = −0.86 |
| Phantom forte | −1.3 | +0.5 | estremo del range nwLH | Methodology §5.1 |
| Quintessenza lieve | −0.9 | −0.3 | prossimo al best-fit DESI+CMB+PantheonPlus | Karim2025, eq. (26): w₀ = −0.838±0.055, wₐ = −0.62 |

**Nota:** i valori di injection sono fissati nel Methodology e non soggetti a ricalibrzione tramite questo documento. Il phantom crossing avviene a redshift z_cross dove w(z_cross) = −1, ovvero z_cross = −wₐ/( w₀ + wₐ) − 1. Per DESI+CMB+DESY5: z_cross ≈ 0.4. Fonte: Karim et al. 2025, testo dopo eq. (28).

### 7.2 Permutation Test

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| N shuffles | 1.000 | Methodology §5.1 |
| Statistica | correlazione parziale r(pipeline, w₀ \| Ωm, σ₈) | Methodology §5.1 |
| Significatività | σ = (\|r_obs\| − mean(r_null)) / std(r_null) | Methodology §5.1 |

### 7.3 Threshold Gate 5 — Venue Determination

| Significatività σ | Esito | Venue target | Fonte |
|-------------------|-------|--------------|-------|
| σ ≥ 2.0 | Phantom crossing rilevato | Nature Astronomy / PRL | Methodology §5.1 — verbatim |
| 1.0 ≤ σ < 2.0 | Evidenza marginale | Physical Review D | idem |
| σ < 1.0 | Non-rilevazione | JCAP (upper bound documentato) | idem |

**Contesto di riferimento:** le significatività DESI DR2 per DDE su diverse combinazioni di dataset variano da 1.7σ a 4.2σ (Karim et al. 2025, Tabella VI). Un rilevamento CAUCHY a σ ≥ 2.0 su simulazioni Quijote sarebbe comparabile alla evidenza statistica osservata da DESI DR2 su dati reali — questo è il benchmark di rilevanza scientifica del Gate 5.

---

## 8 — Gate 6: Sistematiche DESI (se applicabile)

### 8.1 Threshold Robustezza

| Test | Threshold | Fonte |
|------|-----------|-------|
| Variazione del segnale topologico sotto perturbazione delle sistematiche | < 1σ (del valore centrale) | Methodology §6.2 — verbatim: "non cambia significativamente (< 1σ)" |
| Robustezza HOD (Fase 5) | variazione su w₀ tra Zheng 2007 e AbacusSummit | < 1σ | Methodology §5.2 — verbatim |

---

## 9 — Parametri TDA Operativi

### 9.1 Feature Estratte dalle Betti Curves

Le feature estratte sono quelle specificate nel Methodology §1.2:

**β₁ (loops / filamenti cosmici):**
- Posizione del picco: `b1_peak_position`
- Altezza del picco: `b1_peak_height`
- Larghezza a metà altezza (FWHM): `b1_fwhm`
- Integrale totale: `b1_total`

**β₂ (vuoti cosmici chiusi):**
- Numero massimo di vuoti chiusi: `b2_max_count`
- Persistenza media: `b2_mean_persistence`
- Integrale ad alta persistenza (top 10%): `b2_high_persistence_integral`

**β₀ (cluster / componenti connesse):**
- Valore al livello di densità media: `b0_at_mean_density`

**Filtrazione:** supralivello su campo di densità (gudhi `CubicalComplex`). Motivazione: diretta applicabilità a campi su griglia cubica 128³.

### 9.2 Parametri di Binning per Istogrammi (se usati)

| Parametro | Valore | Fonte |
|-----------|--------|-------|
| N_bin per istogramma (se metodo Yip) | 1.260 | Yip et al. 2024 — motivato da compromesso gaussianità/convergenza/potere. Da adattare al contesto CAUCHY |
| Valori di k per filtrazione α-DTMℓ (se usata) | {1, 5, 15, 30, 60, 100} | Yip et al. 2024 §2.2. Applicabile solo se si adotta la filtrazione α-DTMℓ invece di supralivello |

**Nota:** CAUCHY usa la filtrazione di supralivello su campi di griglia (non α-DTMℓ su cataloghi di punti). I parametri Yip sono riportati per riferimento e per eventuale confronto metodologico nel paper.

---

## 10 — Registro dei Valori Non Verificati

I seguenti valori in questo documento sono stime operative non direttamente tracciate a un paper specifico con benchmark numerico preciso. Devono essere rivisti dal PI prima dell'esecuzione della fase corrispondente:

| Parametro | Valore | Sezione | Azione richiesta |
|-----------|--------|---------|-----------------|
| Threshold R (T1 test) | ≥ 0.20 | §4.2 | Motivazione fisica fornita e uso di W₂ supportato da Tsizh et al. 2023 (MNRAS), ma il valore specifico 0.20 è una stima operativa senza precedente letterale in letteratura. Eseguire run pilota su 200 campi prima del training completo e verificare la distribuzione dei valori W₂ osservati. RecalibrationReport per Gate 2 è considerato probabile. |
| Soglia "soft" \|r_GNN\| ≥ 0.15 | 0.15 | §3.4 | Stima preliminare — da rivedere alla luce dei risultati del Gate 1b |
| Correlazione \|τ(x)\| vs hessiano | ≥ 0.05 | §4.2 | Non tracciato — sanity check qualitativo |

---

## 11 — Registro delle Fonti Numeriche

| Valore | Paper | Sezione/Tabella | arXiv |
|--------|-------|-----------------|-------|
| R = 5 Mpc/h (smoothing scale) | Abedi et al. 2025 | §2, Fig. 5-8 | 2410.01751v2 |
| R = 5 Mpc/h (confermato) | Jalali Kanafi et al. 2024 | §III | MNRAS 2024 (arXiv:2311.13520) |
| W₂ come metrica discriminazione cosmologie | Tsizh et al. 2023 | §3 | arXiv:2301.09411, MNRAS |
| σ_PH(Ωm) = ±0.014 (estrapolato) | Yip et al. 2024 | Tabella 1 | 2403.13985v2 |
| σ_PH(σ₈) = ±0.005 (estrapolato) | Yip et al. 2024 | Tabella 1 | 2403.13985v2 |
| σ_PH(w) = ±0.062 (estrapolato) | Yip et al. 2024 | Tabella 1 | 2403.13985v2 |
| N_bin = 1.260 | Yip et al. 2024 | §2.3 | 2403.13985v2 |
| k ∈ {1,5,15,30,60,100} | Yip et al. 2024 | §2.2 | 2403.13985v2 |
| ρ(Ωm,σ₈)_Pk ≈ −0.95 | Methodology v2.0 | §1.3 | — (valore tipico dalla letteratura P(k)) |
| w₀ = −0.752±0.057, wₐ = −0.86 (DESI+CMB+DESY5) | Karim et al. 2025 | eq. (28) | 2503.14738v3 |
| w₀ = −0.838±0.055, wₐ = −0.62 (DESI+CMB+PantheonPlus) | Karim et al. 2025 | eq. (26) | 2503.14738v3 |
| z_cross ≈ 0.4 (DESI+CMB+DESY5) | Karim et al. 2025 | testo §VII.A dopo eq. (28) | 2503.14738v3 |
| Significatività DDE: 2.8σ–4.2σ | Karim et al. 2025 | Tabella VI | 2503.14738v3 |
| PH migliore di P₀+P₂+B₀ per 8/10 parametri | Yip et al. 2024 | §3.1 | 2403.13985v2 |
| Combinazione PH+P₀+P₂+B₀ riduce vincoli del 12-33% | Yip et al. 2024 | §3.2 | 2403.13985v2 |
| N_sim fiduciali Yip = 14.500 | Yip et al. 2024 | §2.1 | 2403.13985v2 |
| Parametri fiduciali Quijote | Yip et al. 2024 / Villaescusa-Navarro 2020 | §2.1 | 2403.13985v2 |

---

## 12 — Procedura di Aggiornamento

Questo documento è un **prior congelato**. Le modifiche seguono regole diverse per tipo:

**Modifiche pre-esecuzione (prima del Gate 0):** il PI può correggere valori marcati `[VALORE NON VERIFICATO]` o segnalati in §10, aggiungendo una CHANGELOG entry di tipo `architecture` con motivazione. Non richiede il Protocollo di Ricalibrzione.

**Modifiche durante l'esecuzione (dopo il Gate 0):** ogni modifica a un threshold di un gate già superato richiede il Protocollo di Ricalibrzione Formale (Methodology §2.4). Questo genera un RecalibrationReport e un nuovo FrozenPriorV versioned.

**Mai:** modificare un threshold retroattivamente per far passare un gate già valutato.

---

*CAUCHY Execution Parameters v1.0*  
*Prodotto: Aprile 2026*  
*Prossima revisione: dopo approvazione PI, prima della Phase 0*  
*Autorizzazione PI richiesta prima dell'uso operativo*
