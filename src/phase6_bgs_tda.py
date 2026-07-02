"""
CAUCHY — Phase 6
src/phase6_bgs_tda.py

Estrae le 8 feature TDA dal campo BGS DESI DR1 voxelizzato.
Usa la stessa pipeline di Phase 5 con la convenzione birth/death corretta.

Convenzione gudhi (fix v3, Phase 5):
  birth_s = -diag[:,0]   (soglia alta, superlevel)
  death_s = -diag[:,1]   (soglia bassa, superlevel)
  persistenza = birth_s - death_s > 0

Feature (Execution Parameters §9.1):
  [0] b1_peak_pos        soglia al picco curva beta_1
  [1] b1_peak_height     altezza picco beta_1
  [2] b1_fwhm            FWHM picco (0 se picco troppo stretto)
  [3] b1_integral        integrale curva beta_1
  [4] b2_max_count       numero loop nel diagramma persistenza
  [5] b2_mean_persistence persistenza media (positiva con fix v3)
  [6] b2_high_persist    count loop con persistenza > p90
  [7] b0_at_mean         beta_0 alla soglia media del campo

Incertezze: bootstrap jackknife su 20 patch angolari (solo NGC, abbastanza galassie).

Input:
  data/processed/phase6_fields/bgs_ngc_delta_128.npy
  data/processed/phase6_fields/bgs_ngc_mask_128.npy
  data/processed/phase6_fields/bgs_sgc_delta_128.npy
  data/processed/phase6_fields/bgs_sgc_mask_128.npy
  results/phase6_voxelize_diagnostics.json

Output:
  results/phase6_bgs_tda_features.json
  results/phase6_bgs_tda_diagnostics.json

Uso:
  python src/phase6_bgs_tda.py [--n_thresh 100] [--n_bootstrap 20] [--project_root .]
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_thresh", type=int, default=100,
                    help="Numero soglie filtrazione (default 100, identico Phase 5)")
parser.add_argument("--n_bootstrap", type=int, default=20,
                    help="Numero patch jackknife per incertezza (default 20)")
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

ROOT    = Path(args.project_root)
FLD_DIR = ROOT / "data" / "processed" / "phase6_fields"
RES_DIR = ROOT / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(args.seed)

print("=" * 70)
print("CAUCHY Phase 6 — BGS TDA Feature Extraction")
print(f"n_thresh={args.n_thresh}, n_bootstrap={args.n_bootstrap}")
print("=" * 70)

# ---------------------------------------------------------------------------
# TDA feature extraction — identica a Phase 5 con fix v3
# ---------------------------------------------------------------------------
def compute_tda_features(delta_field, mask, n_thresh=100):
    """
    Estrae 8 feature TDA dal campo di densita.

    Convenzione birth/death (fix v3 Phase 5):
      birth_s = -diag[:,0]  (soglia alta superlevel)
      death_s = -diag[:,1]  (soglia bassa superlevel)
      persistenza = birth_s - death_s > 0

    La maschera viene applicata: voxel fuori survey = 0 (gia impostato in voxelize).
    """
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato: conda install -c conda-forge gudhi")

    field = delta_field.astype(np.float64)

    # Thresholds in coordinate originali (field_s)
    # Solo voxel dentro la survey per determinare il range
    field_in = field[mask]
    nu_min = float(np.percentile(field_in, 1))   # robusto agli outlier
    nu_max = float(np.percentile(field_in, 99))
    thresholds = np.linspace(nu_min, nu_max, n_thresh)

    # CubicalComplex su -field (sublevel di -field = superlevel di field)
    field_neg = -field
    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()

    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def process_diag(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        finite = np.isfinite(d[:, 1])
        df = d[finite]
        # Fix v3: birth_s = -col0, death_s = -col1 (convenzione corretta)
        birth = -df[:, 0]
        death = -df[:, 1]
        pers  = birth - death   # > 0 per definizione
        return birth, death, pers

    birth_0, death_0, pers_0 = process_diag(diag_0)
    birth_1, death_1, pers_1 = process_diag(diag_1)

    # Betti curves — thresholds e birth/death in coordinate originali
    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    feats = np.zeros(8, dtype=np.float32)

    # b1 features dalla curva di Betti
    if b1_curve.max() > 0:
        pk_idx   = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])
        feats[1] = float(b1_curve[pk_idx])
        half     = b1_curve.max() / 2.0
        above    = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) \
                   if len(above) > 1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))

    # b2 features dal diagramma di persistenza
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))
        feats[5] = float(np.mean(pers_1))
        p90      = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))

    # b0_at_mean
    mean_val = float(field[mask].mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_val))
    feats[7] = float(b0_curve[idx_mean])

    diag_info = {
        "n_loops_beta1": int(len(pers_1)),
        "n_components_beta0": int(len(pers_0)),
        "b1_curve_max": float(b1_curve.max()),
        "nu_min": float(nu_min),
        "nu_max": float(nu_max),
        "persistence_mean": float(np.mean(pers_1)) if len(pers_1) > 0 else 0.0,
        "persistence_std":  float(np.std(pers_1))  if len(pers_1) > 0 else 0.0,
    }
    # Raw H1 persistence pairs — needed for persistence diagram figure (paper fig3)
    # birth_1 and death_1 are already in field coordinates (fix v3 applied above)
    raw_pairs = {
        "birth_h1": birth_1,   # ndarray, shape (N_h1,)
        "death_h1": death_1,   # ndarray, shape (N_h1,)
    }
    return feats, diag_info, raw_pairs


def run_tda_region(region):
    """Calcola feature TDA per una regione NGC/SGC con bootstrap jackknife."""
    delta_file = FLD_DIR / f"bgs_{region.lower()}_delta_128.npy"
    mask_file  = FLD_DIR / f"bgs_{region.lower()}_mask_128.npy"

    assert delta_file.exists(), f"Mancante: {delta_file}"
    assert mask_file.exists(),  f"Mancante: {mask_file}"

    print(f"\n{'='*60}")
    print(f"TDA BGS {region}")
    print(f"{'='*60}")

    delta = np.load(delta_file)
    mask  = np.load(mask_file)

    print(f"  Campo: {delta.shape}, dtype={delta.dtype}")
    print(f"  Voxel validi: {mask.sum():,} ({100*mask.mean():.1f}%)")
    print(f"  delta: mean={delta[mask].mean():.4f}  std={delta[mask].std():.4f}")

    # --- Feature TDA sul campo completo ---
    print(f"  Calcolo TDA (n_thresh={args.n_thresh})...")
    t0 = time.time()
    feats, diag_info, raw_pairs = compute_tda_features(delta, mask, args.n_thresh)
    t_tda = time.time() - t0
    print(f"  Completato in {t_tda:.1f}s")

    feature_names = [
        'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
        'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
    ]
    print(f"\n  Feature TDA:")
    for j, (name, val) in enumerate(zip(feature_names, feats)):
        zero_flag = "  <- zero" if val == 0.0 else ""
        print(f"    {name:<25}: {val:14.4f}{zero_flag}")

    # --- Bootstrap jackknife per incertezze ---
    # Solo se la regione ha abbastanza galassie (NGC ha 217k, SGC 82k)
    feats_bootstrap = []
    if mask.sum() > 100000 and args.n_bootstrap > 0:
        print(f"\n  Bootstrap jackknife ({args.n_bootstrap} patch)...")
        rng = np.random.default_rng(args.seed)

        # Divide i voxel validi in n_bootstrap patch casuali
        valid_idx = np.argwhere(mask)  # [N_valid, 3]
        n_valid   = len(valid_idx)
        patch_ids = rng.integers(0, args.n_bootstrap, size=n_valid)

        t_bs = time.time()
        for patch in range(args.n_bootstrap):
            # Leave-one-out: escludi patch corrente
            delta_bs = delta.copy()
            excl_idx = valid_idx[patch_ids == patch]
            delta_bs[excl_idx[:, 0], excl_idx[:, 1], excl_idx[:, 2]] = 0.0
            mask_bs = mask.copy()
            mask_bs[excl_idx[:, 0], excl_idx[:, 1], excl_idx[:, 2]] = False

            if mask_bs.sum() < 50000:
                continue

            feats_bs, _, _ = compute_tda_features(delta_bs, mask_bs, args.n_thresh)
            feats_bootstrap.append(feats_bs)

            if (patch + 1) % 5 == 0:
                print(f"    patch {patch+1}/{args.n_bootstrap}  "
                      f"({time.time()-t_bs:.0f}s)")

        if feats_bootstrap:
            feats_arr = np.array(feats_bootstrap)
            # Errore jackknife: std * sqrt((n-1)/n * n)  = std * sqrt(n-1)
            n_bs = len(feats_arr)
            feats_err = np.std(feats_arr, axis=0) * np.sqrt(n_bs - 1)
            print(f"  Incertezze jackknife ({n_bs} patch validi):")
            for name, val, err in zip(feature_names, feats, feats_err):
                if val != 0:
                    print(f"    {name:<25}: {val:.4f} +/- {err:.4f} "
                          f"({100*err/abs(val):.1f}%)")
        else:
            feats_err = np.zeros(8, dtype=np.float32)
    else:
        feats_err = np.zeros(8, dtype=np.float32)
        print("  Bootstrap saltato (insufficiente copertura)")

    elapsed = time.time() - t0
    return {
        "region": region,
        "features": feats.tolist(),
        "features_err_jackknife": feats_err.tolist(),
        "feature_names": feature_names,
        "n_bootstrap_valid": len(feats_bootstrap),
        "tda_diagnostics": diag_info,
        "delta_mean": float(delta[mask].mean()),
        "delta_std":  float(delta[mask].std()),
        "n_valid_voxels": int(mask.sum()),
        "elapsed_s": float(elapsed),
        "_raw_pairs": raw_pairs,   # not serialised to JSON (popped before json.dump)
    }


# ---------------------------------------------------------------------------
# Confronto con prior nwLH (Phase 5 B3)
# ---------------------------------------------------------------------------
def compare_with_prior(feats_desi, region_label):
    """
    Posiziona le feature DESI rispetto alla distribuzione dei mock nwLH.
    Carica results/phase5_hod_b3_features.npz se disponibile.
    """
    prior_file = RES_DIR / "phase5_hod_b3_features.npz"
    if not prior_file.exists():
        return {"status": "prior_not_found", "note": "Eseguire Phase 5 prima"}

    data  = np.load(prior_file, allow_pickle=True)
    fvecs = data['fvecs_hod_b3']  # [2000, 8]
    w0    = data['w0']

    feature_names = [
        'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
        'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
    ]

    prior_stats = {}
    desi_in_prior = True

    for j, name in enumerate(feature_names):
        f_mock = fvecs[:, j]
        f_desi = feats_desi[j]
        if f_mock.std() == 0:
            continue
        percentile = float(np.mean(f_mock < f_desi) * 100)
        z_score = float((f_desi - f_mock.mean()) / f_mock.std())
        in_range = abs(z_score) < 3.0
        if not in_range:
            desi_in_prior = False
        prior_stats[name] = {
            "desi_value": float(f_desi),
            "mock_mean": float(f_mock.mean()),
            "mock_std":  float(f_mock.std()),
            "z_score": z_score,
            "percentile": percentile,
            "in_3sigma_prior": in_range,
        }

    return {
        "status": "completed",
        "desi_in_prior_3sigma": desi_in_prior,
        "feature_comparison": prior_stats,
        "note": "z_score = (DESI - mock_mean) / mock_std"
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
results = {
    "schema_version": "2.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "n_thresh": args.n_thresh,
    "n_bootstrap": args.n_bootstrap,
    "tda_convention": "birth=-diag[:,0], death=-diag[:,1], pers=birth-death>0 (fix v3)",
    "regions": {}
}

for region in ["NGC", "SGC"]:
    delta_f = FLD_DIR / f"bgs_{region.lower()}_delta_128.npy"
    if not delta_f.exists():
        print(f"  {region}: campo non trovato, skip")
        continue
    results["regions"][region] = run_tda_region(region)

# Confronto con prior Phase 5
print(f"\n{'='*70}")
print("Confronto con prior nwLH Phase 5 (B3)")
print(f"{'='*70}")

for region, info in results["regions"].items():
    print(f"\n  {region}:")
    comp = compare_with_prior(np.array(info["features"]), region)
    results["regions"][region]["prior_comparison"] = comp
    if comp["status"] == "completed":
        in_p = comp["desi_in_prior_3sigma"]
        print(f"  DESI dentro prior 3sigma: {'SI' if in_p else 'NO (extrapolazione!)'}")
        for name, stat in comp["feature_comparison"].items():
            if stat["mock_std"] > 0 and stat["desi_value"] != 0:
                print(f"    {name:<25}: z={stat['z_score']:+.2f}  "
                      f"percentile={stat['percentile']:.0f}%")
    else:
        print(f"  {comp['note']}")

# Salva — strip non-serialisable _raw_pairs before dumping
results_for_json = {
    "schema_version": results["schema_version"],
    "timestamp": results["timestamp"],
    "n_thresh": results["n_thresh"],
    "n_bootstrap": results["n_bootstrap"],
    "tda_convention": results["tda_convention"],
    "regions": {
        reg: {k: v for k, v in info.items() if k != "_raw_pairs"}
        for reg, info in results["regions"].items()
    }
}
out_file = RES_DIR / "phase6_bgs_tda_features.json"
with open(out_file, "w") as f:
    json.dump(results_for_json, f, indent=2)

print(f"\n{'='*70}")
print("RIEPILOGO")
print(f"{'='*70}")
for region, info in results["regions"].items():
    feats = info["features"]
    print(f"\n  {region}:")
    print(f"    b2_mean_persistence: {feats[5]:.4f}  "
          f"(Phase5 mock range: [-0.32, -0.21] -> atteso positivo con fix v3)")
    print(f"    b1_peak_height:      {feats[1]:.0f}")
    print(f"    b2_max_count:        {feats[4]:.0f}")
    print(f"    Tempo:               {info['elapsed_s']:.0f}s")

print(f"\n  Output: {out_file}")
print(f"\nProssimo: python src/phase6_mock_calibration.py")
print(f"{'='*70}")

# ---------------------------------------------------------------------------
# Save raw H1 persistence pairs for fig3 (persistence diagram)
# ---------------------------------------------------------------------------
# We save the NGC raw pairs (DESI) from the full-field TDA run above.
# For the mock panel we save a stub with empty arrays — the caller should
# re-run compute_tda_features on a single representative mock field and
# merge the output, or generate the mock pairs via phase7_make_mock_diag.py.
# The NGC raw_pairs dict is stored in results["regions"]["NGC"]["_raw_pairs"]
# during run_tda_region; we extract it here.

raw_out = RES_DIR / "phase6_bgs_persistence_raw.npz"
try:
    ngc_raw = results["regions"]["NGC"].pop("_raw_pairs", None)
    if ngc_raw is not None:
        np.savez(
            str(raw_out),
            birth_desi=ngc_raw["birth_h1"],
            death_desi=ngc_raw["death_h1"],
            birth_mock=np.array([]),   # placeholder — fill with mock run
            death_mock=np.array([]),   # placeholder — fill with mock run
        )
        print(f"\n  Raw persistence pairs saved: {raw_out}")
        print(f"  N(H1, DESI NGC) = {len(ngc_raw['birth_h1']):,}")
        print("  Note: birth_mock/death_mock are empty placeholders.")
        print("  To populate, run compute_tda_features on one mock field and")
        print("  re-save with: np.savez(..., birth_mock=..., death_mock=...)")
    else:
        print("\n  [WARN] _raw_pairs not found — phase6_bgs_persistence_raw.npz not saved")
except Exception as e:
    print(f"\n  [WARN] Could not save raw persistence pairs: {e}")
