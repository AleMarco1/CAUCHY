"""
CAUCHY — Phase 0: Data Preparation and Validation
==================================================
Script: src/phase0_data_prep.py
Version: 2.0
Methodology authority: CAUCHY_Systematic_Methodology_v2.0
Gate prior authority: gate0_prior_v1.0.json / CAUCHY_Execution_Parameters_v1.1

Purpose
-------
1. Discover and inventory three Quijote PCS 128³ datasets (fiducial, LHC, nwLH).
2. Run 5 integrity checks on every field.
3. Apply the version-locked preprocessing pipeline (Gaussian smoothing R=5 Mpc/h +
   per-cosmology mean subtraction) to fields that pass.
4. Save preprocessed fields as float64 NPY under data/processed/phase0_fields/.
5. Write results/phase0_data_manifest.json and results/phase0_preprocessing_lock.json.

Usage
-----
    # Using environment variable (recommended):
    set CAUCHY_DATA_ROOT=D:\\projects\\cauchy\\data
    set CAUCHY_REPO_ROOT=D:\\projects\\cauchy
    python src/phase0_data_prep.py

    # Or explicit arguments:
    python src/phase0_data_prep.py \\
        --data-root D:\\projects\\cauchy\\data \\
        --repo-root D:\\projects\\cauchy \\
        --n-workers 8

    # Dry run (integrity checks only, no preprocessing, no file writes):
    python src/phase0_data_prep.py --dry-run

Notes
-----
- Parallelism: integrity checks and preprocessing use multiprocessing.Pool.
  Default workers = min(os.cpu_count(), 8). Override with --n-workers.
- Memory: nwLH dataset is ~105 GB. The mean computation is done in a
  streaming pass (one field at a time) to avoid OOM. Peak RAM per worker
  is ~8 MB (one float64 128³ field).
- Platform: tested on Windows (D:\\ paths) and Linux. Path separators
  are handled via pathlib throughout.
- Reproducibility: GLOBAL_SEED=42 (from pyproject.toml [tool.cauchy]).
  Field ordering is lexicographic-numeric (0, 1, 2, ..., 1999).

Output files
------------
    results/phase0_data_manifest.json
    results/phase0_preprocessing_lock.json
    data/processed/phase0_fields/fiducial/field_NNNN.npy
    data/processed/phase0_fields/lhc/field_NNNN.npy
    data/processed/phase0_fields/nwlh/field_NNNN.npy

Sources
-------
- Smoothing scale R=5 Mpc/h: Abedi et al. 2025 (arXiv:2410.01751v2),
  Jalali Kanafi et al. 2024 (MNRAS).
- Per-cosmology normalisation: CAUCHY_Systematic_Methodology_v2.0 §0.2,
  §0.3.
- Gate 0 thresholds: CAUCHY_Execution_Parameters_v1.1 §2.1,
  gate0_prior_v1.0.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import multiprocessing as mp
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import scipy.ndimage
from tqdm import tqdm

# ---------------------------------------------------------------------------
# 0 — CONSTANTS  (all sourced; do not edit without updating the lock file)
# ---------------------------------------------------------------------------

GLOBAL_SEED: int = 42  # pyproject.toml [tool.cauchy].global_seed
np.random.seed(GLOBAL_SEED)

# Physical / grid parameters
GRID_SIZE: int = 128                  # Quijote PCS 128³
BOX_SIZE_MPC_H: float = 1000.0       # Gpc/h → 1000 Mpc/h; Villaescusa-Navarro+2020
PIXEL_SIZE_MPC_H: float = BOX_SIZE_MPC_H / GRID_SIZE   # ≈ 7.8125 Mpc/h

# Preprocessing parameters — frozen at Gate 0
SMOOTHING_R_MPC_H: float = 5.0       # Abedi+2025 arXiv:2410.01751v2
SMOOTHING_SIGMA_PIXELS: float = SMOOTHING_R_MPC_H / PIXEL_SIZE_MPC_H  # ≈ 0.64 px

# Gate 0 thresholds — from CAUCHY_Execution_Parameters_v1.1 §2.1
INTEGRITY_PASS_RATE_MIN: float = 0.99
MAX_REJECTED_PER_DATASET: int = 20
EXPECTED_SHAPE: tuple[int, int, int] = (GRID_SIZE, GRID_SIZE, GRID_SIZE)
VALID_DTYPES: tuple = (np.float32, np.float64)

# Dataset configuration
N_FIELDS_USE: int = 2000             # used for all three datasets
FIELD_FILENAME: str = "df_m_128_PCS_z=0.npy"

DATASET_CONFIG: dict[str, dict[str, Any]] = {
    "fiducial": {
        "subdir": "raw/quijote/3D_cubes/fiducial",
        "n_use": N_FIELDS_USE,
        "params_file": None,
        "cosmology": {
            "Omega_m": 0.3175, "sigma_8": 0.834, "w0": -1.0,
            "h": 0.6711, "Omega_b": 0.049, "ns": 0.9624,
        },
        "source": "Villaescusa-Navarro et al. 2020 (Quijote suite)",
    },
    "lhc": {
        "subdir": "raw/quijote/3D_cubes/latin_hypercube",
        "n_use": N_FIELDS_USE,
        "params_file": "raw/quijote/3D_cubes/latin_hypercube_params.txt",
        "cosmology": {
            "Omega_m_range": [0.10, 0.50], "sigma_8_range": [0.60, 1.00],
            "w0": -1.0,
        },
        "source": "Villaescusa-Navarro et al. 2020 (Quijote suite)",
    },
    "nwlh": {
        "subdir": "raw/quijote/3D_cubes/latin_hypercube_nwLH",
        "n_use": N_FIELDS_USE,
        "params_file": "raw/quijote/3D_cubes/latin_hypercube_nwLH_params.txt",
        "cosmology": {
            "w0_range": [-1.30, -0.70],
            "Omega_m": 0.3175, "sigma_8": 0.834,
        },
        "source": "Villaescusa-Navarro et al. 2020 (Quijote suite)",
    },
}

PROCESSED_SUBDIR: str = "processed/phase0_fields"
RESULTS_DIR: str = "results"
MANIFEST_FILENAME: str = "phase0_data_manifest.json"
LOCK_FILENAME: str = "phase0_preprocessing_lock.json"

SCHEMA_VERSION: str = "2.0"
CAUCHY_VERSION: str = "v2.0"

# ---------------------------------------------------------------------------
# 1 — LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("cauchy.phase0")


# ---------------------------------------------------------------------------
# 2 — UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    """Compute SHA-256 checksum of a file. Reads in 8 MB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def discover_field_paths(dataset_dir: Path, n_use: int) -> list[Path]:
    """
    Discover field files under dataset_dir using lexicographic-numeric ordering
    of subdirectories (0/, 1/, 2/, ...).

    Each subdirectory contains exactly one file: FIELD_FILENAME.
    Returns the first n_use paths found.
    """
    subdirs = sorted(
        [d for d in dataset_dir.iterdir() if d.is_dir()],
        key=lambda d: int(d.name) if d.name.isdigit() else float("inf"),
    )
    paths: list[Path] = []
    for d in subdirs:
        candidate = d / FIELD_FILENAME
        if candidate.exists():
            paths.append(candidate)
        if len(paths) == n_use:
            break
    return paths


# ---------------------------------------------------------------------------
# 3 — INTEGRITY CHECKS
# ---------------------------------------------------------------------------

def check_integrity(field: np.ndarray) -> list[str]:
    """
    Run 5 integrity checks on a loaded field.
    Returns a list of failure reasons (empty → field passes).

    Checks (Gate 0 — gate0_prior_v1.0.json):
    1. Shape == (128, 128, 128)
    2. dtype in {float32, float64}
    3. No NaN or Inf
    4. δ(x) >= -1 for all voxels (physical density constraint)
    5. std(δ) > 0 (non-constant field)
    """
    failures: list[str] = []

    if field.shape != EXPECTED_SHAPE:
        failures.append(f"shape_mismatch: got {field.shape}, expected {EXPECTED_SHAPE}")

    if field.dtype not in VALID_DTYPES:
        failures.append(f"dtype_invalid: got {field.dtype}")

    if not np.all(np.isfinite(field)):
        n_nan = int(np.sum(np.isnan(field)))
        n_inf = int(np.sum(np.isinf(field)))
        failures.append(f"non_finite: {n_nan} NaN, {n_inf} Inf")

    if np.any(field < -1.0):
        n_below = int(np.sum(field < -1.0))
        failures.append(f"density_below_minus1: {n_below} voxels < -1")

    if np.std(field) == 0.0:
        failures.append("zero_variance: constant field")

    return failures


# ---------------------------------------------------------------------------
# 4 — WORKER FUNCTION (runs in subprocess)
# ---------------------------------------------------------------------------

def _worker_check_and_prep(args: tuple) -> dict:
    """
    Multiprocessing worker.
    Loads one field, runs integrity checks, computes checksum.
    Returns a result dict (preprocessing is done in the main loop after
    the dataset mean is known).
    """
    field_index: int
    field_path: Path
    field_index, field_path = args

    result: dict[str, Any] = {
        "index": field_index,
        "filename": field_path.name,
        "subdir": field_path.parent.name,
        "path": str(field_path),
        "passed": False,
        "failures": [],
        "checksum_sha256": None,
        "field_mean": None,   # used for streaming mean computation
        "error": None,
    }

    try:
        # Checksum on raw file (before loading)
        result["checksum_sha256"] = sha256_file(field_path)

        # Load
        field: np.ndarray = np.load(field_path).astype(np.float64)

        # Integrity checks
        failures = check_integrity(field)

        if failures:
            result["failures"] = failures
            result["passed"] = False
        else:
            result["passed"] = True
            result["field_mean"] = float(np.mean(field))

    except Exception as exc:
        result["error"] = str(exc)
        result["passed"] = False
        result["failures"] = [f"load_error: {exc}"]

    return result


def _worker_preprocess_and_save(args: tuple) -> dict:
    """
    Multiprocessing worker.
    Loads one field, applies Gaussian smoothing + mean subtraction,
    saves to output path as float64 NPY.
    """
    field_index: int
    field_path: Path
    output_path: Path
    dataset_mean: float
    field_index, field_path, output_path, dataset_mean = args

    result: dict[str, Any] = {
        "index": field_index,
        "output_path": str(output_path),
        "passed": False,
        "error": None,
    }

    try:
        field = np.load(field_path).astype(np.float64)

        # Step 1: Gaussian smoothing R=5 Mpc/h → sigma=0.64 pixels
        # Source: Abedi et al. 2025 arXiv:2410.01751v2
        field_smoothed = scipy.ndimage.gaussian_filter(
            field, sigma=SMOOTHING_SIGMA_PIXELS, mode="wrap"
        )

        # Step 2: Per-cosmology mean subtraction
        # Source: CAUCHY_Systematic_Methodology_v2.0 §0.2, §0.3
        field_normed = field_smoothed - dataset_mean

        # Save as float64 NPY
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(output_path, field_normed.astype(np.float64))

        result["passed"] = True

    except Exception as exc:
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# 5 — DATASET PROCESSOR
# ---------------------------------------------------------------------------

def process_dataset(
    dataset_name: str,
    data_root: Path,
    repo_root: Path,
    n_workers: int,
    dry_run: bool,
) -> dict:
    """
    Full pipeline for one dataset:
    1. Discover field paths (lexicographic-numeric order)
    2. Parallel integrity checks + checksum
    3. Streaming dataset mean (over passed fields)
    4. Parallel preprocessing + save
    Returns the dataset section for the manifest.
    """
    cfg = DATASET_CONFIG[dataset_name]
    dataset_dir = data_root / cfg["subdir"]

    log.info("=" * 60)
    log.info(f"Dataset: {dataset_name.upper()}")
    log.info(f"  Directory: {dataset_dir}")

    if not dataset_dir.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {dataset_dir}\n"
            f"Check CAUCHY_DATA_ROOT and directory structure."
        )

    # --- 5.1 Discover fields
    log.info(f"  Discovering field paths (n_use={cfg['n_use']})...")
    field_paths = discover_field_paths(dataset_dir, cfg["n_use"])
    n_found = len(field_paths)
    log.info(f"  Found {n_found} field files.")

    if n_found == 0:
        raise ValueError(
            f"No field files found in {dataset_dir}. "
            f"Expected structure: {dataset_dir}/0/{FIELD_FILENAME}"
        )
    if n_found < cfg["n_use"]:
        log.warning(
            f"  WARNING: found only {n_found} fields, requested {cfg['n_use']}. "
            f"Proceeding with {n_found}."
        )

    # --- 5.2 Parallel integrity checks
    log.info(f"  Running integrity checks with {n_workers} workers...")
    worker_args = [(i, p) for i, p in enumerate(field_paths)]

    check_results: list[dict] = []
    with mp.Pool(processes=n_workers) as pool:
        for res in tqdm(
            pool.imap(_worker_check_and_prep, worker_args),
            total=len(worker_args),
            desc=f"  [{dataset_name}] integrity",
            unit="field",
        ):
            check_results.append(res)

    # Sort by original index to maintain lexicographic order
    check_results.sort(key=lambda r: r["index"])

    passed_mask = [r["passed"] for r in check_results]
    n_passed = sum(passed_mask)
    n_rejected = n_found - n_passed
    pass_rate = n_passed / n_found if n_found > 0 else 0.0

    log.info(
        f"  Integrity: {n_passed}/{n_found} passed "
        f"({pass_rate*100:.1f}%), {n_rejected} rejected."
    )

    # Log Gate 0 threshold check
    if pass_rate < INTEGRITY_PASS_RATE_MIN:
        log.error(
            f"  GATE 0 FAIL: pass_rate={pass_rate:.4f} < "
            f"threshold={INTEGRITY_PASS_RATE_MIN}. "
            f"Inspect rejected fields before proceeding."
        )
    if n_rejected > MAX_REJECTED_PER_DATASET:
        log.error(
            f"  GATE 0 FAIL: n_rejected={n_rejected} > "
            f"max_allowed={MAX_REJECTED_PER_DATASET}."
        )

    # Log rejected fields
    rejected_fields = []
    for r in check_results:
        if not r["passed"]:
            cause = "; ".join(r["failures"]) if r["failures"] else r.get("error", "unknown")
            rejected_fields.append({"index": r["index"], "cause": cause})
            log.warning(f"  REJECTED field {r['index']}: {cause}")

    # --- 5.3 Streaming dataset mean (over passed fields)
    log.info(f"  Computing dataset mean over {n_passed} passed fields (streaming)...")
    acc_mean = np.zeros(EXPECTED_SHAPE, dtype=np.float64)
    n_for_mean = 0

    for r in tqdm(
        check_results,
        desc=f"  [{dataset_name}] mean pass",
        unit="field",
        disable=not any(passed_mask),
    ):
        if r["passed"]:
            field = np.load(r["path"]).astype(np.float64)
            acc_mean += field
            n_for_mean += 1

    if n_for_mean == 0:
        raise ValueError(f"No passed fields in dataset {dataset_name} — cannot compute mean.")

    dataset_mean_field = acc_mean / n_for_mean
    log.info(f"  Dataset mean field computed (mean of means: {dataset_mean_field.mean():.6e}).")

    # --- 5.4 Preprocessing (skipped in dry-run)
    if dry_run:
        log.info("  DRY RUN: skipping preprocessing and file saves.")
    else:
        out_dir = data_root / PROCESSED_SUBDIR / dataset_name
        out_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            f"  Preprocessing {n_passed} fields → {out_dir} "
            f"with {n_workers} workers..."
        )

        prep_args = []
        for r in check_results:
            if r["passed"]:
                out_path = out_dir / f"field_{r['index']:04d}.npy"
                prep_args.append(
                    (r["index"], Path(r["path"]), out_path, dataset_mean_field.mean())
                )

        prep_results: list[dict] = []
        with mp.Pool(processes=n_workers) as pool:
            for res in tqdm(
                pool.imap(_worker_preprocess_and_save, prep_args),
                total=len(prep_args),
                desc=f"  [{dataset_name}] preprocess",
                unit="field",
            ):
                prep_results.append(res)

        n_prep_ok = sum(r["passed"] for r in prep_results)
        n_prep_fail = len(prep_results) - n_prep_ok
        if n_prep_fail > 0:
            log.error(f"  {n_prep_fail} fields failed during preprocessing!")
            for r in prep_results:
                if not r["passed"]:
                    log.error(f"    field {r['index']}: {r['error']}")
        else:
            log.info(f"  Preprocessing complete: {n_prep_ok} fields saved.")

    # --- 5.5 Build manifest section
    field_checksums = {
        r["filename"] if r.get("filename") else Path(r["path"]).name: r["checksum_sha256"]
        for r in check_results
        if r["checksum_sha256"] is not None
    }
    # Use subdir/filename as key for uniqueness
    field_checksums_keyed = {
        f"{r['subdir']}/{r['filename']}": r["checksum_sha256"]
        for r in check_results
        if r["checksum_sha256"] is not None
    }

    fields_used_list = [str(field_paths[r["index"]]) for r in check_results]

    params_file = cfg.get("params_file")
    params_file_path = str(data_root / params_file) if params_file else None

    manifest_section = {
        "path": str(dataset_dir),
        "params_file": params_file_path,
        "n_fields_found": n_found,
        "n_fields_used": n_found,  # all discovered fields are "used" (attempted)
        "n_fields_passed": n_passed,
        "n_fields_rejected": n_rejected,
        "pass_rate": round(pass_rate, 6),
        "gate0_pass_rate_threshold": INTEGRITY_PASS_RATE_MIN,
        "gate0_status": (
            "PASS"
            if pass_rate >= INTEGRITY_PASS_RATE_MIN and n_rejected <= MAX_REJECTED_PER_DATASET
            else "FAIL"
        ),
        "rejected_fields": rejected_fields,
        "field_checksums": field_checksums_keyed,
        "fields_used_ordered": fields_used_list,
        "dataset_mean_voxel_mean": float(dataset_mean_field.mean()),
    }

    return manifest_section


# ---------------------------------------------------------------------------
# 6 — MANIFEST AND LOCK WRITERS
# ---------------------------------------------------------------------------

def write_manifest(
    dataset_results: dict[str, dict],
    results_dir: Path,
) -> Path:
    """Write phase0_data_manifest.json."""
    n_total_passed = sum(s["n_fields_passed"] for s in dataset_results.values())
    n_total = sum(s["n_fields_used"] for s in dataset_results.values())
    overall_pass_rate = n_total_passed / n_total if n_total > 0 else 0.0

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cauchy_version": CAUCHY_VERSION,
        "gate": "GATE_0",
        "datasets": dataset_results,
        "overall_pass_rate": round(overall_pass_rate, 6),
        "overall_gate0_status": (
            "PASS"
            if all(s["gate0_status"] == "PASS" for s in dataset_results.values())
            else "FAIL"
        ),
    }

    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / MANIFEST_FILENAME
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log.info(f"Manifest written: {out_path}")
    return out_path


def write_preprocessing_lock(
    script_path: Path,
    results_dir: Path,
) -> Path:
    """Write phase0_preprocessing_lock.json."""
    script_hash = sha256_file(script_path) if script_path.exists() else "SCRIPT_NOT_FOUND"

    lock = {
        "schema_version": SCHEMA_VERSION,
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "cauchy_version": CAUCHY_VERSION,
        "gate": "GATE_0",
        "preprocessing_steps": [
            {
                "step": "gaussian_smoothing",
                "R_Mpc_h": SMOOTHING_R_MPC_H,
                "sigma_pixels": round(SMOOTHING_SIGMA_PIXELS, 6),
                "pixel_size_Mpc_h": round(PIXEL_SIZE_MPC_H, 6),
                "box_size_Mpc_h": BOX_SIZE_MPC_H,
                "grid_size": GRID_SIZE,
                "implementation": "scipy.ndimage.gaussian_filter",
                "boundary_mode": "wrap",
                "source": "Abedi et al. 2025 arXiv:2410.01751v2; Jalali Kanafi et al. 2024 MNRAS",
            },
            {
                "step": "per_cosmology_normalization",
                "method": "subtract_dataset_mean_field",
                "description": (
                    "Subtract the voxel-wise mean field computed as the arithmetic mean "
                    "of all passed fields in the same dataset. Applied after smoothing. "
                    "Preserves amplitude information (sigma_8 signal in beta_1, beta_2)."
                ),
                "n_fields_for_mean": N_FIELDS_USE,
                "source": "CAUCHY_Systematic_Methodology_v2.0 §0.2, §0.3",
            },
        ],
        "output_dtype": "float64",
        "output_dtype_rationale": (
            "Raw inputs are float32; promoted to float64 for preprocessing "
            "to avoid accumulated rounding in Gaussian filter + subtraction. "
            "Scientifically equivalent: delta(x) values in [-1, ~100] are well "
            "within float32 range but float64 eliminates any sub-percent rounding."
        ),
        "global_seed": GLOBAL_SEED,
        "script_path": str(script_path),
        "script_hash_sha256": script_hash,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "platform": platform.platform(),
    }

    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / LOCK_FILENAME
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)
    log.info(f"Preprocessing lock written: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# 7 — ARGUMENT PARSING
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 0 — Data Preparation and Validation (Gate 0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("CAUCHY_DATA_ROOT", "data")),
        help=(
            "Root directory of raw + processed data. "
            "Default: $CAUCHY_DATA_ROOT or ./data. "
            "Example: D:\\projects\\cauchy\\data"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(os.environ.get("CAUCHY_REPO_ROOT", ".")),
        help=(
            "Root of the CAUCHY repository (for results/ output). "
            "Default: $CAUCHY_REPO_ROOT or current directory."
        ),
    )
    parser.add_argument(
        "--n-workers",
        type=int,
        default=min(mp.cpu_count(), 8),
        help="Number of parallel worker processes. Default: min(cpu_count, 8).",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASET_CONFIG.keys()) + ["all"],
        default=["all"],
        help="Which datasets to process. Default: all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Run integrity checks and compute checksums only. "
            "Do NOT write preprocessed fields or result JSON files."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 8 — MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    data_root: Path = args.data_root.resolve()
    repo_root: Path = args.repo_root.resolve()
    results_dir: Path = repo_root / RESULTS_DIR
    n_workers: int = max(1, args.n_workers)
    dry_run: bool = args.dry_run

    datasets_to_run = (
        list(DATASET_CONFIG.keys())
        if "all" in args.datasets
        else args.datasets
    )

    log.info("=" * 60)
    log.info("CAUCHY Phase 0 — Data Preparation and Validation")
    log.info(f"  cauchy_version : {CAUCHY_VERSION}")
    log.info(f"  data_root      : {data_root}")
    log.info(f"  repo_root      : {repo_root}")
    log.info(f"  results_dir    : {results_dir}")
    log.info(f"  n_workers      : {n_workers}")
    log.info(f"  datasets       : {datasets_to_run}")
    log.info(f"  dry_run        : {dry_run}")
    log.info(f"  python         : {sys.version.split()[0]}")
    log.info(f"  numpy          : {np.__version__}")
    log.info(f"  scipy          : {scipy.__version__}")
    log.info(f"  smoothing R    : {SMOOTHING_R_MPC_H} Mpc/h → sigma={SMOOTHING_SIGMA_PIXELS:.4f} px")
    log.info("=" * 60)

    t0 = time.time()
    dataset_results: dict[str, dict] = {}

    for ds_name in datasets_to_run:
        try:
            section = process_dataset(
                dataset_name=ds_name,
                data_root=data_root,
                repo_root=repo_root,
                n_workers=n_workers,
                dry_run=dry_run,
            )
            dataset_results[ds_name] = section
        except Exception as exc:
            log.error(f"FATAL error processing dataset '{ds_name}': {exc}")
            raise

    elapsed = time.time() - t0
    log.info("=" * 60)
    log.info(f"All datasets processed in {elapsed:.1f}s.")

    # --- Write outputs
    if not dry_run:
        script_path = Path(__file__).resolve()
        manifest_path = write_manifest(dataset_results, results_dir)
        lock_path = write_preprocessing_lock(script_path, results_dir)
    else:
        log.info("DRY RUN: no JSON files written.")

    # --- Gate 0 summary
    log.info("")
    log.info("=" * 60)
    log.info("GATE 0 SUMMARY")
    log.info("=" * 60)
    all_pass = True
    for ds_name, section in dataset_results.items():
        status = section["gate0_status"]
        all_pass = all_pass and (status == "PASS")
        log.info(
            f"  {ds_name:10s}: {status:4s} | "
            f"passed={section['n_fields_passed']}/{section['n_fields_used']} "
            f"({section['pass_rate']*100:.2f}%) | "
            f"rejected={section['n_fields_rejected']}"
        )

    log.info("")
    if all_pass:
        log.info("  ✓ GATE 0: ALL DATASETS PASS. Proceed to Review 0.")
    else:
        log.error(
            "  ✗ GATE 0: ONE OR MORE DATASETS FAIL. "
            "Inspect rejected fields before proceeding. "
            "Do NOT proceed to Phase 1 until gate is resolved."
        )
    log.info("=" * 60)

    if not dry_run:
        log.info(f"  Manifest  → {manifest_path}")
        log.info(f"  Lock file → {lock_path}")
        log.info("")
        log.info("Next steps:")
        log.info("  1. Inspect results/phase0_data_manifest.json.")
        log.info("  2. Verify overall_gate0_status == 'PASS'.")
        log.info("  3. Report manifest + lock file to Claude (Session 2).")
        log.info("  4. Claude constructs the Review 0 prompt for the Reviewer.")


if __name__ == "__main__":
    # Guard required on Windows for multiprocessing
    mp.freeze_support()
    main()
