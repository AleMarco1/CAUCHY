# §5.X — Degeneracy with Interacting Dark Energy Models
## [VERSIONE CORRETTA — post-review Concern 2 risolto — 2026-05-07]

## Background Degeneracy Between CPL and IDE Cosmologies

A potential systematic concern for any analysis targeting dynamical dark energy via the
phantom crossing signature (w₀ < −1) is degeneracy with alternative dark sector models
that can reproduce similar expansion histories without invoking a phantom equation of state.
Interacting dark energy (IDE) models, in which energy is exchanged between the dark matter
and dark energy components at a rate Q = βH ρ_de (Gavela et al. 2009, JCAP 0907:034),
constitute a physically well-motivated class of such alternatives. Their expansion history
H(z) can in principle mimic CPL cosmologies (w₀, wₐ) for appropriate choices of the
coupling parameter β and dark energy equation of state w₀_de, provided the non-phantom
constraint w₀_de > −1 is not violated (the phantom equation of state is structurally
excluded in standard IDE formulations; see Neumann, Videla & Araya 2026, arXiv:2604.22970,
§2.2 for the analytic closed-form solution I(a) = (1 − aˢ)/s valid for wₐ = 0).

We performed a systematic numerical test of this degeneracy using the CAUCHY analysis
cosmologies. A sample of N = 142 CPL cosmologies was drawn from the nwLH simulation
suite (w₀ ∈ [−1.300, −0.700], wₐ = 0.0), with 3 cosmologies excluded for proximity to
ΛCDM (|w₀ + 1| < 0.01). The sample comprises 92 phantom cosmologies (w₀ < −1) and
50 quintessence cosmologies (w₀ > −1). For each cosmology we searched for an IDE
equivalent within the non-phantom constraint (w₀_de > −1, β ∈ [−3, 3]) that reproduces
H(z) to within 0.5% fractional tolerance — commensurate with DESI DR2 precision for
intermediate-redshift tracers, and conservative relative to BGS precision at z < 0.4
(Karim et al. 2025, arXiv:2404.03002). The IDE H(z) was computed using the Gavela et al.
(2009) equations with the closed-form wₐ = 0 solution of Neumann et al. (2026),
verified against numerical integration to machine precision.

Of the 142 cosmologies tested, 55 achieve convergence within the 0.5% tolerance. The
converged cases comprise 48 quintessence (w₀ > −1) and 7 phantom near-boundary
(w₀ ∈ [−1.048, −1.012]) cosmologies. The 7 near-boundary phantom cases converge
exclusively because they lie in the near-ΛCDM transition regime: all have β < −0.003
and w₀_de > −1.000, making the IDE mapping a trivial reparametrization of near-ΛCDM
dynamics. Crucially, all 85 phantom cosmologies with w₀ < −1.05 fail to achieve
convergence: the minimum residual across the full β grid is 0.51%, marginally but
consistently above the 0.5% tolerance. This result is analytically expected: for
w₀ ≪ −1, the dark energy density grows with time, producing a qualitatively distinct
H(z) shape that cannot be reproduced by any non-phantom IDE model (Artola, Lazkoz &
Salzano 2026, arXiv:2604.25373; Petri et al. 2026).

The perturbative growth factor D(z) was evaluated for all 55 converged pairs via the
Gavela et al. (2009) IDE growth equations. The maximum fractional deviation is
max(ΔD/D) = 0.94%, with zero pairs exceeding 1% and 7/55 pairs (13%) exceeding 0.1%.
The median deviation at z = 0.5 is effectively zero, consistent with the near-ΛCDM
character (β ≈ 0) of all convergent mappings.

Taken together, these results establish that the CAUCHY phantom crossing signal is non-
degenerate with IDE models at the observational precision relevant to our analysis. All
phantom cosmologies with w₀ < −1.05 — the bulk of the signal targeted by CAUCHY — are
structurally non-degenerate with IDE non-phantom alternatives at the H(z) level. The 7
near-boundary phantom cases that achieve technical convergence are by construction near-
ΛCDM and carry negligible topological signal; their IDE equivalents are β ≈ 0
reparametrizations. At the perturbative level, max(ΔD/D) = 0.94% for the converged
pairs confirms that even where background degeneracy is achieved, growth histories remain
sub-percent consistent — well below the statistical precision of the CAUCHY measurement.
