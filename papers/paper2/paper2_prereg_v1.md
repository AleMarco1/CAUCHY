# CAUCHY Paper 2 — Pre-registered analysis protocol

**Sensitivity of H1 generator counts in DESI BGS to the fiducial cosmology (Alcock–Paczyński response)**

Alessandro — independent researcher, Verona, Italy — ORCID 0009-0002-3682-1815

**Version 1.0 — deposited 27 August 2026**
Pipeline archive: Zenodo concept DOI [10.5281/zenodo.21128856](https://doi.org/10.5281/zenodo.21128856)

---

## 0. What this document commits to, and what it does not

This protocol pre-registers **Phase 3 onward**: the Component A measurement of how the H1 generator
deficit responds to the choice of fiducial cosmology, together with Components B, C and D as scoped
in §8.

It does **not** pre-register Phases 0–2. Those are already executed, and §2 reports them in full,
including two predictions that were declared in advance and **falsified**. They are reported here
because the Phase 3 design depends on them, not because they are being presented as pre-registered.

**§1 is the mandatory transparency section.** Everything already in hand at the date of deposit is
listed there. A reader who wants to know what was still genuinely unknown when this document was
filed should read §1 first and treat the rest accordingly.

### Non-negotiable clauses

1. **No threshold in §5 may be renegotiated once a Phase 3 run has started.** If a result falls in a
   zone this rule does not cover, it is reported as such and the rule is declared incomplete. It is
   not extended after the fact.
2. **Null and dissolving results are publishable outcomes.** Outcome E1 (§5.3) — the anomaly shows no
   measurable AP response — is a reportable result, not a failure.
3. **Falsified predictions stay falsified.** They are recorded with the reason the threshold was
   mis-set. They are not re-derived to fit the observation.
4. **Amendments are append-only.** They go in `src/paper2_v1_amendments.jsonl`; the frozen reference
   file is never edited. Any amendment after this deposit is recorded with a UTC timestamp and cited
   in the manuscript.

---

## 1. Results already in hand at the date of deposit

### 1.1 Component D — fully executed on ensemble v1

Component D (the response of `N_H1` to the seven Quijote cosmological parameters) was **completed
before this deposit**. Predictions P1–P5 and Q1–Q5 were written into the analysis scripts before the
results were computed, which respects the spirit of pre-registration, but the deposit postdates the
execution. The findings:

- **D2, partial correlations at n = 2000.** `n_s` leads, partial *r* = **+0.3976** (NGC) and
  **+0.4163** (SGC), i.e. 7.4σ and 8.4σ above the declared threshold of 0.25. `w₀` gives +0.0549 and
  +0.0474, **not significant after Bonferroni correction** (*p* = 0.0133 / 0.0319 against
  0.05/7 = 0.0071). **Prediction P1 is FALSIFIED by 0.005**: the threshold was mis-calibrated.
- **D4, sensitivity ceiling.** The implied 1σ constraint on `w₀` is **±3.13** (NGC) and **±5.71**
  (SGC), against ±0.06 from DESI BAO — worse by factors of 52 and 95. H1 counts are not a
  competitive cosmological probe, and this paper does not claim otherwise.
- **D5, R² ceiling.** Observed 0.2606 / 0.2773 against a ceiling of 0.698 from the variance
  decomposition: **62.7% / 60.3% of the cosmological variance is unexplained by the seven
  parameters.**
- **D6, non-linearity and P(k). Q1, Q2, Q3 and Q4 are all FALSIFIED.** Quadratic terms add +0.0512
  and interactions +0.0546 (R²_cv 0.2554 → 0.3066 → 0.3612): the gap narrows from 63.4% to 48.3% but
  does not close. P(k) from cache explains 0.3263, closing 21.5% of the gap.
  **Two reservations, both declared:** the model sequence **does not converge**, so 48.3% is an upper
  bound and not a measurement; and the **provenance of `pk_matrix` is not established** (110 bins, no
  k vector), so the P(k) test may be measuring the wrong spectrum. Tests B and C of D6 are not
  interpretable until that is resolved.
- **The most robust D6 result, which holds regardless.** The first principal component of log P(k)
  explains **92.4%** of the spectral variance and has R²_cv = **−0.0016** against `N_H1`. The
  dominant spectral mode — essentially the amplitude — **predicts nothing.** This is the most direct
  empirical confirmation of monotone invariance (Proposition 1).

D2 and D6 will be repeated on ensemble v2 with predictions P1–P5 and Q1–Q5 unchanged; v1 results
remain in the record labelled `ensemble: v1`.

### 1.2 Phases 0–2 — executed

See §2. Two predictions declared in advance were falsified (2.2a and the padding-ladder dispersion).

### 1.3 A correction owed to Paper 1, discovered during this work

The survey mask is built as `field_r > 0.01 * field_r.mean()` (mean over the **full** 128³ cube;
producer `phase6_bgs_voxelize.py:182-183`). M26 and Paper 1 describe this cut as "P10 of the random
density". **It is not a percentile at all**: it cuts NGC at P3.914 (307 805 of 320 342 non-zero
voxels) and SGC at P3.403 (172 225 of 178 293), i.e. a different percentile in each hemisphere. The
P10 mask does not reproduce the frozen one (288 307 voxels, Jaccard 0.9367). Further, across
P5 → P10 the z-score of the **skewness inverts sign** (−4.58 → +7.69), while mean, standard
deviation and kurtosis keep their sign over P5–P15. The mask actually used sits on the P5 side, so
the published Table 3 value is on the correct side of its own mask; the label and the stability claim
are what require correction. This is being handled in the Paper 1 revision (referee point R2.6) and
is recorded here because it was found by this work.

### 1.4 What was genuinely unknown at deposit

The entire Component A measurement: the response of `N_H1` and of the deficit *D* to the nine grid
points of §4; the symmetry of that response; the completeness of the (α_iso, F_AP) family against the
four corners; and consequently which of the four outcomes E1–E4 obtains.

---

## 2. Frozen inputs

### 2.1 Reference set

`src/paper2_v1_reference.json`, sha256
`332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d` — **immutable**. Ensemble v1 is
5 tiers, 34 836 files, 26.771 GiB, digests reproduced. Every reported number carries a v1 or v2
label; the unqualified phrase "fiducial ensemble" is retired.

### 2.2 The anomaly under study

| | file → field | *n* | mean | sd (ddof = 1) | DESI | deficit *D* | rank |
|---|---|---|---|---|---|---|---|
| NGC | `per_mock_NGC_R5.jsonl` → `base.N_H1` | 2000 | 35 436.686 | 312.9891651683112 | **28 256** | 7180.7 (20.26%) | 1/2001 |
| SGC | `per_mock_SGC_R5.jsonl` → `base.N_H1` | 2000 | 18 712.9675 | 197.7873817207103 | **15 122** | 3591.0 (19.19%) | 1/2001 |

The M26 baselines (35 467.15 / 18 693.595) are **superseded**: they differ by ∓0.10σ with opposite
signs in the two hemispheres, the signature of a path-collision defect in which mock indices 0–199
were overwritten by a run with a different HOD. Paper 1 values are operative.

### 2.3 Fiducial geometry

| | NGC | SGC |
|---|---|---|
| `box_size_mpc_h` | 1997.3629167166155 | 1904.4501607158168 |
| `cell_size_mpc_h` | 15.604397786848558 | 14.878516880592318 |
| `sigma_px` | 0.32042249039652254 | 0.3360550006514459 |
| `n_valid_voxels` | 307 805 | 172 225 |
| `N_data` / `N_rand` | 217 614 / 13 248 857 | 82 429 / 5 432 939 |
| `mask_threshold` | 0.020012933760881424 | 0.008570596575737 |
| occupancy | 0.7070 gal/voxel | 0.4786 |

---

## 3. Phase 2 gates — executed, reported here

All Phase 2 gates below are data-side only and cost 10–12 s per run. Every one was run with a
provenance guard (`paper2_gate21.py snapshot`) over 11 protected files; all digests were unchanged
before and after.

| gate | prediction declared in advance | result | verdict |
|---|---|---|---|
| **2.1** closure vs Paper 1 | 28 256 / 15 122 exactly | Δ = 0 both | **confirmed** |
| **2.1-M** mask reproducible from randoms | array identity | `np.array_equal` true both | **confirmed** |
| **2.1-D₂** Phase 2 runner closes at fiducial | Δ = 0 | Δ = 0 both | **confirmed** |
| **2.2b** α = 1.05, `pad = 5α` | Δ = 0 exactly | Δ = 0 both | **confirmed** |
| **2.2a** α = 1.05, additive pad | \|Δ\| ≤ 5 generators | **+34 / +6** | **FALSIFIED** |
| **2.3** same dilation, R fixed at 5 | Δ > 0 | +391 / +254 | **confirmed** |
| **2.4** monotonicity of f(r) | strictly increasing | 12/12 | **confirmed** |
| **2.6** padding ladder | dispersion ≤ 0.25σ | **1.00σ / 1.36σ** | **FALSIFIED** |
| **2.7** mask-threshold ladder, constant cube | slope compatible within 2σ | 1.11σ / 1.62σ | **confirmed** |

### 3.1 Why 2.2a was falsified, and why it is not repaired

The ≤ 5 threshold was justified by CIC continuity **at fixed mask**, and was written before gate
2.1-M made mask re-derivation mandatory. Additive padding leaves the box 0.5 h⁻¹Mpc shorter than the
proportional one, misaligning grid and galaxies by 0.031 voxel; the mask threshold is a hard cut, so
boundary voxels flip (307 805 → 308 021 and 172 225 → 172 364). The threshold was mis-set. It is
recorded as falsified.

An attribution diagnostic (mask deliberately frozen under a different geometry) separates two
channels: **mask boundary +11 / +18** — same sign in both hemispheres — and **residual at fixed mask
+23 / −12** — sign not fixed. The boundary does not expand, it **remixes**: 335 voxels in and 119 out
in NGC, 218 and 79 in SGC.

### 3.2 The isotropic channel, isolated by construction

Gates 2.3 and 2.2a share geometry and mask exactly; only `R_SMOOTH` differs. The difference **is** the
isotropic channel: **+357 (NGC)** and **+248 (SGC)**, i.e. +1.263% and +1.640% for a −4.74% change in
σ_px. Elasticity **−0.267 (NGC)** against **−0.346 (SGC)**: SGC is 30% more sensitive, consistent with
its lower occupancy and a more shot-noise-dominated field.

*Calibration note: α = 1.05 lies outside the physical range (|1−α| ≤ 0.0406). None of these numbers
is quoted as a signal sensitivity; they are gates, and are re-measured at the grid α values.*

### 3.3 `N_H1` tracks the survey voxel count

The padding ladder (nine pads, 5.0 → 9.0, grid displacement to 0.51 voxel) showed a **monotone drift**,
not jitter: `N_H1` falls together with `n_valid_voxels` (NGC −1.108% against −1.050%; SGC −1.779%
against −1.144%). The mask-threshold ladder at **constant cube** (cell fixed to zero excursion, voxels
moved 2.2%) separates voxel count from resolution:

| | slope d`N_H1`/d*V* | correlation | elasticity |
|---|---|---|---|
| NGC | **0.1009 ± 0.0016** | *r* = 0.9992 | **1.098 ± 0.017** |
| SGC | **0.0945 ± 0.0036** | *r* = 0.9950 | **1.074 ± 0.041** |

The regressor is the **voxel count**, not the resolution, and the response is mildly **super-linear**:
`N_H1` ∝ *V*^1.08. Voxels added at the boundary carry more loops than the average. The two
hemispheres agree (1.62σ).

**Limit of validity, declared.** Applying this slope to the padding-ladder data reduces the excursion
from 313 to 89 (NGC) and 269 to 83 (SGC), but a **residual trend against voxel count survives**
(−0.0112 ± 0.0016 and +0.0192 ± 0.0036, opposite signs). A second channel exists at variable cube —
almost certainly the cell — which the constant-cube ladder cannot see. **The voxel-count correction is
valid at fixed cell, not in general.**

### 3.4 Measurement floors

| regime | NGC | SGC | applies to |
|---|---|---|---|
| variable cube, after regression on voxels | 31.8 gen (0.102σ) | 21.5 gen (0.109σ) | not used in this design |
| **constant cube** | **10.1 gen (0.032σ)** | **12.8 gen (0.065σ)** | **the §4 grid** |

The constant-cube gauge holds *L*, Δ*x* and σ_px fixed by construction, so the floor entering
Component A is the lower one.

---

## 4. The measurement grid

Nine points, **constant-cube gauge**: *L*, Δ*x* and σ_px identical to fiducial at every point. This is
authorised by Proposition 2 — α_iso is gauge — and the tiling scale (1000 h⁻¹Mpc, external) consumes
that freedom by fixing the correct gauge.

**Line B**, *f*(*r*) = *A r^p* with *p* = *F*_AP in the pipeline convention (α_∥/α_⊥, the reciprocal of
the standard):

| | *p* (pipeline) | *F* standard ⊥/∥ | residual (h⁻¹Mpc) | vox NGC | vox SGC |
|---|---|---|---|---|---|
| B1 | 0.97104812 | 1.029815 | 8.8750 | 0.5687 | 0.5965 |
| B2 | 0.98538897 | 1.014828 | 4.4375 | 0.2844 | 0.2982 |
| **B3** | **1.00000000** | 1.000000 | **0** | 0 | 0 |
| B4 | 1.01488843 | 0.985330 | 4.4375 | 0.2844 | 0.2982 |
| B5 | 1.03006174 | 0.970816 | 8.8750 | 0.5687 | 0.5965 |

Residuals are equispaced in the **Chebyshev minimax gauge**. Least squares overestimates the
anisotropic signal by up to 26.4% and is not used.

**Corners**, *D*_C = *c* · *D*_C,fid · *g*(*z*), re-gauged: C1 (Ω_m 0.25, *w*₀ −1.2), C2 (0.25, −0.8),
C3 (0.35, −1.2), C4 (0.35, −0.8), with voxel residuals 0.5409, 0.1067, 0.1325, 0.3729 (NGC).

**Constant across the grid by construction:** tiling replicas (15 NGC, 10 SGC at all nine points),
σ_px (relative excursion 6 × 10⁻¹⁴), and the fraction of voxels with w̄ < 0.99. None of the three
enters the error budget as a systematic to subtract.

**Ω_m and w₀ label the deformation; they are not the model's cosmological state.** Once a `dc_tab` is
injected, OMM/OML no longer describe the mapping and must not be reported as a cosmology.

**Admissibility (item 1.2c):** all NGC points admitted (+3.9% margin against the practical limit); all
SGC points **admitted with caveat** (−6.9%), not excluded. The SGC caveat is exactly one EDT
quantisation level, so it is stated as "σ_px sits at the limit in SGC", never as "exceeds it by 6.9%".

---

## 5. Decision rule

### 5.1 What is measured

*D*(*g*) = ⟨`N_H1`⟩_mock(*g*) − `N_H1`^DESI(*g*).

The data side is **deterministic**: differences in `N_H1`^DESI between grid points are exact. All
noise is on the mock side.

**AP acts on both sides.** If data and mocks respond identically the response **cancels in *D***. The
quantity of interest is the **differential** response ∂*D*/∂*F*_AP, not ∂`N_H1`/∂*F*_AP, which can be
large — it is a real geometric effect — without *D* moving by a single generator. **Both are reported,
separately.** Conflating them is the easiest error available in this paper.

**Primary statistic:** `N_H1` at erosion ***k* = 1**, both hemispheres, with **empirical rank** in the
mock ensemble as the primary significance measure — not a parametric z-score. *k* = 0 reported in
parallel for continuity with v1 numbers.

### 5.2 Thresholds

| | symbol | value |
|---|---|---|
| paired mocks per point | *N* | **200** |
| per-realisation dispersion of Δ`N_H1` | σ_Δ | 250.5 |
| **detectability** | 3σ_Δ/√*N* | **53 generators** |
| **relevance, NGC** | 1.1 pp of deficit | **390 generators** |
| **relevance, SGC** | 1.1 pp of deficit | **206 generators** |
| physical range of *F*_AP | \|*F*−1\| | **0.027** |
| line B coverage | \|*F*−1\| | 0.0301 (11% margin) |

The relevance threshold is anchored to the largest already-characterised systematic, the mask-rule
ambiguity, worth ~1.1 percentage points of deficit. The "3σ_Δ ≈ 750" of an earlier revision was the
3σ for a single realisation rather than for the mean, conservative by √200 ≈ 14, and is withdrawn.

### 5.3 The four outcomes

Let Δ*D*_max be the excursion of *D* along line B, between B1 and B5.

| | condition | conclusion |
|---|---|---|
| **E1** | Δ*D*_max < 53 | **Upper limit.** Report the 3σ bound on ∂*D*/∂*F*_AP. Proposition 2 is the principal result; M26 limitation (ix) closes with a bound. |
| **E2** | 53 ≤ Δ*D*_max < 390 (206) | **Sub-dominant sensitivity measurement.** AP enters the budget as a minor term. (ix) closes with a measurement. |
| **E3** | Δ*D*_max ≥ 390 (206) | **First-order systematic.** The central deficit is re-quoted with a fiducial-cosmology uncertainty and M26 §5 is updated. |
| **E4** | E3 **and** extrapolation zeroes *D* within the physical range | **AP may explain the deficit.** To be verified by direct measurement at the required *F*, never by extrapolation. |

### 5.4 Required *F*_AP

The value that would zero the deficit under linear extrapolation of the measured response.

- **\|*F*_req − 1\| > 0.027 → AP cannot explain the deficit**, whatever the amplitude of the response.
  This is a clean falsification and is stated as such.
- **\|*F*_req − 1\| ≤ 0.027 →** the point at *F*_req is executed and **measured**.

### 5.5 Symmetry test (free, given a symmetric line)

Fit *D*(*F*) = *D*₀ + *a*(*F*−1) + *b*(*F*−1)² on the five B points.

- \|*a*\| > 3σ(*a*) and \|*b*\| < 3σ(*b*) → **odd** response: compression and radial stretching are not
  equivalent; the topology sees a **direction**.
- \|*b*\| > 3σ(*b*) and \|*a*\| < 3σ(*a*) → **even** response: the topology sees radial/transverse
  misalignment as a **degradation**, not a direction.
- both → both reported.

### 5.6 Completeness test on the corners

Predict *D*(*C_i*) from line B by interpolation in effective *F*, at the same 53-generator threshold.

- **\|*D*_obs − *D*_pred\| < 53 at all four** → the (α_iso, *F*_AP) family is sufficient; a closed
  two-variable response surface is reported.
- **fails at C1 and/or C4 but not C2 and C3** → the **third channel** is real. It has a declared
  signature: it must fail where the channel is large (0.082 voxel at C1, 0.047 at C4) and not where it
  is small (0.006 and 0.005).
- **fails everywhere, C2 and C3 included** → not the third channel. It is tiling or carving
  re-randomisation, and decomposition §6 must close it **before** any derivative is interpreted.

---

## 6. Error budget and corrections

Five contributions, of which one is new and measured in Phase 2:

| | contribution | treatment |
|---|---|---|
| (a) | σ_px convention | constant by gauge; not subtracted |
| (b) | *F*_AP anisotropy | the signal |
| (c) | carving re-randomisation at fixed geometry | measured with different seeds, subtracted in quadrature |
| (d) | tiling | already bounded: replica randomisation over 100 mocks shifts the mean by −13 generators (0.037% of a 7181 deficit), scatter ratio 0.97 |
| **(e)** | **survey voxel count** | **subtracted**, not added in quadrature: Δ`N_H1` − *s*·Δ*V* with *s* = 0.1009 (NGC), 0.0945 (SGC) |

Added in quadrature: the constant-cube floor, **10 generators (NGC), 13 (SGC)**, plus (c).

Correction (e) is valid **at fixed cell only** (§3.3). On the nine grid points the cell is fixed by
construction. For any point at non-constant cube, the second channel must be re-measured before
correcting.

---

## 7. Mandatory procedure

1. **Gate first.** Every script reproduces at least one frozen reference value before reporting any
   new measurement. Decision rules and predictions are declared before results are viewed.
2. **Geometry injection sequence** (all seven steps, each for a measured reason):
   `R_SMOOTH` assigned **before** `set_geometry` → `set_geometry(z_tab, dc_tab)` →
   `positions(region, "ran")` → `derive_box` → `set_geometry(box_min, box_size)` → **mask re-derived**
   from the randoms, never `np.load` → `build_field` → `compute_tda_features(..., masked=True)`.
3. **The mask is a shared node** read by ~30 scripts across M26, Paper 1 and its revisions. It is
   never regenerated in place; a re-derived mask is written under a new filename and compared in
   memory.
4. **Deformations are built as ratios** on the module's fiducial *D*_C table, never integrated from
   scratch, so that the module's c/H₀ constant cancels exactly (residual 1.06 × 10⁻⁴ voxel, 2700×
   below the smallest line-B signal).
5. **Provenance.** All numerical records are append-only JSONL with atomic fsync writes and frozen
   SHA-256 manifests. A snapshot of protected files is taken before and after every run.
6. **Empirical ranks over Gaussian z-scores** as the primary significance statistic.

---

## 8. Scope, and what this protocol does not cover

**Covered:** Component A (Phase 3), Component B (FKP-weighted ensemble v2, Phase 4), Component C
(erosion/FKP tension, factor ~24 unexplained), Component D repeated on v2.

**Not covered, and to be measured without a pre-registered rule:**
- carving re-randomisation at fixed geometry (gate 2.5, still open at deposit);
- the number of galaxies changing selection state per grid point;
- the second (cell) channel of §3.3, if a non-constant-cube point is ever required;
- the provenance of `pk_matrix`, which gates the interpretation of D6 tests B and C.

**Known open threads at deposit:** the R² model sequence in D6 does not converge, so "48.3%
unexplained by a polynomial" is an upper bound and not a measurement; `practical_limit_SGC` was never
computed (a Paper 1 observation, not a Paper 2 one); and the independent-volume fraction measured on
the grid (0.7111–0.7125) differs by 2% from the reference value (0.696), unattributed.

---

## 9. Amendment record

Amendments to the frozen reference live in `src/paper2_v1_amendments.jsonl`, append-only, each citing
the reference sha256 measured at write time. Ten records exist at deposit. Any amendment after this
date is listed in the manuscript with its UTC timestamp.

**Version history of this protocol**

| version | date | change |
|---|---|---|
| 1.0 | 2026-08-27 | initial deposit |
