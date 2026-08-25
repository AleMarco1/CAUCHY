# Revision records — MNRAS MN-26-2100-P

Frozen numerical records and the scripts that produced them for the referee
revision of *A like-for-like framework for persistent homology on galaxy
surveys, and a topological anomaly in DESI BGS*.

Every quantitative claim added to the manuscript during the revision traces to
one of the files below. The mapping is given explicitly so that a reader can go
from a number in the paper to the record that holds it without reading the code.

All scripts are run from the project root with the `cauchy` environment active.
Software versions: gudhi 3.11.0, numpy 2.4.6, scipy 1.17.1, Python 3.11.15.

---

## Gates

Every script that produces a number for the manuscript enforces at least one
gate and refuses to write output if it fails.

| gate | what it checks | where |
|---|---|---|
| Reproduction | the DESI field rebuilt through `phase8_cutsky_mocks.build_field` gives `beta1_max = 28256` | `rev1_r14_monotone.py`, `rev1_r13_beta1curve.py` |
| Box–Cox anchoring | `build_field_eps(eps=0)` equals `P8.build_field` element for element | `rev1_r14_monotone.py` |
| Diagram consistency | the extracted masked H1 diagram agrees with `P8.compute_tda_features` in count and mean persistence, field by field | `rev1_r13_beta1curve.py` |
| Provenance | recomputing `beta1_max` from a stored raw mock delta reproduces the frozen ensemble entry exactly | `rev1_r14_monotone.py`, `rev1_r13_beta1curve.py` |
| Null | the copied carving routine, with the modification switched off, returns a bit-identical result to `P8.carve_cutsky` from the same generator state | `rev1_r11_pilot.py` |
| Closure | each decomposition of the deficit sums to the total deficit | `rev1_r13_beta1curve.py`, `rev1_r13_split.py` |

---

## Referee point 4 — the log-transform (Section 4.1, Table 1)

`src/rev1_r14_monotone.py`

| record | holds |
|---|---|
| `rev1_r14_monotone_inspect.json` | discretized kernel weights at the canonical smoothing; format of the candidate mock directories |
| `rev1_r14_monotone_provenance.json` | provenance gate on the raw mock deltas, 5/5 exact |
| `rev1_r14_monotone_testA.json` | monotone-invariance test: `beta1_max = 28256` under all three tie-preserving remaps; `<pers1>` ratios 0.55, 417, 9.5; tie statistics (9,364 cells in 4,272 groups); tie-breaking variant at 28,259 |
| `rev1_r14_monotone_deltastats.json` | raw-contrast amplitudes: DESI max 125.47, mock max median 3474.6 (range 2417–32244), std ratio median 30.87 |
| `rev1_r14_monotone_testB.json` | Box–Cox family on data and 50 mocks: deficit 20.3% at eps=0 to 17.6% at eps=1; Spearman >= 0.9965; mock means 35445.6 and 35262.3 |

Reproduce:

```
python src\rev1_r14_monotone.py --mode inspect
python src\rev1_r14_monotone.py --mode testA
python src\rev1_r14_monotone.py --mode deltastats --n_mocks 100
python src\rev1_r14_monotone.py --mode provenance --mock_dir data\processed\paper1_mock_deltas\NGC --frozen results\phase9_ngc_clean_beta1.npz
python src\rev1_r14_monotone.py --mode testB --n_mocks 50 --mock_dir data\processed\paper1_mock_deltas\NGC --frozen results\phase9_ngc_clean_beta1.npz
```

---

## Referee point 3 — structure of the beta_1 curve (Section 5.2, Section 7 item xi)

`src/rev1_r13_beta1curve.py`, `src/rev1_r13_split.py`

| record | holds |
|---|---|
| `rev1_r13_beta1curve.json` | beta_1 curve on a common threshold grid (DESI peak nu=1.36 height 8,490; mock peak nu=0.24 height 13,259; below the 3-sigma band on 45% of occupied thresholds, above on 43%); sigma_nu 2.686 against 2.089; four decompositions of the deficit with their per-bin residuals |
| `rev1_r13_beta1curve.npz` | per-field birth and persistence histograms, beta_1 curves and sigma for the DESI field and 200 mocks |
| `rev1_r13_persistence_split.json` | three-way split in normalised persistence: excess 1,908.1 below 0.054 sigma, deficit 9,408.2 in the bulk, excess 332.5 above 1.847 sigma, closing on the total 7,167.6 |

The raw-threshold decomposition is reported in the paper as dominated by the
one-point difference between the fields, not as a scale decomposition. A clean
scale decomposition requires matched one-point distributions and is listed as
future work.

Reproduce:

```
python src\rev1_r13_beta1curve.py --n_mocks 200 --mock_dir data\processed\paper1_mock_deltas\NGC --frozen results\phase9_ngc_clean_beta1.npz
python src\rev1_r13_split.py
```

---

## Referee point 1 — tiling and cosmic variance (Section 5.6, Section 7 item vii)

`src/rev1_r11_tiling.py`, `src/rev1_r11_pilot.py`, `src/rev1_r11_summary.py`

| record | holds |
|---|---|
| `rev1_r11_tiling.json` | tiling duplication measured exactly (307,805 in-survey voxels on 214,215 distinct box cells; independent volume 69.6%; 58.8% of voxels on reused cells; mean multiplicity 1.437, maximum 5); the width the distribution would need for the observation to reach 3 and 2 sigma |
| `rev1_r11_pilot.json` | 100 mocks regenerated with randomly reoriented replicas against the standard tiling: scatter ratio 0.9726 [0.8487, 1.1183], mean shift −12.79 generators; null gate passed |
| `rev1_r11_summary.json` | the two combined on the correct quantity, and a note on a mislabelled field in the pilot record (see below) |

**Note on `rev1_r11_pilot.json`.** Its field
`geometric_expectation_if_var_scales_as_inverse_volume = 1.199` is the expected
inflation of the *realisation term alone*. The pilot measures the *total*
scatter, and the realisation term is 13.4% of the variance, so the
corresponding expectation for the total is 1.029. The comparison quoted in the
paper uses 1.029; `rev1_r11_summary.json` recomputes it and records the
discrepancy rather than silently overwriting the pilot record.

Reproduce:

```
python src\rev1_r11_tiling.py
python src\rev1_r11_pilot.py --n_mocks 100
python src\rev1_r11_summary.py
```

---

## Referee point 2 — H_2 and point-cloud filtrations (Section 6.2, Section 7 item x)

No new computation. The sampling argument uses two numbers already in the
paper — 217,614 galaxies in 307,805 in-survey voxels at a cell size of
15.6044 h^-1 Mpc — giving 0.71 galaxies per voxel and a mean inter-galaxy
separation of 17.5 h^-1 Mpc. It can be checked in one line:

```
python -c "N=217614; V=307805; dx=1997.3629167166155/128; n=N/(V*dx**3); print('occupancy %.4f | separation %.2f | occupancy at 256^3 %.4f'%(N/V, n**(-1/3), N/V/8))"
```

---

## Not archived

`results/revision/desi_inputs_cache.npz` is a cache of the DESI CIC data and
random fields, written on the first run of any mode and reused afterwards to
avoid reloading the catalogues. It is derived entirely from the public DESI
BGS DR1 catalogues, it is large, and every script re-runs the reproduction gate
against it, so a stale cache would be caught. It is excluded from the
repository and from the archive.
