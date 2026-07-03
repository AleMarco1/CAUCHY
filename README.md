# CAUCHY

**Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis**

A topological data analysis (TDA) pipeline for persistent homology on **observed**
galaxy fields. CAUCHY characterizes the discretization and survey-geometry
systematics that dominate naive PH comparisons between a bounded survey and
periodic-box mocks, provides a like-for-like cut-sky comparison framework, and
applies it to the DESI Bright Galaxy Survey (BGS DR1) against the 2000 Quijote
nwLH mock cosmologies.

This repository accompanies the paper:

> **Persistent homology on an observed galaxy field: discretization and
> survey-geometry systematics, a like-for-like framework, and a topological
> anomaly in DESI BGS**
> A. Marconi (2026), submitted to JCAP. arXiv:XXXX.XXXXX

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21158278.svg)](https://doi.org/10.5281/zenodo.21158278)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

Three-dimensional persistent homology had previously been applied to simulated
periodic boxes or 2D projected maps, not to an observed spectroscopic galaxy
field. Doing so, we find the exercise is dominated by two systematics that can
masquerade as physical anomalies:

1. **The σ_px systematic** — the mean H₁ persistence depends on the
   dimensionless smoothing parameter σ_px = R/Δx (kernel width in *voxel*
   units), not on the physical scale R alone: +8.42σ between σ_px = 0.216 and
   0.640 on matched mock fields. Cross-survey comparisons at fixed R are
   structurally biased.
2. **The boundary artefact** — embedding a masked survey (14.7% fill) in a
   zero-padded cube and running an unmasked filtration truncates the
   persistence diagram, manufacturing an anti-correlated "dual signature"
   (high mean persistence, suppressed loop count) that mimics a physical
   signal.

The repository implements the **like-for-like framework** that removes both:
cut-sky mocks carved by the DESI footprint and n(z), in redshift space,
density- and σ_px-matched, analysed with a masked filtration on both sides.

Applied to DESI BGS NGC, most of the apparent signal dissolves. One feature
survives every control: an **H₁ generator deficit** — the DESI field contains
fewer loops than **all 2000** like-for-like ΛCDM/w₀CDM mocks (empirical
p < 1/2000), robust to observational weighting, to an HOD refit to the measured
w_p(r_p), and to a density-dependent incompleteness surrogate. No
w₀ ∈ [−1.30, −0.70] reproduces it (extrapolation would require w₀ ≈ −294),
formally excluding w₀CDM (w_a = 0) as its origin. The deficit is reported as an
**open anomaly — explicitly not a dark-energy detection**.

---

## ⚠ Note on superseded results (v1)

Earlier versions of this repository (and the v1 Zenodo archive) implemented the
analysis of the original submission, whose headline results — a
⟨pers₁⟩ anomaly of +5.96σ to +29.9σ, the "dual topological signature", and a
phantom dark-energy interpretation — are **superseded and retracted**. The
+29.9σ figure in particular arose from post-hoc conditioning on a
cosmology-dependent variable and should not be used. The paper's Appendix D
documents the full methodological evolution; the v1 archive is retained for
transparency.

---

## Repository structure

```
cauchy/
├── README.md                     This file
├── LICENSE                       MIT license
├── environment.yml               Conda environment specification
├── requirements.txt              pip dependencies (alternative to conda)
├── paper/
│   └── paper C/
│       └── cauchy_paper_c_jcap.pdf   Submitted manuscript (Paper C)
├── src/                          Analysis pipeline
│   ├── phase8_cutsky_mocks.py        Like-for-like cut-sky construction (core)
│   ├── phase8_test2_masked.py        Masked filtration — MAIN RESULT (N=2000)
│   ├── phase8_field_diagnostic.py    Field-amplitude diagnostics
│   ├── phase8_weight_check.py        Observational-weighting robustness
│   ├── phase8_smoothness_check.py    Small-scale structure comparison
│   ├── phase8_weight_smoothness.py   Weights-vs-smoothness A/B resolution
│   ├── phase8_hod_fit.py             HOD fit to DESI wp(rp) + n̄ (TreeCorr)
│   ├── phase8_w0_exclusion.py        w0CDM (wa=0) exclusion analysis
│   ├── phase8_fiber_surrogate.py     Incompleteness (fiber-assignment) surrogate
│   └── phase*_*.py                   Phases 0–7: earlier pipeline stages,
│                                     retained for the documented evolution
│                                     (paper Appendix D)
├── results/                      Frozen numerical records (JSON)
│   ├── phase8_test2_masked.json      Main result (β₁ᵐᵃˣ deficit, N=2000)
│   ├── phase8_w0_exclusion.json      w0 exclusion
│   ├── phase8_hod_bestfit.json       HOD fit
│   ├── phase8_test2_hodfit.json      Deficit under the fitted HOD
│   ├── phase8_fiber_surrogate.json   Incompleteness surrogate
│   ├── phase8_cutsky_test1.json      Exact-replica diagnostic (Test 1)
│   └── phase*_*.json                 Phases 0–7 records
├── gate8_prior_v1_0.json         Pre-registered Phase-8 gate protocol
├── CHANGELOG.md                  Complete decision log
└── data/                         (not tracked — see Data section below)
```

---

## Installation

### Option A — conda (recommended)

```bash
git clone https://github.com/AleMarco1/CAUCHY.git
cd CAUCHY
conda env create -f environment.yml
conda activate cauchy
```

### Option B — pip

```bash
git clone https://github.com/AleMarco1/CAUCHY.git
cd CAUCHY
python -m venv venv
source venv/bin/activate       # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Key dependencies

| Package | Purpose |
|---|---|
| `gudhi` | Persistent homology (CubicalComplex) |
| `numpy`, `scipy` | Numerical core; periodic wp(r_p) pair counting |
| `astropy` | FITS catalogue I/O |
| `matplotlib` | Figures |
| `TreeCorr` | DESI projected clustering wp(r_p) (Landy–Szalay) |
| `torch` + `e3nn` | Branch B (SE(3)-equivariant network; paper Appendix E) |

**Note on hardware/platform:** the Phase-8 pipeline (main results) runs on CPU;
the full N=2000 masked run takes a few hours on a desktop. `TreeCorr` is used
for the survey clustering and a self-contained numpy/scipy periodic pair
counter for the mock clustering, because `Corrfunc` does not build on Windows.

---

## Data

The analysis uses two publicly available datasets, **not tracked in this
repository** due to size. Download them separately and place them under `data/`.

### DESI BGS DR1

The DESI Bright Galaxy Survey Data Release 1 clustering catalogues (NGC).
Available through the DESI Data Release portal (https://data.desi.lbl.gov/).
Required files:
- `BGS_BRIGHT-21.5_NGC_clustering.dat.fits` (galaxy catalogue, 217,614 galaxies)
- `BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits` (random catalogue)
- `BGS_BRIGHT-21.5_NGC_nz.txt` (radial selection n(z))

### Quijote nwLH

The Quijote *nwLH* (new Latin Hypercube) simulation suite (2000 cosmologies,
w₀ ∈ [−1.30, −0.70], w_a = 0), **FoF halo catalogues at z = 0.5**
(`groups_003`). Available through the Quijote project
(https://quijote-simulations.readthedocs.io/).

Expected layout:
```
data/
└── raw/
    ├── desi_dr1/
    │   ├── BGS_BRIGHT-21.5_NGC_clustering.dat.fits
    │   ├── BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits
    │   └── BGS_BRIGHT-21.5_NGC_nz.txt
    └── quijote/
        └── 3D_cubes/
            └── latin_hypercube_nwLH_hod/     (FoF halo catalogues + params file)
```

---

## Reproducing the main results

The pipeline is organized in numbered phases; each phase reads the frozen JSON
records of earlier phases and writes its own, so every number is traceable.

```bash
cd src

# 0. Validate the halo-catalogue reader (positions, masses, velocities)
python phase8_cutsky_mocks.py --check_fof --project_root ..

# 1. MAIN RESULT — like-for-like masked comparison, N=2000
#    (β₁ᵐᵃˣ deficit: DESI below all 2000 mocks, empirical p < 1/2000)
python phase8_test2_masked.py --n_pilot 2000 --project_root ..

# 2. Exclusion battery
python phase8_w0_exclusion.py    --project_root ..   # w0CDM (wa=0) exclusion
python phase8_hod_fit.py         --project_root ..   # HOD fit to wp(rp)+n̄
python phase8_test2_masked.py --n_pilot 200 \
       --hod_json ../results/phase8_hod_bestfit.json --project_root ..
python phase8_fiber_surrogate.py --project_root ..   # incompleteness surrogate
python phase8_weight_check.py    --project_root ..   # weighting robustness
```

### Numerical traceability

Every quantitative claim in the paper is traceable to a frozen JSON record
under `results/`. The JSON files are the canonical source; the figures and
paper values are derived from them. Gate thresholds were pre-registered
(`gate8_prior_v1_0.json`) before execution.

---

## Main results (Paper C)

| Quantity | Value | Source |
|---|---|---|
| β₁ᵐᵃˣ DESI BGS NGC (masked) | 28,256 | `phase8_test2_masked.json` |
| β₁ᵐᵃˣ mocks, like-for-like (N=2000) | 35,437 ± 313 | `phase8_test2_masked.json` |
| **Deficit significance (empirical)** | **p < 1/2000** (below all mocks) | `phase8_test2_masked.json` |
| ⟨pers₁⟩ under masked framework | rank 98.0% — not significant | `phase8_test2_masked.json` |
| σ_px systematic | +8.42σ (σ_px 0.216 → 0.640) | `phase6_sigma_px_test.json` |
| w₀ needed to reach DESI | ≈ −294 → **w₀CDM (wₐ=0) excluded** | `phase8_w0_exclusion.json` |
| Deficit under HOD refit to wp(rp) | unchanged (rank 1/200) | `phase8_test2_hodfit.json` |
| Incompleteness surrogate (≤30% drop) | opposite sign — does not explain | `phase8_fiber_surrogate.json` |
| Branch B null (Appendix E) | 1.68 ± 0.43σ, sign-alternating | `phase7_t1_variability.json` |

---

## Citation

If you use this code or the CAUCHY pipeline, please cite the paper:

```bibtex
@article{Marconi2026CAUCHY,
  author  = {Marconi, Alessandro},
  title   = {{Persistent homology on an observed galaxy field: discretization
             and survey-geometry systematics, a like-for-like framework, and a
             topological anomaly in DESI BGS}},
  journal = {JCAP},
  year    = {2026},
  note    = {arXiv:XXXX.XXXXX},
  doi     = {10.XXXX/XXXXX}
}
```

and the software archive:

```bibtex
@software{cauchy_pipeline,
  author  = {Marconi, Alessandro},
  title   = {{CAUCHY: Cosmic Anomaly via Unified Cosmological
             Hyper-fields analYsis --- pipeline v2.0}},
  year    = {2026},
  doi     = {10.5281/zenodo.21158278},
  url     = {https://github.com/AleMarco1/CAUCHY}
}
```

---

## Acknowledgments

This work makes use of the DESI and Quijote public datasets. The author thanks
Francisco Villaescusa-Navarro for guidance on the Quijote nwLH simulation suite.

Portions of the analysis code and documentation were drafted with AI assistance;
all scientific content and results were verified and approved by the author.

---

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

Alessandro Marconi — Independent Researcher, Verona, Italy
ORCID: [0009-0002-3682-1815](https://orcid.org/0009-0002-3682-1815)
Email: ale1marconi@gmail.com
