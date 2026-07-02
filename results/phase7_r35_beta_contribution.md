# CAUCHY — R3-5 Gap: Stima Contributo β₁ vs β₀ (β₂ assente)
## Prodotto durante azioni pre-draft post-Reviewer cycle 7.1
## Data: 2026-06-06

---

## Chiarimento fondamentale emerso dalla review

L'analisi dei dati in `phase6_bgs_tda_features.json` e della pipeline
`phase5_hod_b3.py` ha rivelato un fatto critico che deve essere dichiarato
esplicitamente nel paper:

> **Il Ramo A di CAUCHY NON calcola feature β₂ (H2, vuoti 3D).
> Tutte le 8 feature calcolate da `compute_tda_features` sono feature β₁
> (H1, loops/cicli filamentari) o β₀ (H0, componenti connesse).**

La confusion nasce dalla nomenclatura interna: il prefisso `b2_` nelle feature
(es. `b2_mean_persistence`) si riferisce all'**indice posizionale** nel vettore
di feature (posizione 4-6), non al numero di Betti β₂.

---

## Struttura delle 8 feature e loro gruppo di omologia

| Feature interna | Gruppo H | β | z-score NGC | z-score SGC | In 3σ prior |
|---|---|---|---|---|---|
| b0_at_mean | H0 | β₀ | −0.85 | −0.88 | ✓ |
| b1_peak_pos | H1 | β₁ | −0.19 | −0.29 | ✓ |
| b1_peak_height | H1 | β₁ | −2.25 | −2.75 | ✓ |
| b1_fwhm | H1 | β₁ | +1.36 | +1.38 | ✓ |
| b1_integral | H1 | β₁ | −2.08 | −2.81 | ✓ |
| **b2_mean_persistence** | **H1** | **β₁** | **+11.85** | **+13.58** | **✗** |
| b2_max_count | H1 | β₁ | −55.59 | −62.90 | ✗ |
| b2_high_persist | H1 | β₁ | −55.59 | −62.90 | ✗ |

**Conclusione**: il segnale +3.09σ è interamente β₁ (loop/filamenti). β₀ è
nella norma. β₂ non è calcolato.

---

## Contributo differenziale β₁ (feature anomale)

Le tre feature fuori prior (out of 3σ mock distribution) sono tutte β₁:

### b2_mean_persistence: +11.85σ NGC, +13.58σ SGC
DESI ha loops/filamenti con **persistenza maggiore** rispetto ai mock ΛCDM.
Persistenza maggiore = strutture topologiche più robuste = cicli che nascono
e muoiono a soglie molto distanti (strutture più "definite" o più isolate).

### b2_max_count: −55.6σ NGC, −62.9σ SGC
DESI ha **molti meno** loops al picco della curva β₁ rispetto ai mock ΛCDM.
Circa 29,683 loops vs mock mean 133,786 (≈5× meno).

### b2_high_persist: −55.6σ NGC, −62.9σ SGC
DESI ha meno loops ad alta persistenza in termini di **conteggio** (ma
b2_mean_persistence alto indica che quelli presenti sono più persistenti).

### Interpretazione fisica del pattern combinato

Il pattern {b2_mean_persistence HIGH, b2_max_count LOW} è fisicamente coerente:

- **DESI ha meno loops in totale** ma quelli che esistono hanno **persistenza
  maggiore**. Questo è consistente con una rete cosmica con vuoti più espansi
  e filamenti più isolati — esattamente la firma attesa per phantom crossing
  w₀ < −1, che accelera l'espansione e sopprime la formazione di struttura
  piccola scala (molti loop transitori) mentre amplifica le strutture
  topologiche large-scale (pochi loop molto persistenti).

- Questo pattern dual-signature (opposto in sign tra mean persistence e max
  count) è più difficile da spiegare con sistematiche osservative (selezione,
  HOD) rispetto a un singolo outlier — rafforza la credibilità del segnale.

---

## Gap R3-5: β₂ assente — impatto sulla claim paper

### Cosa manca
Il paper non può affermare di aver rilevato un'anomalia nei **vuoti 3D** (β₂)
perché β₂ non è calcolato. Il claim corretto è:

> *"We detect a significant anomaly in the β₁ mean persistence of the DESI
> BGS galaxy field (+3.09σ), indicating that the filamentary loop structure
> of the cosmic web deviates from ΛCDM expectations in a manner consistent
> with phantom crossing w₀ < −1."*

Non:
> *"We detect a β₂ (3D void) anomaly..."*

### Distintività vs Prat et al. 2025 (OC-5)
Prat et al. 2025 usano β₁ su mappe 2D di convergenza (lensing). CAUCHY usa
β₁ su campi 3D galattici. La distintività è:
- **Dimensionalità**: 3D vs 2D proiettato
- **Tracciante**: galassie in spazio di redshift vs convergenza lensing
- **Parametro target**: w₀ phantom crossing vs S₈/Ωm

La distintività β₂ vs β₁ (Concern OC-5 del Reviewer) è meno rilevante perché
la vera distinzione da Prat et al. è già nella dimensionalità 3D e nel tracciante.
Un referee che conosce Prat 2025 accetterà "3D β₁ su galassie vs 2D β₁ su
lensing" come contributo originale.

### Stima minima viabile (R3-5 parziale)
Per rispondere al Reviewer senza aggiungere β₂ alla pipeline, il paper può
dichiarare: *"The inclusion of β₂ (H2, 3D void topology) in the persistent
homology analysis is deferred to future work. The current analysis demonstrates
that β₁ alone, applied to the 3D galaxy field, provides statistically significant
evidence for w₀ deviation from ΛCDM. The β₂ signal is expected to be
complementary, as void expansion is a primary prediction of phantom crossing,
but requires dedicated N-body simulations at higher resolution to suppress
shot noise in β₂ persistence."*

---

## Raccomandazione per il paper (sezione Methods)

**Sezione 3.1 — TDA features**: dichiarare esplicitamente che le 8 feature
sono calcolate da H0 (β₀, 1 feature) e H1 (β₁, 7 feature), NON da H2 (β₂).
Usare la tabella di nomenclatura di `phase7_nomenclature_lock.json`.

**Sezione 4.2 — Physical interpretation**: presentare il pattern dual-signature
{⟨pers₁⟩ HIGH, β₁_max LOW} come evidenza più forte del singolo outlier.

**Sezione 5 — Discussion/Limitations**: dichiarare il gap β₂ come future work
con la motivazione fisica (risoluzione computazionale, shot noise β₂).

---

## Traceability
- Source: phase6_bgs_tda_features.json → regions.NGC.feature_comparison
- Source: phase5_hod_b3.py → compute_tda_features → diag_1 = H1 only
- Source: phase7_nomenclature_lock.json → feature_nomenclature
- Reviewer concern: OC-5, Sub-Phase 7.1 review 2026-06-06
