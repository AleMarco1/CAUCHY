# CAUCHY

**Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis**

A topological data analysis (TDA) pipeline that searches for phantom dark energy
signatures in the DESI Bright Galaxy Survey (BGS DR1) galaxy density field, using
persistent homology compared against the Quijote nwLH mock cosmologies.

This repository accompanies the paper:

> **Cosmology with persistent homology: a topological anomaly in the DESI BGS galaxy field**
> A. Marconi (2026), submitted to JCAP. arXiv:XXXX.XXXXX

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

CAUCHY measures the mean $H_1$ persistence $\langle\mathrm{pers}_1\rangle$ of the
3D galaxy density field and compares it to 2000 $w_0$CDM mock cosmologies. The main
result is a topological anomaly of the DESI BGS field relative to the $\Lambda$CDM
mock distribution, significant at $+9.45\sigma$ (density-calibrated HOD, full sample)
and $+29.9\sigma$ (density-controlled subset).

The analysis comprises two independent pipelines:

- **Branch A (TDA):** persistent homology on the log-transformed density field via
  `gudhi` CubicalComplex, extracting $H_0$ and $H_1$ features.
- **Branch B (CNN+GNN):** an SE(3)-equivariant neural network producing a tension
  field, used as an independent cross-check (null result at $z=0$, as physically
  expected).

A key methodological finding is that $\langle\mathrm{pers}_1\rangle$ depends on the
dimensionless smoothing parameter $\sigma_\mathrm{px} = R/\Delta x$ rather than the
physical smoothing scale $R$ — motivating a $\sigma_\mathrm{px}$-matched comparison
framework (Comparison B).

---

## Repository structure

```
cauchy/
├── README.md                     This file
├── LICENSE                       MIT license
├── environment.yml               Conda environment specification
├── requirements.txt              pip dependencies (alternative to conda)
├── paper/                        LaTeX source of the paper
│   ├── cauchy_paper_b_jcap.tex
│   ├── jcappub.sty
│   ├── JHEP.bst
│   ├── cauchy.bib
│   └── figures/                  Publication figures (PNG + PDF)
├── src/                          Analysis pipeline
│   ├── cauchy_figures.py         Reproduces all 8 publication figures
│   ├── phase_r51_*.py            HOD marginalization / calibration
│   ├── phase_b3_cal135*.py       Density-calibrated HOD runs
│   ├── phase_cal135_action_a.py  Density-controlled subset + partial correlation
│   ├── phase_oc1_pk_hod.py       Power spectrum vs TDA comparison
│   ├── phase_h2_diagnostic.py    H2 lattice-artefact diagnostic
│   ├── phase_halo_completeness.py FoF completeness at log Mmin = 13.5
│   └── phase_hod_fit_wp.py       wp(rp) projected clustering (TreeCorr)
├── results/                      Frozen numerical records (JSON)
│   ├── phase6_*.json             Main anomaly results
│   ├── phase5_*.json             HOD pipeline
│   ├── phase7_*.json             Robustness tests
│   └── ...
└── data/                         (not tracked — see Data section below)
```

---

## Installation

### Option A — conda (recommended)

```bash
git clone https://github.com/USERNAME/cauchy.git
cd cauchy
conda env create -f environment.yml
conda activate cauchy
```

### Option B — pip

```bash
git clone https://github.com/USERNAME/cauchy.git
cd cauchy
python -m venv venv
source venv/bin/activate       # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Key dependencies

| Package | Purpose |
|---|---|
| `gudhi` | Persistent homology (CubicalComplex) |
| `numpy`, `scipy` | Numerical core |
| `matplotlib` | Figures |
| `torch` + `e3nn` | Branch B (SE(3)-equivariant network) |
| `Pylians` | Density field / power spectrum utilities |
| `TreeCorr` | Projected clustering wp(rp) |
| `PySR` | Symbolic regression (optional) |

**Note on hardware:** Branch B (CNN+GNN) benefits from a CUDA-capable GPU. Branch A
(TDA) and figure reproduction run on CPU. The reference environment used an
RTX 5060 Ti (16 GB) with CUDA under Windows; the code is platform-independent, but
`TreeCorr` is used instead of `Corrfunc` for the projected clustering because the
latter is difficult to build on Windows.

---

## Data

The analysis uses two publicly available datasets, **not tracked in this repository**
due to size. Download them separately and place them under `data/`.

### DESI BGS DR1

The DESI Bright Galaxy Survey Data Release 1 clustering catalogues (NGC and SGC).
Available through the DESI Data Release portal (https://data.desi.lbl.gov/).
Required files:
- `BGS_BRIGHT-21.5_NGC_clustering.dat.fits` (galaxy catalogue, 217,614 galaxies)
- `BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits` (random catalogue)

### Quijote nwLH

The Quijote *nwLH* (new Latin Hypercube) simulation suite (2000 cosmologies,
$w_0 \in [-1.30, -0.70]$, $w_a = 0$). Available through the Quijote project
(https://quijote-simulations.readthedocs.io/). Place the 3D density cubes under
`data/raw/quijote/3D_cubes/` and the HOD galaxy catalogues under the corresponding
subdirectory.

Expected layout:
```
data/
├── raw/
│   ├── desi_dr1/
│   │   ├── BGS_BRIGHT-21.5_NGC_clustering.dat.fits
│   │   └── BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits
│   └── quijote/
│       ├── 3D_cubes/
│       └── latin_hypercube_nwLH_hod/
```

---

## Reproducing the results

### Figures

All eight publication figures are reproduced from embedded numerical data
(no external data required):

```bash
cd src
python cauchy_figures.py
```

Figures are written to `results/figures/` as both PNG and PDF.

### Key analysis steps

The pipeline is organized in numbered phases. Each phase reads the frozen JSON
records from earlier phases and writes its own, so results are fully traceable.
The main results can be regenerated as follows (requires the data above):

```bash
cd src

# Density-calibrated HOD (log Mmin = 13.5) — main anomaly result
python phase_b3_cal135_v2.py

# Density-controlled subset + unbiased partial correlation
python phase_cal135_action_a.py

# Power spectrum vs TDA comparison (isometric, OC-1)
python phase_oc1_pk_hod.py

# H2 lattice-artefact diagnostic
python phase_h2_diagnostic.py
```

### Numerical traceability

Every quantitative claim in the paper is traceable to a frozen JSON record under
`results/`, organized by analysis phase (e.g. `phase6_gate_result.json` for the
main anomaly, `phase7_t1_variability.json` for the Branch B null). The JSON files
are the canonical source; the figures and paper values are derived from them.

---

## Main results

| Quantity | Value | Source |
|---|---|---|
| $\langle\mathrm{pers}_1\rangle$ DESI BGS NGC | $0.459 \pm 0.005$ | `phase6_bgs_tda_features.json` |
| Anomaly (B3 baseline) | $+5.96\sigma$ | `phase6_scenario2_final.json` |
| Anomaly (HOD-13.5, full) | $+9.45\sigma$ | `phase_b3_cal135_v2_diagnostics.json` |
| Anomaly (HOD-13.5, DC subset) | $+29.9\sigma$ | `phase_cal135_action_a.json` |
| $\sigma_\mathrm{px}$ systematic | $+8.42\sigma$ | `phase6_sigma_px_test.json` |
| Branch B null | $1.68 \pm 0.43\sigma$ | `phase7_t1_variability.json` |
| TDA vs P(k) (isometric) | $2.80\sigma$ vs $2.51\sigma$ | `phase_oc1_pk_hod.json` |

---

## Citation

If you use this code or the CAUCHY pipeline, please cite the paper:

```bibtex
@article{Marconi2026CAUCHY,
  author  = {Marconi, Alessandro},
  title   = {{Cosmology with persistent homology: a topological anomaly
             in the DESI BGS galaxy field}},
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
             Hyper-fields analYsis — pipeline v1.0}},
  year    = {2026},
  doi     = {10.5281/zenodo.XXXXXXX},
  url     = {https://github.com/USERNAME/cauchy}
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
