"""
CAUCHY — Phase 8, Script 2
src/phase8_test2_masked.py

TEST 2 (definitive, publishable): the correct like-for-like masked pipeline.

Differences from Test 1:
  - Exterior EXCLUDED from the filtration on BOTH sides (compute_tda_features
    masked=True): H1 loops crossing the survey boundary are cut, identically for
    DESI and mocks. This is the topologically correct treatment of a bounded
    survey (option (i), gate8).
  - Satellites get VIRIAL intra-halo velocities (option (b)): v_sat = v_halo +
    N(0, sigma_1d(M)), sigma_1d from the virial relation. Addresses R3 minor 2.
  - DESI reference RECOMPUTED with masked=True — does NOT reuse Test 1's number.

Everything else (log build_field, cut-sky carving, n(z), density target, sigma_px)
is inherited unchanged from phase8_cutsky_mocks.

Gate 2 (frozen): DESI must sit > +3 sigma above the mock <pers1> distribution AND
> +3 sigma below (i.e. z < -3) the mock beta1_max distribution, by empirical rank.
Primary claim = beta1_max (robust); <pers1> secondary. Ranks primary at N=200.

Usage:
  python src\\phase8_test2_masked.py --n_pilot 200 --project_root D:\\projects\\cauchy
  python src\\phase8_test2_masked.py --n_pilot 2000 --project_root D:\\projects\\cauchy  (after pilot passes)
"""

import argparse
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M

# Gravitational constant in (km/s)^2 * Mpc / Msun
G_KMS2_MPC_MSUN = 4.30091e-9


def sigma1d_virial(mass_h, r_vir_mpc):
    """1D velocity dispersion from the virial relation, per component [km/s].
    sigma_3d^2 = G M / R_vir ; sigma_1d = sigma_3d / sqrt(3). Order-of-magnitude
    but standard for a robustness pilot; gives ~few hundred to ~1000 km/s."""
    r = np.maximum(r_vir_mpc, 1e-3)
    sigma_3d = np.sqrt(G_KMS2_MPC_MSUN * mass_h / r)
    return sigma_3d / np.sqrt(3.0)


def populate_with_virial(pos_h, mass_h, vel_h, hod_params, rng):
    """Like M.populate_halos_hod_with_vel but satellites get halo bulk velocity
    PLUS an isotropic virial dispersion (option (b))."""
    (log_Mmin, sigma_logM, log_M0, log_M1, alpha,
     A_cen, A_sat, eta_vel, eta_conc) = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3)), np.zeros((0, 3))

    p_cen = np.clip(M.mean_Ncen(mass_h, log_Mmin, sigma_logM), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(M.mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    pos_list, vel_list = [], []
    if is_central.any():
        pos_list.append(pos_h[is_central])
        vel_list.append(vel_h[is_central])   # centrals: halo bulk velocity

    rho_crit = 2.775e11 * M.OMM
    for i in range(N_h):
        ns = int(n_sat[i])
        if ns <= 0:
            continue
        r_vir = np.clip((3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit)) ** (1.0 / 3.0),
                        0.01, 5.0) * eta_conc
        u = rng.random(ns)
        r = r_vir * u ** (1.0 / 3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(ns))
        phi = 2.0 * np.pi * rng.random(ns)
        dxyz = np.column_stack([r * np.sin(theta) * np.cos(phi),
                                r * np.sin(theta) * np.sin(phi),
                                r * np.cos(theta)])
        pos_list.append((pos_h[i] + dxyz) % M.BOXSIZE_MOCK)
        s1d = sigma1d_virial(mass_h[i], r_vir) * eta_vel
        v_sat = vel_h[i][None, :] + rng.normal(0.0, s1d, size=(ns, 3))
        vel_list.append(v_sat)

    if not pos_list:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.vstack(pos_list), np.vstack(vel_list)


def recompute_desi_reference_masked(mask, field_r, sum_wr):
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
    feats = M.compute_tda_features(nu_desi, mask, M.N_THRESH, masked=True)
    return float(feats[5]), float(feats[4])


def load_nwlh_params():
    """Load per-simulation (Om, s8, w0) from the nwLH params file. The Quijote
    nwLH latin hypercube params are columns (Om, Ob, h, ns, s8, w0). Returns a
    dict index -> (Om, s8, w0). Robust: tries a few candidate paths; prints the
    inferred w0 range so the column mapping can be sanity-checked (should span
    ~[-1.30, -0.70])."""
    candidates = [
        M.ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt",
        M.ROOT / "data" / "raw" / "quijote" / "latin_hypercube_nwLH_params.txt",
        M.HOD_CATALOG_DIR / "latin_hypercube_nwLH_params.txt",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        print("  [WARN] nwLH params file not found — per-mock w0 will be NaN. "
              "Set the path in load_nwlh_params().")
        return None
    tab = np.loadtxt(path)
    # columns: Om Ob h ns s8 Mnu w0  (7 columns — note M_nu in col 5)
    Om, s8, w0 = tab[:, 0], tab[:, 4], tab[:, 6]
    print(f"  [params] {path.name}: N={len(tab)}, w0 range [{w0.min():.3f}, {w0.max():.3f}] "
          f"(expect ~[-1.30, -0.70]); Om [{Om.min():.3f}, {Om.max():.3f}]")
    return {i: (float(Om[i]), float(s8[i]), float(w0[i])) for i in range(len(tab))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_pilot", type=int, default=200)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save_fields", action="store_true")
    ap.add_argument("--hod_json", type=str, default=None,
                    help="JSON with best-fit HOD (phase8_hod_bestfit.json) to override B3 median")
    args = ap.parse_args()

    hod_params = M.HOD_MEDIAN
    hod_tag = "B3_median"
    if args.hod_json:
        hj = json.load(open(args.hod_json))
        hod_params = np.array(hj["best_fit"]["hod_vector"], float)
        hod_tag = f"fitted(logMmin={hod_params[0]},logM1={hod_params[3]},a={hod_params[4]})"
        print(f"  HOD override: {hod_tag}")

    out_fields = M.RES_DIR / "phase8_test2_fields"
    if args.save_fields:
        out_fields.mkdir(parents=True, exist_ok=True)

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("CAUCHY Phase 8 — Script 2: Test 2 (masked, definitive)")
    print("=" * 70)
    print(f"  n_pilot={args.n_pilot}, exterior EXCLUDED from filtration, virial sat vel")
    print(f"  mask fill {100*mask.mean():.1f}%")

    print("\n[1/3] Random field + DESI reference (masked)...")
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    pers1_desi, beta1_desi = recompute_desi_reference_masked(mask, field_r, sum_wr)
    print(f"  <pers1>_DESI (masked)  = {pers1_desi:.5f}")
    print(f"  beta1_max_DESI (masked)= {beta1_desi:.0f}")

    print(f"\n[2/3] Loop su {args.n_pilot} mock (virial vel, masked TDA)...")
    pers1_list, beta1_list, ngal_list, index_list = [], [], [], []
    t0 = time.time()
    for i in range(args.n_pilot):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = populate_with_virial(pos_h, mass_h, vel_h, hod_params, rng)
        if len(pos_gal) < 100:
            continue
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            continue
        feats = M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)
        beta1_list.append(float(feats[4]))
        pers1_list.append(float(feats[5]))
        ngal_list.append(int(len(pos_sel)))
        index_list.append(i)
        if args.save_fields:
            np.savez(out_fields / f"test2_{i:04d}.npz", delta=nu)
        if (i + 1) % 20 == 0 or i == 0:
            eta = (time.time() - t0) / (i + 1) * (args.n_pilot - i - 1) / 60
            print(f"  [{i+1}/{args.n_pilot}] N_sel~{np.median(ngal_list):.0f} "
                  f"<pers1>={np.mean(pers1_list):.4f} beta1_max={np.mean(beta1_list):.0f} "
                  f"ETA={eta:.1f}min")

    # Per-mock table (index, w0, Om, s8, pers1, beta1_max) for the w0 analysis.
    params = load_nwlh_params()   # dict index -> (Om, s8, w0) or None
    tbl = M.RES_DIR / "phase8_test2_permock.csv"
    with open(tbl, "w") as f:
        f.write("index,w0,Om,s8,pers1,beta1_max\n")
        for k, idx in enumerate(index_list):
            om, s8, w0 = params.get(idx, (np.nan, np.nan, np.nan)) if params else (np.nan, np.nan, np.nan)
            f.write(f"{idx},{w0},{om},{s8},{pers1_list[k]},{beta1_list[k]}\n")
    print(f"  [table] per-mock saved -> {tbl}")

    pers1 = np.array(pers1_list)
    beta1 = np.array(beta1_list)
    n_ok = len(pers1)
    if n_ok < 20:
        print(f"[ERRORE] Solo {n_ok} mock validi."); sys.exit(1)

    p_mean, p_std = float(pers1.mean()), float(pers1.std(ddof=1))
    b_mean, b_std = float(beta1.mean()), float(beta1.std(ddof=1))
    z_pers1 = (pers1_desi - p_mean) / p_std
    z_beta1 = (beta1_desi - b_mean) / b_std
    rank_pers1 = float(np.mean(pers1 < pers1_desi))
    rank_beta1 = float(np.mean(beta1 < beta1_desi))

    survives = (z_pers1 > 3.0) and (z_beta1 < -3.0)
    # primary claim is beta1_max (robust); report its status explicitly too
    beta1_anomalous = (z_beta1 < -3.0)
    verdict = "SURVIVES" if survives else ("BETA1_ONLY" if beta1_anomalous else "DISSOLVED")

    print(f"\n[3/3] Verdetto Test 2 (N={n_ok})...")
    print(f"  <pers1>:   DESI={pers1_desi:.4f}  mock={p_mean:.4f}±{p_std:.4f}  "
          f"z={z_pers1:+.2f}  rank={rank_pers1*100:.1f}%")
    print(f"  beta1_max: DESI={beta1_desi:.0f}  mock={b_mean:.0f}±{b_std:.0f}  "
          f"z={z_beta1:+.2f}  rank={rank_beta1*100:.1f}%")
    print(f"\n  >>> VERDETTO TEST 2: {verdict}")
    print(f"      (primary claim beta1_max anomalous: {beta1_anomalous})")

    out = {
        "schema_version": "1.0",
        "output_id": "phase8_test2_masked",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "gate8_prior_v1_0.json (Test 2)",
        "n_pilot_requested": args.n_pilot,
        "n_mock_valid": n_ok,
        "masked_filtration": True,
        "satellite_velocity": "option_b_virial_dispersion",
        "hod": hod_tag,
        "desi_reference_masked": {"pers1": pers1_desi, "beta1_max": beta1_desi},
        "mock_pers1": {"mean": p_mean, "std": p_std, "z_desi": z_pers1, "rank_desi": rank_pers1},
        "mock_beta1_max": {"mean": b_mean, "std": b_std, "z_desi": z_beta1, "rank_desi": rank_beta1},
        "median_ngal_selected": float(np.median(ngal_list)),
        "verdict": verdict,
        "primary_claim_beta1_max_anomalous": beta1_anomalous,
        "n_floor_note": f"N={n_ok}; empirical p-floor ~1/{n_ok+1}. Ranks primary.",
    }
    outp = M.RES_DIR / ("phase8_test2_hodfit.json" if args.hod_json
                        else "phase8_test2_masked.json")
    with open(outp, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[SAVED] {outp}")
    print("[COMPLETATO] Test 2 terminato.")


if __name__ == "__main__":
    main()
