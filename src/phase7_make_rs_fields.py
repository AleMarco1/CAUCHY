"""
phase7_make_rs_fields.py — CAUCHY Sub-Phase 7.0
Genera campi 3D in redshift space (128^3, PCS MAS) da snapshot Quijote nwLH
usando Pylians3. Output: df_m_128_RS_z=0.npy (stessa convenzione dei campi
real-space precomputati df_m_128_PCS_z=0.npy).

Pipeline:
  1. Legge snapshot HDF5 (snapdir_004/snap_004) — posizioni e velocità DM
  2. Applica RSL.pos_redshift_space (piano-parallelo, LOS = asse 2 = z)
  3. Voxelizza su griglia 128^3 con MASL.density_field_gadget (do_RSD=False
     perché le posizioni sono già in RS) — oppure direttamente con
     MASL.MA su pos RS.
  4. Calcola campo di densità contrasto: delta = rho/<rho> - 1
  5. Salva come float32 .npy nella stessa cartella dello snapshot

Parametri cosmologici nwLH fissi (Quijote docs):
  Omega_m = 0.3175, h = 0.6711
  H(z=0) = 100 * h = 67.11 km/s/(Mpc/h)    [usato da RSL]
  BoxSize = 1000.0 Mpc/h
  z = 0.0  (snapdir_004)

Dipendenze:
  pip install Pylians3 hdf5plugin
  (hdf5plugin necessario per leggere snapshot compressi Blosc)

Uso:
  python phase7_make_rs_fields.py [--test N] [--start I] [--end J]

  --test N   processa solo N sim (default: tutte le 200 del subset)
  --start I  primo indice del subset (default: 0)
  --end   J  ultimo indice escluso (default: 2000)
  --stride S passo tra gli indici (default: 10) → 0,10,20,...

Esempio per test rapido su 3 sim:
  python phase7_make_rs_fields.py --test 3

Esempio per tutte le 200 sim del subset:
  python phase7_make_rs_fields.py
"""

if __name__ == '__main__':
    import sys
    import argparse
    import json
    import numpy as np
    from pathlib import Path
    from datetime import datetime, timezone

    # ── argparse ──────────────────────────────────────────────────────────────
    parser = argparse.ArgumentParser()
    parser.add_argument('--test',   type=int, default=None,
                        help='Process only first N sims (quick test)')
    parser.add_argument('--start',  type=int, default=0)
    parser.add_argument('--end',    type=int, default=2000)
    parser.add_argument('--stride', type=int, default=10)
    args = parser.parse_args()

    # ── Import Pylians ────────────────────────────────────────────────────────
    try:
        import MAS_library as MASL
        import redshift_space_library as RSL
    except ImportError:
        print("[ERROR] Pylians3 not found.")
        print("  Install with:  pip install Pylians3 hdf5plugin")
        print("  Then re-run this script.")
        sys.exit(1)

    try:
        import hdf5plugin  # needed for Blosc-compressed HDF5 snapshots
    except ImportError:
        print("[WARNING] hdf5plugin not found — compressed snapshots may fail.")
        print("  Install with:  pip install hdf5plugin")

    import h5py

    # ── Configuration ────────────────────────────────────────────────────────
    PROJECT_ROOT  = Path(r"D:\projects\cauchy")

    # Path to Quijote snapshots — adjust if your Globus download landed elsewhere
    # Expected structure: SNAP_ROOT/<idx>/snapdir_004/snap_004.hdf5
    # (or snap_004.0.hdf5 if split into subfiles)
    SNAP_ROOT     = PROJECT_ROOT / "data" / "raw" / "quijote" / "snapshots" / "latin_hypercube_nwLH"

    # Output goes into same folder as the existing PCS fields
    FIELD_ROOT    = PROJECT_ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH"

    OUTPUT_JSON   = PROJECT_ROOT / "results" / "phase7_rs_generation_log.json"

    RS_FILENAME   = "df_m_128_RS_z=0.npy"
    SNAP_SUBDIR   = "snapdir_004"   # z=0 for nwLH (snapdir_004 = a=1)
    SNAP_PREFIX   = "snap_004"

    # Cosmological parameters (fixed for all nwLH sims)
    BOXSIZE       = 1000.0   # Mpc/h
    H_LITTLE      = 0.6711   # dimensionless Hubble
    HUBBLE_Z0     = 100.0 * H_LITTLE  # H(z=0) in km/s/(Mpc/h) = 67.11
    REDSHIFT      = 0.0
    LOS_AXIS      = 2        # plane-parallel, LOS along z-axis

    GRID          = 128
    PTYPES        = [1]      # dark matter only
    MAS           = 'PCS'    # match existing real-space fields (df_m_128_PCS_z=0.npy)

    # ── Sim indices ───────────────────────────────────────────────────────────
    sim_indices = list(range(args.start, args.end, args.stride))
    if args.test is not None:
        sim_indices = sim_indices[:args.test]

    print("=" * 60)
    print("CAUCHY Phase 7.0 — RS Field Generation via Pylians3")
    print("=" * 60)
    print(f"  Snapshot root : {SNAP_ROOT}")
    print(f"  Output root   : {FIELD_ROOT}")
    print(f"  N sims        : {len(sim_indices)}")
    print(f"  MAS           : {MAS}  |  Grid: {GRID}^3  |  LOS axis: {LOS_AXIS}")
    print(f"  H(z=0)        : {HUBBLE_Z0:.2f} km/s/(Mpc/h)")
    print()

    # ── Check snapshot root ───────────────────────────────────────────────────
    if not SNAP_ROOT.exists():
        print(f"[ERROR] Snapshot root not found: {SNAP_ROOT}")
        print("  Expected Globus download path. Adjust SNAP_ROOT in script if different.")
        sys.exit(1)

    # ── Helper: find snapshot file ────────────────────────────────────────────
    def find_snap(idx):
        """Return path prefix for Pylians (without .hdf5 extension).
        Handles both single-file and multi-subfile cases."""
        snap_dir = SNAP_ROOT / str(idx) / SNAP_SUBDIR
        if not snap_dir.exists():
            return None
        # Try single file first
        for ext in ['.hdf5', '.0.hdf5', '']:
            p = snap_dir / (SNAP_PREFIX + ext)
            if p.exists():
                # Return prefix without extension (Pylians reads by prefix)
                return str(snap_dir / SNAP_PREFIX)
        return None

    # ── Helper: read pos+vel directly via h5py (fallback if Pylians read fails) ──
    def read_snap_h5(idx):
        """Read DM positions (Mpc/h) and velocities (km/s) from HDF5 snapshot."""
        snap_dir = SNAP_ROOT / str(idx) / SNAP_SUBDIR
        # Find HDF5 files (may be split)
        files = sorted(snap_dir.glob(SNAP_PREFIX + '*.hdf5'))
        if not files:
            return None, None

        pos_list, vel_list = [], []
        for fpath in files:
            with h5py.File(str(fpath), 'r') as f:
                # PartType1 = dark matter
                pos = f['PartType1/Coordinates'][:]    # internal units: Mpc/h * 1e3 (kpc/h)
                vel = f['PartType1/Velocities'][:]     # internal units: km/s * sqrt(a)

                # Unit conversion
                # Gadget internal: positions in kpc/h → convert to Mpc/h
                pos = pos.astype(np.float32) / 1000.0

                # Gadget internal velocities: v_gadget = a^(1/2) * v_pec (km/s)
                # At z=0, a=1, so v_gadget = v_pec directly
                vel = vel.astype(np.float32)

                pos_list.append(pos)
                vel_list.append(vel)

        pos_all = np.concatenate(pos_list, axis=0)
        vel_all = np.concatenate(vel_list, axis=0)
        return pos_all, vel_all

    # ── Helper: compute RS density field ────────────────────────────────────
    def make_rs_field(idx):
        """
        Returns 128^3 float32 density contrast field delta = rho/<rho> - 1
        in redshift space, or None on failure.
        """
        pos, vel = read_snap_h5(idx)
        if pos is None:
            return None, "snapshot_not_found"

        # Apply RSD: shift positions along LOS_AXIS by v_pec / H(z)
        # RSL.pos_redshift_space modifies pos in-place
        # Signature: pos_redshift_space(pos, vel, BoxSize, Hubble, redshift, axis)
        # vel must be peculiar velocity in km/s; pos in Mpc/h; BoxSize in Mpc/h
        # Hubble in km/s/(Mpc/h)
        RSL.pos_redshift_space(pos, vel, BOXSIZE, HUBBLE_Z0, REDSHIFT, LOS_AXIS)
        # pos is now in redshift space (periodic boundary applied internally)

        # Voxelize: MASL.MA (direct from positions array)
        # Returns density field (number counts per voxel)
        delta = np.zeros((GRID, GRID, GRID), dtype=np.float32)
        MASL.MA(pos, delta, BOXSIZE, MAS)

        # Density contrast: delta = n/<n> - 1
        mean_n = np.mean(delta, dtype=np.float64)
        if mean_n == 0:
            return None, "zero_mean_density"
        delta = delta.astype(np.float64)
        delta /= mean_n
        delta -= 1.0

        return delta.astype(np.float32), "ok"

    # ── Main loop ─────────────────────────────────────────────────────────────
    results = {"ok": [], "skipped_exists": [], "error": {}}

    for i, idx in enumerate(sim_indices):
        out_path = FIELD_ROOT / str(idx) / RS_FILENAME

        # Skip if already generated
        if out_path.exists():
            results["skipped_exists"].append(idx)
            if (i + 1) % 20 == 0:
                print(f"  [{i+1:3d}/{len(sim_indices)}] sim {idx}: already exists, skipped")
            continue

        delta, status = make_rs_field(idx)

        if delta is None:
            results["error"][str(idx)] = status
            print(f"  [{i+1:3d}/{len(sim_indices)}] sim {idx}: FAILED ({status})")
            continue

        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(out_path), delta)
        results["ok"].append(idx)

        if (i + 1) % 10 == 0 or args.test is not None:
            print(f"  [{i+1:3d}/{len(sim_indices)}] sim {idx}: OK "
                  f"  delta: mean={delta.mean():.4f} std={delta.std():.4f}  → {out_path.name}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Generated    : {len(results['ok'])}")
    print(f"  Already exist: {len(results['skipped_exists'])}")
    print(f"  Errors       : {len(results['error'])}")
    if results["error"]:
        for idx, reason in list(results["error"].items())[:10]:
            print(f"    sim {idx}: {reason}")

    log = {
        "schema_version": "1.0",
        "script": "phase7_make_rs_fields.py",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params": {
            "grid": GRID, "MAS": MAS, "LOS_axis": LOS_AXIS,
            "BoxSize_Mpch": BOXSIZE, "H_z0_kms_Mpch": HUBBLE_Z0,
            "redshift": REDSHIFT, "ptypes": PTYPES
        },
        "n_requested": len(sim_indices),
        "n_generated": len(results["ok"]),
        "n_skipped_exists": len(results["skipped_exists"]),
        "n_errors": len(results["error"]),
        "errors": results["error"]
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(str(OUTPUT_JSON), 'w') as f:
        json.dump(log, f, indent=2)
    print(f"\n  Log: {OUTPUT_JSON}")
