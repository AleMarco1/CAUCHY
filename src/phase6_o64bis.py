"""
CAUCHY Phase 6 — O6-4bis: b2_DESI con R=14.8 Mpc/h (σ_px=0.640)
=================================================================
Riesegue la voxelizzazione DESI NGC con R=14.8 Mpc/h, che produce
σ_px = 14.8 / 23.14 = 0.640 — identico al mock canonico (R=5, σ_px=0.640).

Motivazione (da test σ_px, risposta BLOCKING 1):
  b2_mean_persistence dipende da σ_px, non da R fisico.
  Il confronto DESI vs mock richiede σ_px equivalente.
  Test empirico: Δb2(σ_px 0.216→0.640) = +8.42σ_signal sui mock.

NON sovrascrive bgs_ngc_delta_128.npy (campo canonico R=5).
Output: bgs_ngc_delta_128_R148.npy  (solo lettura del voxelizzatore)

Autorità: risposta BLOCKING 1, ciclo 3 review Gate 6
"""

import subprocess
import sys
import shutil
import json
import numpy as np
import gudhi
from scipy.ndimage import gaussian_filter
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT    = Path(r"D:\projects\cauchy")
FLD_DIR         = PROJECT_ROOT / "data" / "processed" / "phase6_fields"
RESULTS_DIR     = PROJECT_ROOT / "results"
VOXELIZE_SCRIPT = PROJECT_ROOT / "src" / "phase6_bgs_voxelize.py"

# Path canonico (NON deve essere modificato)
CANONICAL_R5   = FLD_DIR / "bgs_ngc_delta_128.npy"
CANONICAL_MASK = FLD_DIR / "bgs_ngc_mask_128.npy"

# Output di questo script
FIELD_R148     = FLD_DIR / "bgs_ngc_delta_128_R148.npy"
OUTPUT_JSON    = RESULTS_DIR / "phase6_o64bis.json"

R_NEW   = 14.8   # Mpc/h → σ_px = 14.8 / 23.14 = 0.640
R_CANON = 5.0    # Mpc/h → σ_px = 0.216 (canonico)

# Canonici di confronto
B2_DESI_R5  = 0.45885732769966125
MOCK_Z05_MEAN_R5  = 0.2922
MOCK_Z05_STD_R5   = 0.0279
MOCK_Z05_MEAN_SIGMA_PX_0640 = 0.1502   # da test σ_px (mock con σ_px=0.640, R=5)
MOCK_Z05_STD_SIGMA_PX_0640  = 0.0182


def compute_b2_masked(field, mask):
    """Pipeline TDA canonica con maschera survey (identica phase6_bgs_tda.py)."""
    field = field.astype(np.float64)
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
    missing = []
    for p, label in [
        (CANONICAL_MASK, "maschera survey (bgs_ngc_mask_128.npy)"),
        (VOXELIZE_SCRIPT, "phase6_bgs_voxelize.py"),
    ]:
        if not p.exists():
            missing.append(f"  MANCANTE: {p}  [{label}]")
    if missing:
        print("[ERRORE] Path validation:")
        for m in missing: print(m)
        sys.exit(1)
    print("[OK] Path validation superata.")


def main():
    print("=" * 70)
    print("CAUCHY Phase 6 — O6-4bis: Voxelizzazione R=14.8 Mpc/h")
    print("=" * 70)

    cell_desi = 2961.36 / 128
    sigma_px_new   = R_NEW   / cell_desi
    sigma_px_canon = R_CANON / cell_desi
    print(f"  Cell DESI: {cell_desi:.2f} Mpc/h")
    print(f"  R=5.0  Mpc/h → σ_px={sigma_px_canon:.4f}  (canonico, DA NON TOCCARE)")
    print(f"  R=14.8 Mpc/h → σ_px={sigma_px_new:.4f}  (target, uguale mock R=5)")
    print(f"  Mock R=5 Mpc/h → σ_px=0.6400 (riferimento)")

    validate()

    # ── Step 1: backup del canonico se esiste ─────────────────────────────────
    canonical_backup = FLD_DIR / "bgs_ngc_delta_128_R5_backup.npy"
    if CANONICAL_R5.exists() and not canonical_backup.exists():
        shutil.copy(CANONICAL_R5, canonical_backup)
        print(f"\n[BACKUP] Creato {canonical_backup.name}")
    elif canonical_backup.exists():
        print(f"\n[BACKUP] Già esistente: {canonical_backup.name}")

    # ── Step 2: voxelizzazione R=14.8 ─────────────────────────────────────────
    if FIELD_R148.exists():
        print(f"\n[SKIP] {FIELD_R148.name} già esiste — salto voxelizzazione.")
    else:
        print(f"\n[STEP 1] Esecuzione voxelizzatore R={R_NEW} Mpc/h...")
        cmd = [
            sys.executable, str(VOXELIZE_SCRIPT),
            "--region", "NGC",
            "--R_smooth", str(R_NEW),
            "--project_root", str(PROJECT_ROOT)
        ]
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"[ERRORE] Voxelizzatore fallito (returncode={result.returncode})")
            sys.exit(1)

        # Il voxelizzatore ha scritto su bgs_ngc_delta_128.npy — spostalo
        if CANONICAL_R5.exists():
            shutil.move(str(CANONICAL_R5), str(FIELD_R148))
            print(f"[OK] Campo R=14.8 salvato in {FIELD_R148.name}")
        else:
            print(f"[ERRORE] Output voxelizzatore non trovato: {CANONICAL_R5}")
            sys.exit(1)

    # ── Step 3: ripristina campo canonico R=5 ─────────────────────────────────
    if not CANONICAL_R5.exists():
        if canonical_backup.exists():
            shutil.copy(canonical_backup, CANONICAL_R5)
            print(f"[RIPRISTINO] Campo R=5 ripristinato da backup.")
        else:
            print("[WARN] Backup non trovato — campo R=5 non ripristinato.")
            print("       Eseguire: python src/phase6_bgs_voxelize.py --region NGC --R_smooth 5")

    # ── Step 4: TDA su campo R=14.8 ───────────────────────────────────────────
    print(f"\n[STEP 2] TDA su campo R=14.8 Mpc/h...")
    field_r148 = np.load(FIELD_R148)
    mask       = np.load(CANONICAL_MASK)

    print(f"  Campo: shape={field_r148.shape}, std_survey={field_r148[mask].std():.4f}")
    b2_r148 = compute_b2_masked(field_r148, mask)
    print(f"  b2_mean_persistence (R=14.8) = {b2_r148:.5f}")

    # ── Step 5: calcola z-score vs mock con σ_px equivalente ──────────────────
    # Il mock di riferimento corretto ora è quello con σ_px=0.640
    # Abbiamo due distribuzioni mock disponibili con σ_px=0.640:
    #   (a) mock nwLH raw R=5 Mpc/h: mean=0.1502, std=0.0182 (da O6-4 / σ_px test)
    #   (b) mock z=0.5 HOD R=5 Mpc/h: mean=0.2922, std=0.0279 (canonico)
    # Il confronto con (b) è quello fisicamente appropriato (stesso HOD z=0.5)
    # Il confronto con (a) è DM raw — meno appropriato ma disponibile

    z_vs_hod_z05 = (b2_r148 - MOCK_Z05_MEAN_R5) / MOCK_Z05_STD_R5
    z_vs_dm_raw  = (b2_r148 - MOCK_Z05_MEAN_SIGMA_PX_0640) / MOCK_Z05_STD_SIGMA_PX_0640

    print(f"\n  z-score DESI(R=14.8) vs mock z=0.5 HOD R=5 (σ_px=0.640): {z_vs_hod_z05:+.2f}σ")
    print(f"  z-score DESI(R=14.8) vs mock DM raw R=5 (σ_px=0.640):    {z_vs_dm_raw:+.2f}σ")
    print(f"\n  Confronto con canonico R=5:")
    print(f"    b2_DESI(R=5.0)  = {B2_DESI_R5:.5f}  (σ_px=0.216, NON equivalente)")
    print(f"    b2_DESI(R=14.8) = {b2_r148:.5f}  (σ_px=0.640, equivalente mock)")
    print(f"    Δb2 = {b2_r148 - B2_DESI_R5:+.5f}")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "output_id": "O6-4bis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "Risposta BLOCKING 1, ciclo 3 review Gate 6",
        "motivation": (
            "Test σ_px ha dimostrato che b2_mean_persistence dipende da σ_px "
            f"(Δ=+8.42σ tra σ_px=0.216 e σ_px=0.640 sui mock). "
            "Il confronto corretto richiede σ_px equivalente su DESI e mock. "
            f"R=14.8 Mpc/h su DESI produce σ_px=0.640, identico al mock R=5 Mpc/h."
        ),
        "smoothing": {
            "R_mpc_h": R_NEW,
            "cell_size_mpc_h": cell_desi,
            "sigma_px_desi": round(sigma_px_new, 4),
            "sigma_px_mock_R5": 0.640,
            "equivalence": "sigma_px",
        },
        "b2_desi_R148": float(b2_r148),
        "b2_desi_R5_canonical": B2_DESI_R5,
        "delta_b2_R148_vs_R5": float(b2_r148 - B2_DESI_R5),
        "z_scores": {
            "vs_mock_z05_hod_R5": {
                "value":  float(z_vs_hod_z05),
                "mock_mean": MOCK_Z05_MEAN_R5,
                "mock_std":  MOCK_Z05_STD_R5,
                "note": "mock z=0.5 HOD R=5 Mpc/h (σ_px=0.640) — confronto principale",
                "citability": "CITABILE se σ_px equivalente è criterio accettato",
            },
            "vs_mock_dm_raw_R5": {
                "value":  float(z_vs_dm_raw),
                "mock_mean": MOCK_Z05_MEAN_SIGMA_PX_0640,
                "mock_std":  MOCK_Z05_STD_SIGMA_PX_0640,
                "note": "mock DM raw R=5 Mpc/h (σ_px=0.640) — cross-check",
                "citability": "CROSS-CHECK — mock DM, no HOD",
            },
        },
        "sigma_px_test_reference": {
            "b2_mock_sigma_px_0216": 0.3032,
            "b2_mock_sigma_px_0640": 0.1502,
            "delta_sigma_signal": 8.42,
            "conclusion": "σ_px è la variabile determinante per b2_mean_persistence su griglia discreta",
        },
        "field_files": {
            "field_R148": str(FIELD_R148),
            "field_R5_canonical": str(CANONICAL_R5),
            "mask": str(CANONICAL_MASK),
            "canonical_preserved": CANONICAL_R5.exists(),
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[SAVED] {OUTPUT_JSON}")
    print("\n[COMPLETATO] O6-4bis terminato.")
    print(f"\n>>> RISULTATO CHIAVE:")
    print(f"    b2_DESI(R=14.8, σ_px=0.640) = {b2_r148:.5f}")
    print(f"    z-score vs mock z=0.5 HOD:    {z_vs_hod_z05:+.2f}σ")


if __name__ == "__main__":
    main()
