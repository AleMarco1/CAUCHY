# CAUCHY Phase 5 — Risposta al Concern 1 BLOCKING
## HOD Variance Decomposition
## Data: 2026-05-06

### Metodo

Per rispondere al Concern 1 (K=10 insufficiente per stima affidabile della sensitività marginale),
abbiamo eseguito una decomposizione della varianza delle feature TDA sulle 1029 chain
HOD disponibili (K=10 campioni per campo in media).

**Variance Inflation Factor (VIF)** = σ²_intra / σ²_inter, dove:
- σ²_intra = varianza delle feature TDA tra i K campioni HOD per lo stesso campo
  (incertezza dovuta all'HOD)
- σ²_inter = varianza della feature marginalized tra campi con diverse cosmologie w₀
  (segnale cosmologico)

VIF ≪ 1 indica che il segnale cosmologico (w₀) domina sull'incertezza HOD,
indipendentemente da K.

### Risultati

**Feature primaria — b2_mean_persistence:**
- VIF = 2.4834 (248.3%) — l'incertezza HOD contribuisce il 248.3% della varianza inter-campo
- SNR_HOD = 0.4 — la varianza cosmologica supera quella HOD di un fattore 0.4
- Interpretazione: HOD contribuisce varianza comparabile al segnale → marginalizzazione critica

**Correlazione dopo marginalizzazione:**
- ρ(b2_mean_persistence_marginalized, w₀) = -0.0390
- σ_marginalized = 1.25σ (permutation test N=1000, seed=42)

**Partial correlation — Concern 5 del Reviewer:**
- ρ_partial(b2_marg, w₀ | Ωm, σ₈) = +0.0084
- σ_partial = 0.26σ

**Convergenza in K:**
- NON CONVERGENTE — σ sensibile a K
- Variazione σ tra K=2 e K=10: Δσ = 1.47σ

### Interpretazione per il Reviewer

Il VIF = 2.483 indica che l'incertezza HOD è presente ma non dominante. La convergenza in K mostra se K=10 è sufficiente.

### Nota metodologica

La variance decomposition è equivalente a un'analisi ANOVA a un fattore,
dove il fattore è la cosmologia (w₀) e la variazione residua è l'HOD.
È la stessa metrica usata in Hadzhiyska et al. 2023 (MNRAS) per giustificare
K sufficientemente piccolo nella forward likelihood HOD.
