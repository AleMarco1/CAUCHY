"""
CAUCHY — curiosity check, not a manuscript deliverable
src/rev1_x_missing_modes.py

How much of the variance of the smoothed field lives in the modes that a
1000 h^-1 Mpc periodic box cannot contain?

This is the one caveat the revision leaves genuinely open: modes larger than the
box are ABSENT from the mocks rather than duplicated, so the replica-randomised
pilot cannot bound them. The question is an amplitude question and it does not
need a simulation: with a linear P(k) and the pipeline's own Gaussian filter,

    sigma^2(<k_cut) / sigma^2(total) ,  W(k) = exp(-k^2 R^2 / 2) ,  R = 5 h^-1 Mpc

says what fraction of the filtered field's variance those modes carry.

Three things make the answer conservative, i.e. an OVER-estimate of the concern:

  * the denominator uses linear theory only. The real field has non-linear
    small-scale power and, in the FKP estimator, shot noise; both add to the
    denominator at high k and shrink the ratio further.
  * galaxy bias is scale-independent on these scales and the growth factor is
    common to numerator and denominator, so both cancel in the ratio. No
    assumption about b or z enters.
  * smoothing at R = 5 suppresses high k, which *raises* the low-k share. An
    unsmoothed field would give a smaller ratio still.

Two cutoffs are reported:

  k_box   = 2 pi / 1000                  modes the periodic box cannot contain
  k_shell = 2 pi / (D_C(0.4) - D_C(0.1)) the largest radial mode the BGS shell
                                         itself can sample

The second is the more interesting of the two: if k_shell > k_box, the survey is
radially shallower than the box and cannot access the missing modes in that
direction at all.

Transfer function: Eisenstein & Hu (1998) no-wiggle. BAO wiggles sit at
k ~ 0.05-0.2 h/Mpc and are irrelevant to an integral cut at k < 0.01.

  python src\\rev1_x_missing_modes.py

Output: results/revision/rev1_x_missing_modes.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.integrate import quad

# Quijote fiducial
OM, OB, H, NS = 0.3175, 0.049, 0.6711, 0.9624
THETA = 2.7255 / 2.7
R_SMOOTH = 5.0          # h^-1 Mpc, the pipeline's Gaussian width
L_BOX = 1000.0          # h^-1 Mpc
ZMIN, ZMAX = 0.1, 0.4

OUT_DIR = Path.cwd() / "results" / "revision"


def pk_nowiggle(k):
    """Eisenstein & Hu (1998) no-wiggle P(k), arbitrary normalisation.
    k in h/Mpc."""
    om_h2, ob_h2 = OM * H * H, OB * H * H
    s = 44.5 * np.log(9.83 / om_h2) / np.sqrt(1.0 + 10.0 * ob_h2 ** 0.75)  # Mpc
    alpha = (1.0
             - 0.328 * np.log(431.0 * om_h2) * OB / OM
             + 0.38 * np.log(22.3 * om_h2) * (OB / OM) ** 2)
    ks = k * s * H                      # k[h/Mpc] * s[Mpc] * h  -> dimensionless
    gamma_eff = OM * H * (alpha + (1.0 - alpha) / (1.0 + (0.43 * ks) ** 4))
    q = k * THETA * THETA / gamma_eff
    l0 = np.log(2.0 * np.e + 1.8 * q)
    c0 = 14.2 + 731.0 / (1.0 + 62.5 * q)
    t = l0 / (l0 + c0 * q * q)
    return k ** NS * t * t


def sigma2(k_lo, k_hi, R):
    f = lambda lk: (lambda k: k ** 3 * pk_nowiggle(k) * np.exp(-k * k * R * R))(np.exp(lk))
    val, _ = quad(f, np.log(k_lo), np.log(k_hi), limit=400)
    return val / (2.0 * np.pi ** 2)


def comoving(z):
    c = 2997.92458  # h^-1 Mpc
    e = lambda x: np.sqrt(OM * (1 + x) ** 3 + (1 - OM))
    return c * quad(lambda x: 1.0 / e(x), 0.0, z)[0]


def main():
    depth = comoving(ZMAX) - comoving(ZMIN)
    k_box = 2 * np.pi / L_BOX
    k_shell = 2 * np.pi / depth

    K_LO, K_HI = 1e-5, 50.0
    tot = sigma2(K_LO, K_HI, R_SMOOTH)
    out = {"cosmology": {"Om": OM, "Ob": OB, "h": H, "ns": NS},
           "R_smooth": R_SMOOTH, "L_box": L_BOX,
           "shell_depth": depth, "k_box": k_box, "k_shell": k_shell,
           "shell_shallower_than_box": bool(depth < L_BOX),
           "fractions": {}}

    print("=" * 70)
    print("Modi assenti dal box periodico: quanta varianza portano?")
    print("=" * 70)
    print(f"  guscio BGS: D_C({ZMIN}) = {comoving(ZMIN):.1f}, "
          f"D_C({ZMAX}) = {comoving(ZMAX):.1f} -> profondita' {depth:.1f} h^-1 Mpc")
    print(f"  k_box   = {k_box:.5f} h/Mpc   (box {L_BOX:.0f} h^-1 Mpc)")
    print(f"  k_shell = {k_shell:.5f} h/Mpc (guscio radiale)")
    print(f"  il guscio e' piu' sottile del box: {depth < L_BOX}\n")

    for name, kc in (("k_box", k_box), ("k_shell", k_shell),
                     ("2x k_box", 2 * k_box), ("k=0.02", 0.02)):
        fr = sigma2(K_LO, kc, R_SMOOTH) / tot
        out["fractions"][name] = {"k_cut": float(kc), "variance_fraction": float(fr)}
        print(f"  sigma^2(k < {kc:.5f}) / sigma^2_tot = {fr:.3e}   [{name}]")

    # where the variance actually lives
    print()
    for target in (0.01, 0.10, 0.50, 0.90):
        lo, hi = 1e-4, 20.0
        for _ in range(60):
            mid = np.sqrt(lo * hi)
            if sigma2(K_LO, mid, R_SMOOTH) / tot < target:
                lo = mid
            else:
                hi = mid
        k = np.sqrt(lo * hi)
        out.setdefault("variance_quantiles", {})[f"{target:.2f}"] = float(k)
        print(f"  il {100*target:>4.0f}% della varianza sta sotto k = {k:.4f} h/Mpc")

    out["timestamp"] = datetime.now(timezone.utc).isoformat()
    out["script"] = "src/rev1_x_missing_modes.py"
    out["status"] = ("curiosity check, not cited in the manuscript; linear, "
                     "real-space, unwindowed, and a bound on the variance "
                     "contribution rather than on a topological count")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / "rev1_x_missing_modes.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[OUT] {p}")


if __name__ == "__main__":
    main()
