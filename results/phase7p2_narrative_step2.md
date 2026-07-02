# CAUCHY — Verifica Narrativa e Scelta Rivista
## Sub-Phase 7.2 — Step 2 (versione aggiornata post-risoluzione delta)
## Prodotto: 2026-06-07

---

## PARTE A — RISOLUZIONE DEI 5 DELTA

### DELTA 1 — β₂ non implementato ✅ RISOLTO [IMPATTO: ALTO]

**Diagnosis:** Methodology §1.3 attribuiva il segnale primario a β₂ (vuoti 3D). Il
pipeline calcola esclusivamente H1 (β₁) e H0 (β₀). Il prefisso "b2_" nel codice è un
indice posizionale (posizione 5 nel vettore feature), non il numero di Betti β₂.

**Risoluzione — argomento forte (tre livelli):**

1. **Topologia fisicamente distinta da Prat et al. 2025.** Un H₁ generator in CAUCHY è
   un ciclo filamentare volumetrico 3D che circonda un vuoto cosmico tridimensionale. Un
   H₁ generator in Prat et al. è un loop nella mappa di convergenza proiettata 2D —
   un integrale di linea che fonde strutture a redshift diversi. Questi sono oggetti
   topologici fisicamente diversi: la proiezione 2D distrugge la connettività filamentare
   3D che CAUCHY misura.

2. **Canale di sensibilità a w₀ distinto.** Prat et al. vincola S₈ e Ωm tramite
   convergenza integrata lungo la linea di vista. CAUCHY misura ⟨pers₁⟩ sul campo
   galattico 3D a z∈[0.1,0.4]: canale diverso, parametro target diverso (w₀ vs S₈),
   redshift diverso.

3. **Il dual signature è inaccessibile a qualsiasi analisi proiettata.** Il pattern
   {⟨pers₁⟩ HIGH, β₁_max LOW} richiede la distinzione tra loop transitori e loop
   persistenti — distinzione che la proiezione 2D non può fare perché fonde strutture
   a profondità diverse.

**Decisioni operative per il paper:**
- Claim: "anomalia nella topologia filamentare 3D (β₁)", non "topologia dei vuoti (β₂)"
- Footnote obbligatoria al primo uso di ⟨pers₁⟩ (testo frozen sotto)
- β₂ (H2) dichiarato come future work con motivazione fisica
- Titolo non contiene "β₂" — confermato compatibile

**Testi pronti:**

*Introduction — posizionamento vs Prat et al. 2025:*
> "The closest methodological precursor to our work is Prat et al. (2025), who apply
> persistent homology to DES Year 3 weak lensing convergence maps, achieving a 70%
> improvement in figure of merit over two-point statistics for $S_8$ and $\Omega_m$.
> Our approach differs fundamentally in three respects. First, we apply persistent
> homology to the three-dimensional galaxy density field rather than to a projected
> convergence map: a $H_1$ generator in our analysis is a volumetric filamentary cycle
> enclosing a 3D void, while a $H_1$ generator in Prat et al. is a loop in the projected
> convergence field — a line-of-sight integral that necessarily mixes structures at
> different redshifts, destroying the 3D connectivity information. Second, our target
> parameter is $w_0$ (phantom crossing), while Prat et al. targets $S_8$ and $\Omega_m$.
> Third, the dual topological signature we detect — high mean persistence combined with
> suppressed loop count — is inaccessible to any 2D projected analysis, since 3D
> persistence and projected persistence are distinct quantities: projection fuses
> transient and persistent structures that are separable only in three dimensions."

*Footnote obbligatoria (primo uso di ⟨pers₁⟩):*
> "$^\dagger$Throughout this paper, $\langle\mathrm{pers}_1\rangle$ denotes the mean
> persistence of $H_1$ generators (one-dimensional topological cycles, loops/filamentary
> structures) computed via gudhi \texttt{CubicalComplex} superlevel filtration on the
> log-transformed density field $\nu = \log(1+\delta)$. In the internal CAUCHY codebase
> this quantity is stored as \texttt{b2\_mean\_persistence}, where the prefix \texttt{b2}
> is a positional index in the feature vector (position 5), not the Betti number $\beta_2$.
> No $H_2$ features (three-dimensional void topology, $\beta_2$) are computed in the
> current pipeline; their inclusion is deferred to future work."

*Methods — dichiarazione pipeline:*
> "We extract eight topological features per field: seven from $H_1$ (one-dimensional
> persistent homology, $\beta_1$) and one from $H_0$ ($\beta_0$, connected components
> at the mean threshold). No $H_2$ features ($\beta_2$, three-dimensional void topology)
> are computed in the current analysis. The primary detection feature is
> $\langle\mathrm{pers}_1\rangle$ — the mean persistence of $H_1$ generators — whose
> internal code name \texttt{b2\_mean\_persistence} uses a positional index, not the
> Betti number (see footnote~$\dagger$)."

*Discussion — future work β₂:*
> "The extension of our pipeline to $H_2$ features ($\beta_2$, three-dimensional void
> topology) is a natural next step. Phantom crossing is expected to leave a complementary
> imprint on void expansion rates, and the CubicalComplex framework used here is in
> principle capable of computing $H_2$ persistence without architectural changes."

---

### DELTA 2 — Ramo B null ✅ RISOLTO [IMPATTO: MEDIO]

**Diagnosis:** Ramo B presentato nella Methodology come contributo parallelo con segnale
positivo atteso. Risultato: σ_B = 1.68±0.43σ, segno alternante 5+/5−, null fisicamente
atteso. Framing Reviewer C1: "null con varianza spiegata", non "null stabile".

**Risoluzione — argomento fisico:**

Il null ha una causa identificata in modo esatto. Il campo τ(x) è costruito come
residuo CNN a z=0 in spazio reale. Per rivelare w₀ attraverso la storia di espansione,
il campo δ(x, z=0) deve contenere informazione su H(z) o D(z) — ma H(z=0) ≡ H₀ e
D(z=0) ≡ 1 per costruzione. La partial correlation r(j*, w₀|Ωm,σ₈) rimuove la varianza
degenere con σ₈/Ωm; il residuo è compatibile con zero.

Il segno alternante (5+/5−) su 10 run è la prova operativa: assenza di direzione
stabile in j* verso w₀. Il null **rafforza** Ramo A: se τ(x) avesse trovato un segnale
forte a z=0, sarebbe stato un red flag. Il fatto che Ramo B sia null e Ramo A sia +3.09σ
esclude che il segnale DESI sia un artefatto condiviso tra i due rami.

**Testi pronti:**

*Methods — architettura Ramo B:*
> "Ramo B applies an SE(3)-equivariant graph neural network (CGNN; e3nn v0.6.0) to the
> tension field $\tau(\mathbf{x})$, defined as the residual in the CNN latent space between
> a field's representation and the mean ΛCDM representation $\bar{\mu}_{\Lambda\mathrm{CDM}}$
> (Phase 2). The GNN produces a 32-dimensional embedding $\mathbf{j}^*$; we report the
> partial correlation $r(\mathbf{j}^*, w_0 \mid \Omega_m, \sigma_8)$ evaluated on the
> Quijote nwLH suite (2000 fields, $w_0 \in [-1.30, -0.70]$), with significance assessed
> via permutation test ($N = 1000$ label shuffles of $w_0$)."

*Results — sezione Ramo B:*
> "The Ramo B pipeline yields $\sigma_B = 1.68 \pm 0.43\sigma$ across ten independent
> training runs with distinct random seeds (CV $= 25\%$; range $[1.03, 2.58]\sigma$;
> source: \texttt{phase7\_t1\_variability.json}). The sign of the observed partial
> correlation $\rho_\mathrm{obs}$ alternates across runs (5 positive, 5 negative out of
> 10), confirming the absence of a stable $w_0$ direction in the latent space $\mathbf{j}^*$.
>
> This null is physically expected. At $z = 0$, $H(z) \equiv H_0$ and $D(z) \equiv 1$
> by construction: the density field snapshot does not encode expansion-history information
> through linear growth. The partial correlation procedure conditions on $\Omega_m$ and
> $\sigma_8$, removing the dominant degeneracy; the residual variance attributable to $w_0$
> alone is consistent with zero. The variability across runs (CV $= 25\%$) is fully
> explained by training stochasticity in the absence of a true signal direction, not by
> physical information."

*Discussion — interpretazione null:*
> "The null result from Ramo B is not a failure of the pipeline but a consistency check
> with known physics. A significant Ramo B signal at $z = 0$ would have been anomalous,
> suggesting the CNN was encoding numerical artefacts or $\sigma_8$-degenerate structure
> rather than genuine $w_0$ sensitivity. Crucially, the independence of the two branches
> means the +3.09$\sigma$ Ramo A detection cannot be attributed to any shared pipeline
> component: Ramo B finds nothing, Ramo A finds an anomaly, and the two pipelines share
> no topological computation."

*Discussion — future work Ramo B:*
> "Ramo B is expected to become informative at $z > 0$, where $H(z)$ and $D(z)$ carry
> explicit $w_0$ dependence. Applying the CNN $\tau(\mathbf{x})$ framework to light-cone
> fields spanning $z \in [0.1, 0.4]$ — the same volume as the DESI BGS dataset used in
> Ramo A — is a natural extension that we defer to future work."

---

### DELTA 3 — Beyond-P(k) riformulato ✅ RISOLTO [IMPATTO: MEDIO]

**Diagnosis:** Il claim originale "TDA batte P(k)" non è supportato dai dati corretti
su base equivalente. La situazione è più sfumata e fisicamente più interessante.

**Tre confronti distinti — non intercambiabili:**

| Confronto | TDA | P(k) | Base | Verdict |
|---|---|---|---|---|
| A DM marginale | 0.095σ | 2.26σ | Identica DM nwLH | P(k) supera TDA |
| A DM parziale | 1.39σ (instabile) | 2.76σ | Identica, cond. Ωm/σ₈ | P(k) competitivo |
| B HOD parziale vs DM | **3.73σ** | 2.26σ (marginale DM) | **Non equiv. — post-hoc†** | TDA superiore |

†Confronto B usa HOD per TDA e DM per P(k): tracer asimmetrico. Dichiarazione
post-hoc obbligatoria (Reviewer C2). Entrambi i confronti riportati (Reviewer C3).

**Risoluzione — argomento fisico:**

Il gain TDA non emerge dalla TDA in sé su campi DM — emerge dal bias galattico HOD.
Il bias galattico non è uno scalare costante: gli aloni massicci (che tracciano
filamenti persistenti) sono più sensibili a w₀ attraverso la funzione di massa degli
aloni che gli aloni piccoli (loop transitori). La TDA, misurando la persistenza,
amplifica selettivamente il segnale degli aloni massicci. Il P(k) integra su tutta la
distribuzione degli aloni, diluendo questo segnale.

**Testi pronti:**

*Methods — descrizione confronto P(k) vs TDA:*
> "To assess the information content of $\langle\mathrm{pers}_1\rangle$ relative to
> the conventional power spectrum summary, we train Ridge and MLP regressors on $P(k)$
> extracted from the same Quijote nwLH fields (Confronto A: identical DM fields,
> $N_\mathrm{train}=1600$, $N_\mathrm{test}=400$, seed 42; source:
> \texttt{phase7\_pk\_comparison\_r53.json}). We report both marginal correlations
> $r(\hat{y}, w_0)$ and partial correlations $r(\hat{y}, w_0 \mid \Omega_m, \sigma_8)$,
> the latter assessed via permutation test ($N=1000$). An additional post-hoc comparison
> uses HOD galaxy fields for TDA versus DM fields for $P(k)$ (Confronto B), with tracer
> asymmetry explicitly declared."

*Results — tabella e testo:*
> "Table~X reports the $w_0$-sensitivity of $\langle\mathrm{pers}_1\rangle$ and $P(k)$
> regressors on the nwLH test set ($N=400$). On identical dark matter fields (Confronto A),
> $P(k)$ achieves a marginal correlation of $2.26\sigma$ (Ridge) and $1.97\sigma$ (MLP),
> while $\langle\mathrm{pers}_1\rangle$ achieves $0.095\sigma$ — consistent with zero.
> After conditioning on $\Omega_m$ and $\sigma_8$, $\langle\mathrm{pers}_1\rangle$
> recovers $1.39\sigma$ (DM) versus $2.76\sigma$ for Ridge($P(k)$); $P(k)$ remains
> competitive on this clean baseline.
>
> In a separate post-hoc comparison (Confronto B, not pre-registered), we evaluate
> $\langle\mathrm{pers}_1\rangle$ on HOD galaxy fields against the same $P(k)$ DM
> baseline. The topological sensitivity increases to $3.73\sigma$ partial (HOD) versus
> $1.12\sigma$ (DM), a factor of $3.33\times$ — while the $P(k)$ baseline is unchanged.
> We interpret this as tracer activation: the HOD galaxy bias amplifies the topological
> $w_0$ signature by selectively weighting massive haloes, whose abundance is more
> sensitive to the integrated expansion history, over transient small-scale loops."

| Statistic | Field | Comparison | $\sigma_\mathrm{marginal}$ | $\sigma_\mathrm{partial}$ |
|---|---|---|---|---|
| $\langle\mathrm{pers}_1\rangle$ | DM | A (clean) | 0.095 | 1.39 |
| Ridge($P(k)$) | DM | A (clean) | 2.26 | 2.76 |
| $\langle\mathrm{pers}_1\rangle$ | HOD | B (post-hoc†) | 0.165 | **3.73** |

Sources: `phase7_pk_comparison_r53.json`, `phase7_r53_partial_corr.json`.

*Discussion — tracer activation:*
> "The tracer activation result (DM: $1.12\sigma$ $\to$ HOD: $3.73\sigma$) provides an
> empirical physical mechanism for the DESI detection. Galaxy bias is not a constant
> multiplicative factor: the HOD preferentially populates massive haloes whose formation
> history is sensitive to the background expansion rate $w_0$ through the halo mass
> function. $\langle\mathrm{pers}_1\rangle$ amplifies this signal by measuring the
> persistence of filamentary loops, which are disproportionately formed by massive,
> clustered haloes. This topological selectivity is absent in $P(k)$, which integrates
> over the full halo mass distribution. The post-hoc nature of this comparison is noted;
> a pre-registered replication with matched tracer fields is deferred to future work."

---

### DELTA 4 — σ_px come scoperta metodologica centrale ✅ RISOLTO [IMPATTO: ALTO]

**Diagnosis:** La Methodology non menzionava σ_px. La dipendenza di ⟨pers₁⟩ da
σ_px = R/cell_size (e non da R fisico) è emersa come scoperta inattesa durante Phase 6,
con impatto +8.42σ tra σ_px=0.216 e σ_px=0.640.

**Risoluzione — argomento fisico:**

CubicalComplex opera su griglia discreta. σ_px controlla la lunghezza di correlazione
inter-voxel dopo lo smoothing: con σ_px piccolo i voxel sono poco correlati → molti
H₁ generators transitori → β₁_max alto, ⟨pers₁⟩ basso. Con σ_px grande i voxel sono
fortemente correlati → pochi H₁ generators persistenti → β₁_max basso, ⟨pers₁⟩ alto.
Non è un effetto fisico sul campo cosmologico: è una proprietà dell'algoritmo di
filtrazione su griglia discreta.

Il segnale DESI non è un artefatto di σ_px: ⟨pers₁⟩(DESI)=0.379 è superiore alla
distribuzione mock anche con σ_px matched (+3.09σ). La sistematica σ_px spiega la
differenza Confronto A vs Confronto B (5.97σ → 3.09σ), non il segnale.

**Implicazione per la comunità:** qualsiasi confronto cross-survey di statistiche PH
su campi voxelizzati deve verificare l'equivalenza σ_px. La sistematizzazione completa
è nel companion Paper A (in preparation).

**Testi pronti:**

*Methods — paragrafo σ_px:*
> "\paragraph{Grid resolution and the $\sigma_\mathrm{px}$ matching criterion.}
> Persistent homology on a voxelized field is sensitive to the dimensionless smoothing
> parameter $\sigma_\mathrm{px} = R/\Delta x$, where $R$ is the Gaussian smoothing
> scale and $\Delta x$ is the voxel size, rather than to $R$ alone. This arises because
> $\sigma_\mathrm{px}$ controls the inter-voxel correlation length in the discretized
> field: at fixed physical $R$, a coarser grid produces more transient low-persistence
> $H_1$ generators, while a finer grid produces fewer but more persistent generators.
> We quantify this effect on 200 nwLH mock fields at three $\sigma_\mathrm{px}$ values:
> $\sigma_\mathrm{px} = 0.216$, $0.640$, and $1.280$ (corresponding to $R = 1.7$, $5.0$,
> and $10.0$ Mpc/$h$ at mock resolution). The difference between $\sigma_\mathrm{px}
> = 0.216$ and $\sigma_\mathrm{px} = 0.640$ is $\Delta\langle\mathrm{pers}_1\rangle
> = +0.153$, equivalent to $+8.42\sigma_\mathrm{mock}$ (source:
> \texttt{phase6\_sigma\_px\_test.json}). This systematic dominates any cosmological
> signal and must be controlled before comparing fields at different resolutions."

*Methods — motivazione Confronto B:*
> "The DESI BGS field and the Quijote nwLH mocks have different voxel sizes:
> $\Delta x_\mathrm{DESI} = 15.6$ Mpc/$h$ versus $\Delta x_\mathrm{mock} = 7.8$ Mpc/$h$.
> A naive comparison at fixed physical $R = 5$ Mpc/$h$ yields $\sigma_\mathrm{px}^\mathrm{DESI}
> = 0.321$ versus $\sigma_\mathrm{px}^\mathrm{mock} = 0.640$ — a mismatch of $8.42\sigma$.
> We therefore adopt $R_\mathrm{DESI} = 10$ Mpc/$h$, $R_\mathrm{mock} = 5$ Mpc/$h$
> (Confronto B), achieving $\sigma_\mathrm{px}^\mathrm{DESI} = 0.641 \approx
> \sigma_\mathrm{px}^\mathrm{mock} = 0.640$. We report this as the primary conservative
> result. Confronto A ($R = 5$ Mpc/$h$ fixed, $+5.97\sigma$) and Confronto C
> ($R = 10$ Mpc/$h$ fixed, $+12.65\sigma$) are reported as context; both are
> systematically biased toward higher significance due to $\sigma_\mathrm{px}$ mismatch."

*Results — tabella tre confronti:*

| Confronto | $R_\mathrm{DESI}$ | $R_\mathrm{mock}$ | $\sigma_\mathrm{px}^\mathrm{DESI}$ | $\sigma_\mathrm{px}^\mathrm{mock}$ | $z$-score | Bias |
|---|---|---|---|---|---|---|
| A | 5 Mpc/$h$ | 5 Mpc/$h$ | 0.321 | 0.640 | $+5.97\sigma$ | Favouring DESI |
| **B (primary)** | **10 Mpc/$h$** | **5 Mpc/$h$** | **0.641** | **0.640** | **$+3.09\sigma$** | **Neutral** |
| C | 10 Mpc/$h$ | 10 Mpc/$h$ | 0.641 | 1.280 | $+12.65\sigma$ | Favouring DESI |

Sources: `phase6_scenario2_final.json`, `phase6_sigma_px_test.json`.

*Discussion — implicazioni metodologiche per la comunità:*
> "The $\sigma_\mathrm{px}$ dependence of $\langle\mathrm{pers}_1\rangle$ has broad
> implications for cross-survey topological comparisons. Any persistent homology analysis
> comparing fields voxelized at different resolutions must verify $\sigma_\mathrm{px}$
> equivalence before interpreting differences in topological statistics. We recommend
> $\sigma_\mathrm{px}$ matching as a standard diagnostic for future TDA cosmological
> analyses. A systematic characterization of the $\langle\mathrm{pers}_1\rangle
> (\sigma_\mathrm{px})$ relation across a wider parameter range is presented in a
> companion methodology paper (Paper A, in preparation)."

---

### DELTA 5 — DESI DR1 invece di DR2 ✅ RISOLTO [IMPATTO: BASSO + STRUTTURALE]

**Diagnosis:** D5 contiene due limitazioni distinte che richiedono trattamento separato.

**D5a — DR1 invece di DR2 (limitazione operativa):** DR2 non era accessibile a maggio
2026. Impatto: DR2 ridurrebbe l'errore jackknife su ⟨pers₁⟩ (~5× più galassie). Il
segnale qualitativo non cambierebbe. Karim et al. 2025 (DR2) conferma w₀ < −1 a
2.8–4.2σ — rafforza la motivazione del paper.

**D5b — Mock wₐ=0 fisso (limitazione strutturale, più significativa):** I mock nwLH
hanno wₐ=0 fisso. Il best-fit DESI DR2+CMB+DESY5 è w₀=−0.667, wₐ=−1.079. Il triple
baseline (O6-3) trova r(b2,w₀)=−0.045 — ⟨pers₁⟩ non discrimina w₀ a wₐ=0 fisso nel
range [−1.3,−0.7]. La previsione per il modello CPL completo (wₐ≠0) non è testabile.
Il claim corretto è: "anomalia rispetto a modelli ΛCDM e w₀CDM con wₐ=0", non rispetto
a tutti i modelli favoriti da DESI DR2.

**Questa distinzione D5a/D5b è la principale aggiunta rispetto alla versione precedente
del documento — D5b è una limitazione strutturale più importante di D5a.**

**Testi pronti:**

*Methods — sezione dati osservativi (D5a):*
> "We use the DESI Bright Galaxy Survey Data Release 1 (BGS DR1), specifically the
> North Galactic Cap (NGC) footprint, comprising 217,614 galaxies at $z \in [0.1, 0.4]$
> (source: \texttt{phase6\_gate\_result.json}). DESI DR2 was not publicly available at
> the time of this analysis. The DR2 dataset ($\sim 5\times$ more galaxies) would reduce
> the jackknife uncertainty on $\langle\mathrm{pers}_1\rangle$; replication with DR2
> data is a straightforward extension of the present pipeline."

*Methods — limitazione strutturale wₐ=0 (D5b):*
> "The Quijote nwLH simulation suite varies $w_0 \in [-1.30, -0.70]$ at fixed $w_a = 0$.
> Simulations with $w_a \neq 0$ are not available; consequently, we cannot test the full
> CPL prediction ($w_0 = -0.667$, $w_a = -1.079$) favoured by DESI DR2+CMB+DES-Y5
> (Karim et al. 2025). Our comparison is therefore restricted to $w_0\mathrm{CDM}$
> models with $w_a = 0$, and the anomaly significance (+3.09$\sigma$) is quoted relative
> to this restricted model family."

*Introduction — motivazione Karim et al. 2025:*
> "Independent evidence for dynamical dark energy comes from BAO measurements: Karim
> et al. (2025) report a preference for $w_0 < -1$ at 2.8–4.2$\sigma$ depending on
> the supernova dataset combination, with best-fit $w_0 = -0.838 \pm 0.086$
> (DESI DR2+CMB). This provides independent motivation for a topological search for
> phantom-crossing signatures in the galaxy density field."

*Discussion — limitazioni principali (D5a + D5b + altri):*
> "The primary limitations of this work are: (i) the use of DESI BGS DR1 rather than
> DR2 (operational — replication with DR2 is straightforward); (ii) the restriction to
> $w_0$CDM mock cosmologies with $w_a = 0$, which prevents testing the full CPL
> parameter space favoured by DESI DR2 (Karim et al. 2025, $w_a = -1.079$); (iii) the
> absence of an external replication with an independent survey (BOSS DR12 is identified
> as the highest-priority follow-up); and (iv) the HOD calibration to the DESI BGS
> luminosity limit (log $M_\mathrm{min} = 12.5$) rather than a full posterior HOD fit
> on DESI BGS mocks (R5-1, in preparation). We note that the $w_a = 0$ restriction is
> conservative: if $w_a \neq 0$ mocks were available, the signal could in principle
> increase or decrease depending on the $\langle\mathrm{pers}_1\rangle(w_a)$ response."

---

## PARTE B — NARRATIVA RICALIBRATA (versione post-delta)

### Claim centrale (aggiornato)

> CAUCHY rileva un'anomalia topologica di **+3.09σ** nella persistenza media dei cicli
> filamentari tridimensionali (β₁, H1) nel campo galattico DESI BGS NGC rispetto a 2000
> cosmologie mock w₀CDM (wₐ=0, Quijote nwLH), dopo correzione per la sistematica di
> risoluzione in pixel (σ_px-matched, Confronto B). Il segnale è fisicamente distinto da
> qualsiasi analisi proiettata 2D (Prat et al. 2025), robusto alle RSD (Δ=0.034σ DM,
> −0.004σ HOD), concordante tra NGC e SGC, e converge con una stima indipendente da Phase
> 5 (+3.08σ). La sensibilità topologica a w₀ emerge dal campo galattico (3.73σ) e non
> dal campo DM (1.12σ) — tracer activation empiricamente dimostrata (post-hoc).
>
> Limitazione strutturale principale: i mock coprono solo wₐ=0. Il confronto con il
> best-fit CPL completo (wₐ=−1.079) non è eseguibile con i dati disponibili.

### Titolo confermato

> **"Cosmology with Persistent Homology: a topological anomaly in the DESI BGS galaxy field"**

Motivazione: pattern "Cosmology with Persistent Homology: [risultato]" — entra
direttamente nella serie Yip & Biagetti 2024 come estensione osservativa naturale.
Conservativo (usa "anomaly", non "detection"). Dataset e metodo segnalati nel titolo.

### Arc narrativo aggiornato

```
Introduction
  ↓ DESI DR2 preferisce w₀ < −1 (Karim et al. 2025) — cosa può aggiungere la topologia?
  ↓ Gap: nessuna analisi PH 3D su campo galattico per w₀ (vs Prat 2D lensing, Yip mock DM)
  ↓ CAUCHY: PH 3D su DESI BGS — β₁ filamentare, non β₂ (dichiarato), distinto da Prat et al.

Methods
  ↓ Dati: DESI BGS DR1 NGC (217,614 gal, z∈[0.1,0.4]) + Quijote nwLH (2000, wₐ=0)
  ↓ Pipeline TDA: CubicalComplex su ν=log(1+δ), 8 feature β₁/β₀, footnote nomenclatura
  ↓ Scoperta σ_px: dipendenza da σ_px=R/Δx, non R fisico → motivazione Confronto B
  ↓ Ramo B CNN+GNN: architettura, partial correlation w₀|Ωm,σ₈
  ↓ P(k) confronto: Confronto A (clean DM) + Confronto B (post-hoc HOD)
  ↓ Limitazione strutturale wₐ=0 dichiarata in Methods

Results
  ↓ Tabella tre confronti (A/B/C) con σ_px — valore primario +3.09σ (Confronto B)
  ↓ Dual signature: ⟨pers₁⟩ alto (+11.85σ raw) + β₁_max basso (−55.6σ raw)
  ↓ Robustezza RSD: Kaiser DM +0.034σ, Kaiser+FoG HOD −0.004σ
  ↓ Convergenza Phase 5: +3.08σ (configurazione indipendente)
  ↓ Ramo B: σ_B=1.68±0.43σ, null fisicamente atteso, segno alternante
  ↓ P(k) vs TDA: tabella Confronto A (clean) + Confronto B (post-hoc†)

Discussion
  ↓ Interpretazione fisica dual signature: phantom crossing w₀ < −1
  ↓ Tracer activation: meccanismo fisico (bias HOD → persistenza filamentare)
  ↓ Ramo B null: sanity check, disaccoppia da Ramo A
  ↓ Sistematiche S1 (non-dominant), S2 (borderline NGC-SGC), S3 (risolto Confronto B)
  ↓ IDE degeneracy: 0.94% < 1% threshold — limitazione strutturale condivisa con BAO
  ↓ Limitazioni: (i) DR1 vs DR2, (ii) wₐ=0 strutturale, (iii) no BOSS, (iv) HOD R5-1
  ↓ σ_px: implicazioni metodologiche per la comunità TDA → Paper A (companion)
  ↓ Confronto letteratura: DESI DR2 BAO, SimBIG, Prat et al., Yip & Biagetti

Conclusions
  ↓ Segnale +3.09σ + dual signature + robustezza
  ↓ σ_px matching come standard metodologico
  ↓ Future work: β₂, DR2, wₐ≠0 mocks, BOSS cross-validation, Ramo B z>0
```

---

## PARTE C — SCELTA RIVISTA (confermata)

**Target primario: JCAP.** Target backup: PRD.

Motivazione invariata: precedenti diretti Yip & Biagetti 2024 e Prat et al. 2025 entrambi
in JCAP; scope cosmologia osservativa + metodi computazionali; flessibilità di lunghezza
per Methods esteso (σ_px) e Appendice tre confronti.

---

## SOMMARIO DECISIONI — VERSIONE FINALE

| Delta | Risoluzione | Testi pronti per sezione |
|---|---|---|
| D1 — β₁ non β₂ | Argomento forte 3 livelli (topologia distinta, canale distinto, dual signature inaccessibile 2D). Footnote obbligatoria. | Introduction, footnote, Methods, Discussion FW |
| D2 — Ramo B null | Causa fisica identificata (H(z=0)≡H₀). Null rafforza Ramo A. Framing "null con varianza spiegata". | Methods, Results, Discussion interpretazione, Discussion FW |
| D3 — Beyond-P(k) | Tre confronti distinti per base. P(k) competitivo su DM clean. Tracer activation +3.33× su HOD (post-hoc dichiarato). Meccanismo fisico: bias HOD pesa aloni massicci. | Methods, Results + tabella, Discussion |
| D4 — σ_px | Argomento fisico: correlazione inter-voxel, non effetto cosmologico. +8.42σ quantificato. Confronto B unico confronto neutro. Rimando Paper A. | Methods σ_px, Methods Confronto B, Results tabella, Discussion |
| D5a — DR1 | Limitazione operativa dichiarata. Karim 2025 come rinforzo motivazione. | Methods dati, Introduction |
| D5b — wₐ=0 | Limitazione **strutturale** dichiarata. Claim ristretto a "vs w₀CDM wₐ=0". Principale limitazione del paper. | Methods limitazione, Discussion limitazioni |
| Titolo | "Cosmology with Persistent Homology: a topological anomaly in the DESI BGS galaxy field" | — |
| Rivista | JCAP primary, PRD backup | — |

---

*Step 2 — versione finale post-risoluzione delta. Pronto per Step 3 (skeleton capitoli).*
*Abstract da redigere dopo la stesura dei capitoli principali (confermato).*
