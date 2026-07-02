"""
CAUCHY Phase 6 — Test σ_px (risposta BLOCKING 1)
=================================================
Verifica se b2_mean_persistence dipende da σ_px (adimensionale) a parità
di scala fisica R in Mpc/h.

Il reviewer (ciclo 1) sostiene che σ_px=0.216 (DESI) vs σ_px=0.640 (mock)
introduce un bias numerico sulla griglia discreta che gonfia b2 su DESI.

Test: calcola b2 su 200 mock nwLH raw con tre smoothing:
  - R=1.69 Mpc/h → σ_px=0.216 (uguale a DESI su box 1000 Mpc/h)
  - R=5.00 Mpc/h → σ_px=0.640 (valore canonico mock)
  - R=10.0 Mpc/h → σ_px=1.280 (già calcolato in O6-4)

Se b2(σ_px=0.216) >> b2(σ_px=0.640): il reviewer ha ragione, il confronto
DESI vs mock è biasato dalla discretizzazione.

Se b2(σ_px=0.216) ≈ b2(σ_px=0.640): il concern 1 è insubstanziale, σ_px
non introduce bias rilevante.

Canone: O6-4 ha già b2_R5_mean=0.150, b2_R10_mean=0.084.
Output: results/phase6_sigma_px_test.json
Autorità: risposta BLOCKING 1, ciclo 3 review Gate 6
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
MOCK_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH"
OUTPUT_PATH  = PROJECT_ROOT / "results" / "phase6_sigma_px_test.json"

CELL_MOCK = 1000.0 / 128   # 7.8125 Mpc/h
N_MOCK    = 200
SEED      = 42

# Tre configurazioni di smoothing
CONFIGS = [
    {"label": "sigma_px_0216", "R_mpc_h": 0.216 * CELL_MOCK, "sigma_px": 0.216,
     "note": "σ_px uguale a DESI (R=1.69 Mpc/h su box 1000 Mpc/h)"},
    {"label": "sigma_px_0640", "R_mpc_h": 5.0,               "sigma_px": 5.0/CELL_MOCK,
     "note": "σ_px canonico mock (R=5 Mpc/h — configurazione O6-4)"},
    {"label": "sigma_px_1280", "R_mpc_h": 10.0,              "sigma_px": 10.0/CELL_MOCK,
     "note": "σ_px doppio (R=10 Mpc/h — già calcolato in O6-4)"},
]

# Canonici da O6-4 (per cross-check)
B2_R5_CANONICAL  = 0.1502   # mock nwLH raw R=5 (O6-4 v3)
B2_R10_CANONICAL = 0.0836   # mock nwLH raw R=10 (O6-4 v3)
B2_DESI_R5       = 0.45885732769966125


def compute_b2(field):
    """b2_mean_persistence con superlevel filtration, convention v3."""
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


def validate():
    if not MOCK_RAW_DIR.exists():
        print(f"[ERRORE] {MOCK_RAW_DIR} non trovata")
        sys.exit(1)
    n = sum(1 for i in range(N_MOCK)
            if (MOCK_RAW_DIR / str(i) / "df_m_128_PCS_z=0.npy").exists())
    print(f"[OK] {n}/{N_MOCK} mock disponibili")
    return n


def main():
    print("=" * 70)
    print("CAUCHY Gate 6 — Test σ_px (risposta BLOCKING 1)")
    print("=" * 70)
    for cfg in CONFIGS:
        print(f"  {cfg['label']}: R={cfg['R_mpc_h']:.2f} Mpc/h, "
              f"σ_px={cfg['sigma_px']:.3f}")
    print(f"  DESI NGC: σ_px=0.216, b2={B2_DESI_R5:.4f}")

    n_avail = validate()
    n_run = min(N_MOCK, n_avail)

    results_per_config = {cfg["label"]: [] for cfg in CONFIGS}
    errors = 0

    print(f"\nProcessamento {n_run} mock...")
    for i in range(n_run):
        path = MOCK_RAW_DIR / str(i) / "df_m_128_PCS_z=0.npy"
        try:
            field_raw = np.load(path).astype(np.float64)
            for cfg in CONFIGS:
                sigma_px = cfg["sigma_px"]
                f_smooth = gaussian_filter(field_raw, sigma=sigma_px, mode='wrap')
                b2 = compute_b2(f_smooth)
                results_per_config[cfg["label"]].append(b2)
        except Exception as e:
            errors += 1
            print(f"  [WARN] sim {i}: {e}")
        if (i + 1) % 50 == 0:
            line = f"  [{i+1}/{n_run}]"
            for cfg in CONFIGS:
                vals = [v for v in results_per_config[cfg["label"]] if not np.isnan(v)]
                if vals:
                    line += f"  {cfg['label']}={np.mean(vals):.4f}"
            print(line)

    # ── Calcola statistiche ────────────────────────────────────────────────────
    print("\n=== RISULTATI ===")
    stats_out = {}
    for cfg in CONFIGS:
        arr = np.array([v for v in results_per_config[cfg["label"]] if not np.isnan(v)])
        mean, std = float(arr.mean()), float(arr.std(ddof=1))
        z_desi = (B2_DESI_R5 - mean) / std
        stats_out[cfg["label"]] = {
            "R_mpc_h":   cfg["R_mpc_h"],
            "sigma_px":  cfg["sigma_px"],
            "note":      cfg["note"],
            "n_mock":    int(len(arr)),
            "b2_mean":   mean,
            "b2_std":    std,
            "z_score_desi": float(z_desi),
        }
        print(f"  {cfg['label']}: b2={mean:.4f}±{std:.4f}, "
              f"z_desi={z_desi:+.2f}σ  [{cfg['note']}]")

    # ── Cross-check con canonici O6-4 ─────────────────────────────────────────
    b2_r5_this  = stats_out["sigma_px_0640"]["b2_mean"]
    b2_r10_this = stats_out["sigma_px_1280"]["b2_mean"]
    print(f"\n  Cross-check O6-4:")
    print(f"    b2_R5  canonico={B2_R5_CANONICAL:.4f}, questo run={b2_r5_this:.4f}, "
          f"diff={abs(b2_r5_this-B2_R5_CANONICAL):.4f}")
    print(f"    b2_R10 canonico={B2_R10_CANONICAL:.4f}, questo run={b2_r10_this:.4f}, "
          f"diff={abs(b2_r10_this-B2_R10_CANONICAL):.4f}")

    # ── Verdetto BLOCKING 1 ────────────────────────────────────────────────────
    b2_lowsig  = stats_out["sigma_px_0216"]["b2_mean"]
    b2_highsig = stats_out["sigma_px_0640"]["b2_mean"]
    delta_sigma_px = b2_lowsig - b2_highsig
    sigma_signal = stats_out["sigma_px_0640"]["b2_std"]
    delta_in_sigma = delta_sigma_px / sigma_signal

    print(f"\n  Differenza b2(σ_px=0.216) - b2(σ_px=0.640) = {delta_sigma_px:+.4f} "
          f"({delta_in_sigma:+.2f}σ_signal)")

    if abs(delta_in_sigma) < 0.5:
        verdict_b1 = "INSUBSTANZIALE"
        interpretation = (
            f"b2_mean_persistence NON è sensibile a σ_px nel range [0.216, 0.640]. "
            f"La differenza è {delta_in_sigma:+.2f}σ_signal < 0.5σ threshold. "
            f"Il concern BLOCKING 1 è insubstanziale: la griglia discreta "
            f"non introduce bias rilevante nel confronto DESI vs mock."
        )
    elif abs(delta_in_sigma) < 1.0:
        verdict_b1 = "BORDERLINE"
        interpretation = (
            f"b2 mostra una sensibilità borderline a σ_px ({delta_in_sigma:+.2f}σ). "
            f"Il concern 1 è parzialmente valido. "
            f"La scelta di equivalenza (fisica vs griglia) deve essere giustificata nel paper."
        )
    else:
        verdict_b1 = "SOSTANZIALE"
        interpretation = (
            f"b2_mean_persistence è sensibile a σ_px ({delta_in_sigma:+.2f}σ). "
            f"Il concern BLOCKING 1 è sostanziale: σ_px diverso introduce "
            f"bias misurabile. Il confronto DESI vs mock richiede correzione."
        )

    print(f"\n  Verdetto BLOCKING 1: {verdict_b1}")
    print(f"  {interpretation}")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "output_id": "phase6_sigma_px_test",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "Risposta BLOCKING 1, ciclo 3 review Gate 6",
        "n_mock": n_run,
        "n_errors": errors,
        "cell_size_mock_mpc_h": CELL_MOCK,
        "b2_desi_r5_canonical": B2_DESI_R5,
        "configs": stats_out,
        "verdict_blocking1": verdict_b1,
        "delta_b2_lowsig_vs_highsig": float(delta_sigma_px),
        "delta_in_sigma_signal": float(delta_in_sigma),
        "interpretation": interpretation,
        "crosscheck_o64": {
            "b2_r5_canonical": B2_R5_CANONICAL,
            "b2_r5_this_run": float(b2_r5_this),
            "b2_r10_canonical": B2_R10_CANONICAL,
            "b2_r10_this_run": float(b2_r10_this),
        },
        "paper_statement": (
            f"To assess the impact of grid discretization on b2_mean_persistence, "
            f"we computed the statistic on 200 nwLH mock fields with three smoothing "
            f"configurations: σ_px=0.216 (matching DESI, R=1.7 Mpc/h), σ_px=0.640 "
            f"(canonical mock, R=5 Mpc/h), and σ_px=1.280 (R=10 Mpc/h). "
            f"The difference between σ_px=0.216 and σ_px=0.640 is "
            f"{delta_sigma_px:+.4f} ({delta_in_sigma:+.2f}σ_signal), "
            f"{'below' if abs(delta_in_sigma) < 0.5 else 'above'} the "
            f"non-dominance threshold of 0.5σ."
        ),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[SAVED] {OUTPUT_PATH}")
    print("[COMPLETATO] Test σ_px terminato.")


if __name__ == "__main__":
    main()
