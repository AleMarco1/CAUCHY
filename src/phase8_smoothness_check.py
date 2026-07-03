"""
CAUCHY — Phase 8, smoothness check
src/phase8_smoothness_check.py

Question: is the robust beta1_max deficit (DESI ~28k loops vs mock ~35k, z=-25)
simply because the DESI field is SMOOTHER than the cut-sky mocks (less small-scale
structure -> fewer H1 loops), rather than a genuine topological difference?

A loop is born from small-scale density fluctuations. If DESI has less small-scale
power (from fiber-assignment incompleteness, unmodelled weights, n(z) imperfections,
or a genuinely smoother field), it will have fewer loops for a mundane reason.

Test: on the SAME nu fields that feed the TDA (DESI rebuilt via build_field, and
N cut-sky mocks), measure small-scale structure three ways, all in-survey only:
  1. gradient variance  <|grad nu|^2>_mask   (local roughness)
  2. small-scale power   integral of P(k) for k > k_split
  3. excursion-set area  fraction of voxels above nu=+1 (rich-structure fraction)

If DESI sits BELOW the mock distribution on these SAME roughness measures, the
loop deficit is smoothness (mundane). If DESI is comparable or ABOVE on roughness
yet still has fewer loops, the deficit is genuinely topological.

Reuses phase8_cutsky_mocks machinery. Fast (~a few minutes, N=30 mocks).

Usage:
  python src\\phase8_smoothness_check.py --n_mock 30 --project_root D:\\projects\\cauchy
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M


def gradient_var(nu, mask):
    """<|grad nu|^2> over in-survey voxels (roughness)."""
    gx, gy, gz = np.gradient(nu)
    g2 = gx**2 + gy**2 + gz**2
    return float(g2[mask].mean())


def small_scale_power(nu, mask, k_split_frac=0.5):
    """Fraction of field power at k > k_split (k_split = k_split_frac * k_Nyquist),
    computed on the masked field (exterior zeroed). Dimensionless roughness proxy."""
    f = nu.copy()
    f[~mask] = 0.0
    F = np.fft.rfftn(f)
    P = np.abs(F)**2
    ng = nu.shape[0]
    kx = np.fft.fftfreq(ng)[:, None, None]
    ky = np.fft.fftfreq(ng)[None, :, None]
    kz = np.fft.rfftfreq(ng)[None, None, :]
    kmag = np.sqrt(kx**2 + ky**2 + kz**2)          # in units of Nyquist=0.5
    k_split = k_split_frac * 0.5
    total = P.sum()
    if total <= 0:
        return 0.0
    return float(P[kmag > k_split].sum() / total)


def excursion_fraction(nu, mask, level=1.0):
    """Fraction of in-survey voxels above nu=level (rich-structure fraction)."""
    din = nu[mask]
    return float(np.mean(din > level))


def summarize(name, vals):
    a = np.array(vals, float)
    return f"{name}: {a.mean():.5g} ± {a.std(ddof=1):.3g}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_mock", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("Phase 8 — smoothness check (is the loop deficit just DESI being smoother?)")
    print("=" * 70)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    # DESI nu (same build_field as the TDA reference)
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
    d_grad = gradient_var(nu_desi, mask)
    d_pow  = small_scale_power(nu_desi, mask)
    d_exc  = excursion_fraction(nu_desi, mask)
    print(f"\nDESI:  grad_var={d_grad:.5g}  smallscale_power={d_pow:.5g}  exc(>1)={d_exc:.5g}")

    print(f"\nMocks (N={args.n_mock})...")
    g_list, p_list, e_list = [], [], []
    for i in range(args.n_mock):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, 3)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = M.populate_halos_hod_with_vel(pos_h, mass_h, vel_h, M.HOD_MEDIAN, rng)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            continue
        g_list.append(gradient_var(nu, mask))
        p_list.append(small_scale_power(nu, mask))
        e_list.append(excursion_fraction(nu, mask))
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}] grad_var={np.mean(g_list):.5g} "
                  f"power={np.mean(p_list):.5g} exc={np.mean(e_list):.5g}")

    g = np.array(g_list); p = np.array(p_list); e = np.array(e_list)
    print("\n" + "=" * 70)
    print("  " + summarize("grad_var       (mock)", g))
    print("  " + summarize("smallscale_pow (mock)", p))
    print("  " + summarize("exc(>1)        (mock)", e))

    zg = (d_grad - g.mean()) / g.std(ddof=1)
    zp = (d_pow  - p.mean()) / p.std(ddof=1)
    ze = (d_exc  - e.mean()) / e.std(ddof=1)
    print(f"\n  DESI z vs mock:  grad_var={zg:+.2f}  smallscale_power={zp:+.2f}  exc(>1)={ze:+.2f}")

    print("\n" + "-" * 70)
    smoother = (zg < -2) or (zp < -2)
    if smoother:
        print("  -> DESI is measurably SMOOTHER than the mocks on the same roughness")
        print("     measures. The loop deficit is (at least partly) a smoothness")
        print("     effect — a mundane explanation (fiber-assignment / weights / n(z) /")
        print("     genuinely lower small-scale power). Must be reported as such; the")
        print("     beta1_max anomaly is NOT cleanly topological.")
    else:
        print("  -> DESI is NOT smoother than the mocks (roughness comparable or higher)")
        print("     yet has ~20% fewer loops. The beta1_max deficit is genuinely")
        print("     topological, not explained by small-scale power alone. This")
        print("     strengthens the anomaly.")
    print("  NOTE: this is diagnostic, not a significance test; interpret with the")
    print("        N=2000 rank.")


if __name__ == "__main__":
    main()
