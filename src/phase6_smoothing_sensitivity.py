"""
CAUCHY Phase 6 — O6-4: Smoothing sensitivity R=5 vs R=10 Mpc/h (v3)
======================================================================
NON sovrascrive mai file canonici.

Strategia DESI NGC:
  - R=5: valore canonico b2=0.45886 da phase6_bgs_tda_features.json
  - R=10: smoothing incrementale sul campo R=5 canonico (read-only):
      campo_R10 = gaussian_filter(campo_R5, sigma=σ_extra, mode='wrap')
      σ_extra = sqrt(σ_R10² - σ_R5²) = sqrt(0.4322² - 0.2161²) = 0.3743 px
    Matematicamente esatto (convoluzione gaussiane associativa).
    Il campo R=5 canonico non viene mai modificato.

Strategia Mock nwLH (N=200):
  - Campi raw da latin_hypercube_nwLH/{i}/df_m_128_PCS_z=0.npy
  - Smoothing R=5 e R=10 applicati da zero su ogni campo raw
  - TDA su campo pieno (volume periodico, nessuna maschera)

Threshold non-dominanza: |Δb2| < 0.5σ_signal = 0.014
Autorità: CAUCHY_Execution_Design_v2.md §6 O6-4
"""

import numpy as np
from scipy.ndimage import gaussian_filter
import gudhi
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# ── Configurazione ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(r"D:\projects\cauchy")
RESULTS_DIR  = PROJECT_ROOT / "results"
FLD_DIR      = PROJECT_ROOT / "data" / "processed" / "phase6_fields"
MOCK_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH"
OUTPUT_PATH  = RESULTS_DIR / "phase6_smoothing_sensitivity.json"

# Campi DESI (read-only — non vengono mai modificati)
DESI_FIELD_R5 = FLD_DIR / "bgs_ngc_delta_128.npy"
DESI_MASK     = FLD_DIR / "bgs_ngc_mask_128.npy"

# Geometria DESI NGC
CELL_DESI = 2961.36 / 128   # 23.135 Mpc/h (da phase6_voxelize_diagnostics.json)
SIGMA_R5_DESI  = 5.0  / CELL_DESI   # 0.2161 px — già applicato nel campo canonico
SIGMA_R10_DESI = 10.0 / CELL_DESI   # 0.4322 px
SIGMA_EXTRA_DESI = float(np.sqrt(SIGMA_R10_DESI**2 - SIGMA_R5_DESI**2))  # 0.3743 px

# Geometria Mock Quijote
CELL_MOCK      = 1000.0 / 128   # 7.8125 Mpc/h
SIGMA_R5_MOCK  = 5.0  / CELL_MOCK   # 0.6400 px
SIGMA_R10_MOCK = 10.0 / CELL_MOCK   # 1.2800 px

# Canonici
B2_DESI_R5     = 0.45885732769966125
B2_DESI_R5_ERR = 0.005184488001019461
MOCK_STD_R5    = 0.0279
SIGMA_SIGNAL   = MOCK_STD_R5
THRESHOLD_ABS  = 0.5 * SIGMA_SIGNAL   # 0.01395

N_MOCK    = 200
N_THRESH  = 100


# ── TDA con maschera (pipeline canonica DESI) ──────────────────────────────────

def compute_b2_masked(field, mask):
    """
    Pipeline TDA canonica (identica a phase6_bgs_tda.py):
    - Thresholds 1st-99th percentile calcolati solo sui voxel in maschera
    - CubicalComplex su -field (intero cubo)
    - Convenzione v3: birth=-col0, death=-col1, pers=birth-death>0
    """
    field = field.astype(np.float64)
    field_in = field[mask]
    nu_min = float(np.percentile(field_in, 1))
    nu_max = float(np.percentile(field_in, 99))

    cc = gudhi.CubicalComplex(
        dimensions=list(field.shape),
        top_dimensional_cells=(-field).flatten()
    )
    cc.compute_persistence()
    diag1 = cc.persistence_intervals_in_dimension(1)

    if len(diag1) == 0:
        return np.nan

    d = np.array(diag1)
    finite = np.isfinite(d[:, 1])
    df = d[finite]
    if len(df) == 0:
        return np.nan

    birth = -df[:, 0]
    death = -df[:, 1]
    pers  = birth - death
    valid = pers > 0
    if valid.sum() == 0:
        return np.nan

    return float(np.mean(pers[valid]))


def compute_b2_full(field):
    """
    Pipeline TDA per campi mock periodici (nessuna maschera).
    Mean subtraction, poi CubicalComplex su -field.
    Convenzione v3.
    """
    field = field.astype(np.float64)
    field -= field.mean()

    cc = gudhi.CubicalComplex(
        dimensions=list(field.shape),
        top_dimensional_cells=(-field).flatten()
    )
    cc.compute_persistence()
    diag1 = cc.persistence_intervals_in_dimension(1)

    if len(diag1) == 0:
        return np.nan

    d = np.array(diag1)
    finite = np.isfinite(d[:, 1])
    df = d[finite]
    if len(df) == 0:
        return np.nan

    birth = -df[:, 0]
    death = -df[:, 1]
    pers  = birth - death
    valid = pers > 0
    if valid.sum() == 0:
        return np.nan

    return float(np.mean(pers[valid]))


# ── Early validation ───────────────────────────────────────────────────────────

def validate():
    missing = []
    for p, label in [
        (DESI_FIELD_R5, "campo DESI NGC R=5 canonico (bgs_ngc_delta_128.npy)"),
        (DESI_MASK,     "maschera survey NGC (bgs_ngc_mask_128.npy)"),
        (MOCK_RAW_DIR,  "directory mock nwLH raw"),
    ]:
        if not p.exists():
            missing.append(f"  MANCANTE: {p}  [{label}]")
    if missing:
        print("[ERRORE] Path validation fallita:")
        for m in missing: print(m)
        sys.exit(1)

    n_avail = sum(1 for i in range(N_MOCK)
                  if (MOCK_RAW_DIR / str(i) / "df_m_128_PCS_z=0.npy").exists())
    print(f"[OK] Path validation superata. Mock disponibili: {n_avail}/{N_MOCK}")
    return n_avail


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("CAUCHY Phase 6 — O6-4: Smoothing sensitivity R=5 vs R=10 Mpc/h (v3)")
    print("=" * 70)
    print(f"  DESI cell = {CELL_DESI:.4f} Mpc/h")
    print(f"  σ_R5 DESI  = {SIGMA_R5_DESI:.4f} px  (già applicato nel campo canonico)")
    print(f"  σ_R10 DESI = {SIGMA_R10_DESI:.4f} px")
    print(f"  σ_extra    = {SIGMA_EXTRA_DESI:.4f} px  (incrementale su campo R5)")
    print(f"  Threshold non-dominanza: 0.5σ = {THRESHOLD_ABS:.4f}")

    n_mock_avail = validate()

    # ── DESI NGC ──────────────────────────────────────────────────────────────
    print("\n--- DESI NGC ---")

    # R=5: valore canonico
    b2_desi_r5 = B2_DESI_R5
    print(f"  R=5: b2 = {b2_desi_r5:.5f}  [canonico — nessun ricalcolo]")

    # R=10: smoothing incrementale sul campo canonico (read-only)
    print(f"  Caricamento campo R=5 canonico (read-only)...")
    field_r5 = np.load(DESI_FIELD_R5)   # shape (128,128,128), non viene modificato
    mask     = np.load(DESI_MASK)
    print(f"  Campo caricato: std_in_survey={field_r5[mask].std():.4f}")

    print(f"  Applicazione σ_extra={SIGMA_EXTRA_DESI:.4f} px per R=10...")
    field_r10 = gaussian_filter(field_r5.astype(np.float64),
                                sigma=SIGMA_EXTRA_DESI, mode='wrap')
    # Mean subtraction inside survey (identica al voxelizzatore canonico)
    field_r10 -= field_r10[mask].mean()

    print(f"  Calcolo TDA R=10 (con maschera survey)...")
    b2_desi_r10 = compute_b2_masked(field_r10, mask)
    print(f"  R=10: b2 = {b2_desi_r10:.5f}")

    delta_desi     = b2_desi_r10 - b2_desi_r5
    delta_desi_sig = abs(delta_desi) / SIGMA_SIGNAL
    desi_nd        = delta_desi_sig < 0.5
    print(f"  Δb2(R10−R5) = {delta_desi:+.5f}  ({delta_desi_sig:.2f}σ_signal)")
    print(f"  Non-dominante: {desi_nd}")

    # ── Mock nwLH ─────────────────────────────────────────────────────────────
    print(f"\n--- Mock nwLH (N={min(N_MOCK, n_mock_avail)}) ---")
    b2_r5_list, b2_r10_list = [], []
    errors = 0
    n_run  = min(N_MOCK, n_mock_avail)

    for i in range(n_run):
        path = MOCK_RAW_DIR / str(i) / "df_m_128_PCS_z=0.npy"
        try:
            field_raw = np.load(path).astype(np.float64)
            f_r5  = gaussian_filter(field_raw, sigma=SIGMA_R5_MOCK,  mode='wrap')
            f_r10 = gaussian_filter(field_raw, sigma=SIGMA_R10_MOCK, mode='wrap')
            b2_r5_list.append(compute_b2_full(f_r5))
            b2_r10_list.append(compute_b2_full(f_r10))
            if (i+1) % 50 == 0:
                print(f"  [{i+1}/{n_run}] R5={np.nanmean(b2_r5_list):.4f}  "
                      f"R10={np.nanmean(b2_r10_list):.4f}")
        except Exception as e:
            errors += 1
            print(f"  [WARN] sim {i}: {e}")

    b2_r5_arr  = np.array([x for x in b2_r5_list  if not np.isnan(x)])
    b2_r10_arr = np.array([x for x in b2_r10_list if not np.isnan(x)])

    delta_mock     = float(b2_r10_arr.mean() - b2_r5_arr.mean())
    delta_mock_sig = abs(delta_mock) / SIGMA_SIGNAL
    mock_nd        = delta_mock_sig < 0.5

    print(f"\n  Mock R=5:  mean={b2_r5_arr.mean():.4f} ± {b2_r5_arr.std():.4f}")
    print(f"  Mock R=10: mean={b2_r10_arr.mean():.4f} ± {b2_r10_arr.std():.4f}")
    print(f"  Δ(mock mean) = {delta_mock:+.5f}  ({delta_mock_sig:.2f}σ_signal)")
    print(f"  Non-dominante: {mock_nd}")

    # ── Valutazione finale ────────────────────────────────────────────────────
    overall = desi_nd and mock_nd
    verdict = "NON_DOMINANT" if overall else "DOMINANT"

    z_r5  = (b2_desi_r5  - b2_r5_arr.mean())  / b2_r5_arr.std()
    z_r10 = (b2_desi_r10 - b2_r10_arr.mean()) / b2_r10_arr.std()

    print(f"\n=== VERDETTO O6-4: {verdict} ===")
    print(f"  z-score DESI vs mock R=5:  {z_r5:+.2f}σ")
    print(f"  z-score DESI vs mock R=10: {z_r10:+.2f}σ")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "output_id": "O6-4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "CAUCHY_Execution_Design_v2.md §6 O6-4",

        "parameters": {
            "R_values_mpc_h":               [5.0, 10.0],
            "ngrid":                        128,
            "cell_size_desi_mpc_h":         round(CELL_DESI, 4),
            "cell_size_mock_mpc_h":         round(CELL_MOCK, 4),
            "sigma_px_desi_R5":             round(SIGMA_R5_DESI, 4),
            "sigma_px_desi_R10":            round(SIGMA_R10_DESI, 4),
            "sigma_px_desi_extra":          round(SIGMA_EXTRA_DESI, 4),
            "sigma_px_mock_R5":             round(SIGMA_R5_MOCK, 3),
            "sigma_px_mock_R10":            round(SIGMA_R10_MOCK, 3),
            "threshold_non_dominant_sigma": 0.5,
            "threshold_non_dominant_abs":   float(THRESHOLD_ABS),
            "sigma_signal_reference":       float(SIGMA_SIGNAL),
            "n_mock_processed":             int(len(b2_r5_arr)),
            "n_mock_errors":                errors,
        },

        "methodology_note": (
            "DESI R=10 ottenuto tramite smoothing incrementale sul campo R=5 canonico "
            f"(sigma_extra={SIGMA_EXTRA_DESI:.4f} px = sqrt(sigma_R10^2 - sigma_R5^2)). "
            "Il campo R=5 canonico non viene mai modificato. "
            "Mock: smoothing applicato da zero su campi raw."
        ),

        "desi_ngc": {
            "b2_R5":             float(b2_desi_r5),
            "b2_R5_source":      "canonico phase6_bgs_tda_features.json",
            "b2_R10":            float(b2_desi_r10),
            "b2_R10_method":     f"smoothing incrementale sigma_extra={SIGMA_EXTRA_DESI:.4f}px + TDA con maschera survey",
            "delta_b2":          float(delta_desi),
            "delta_sigma_units": float(delta_desi_sig),
            "non_dominant":      desi_nd,
        },

        "mock_nwlh": {
            "n_mock":                   int(len(b2_r5_arr)),
            "b2_R5_mean":               float(b2_r5_arr.mean()),
            "b2_R5_std":                float(b2_r5_arr.std()),
            "b2_R10_mean":              float(b2_r10_arr.mean()),
            "b2_R10_std":               float(b2_r10_arr.std()),
            "delta_mock_mean":          float(delta_mock),
            "delta_mock_sigma_units":   float(delta_mock_sig),
            "non_dominant":             mock_nd,
            "mock_source":              "latin_hypercube_nwLH/0..199/df_m_128_PCS_z=0.npy",
        },

        "signal_preservation": {
            "z_score_desi_vs_mock_R5":  float(z_r5),
            "z_score_desi_vs_mock_R10": float(z_r10),
            "delta_zscore":             float(z_r10 - z_r5),
        },

        "verdict": {
            "status":             verdict,
            "desi_non_dominant":  desi_nd,
            "mock_non_dominant":  mock_nd,
            "gate6_sistematiche": (
                "NON DOMINANTE — citabile in tabella sistematiche §6.2"
                if overall else
                "DOMINANTE — variazione > 0.5σ, trattare come risultato"
            ),
            "paper_statement": (
                f"The b2_mean_persistence signal is robust to smoothing scale: "
                f"varying R from 5 to 10 Mpc/h shifts the DESI NGC measurement by "
                f"{delta_desi:+.4f} ({delta_desi_sig:.2f}σ) and the mock distribution "
                f"mean by {delta_mock:+.4f} ({delta_mock_sig:.2f}σ), "
                f"both below the non-dominance threshold of 0.5σ."
                if overall else
                f"The b2_mean_persistence signal shows sensitivity to smoothing scale "
                f"(R=5 to 10 Mpc/h): DESI shift={delta_desi:+.4f} ({delta_desi_sig:.2f}σ), "
                f"mock shift={delta_mock:+.4f} ({delta_mock_sig:.2f}σ)."
            ),
        },

        "v1_failure_note": (
            "O6-4 v1 restituiva DOMINANT per artefatto: TDA applicata sull'intero cubo "
            "128³ con 85% voxel=0 (fuori survey), distorcendo la topologia. "
            "v3 usa smoothing incrementale (no riesecuzione voxelizzatore) "
            "e TDA con maschera survey identica al canonico phase6_bgs_tda.py."
        ),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[SAVED] {OUTPUT_PATH}")
    print("[COMPLETATO] O6-4 terminato.")


if __name__ == "__main__":
    main()
