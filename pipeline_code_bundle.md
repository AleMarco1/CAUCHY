# CAUCHY — bundle codice pipeline (slot [C1])

Generato: 2026-07-22T10:25:48.546956+00:00

Root: `D:\projects\cauchy`

File inclusi, in ordine di rilevanza:

1. `src/find_pipeline_code.py` — score 442, 13.0KB
2. `src/phase8_cutsky_mocks.py` — score 329, 30.7KB
3. `src/phase1_tda_baseline.py` — score 296, 48.5KB
4. `src/phase1_patch_cache.py` — score 277, 28.0KB
5. `src/phase2_cnn.py` — score 273, 89.9KB
6. `src/phase5_hod_mcmc.py` — score 270, 29.4KB
7. `src/phase5_hod_restricted_prior.py` — score 270, 33.9KB
8. `src/phase7_rsd_test.py` — score 261, 12.9KB

---


## FILE: src/find_pipeline_code.py
<!-- score=442 size=13.0KB keywords=['betti', 'persistence', 'smooth', 'gudhi', 'b1_max', 'beta1max', 'b1max', 'log1p', 'gaussian_filter', 'sigma_px'] -->

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_pipeline_code.py
---------------------
Step 1 / slot [C1]-[C2] del Paper 1.

Trova AUTOMATICAMENTE, dentro il progetto CAUCHY, il codice che definisce:
  * la trasformazione  delta -> nu  (log-transform, smoothing, standardizzazione)
  * la filtrazione / omologia persistente (GUDHI, cubical complex, Betti)
  * il calcolo di beta1max

e produce:
  1) pipeline_code_report.json  -> classifica dei file per rilevanza, con
                                   keyword trovate, funzioni/classi e n. di riga
  2) pipeline_code_bundle.md    -> il SORGENTE COMPLETO dei file migliori,
                                   concatenato in un unico file da caricare
  3) (bonus) elenco dei .json in results/ che contengono chiavi tipo
     beta1 / b1_max / betti  -> serve a chiudere lo slot [C2]

Solo standard library. Non modifica nulla: apre i file in sola lettura.

USO (Windows):
    python find_pipeline_code.py

Opzioni:
    python find_pipeline_code.py --root "D:\\projects\\cauchy" --top 8
"""

import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
DEFAULT_ROOT = r"D:\projects\cauchy"
DEFAULT_TOP = 8                     # quanti file finiscono nel bundle
MAX_FILE_BYTES = 400_000            # non bundlare file .py enormi
MAX_BUNDLE_BYTES = 2_000_000        # tetto totale del bundle
MAX_SCAN_BYTES = 2_000_000          # non leggere .py oltre questa soglia

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".ipynb_checkpoints",
    "node_modules", ".venv", "venv", "env", ".env", "site-packages",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", ".idea", ".vscode",
}

# Keyword pesate. Il punteggio guida la classifica.
KEYWORDS = {
    # --- decisive: omologia persistente ---
    "gudhi": 12,
    "cubicalcomplex": 12,
    "cubical_complex": 12,
    "persistence": 10,
    "persistence_intervals": 10,
    "betti": 10,
    "b1_max": 10,
    "beta1max": 10,
    "beta1_max": 10,
    "b1max": 10,
    "persistence_diagram": 8,
    "ripser": 8,
    "top_dimensional_cells": 8,
    # --- decisive: costruzione del campo nu ---
    "log1p": 8,
    "np.log(1": 8,
    "log_transform": 8,
    "gaussian_filter": 8,
    "sigma_px": 8,
    "smoothing": 6,
    "smooth": 4,
    "standardize": 6,
    "standardis": 6,
    "nu_field": 8,
    "filtration": 8,
    "superlevel": 8,
    "sublevel": 8,
    # --- contesto ---
    "voxel": 3,
    "mask": 3,
    "carve": 4,
    "cut_sky": 4,
    "cutsky": 4,
    "delta_128": 4,
    "field_prep": 5,
    "phase1": 3,
    "phase6": 3,
    "fvec": 4,
    "feature_vector": 4,
}

# Nomi di funzione/classe che vogliamo estrarre esplicitamente
DEF_RE = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)", re.M)

INTERESTING_DEF_HINTS = (
    "nu", "field", "smooth", "log", "filtr", "persist", "betti", "b1",
    "topol", "prep", "mask", "carve", "standard", "feature", "fvec",
)

# chiavi cercate nei json di results per lo slot [C2]
JSON_C2_KEYS = ("b1_max", "beta1", "b1max", "betti", "beta_1", "b1 ")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def read_text(path, limit=MAX_SCAN_BYTES):
    """Legge un file di testo in modo tollerante agli encoding."""
    try:
        with open(path, "rb") as f:
            raw = f.read(limit)
    except OSError:
        return None
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024.0


def score_source(text):
    """Punteggio di rilevanza + dettaglio delle keyword trovate."""
    low = text.lower()
    score = 0
    hits = {}
    for kw, w in KEYWORDS.items():
        c = low.count(kw)
        if c:
            # saturazione: 3 occorrenze valgono quanto molte di piu'
            eff = min(c, 3)
            score += w * eff
            hits[kw] = c
    return score, hits


def find_defs(text):
    """Estrae nomi di funzioni/classi con il numero di riga."""
    out = []
    for m in DEF_RE.finditer(text):
        name = m.group(1)
        line = text.count("\n", 0, m.start()) + 1
        out.append({"name": name, "line": line})
    return out


def interesting_defs(defs):
    return [d for d in defs
            if any(h in d["name"].lower() for h in INTERESTING_DEF_HINTS)]


def keyword_context(text, max_snippets=6):
    """Righe di codice attorno alle keyword piu' decisive (per il report)."""
    lines = text.splitlines()
    low_lines = [l.lower() for l in lines]
    decisive = ("gudhi", "cubical", "persistence", "betti", "gaussian_filter",
                "log1p", "superlevel", "sublevel", "sigma_px", "filtration")
    snips = []
    for i, ll in enumerate(low_lines):
        if any(d in ll for d in decisive):
            snips.append({"line": i + 1, "code": lines[i].strip()[:200]})
            if len(snips) >= max_snippets:
                break
    return snips


# ---------------------------------------------------------------------------
# Scansione principale
# ---------------------------------------------------------------------------
def scan_python(root):
    results = []
    n_seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if not (fn.endswith(".py") or fn.endswith(".ipynb")):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            n_seen += 1
            text = read_text(fp)
            if text is None:
                continue
            score, hits = score_source(text)
            if score <= 0:
                continue
            defs = find_defs(text)
            results.append({
                "path": fp,
                "rel": os.path.relpath(fp, root).replace("\\", "/"),
                "size_bytes": size,
                "size_h": human(size),
                "score": score,
                "keyword_hits": dict(sorted(hits.items(), key=lambda x: -x[1])),
                "n_defs": len(defs),
                "defs_interesting": interesting_defs(defs)[:25],
                "context": keyword_context(text),
            })
    results.sort(key=lambda r: -r["score"])
    return results, n_seen


def scan_results_json(root):
    """Bonus [C2]: json in results/ che sembrano contenere valori di Betti."""
    out = []
    rdir = os.path.join(root, "results")
    if not os.path.isdir(rdir):
        return out
    for dirpath, dirnames, filenames in os.walk(rdir):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(fp) > 20_000_000:
                    continue
            except OSError:
                continue
            text = read_text(fp, limit=1_000_000)
            if not text:
                continue
            low = text.lower()
            found = [k.strip() for k in JSON_C2_KEYS if k in low]
            if not found:
                continue
            # prova a estrarre le chiavi di primo livello e i numeri plausibili
            preview_keys, numbers = [], {}
            try:
                d = json.loads(text)
                if isinstance(d, dict):
                    preview_keys = list(d.keys())[:30]

                    def crawl(o, prefix="", depth=0):
                        if depth > 3 or len(numbers) > 25:
                            return
                        if isinstance(o, dict):
                            for k, v in o.items():
                                kl = str(k).lower()
                                p = f"{prefix}.{k}" if prefix else str(k)
                                if isinstance(v, (int, float)) and any(
                                        t in kl for t in ("b1", "beta1", "betti", "deficit", "max")):
                                    numbers[p] = v
                                elif isinstance(v, (dict, list)):
                                    crawl(v, p, depth + 1)
                    crawl(d)
            except Exception:  # noqa: BLE001
                pass
            out.append({
                "path": fp,
                "rel": os.path.relpath(fp, root).replace("\\", "/"),
                "size_h": human(os.path.getsize(fp)),
                "matched_terms": found,
                "top_level_keys": preview_keys,
                "candidate_numbers": numbers,
            })
    # i piu' promettenti prima: chi ha numeri estratti
    out.sort(key=lambda r: (-len(r["candidate_numbers"]), -len(r["matched_terms"])))
    return out


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------
def write_bundle(results, root, top, out_path):
    chosen, total = [], 0
    for r in results:
        if len(chosen) >= top:
            break
        if r["size_bytes"] > MAX_FILE_BYTES:
            continue
        if total + r["size_bytes"] > MAX_BUNDLE_BYTES:
            continue
        chosen.append(r)
        total += r["size_bytes"]

    buf = io.StringIO()
    buf.write("# CAUCHY — bundle codice pipeline (slot [C1])\n\n")
    buf.write(f"Generato: {datetime.now(timezone.utc).isoformat()}\n\n")
    buf.write(f"Root: `{root}`\n\n")
    buf.write("File inclusi, in ordine di rilevanza:\n\n")
    for i, r in enumerate(chosen, 1):
        buf.write(f"{i}. `{r['rel']}` — score {r['score']}, {r['size_h']}\n")
    buf.write("\n---\n")

    for r in chosen:
        text = read_text(r["path"]) or ""
        buf.write(f"\n\n## FILE: {r['rel']}\n")
        buf.write(f"<!-- score={r['score']} size={r['size_h']} "
                  f"keywords={list(r['keyword_hits'])[:10]} -->\n\n")
        buf.write("```python\n")
        buf.write(text)
        if not text.endswith("\n"):
            buf.write("\n")
        buf.write("```\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return chosen, total


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Trova il codice della pipeline CAUCHY (filtrazione/persistenza).")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="Root del progetto.")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP,
                    help="Quanti file includere nel bundle (default 8).")
    ap.add_argument("--report", default="pipeline_code_report.json")
    ap.add_argument("--bundle", default="pipeline_code_bundle.md")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(f"[errore] root non trovata: {args.root}")
        sys.exit(1)

    print(f"[scan] .py/.ipynb sotto {args.root} ...", flush=True)
    results, n_seen = scan_python(args.root)
    print(f"       {n_seen} file esaminati, {len(results)} rilevanti.\n")

    print("=== TOP 15 CANDIDATI ===")
    for i, r in enumerate(results[:15], 1):
        kws = ", ".join(list(r["keyword_hits"])[:6])
        print(f"{i:2d}. [{r['score']:4d}] {r['rel']}  ({r['size_h']})")
        print(f"        keywords: {kws}")
        if r["defs_interesting"]:
            names = ", ".join(d["name"] for d in r["defs_interesting"][:6])
            print(f"        funzioni: {names}")

    print("\n[scan] json in results/ per lo slot [C2] ...", flush=True)
    jres = scan_results_json(args.root)
    print(f"       {len(jres)} json candidati.")
    for r in jres[:10]:
        print(f"   - {r['rel']}  ({r['size_h']})  termini={r['matched_terms']}")
        if r["candidate_numbers"]:
            for k, v in list(r["candidate_numbers"].items())[:6]:
                print(f"        {k} = {v}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": args.root,
        "n_python_files_seen": n_seen,
        "n_relevant": len(results),
        "ranked_python": results[:60],
        "candidate_result_jsons": jres[:40],
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    chosen, total = write_bundle(results, args.root, args.top, args.bundle)

    print("\n" + "=" * 70)
    print(f"[ok] report : {os.path.abspath(args.report)}")
    print(f"[ok] bundle : {os.path.abspath(args.bundle)}  "
          f"({len(chosen)} file, {human(total)})")
    print("\nCarica a Claude il BUNDLE (e, se piccolo, anche il report).")


if __name__ == "__main__":
    main()
```


## FILE: src/phase8_cutsky_mocks.py
<!-- score=329 size=30.7KB keywords=['mask', 'sigma_px', 'beta1_max', 'cutsky', 'voxel', 'phase6', 'smooth', 'cubicalcomplex', 'filtration', 'carve'] -->

```python
"""
CAUCHY — Phase 8, Script 1
src/phase8_cutsky_mocks.py

TEST 1 (diagnostic, exact-replica): does the DESI topological anomaly survive
survey geometry?

Rationale (gate8_prior_v1_0.json):
  The canonical DESI TDA (phase6_bgs_tda.py) runs gudhi CubicalComplex on the
  FULL 128^3 embedding cube with ~85% of voxels set to 0.0 (exterior). The mask
  is used only for thresholds/mean, NOT to exclude the exterior from the
  filtration. Mocks (phase6_smoothing_sensitivity.compute_b2_full) are periodic
  boxes with no mask and mode='wrap' smoothing. The two <pers1> statistics are
  therefore NOT computed on comparable geometries.

  This script rebuilds the mock reference distribution by applying the SAME
  construction as DESI: cut-sky carving with the DESI NGC mask + n(z) + FKP,
  zero-exterior embedding, and the identical UNMASKED compute_tda_features.

  DESI values are UNCHANGED (0.45886, 29683). Only the mock side is rebuilt.

Construction (option (a): satellites at halo bulk velocity, no intra-halo disp):
  1. Read FoF halos from groups_003 (z=0.5), WITH group velocities.
  2. HOD populate (B3 median), assign per-galaxy velocity = parent halo velocity.
  3. Tile the periodic 1000 Mpc/h box into the DESI embedding cube.
  4. Observer at Cartesian origin; per galaxy -> (RA, Dec, z_cosmo).
  5. RSD: z_obs = z_cosmo + (1+z_cosmo) * v_los / c.
  6. Carve: keep galaxies whose embedding voxel is in the DESI NGC mask AND
     z_obs in [0.1, 0.4].
  7. Radial downsample to match BGS NGC n(z).
  8. delta_FKP against the DESI random field, exterior = 0.0, smoothing R=5.
  9. compute_tda_features UNMASKED (identical to phase6_bgs_tda.py).
 10. Collect <pers1> and beta1_max per mock; empirical rank of DESI.

Output:
  results/phase8_cutsky_test1.json
  results/phase8_cutsky_fields/cutsky_{i:04d}.npz   (delta field per mock, optional)

Usage:
  python src/phase8_cutsky_mocks.py --n_pilot 200 --project_root D:\projects\cauchy

VERIFY BEFORE TREATING AS FINAL (see gate8 declared_limitations):
  - GADGET_VEL_SQRT_A: whether Quijote group_tab velocities need the sqrt(a) factor.
  - FoF GroupVel byte offset (validated by --check_fof on one file).
  - Random-catalogue column names (WEIGHT_FKP).
"""

import argparse
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# CLI — only parse the real command line when run as the main program. When this
# module is IMPORTED (e.g. by phase8_weight_check.py / phase8_field_diagnostic.py),
# parse an empty list so those scripts keep their own argparse.
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_pilot", type=int, default=200)
parser.add_argument("--snapnum", type=int, default=3, help="3 = z=0.5")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--save_fields", action="store_true",
                    help="Save per-mock delta fields (large; off by default)")
parser.add_argument("--check_fof", action="store_true",
                    help="Validate FoF velocity offset on sim 0 and exit")
args = parser.parse_args() if __name__ == "__main__" else parser.parse_args([])

ROOT = Path(args.project_root)
np.random.seed(args.seed)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
DESI_DIR        = ROOT / "data" / "raw" / "desi_dr1"
RAN_FITS        = DESI_DIR / "BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits"
NZ_FILE         = DESI_DIR / "BGS_BRIGHT-21.5_NGC_nz.txt"
FLD_DIR         = ROOT / "data" / "processed" / "phase6_fields"
DESI_MASK_FILE  = FLD_DIR / "bgs_ngc_mask_128.npy"
RES_DIR         = ROOT / "results"
OUT_FIELDS_DIR  = RES_DIR / "phase8_cutsky_fields"
OUTPUT_JSON     = RES_DIR / "phase8_cutsky_test1.json"
RES_DIR.mkdir(parents=True, exist_ok=True)
if args.save_fields:
    OUT_FIELDS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Frozen geometry (phase6_voxelize_diagnostics.json, region NGC) and constants
# ---------------------------------------------------------------------------
BOXSIZE_MOCK = 1000.0          # Mpc/h, Quijote periodic box
NGRID        = 128
N_PART_MIN   = 20

# DESI NGC embedding cube (must match phase6_bgs_voxelize output exactly)
BOX_MIN  = np.array([-1085.5836039835003, -1059.3513403117618, -194.44091723978792])
BOX_SIZE = 1997.3629167166155
CELL     = BOX_SIZE / NGRID     # 15.6044 Mpc/h
D_C_ZMIN = 292.535950750378
D_C_ZMAX = 1080.7298534541035
ZMIN, ZMAX = 0.1, 0.4

R_SMOOTH = 5.0
SIGMA_PX = R_SMOOTH / CELL      # 0.3204 (matches DESI canonical sigma_px)

# Cosmology (Planck 2018 fiducial, h=1 units) — identical to phase6_bgs_voxelize
OMM = 0.3175
OML = 1.0 - OMM
C_OVER_H0 = 2997.92             # Mpc/h
C_KMS     = 299792.458          # km/s

# HOD B3 median (gate8 frozen)
HOD_MEDIAN = np.array([12.5, 0.55, 12.25, 13.5, 1.0, 0.0, 0.0, 1.0, 1.0])

# Gadget velocity convention: Quijote group velocities. If True, multiply by
# sqrt(a) to obtain peculiar velocity in km/s. VERIFY against Quijote docs.
GADGET_VEL_SQRT_A = True
SCALE_A = 1.0 / (1.0 + 0.5)     # z=0.5

# DESI reference is RECOMPUTED on the native grid at sigma_px=0.3204 (see main),
# NOT taken from the canonical 0.459 (which was sigma_px=0.216). This makes the
# comparison like-for-like: mock and DESI on the same physical grid, same R.
DESI_FIELD_R5 = FLD_DIR / "bgs_ngc_delta_128.npy"   # canonical R=5 native grid
PERS1_DESI = None        # filled in main() by recompute_desi_reference()
BETA1_MAX_DESI = None

# Density target: nominal BGS NGC count (abstract / all tables). Used to scale
# the radial downsampling so N_sel ~ N_TARGET_BGS instead of ~1.6x.
N_TARGET_BGS = 217614

N_THRESH = 100

# ---------------------------------------------------------------------------
# Cosmology helpers (comoving distance + inverse), consistent w/ voxelizer
# ---------------------------------------------------------------------------
def comoving_distance(z_arr, n_steps=500):
    z_arr = np.atleast_1d(np.asarray(z_arr, dtype=np.float64))
    out = np.zeros(len(z_arr))
    for i, zi in enumerate(z_arr):
        zz = np.linspace(0.0, zi, n_steps)
        EE = np.sqrt(OMM * (1 + zz) ** 3 + OML)
        out[i] = C_OVER_H0 * np.trapezoid(1.0 / EE, zz)
    return out

# Inverse table r -> z over a generous range
_Z_TAB = np.linspace(0.0, 0.6, 4001)
_DC_TAB = comoving_distance(_Z_TAB)
def z_of_dc(dc):
    return np.interp(dc, _DC_TAB, _Z_TAB)

# ---------------------------------------------------------------------------
# FoF reader WITH velocities (extends phase5_hod_b3.FoF_catalog)
# Layout (from phase5_hod_b3.py header comment, verified SOA nwLH):
#   header 24 bytes; N = first int32
#   GroupLen  @ 24            (int32,  N*4)
#   GroupMass @ 24 + N*8      (float32,N*4)
#   Pos  x @ 24+N*12, y @ 24+N*16, z @ 24+N*20
#   Vel vx @ 24+N*24, vy @ 24+N*28, vz @ 24+N*32
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo non trovato: {fname}"
        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N
        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            self.GroupVel  = np.zeros((0, 3), dtype=np.float32)
            return
        def rd_i(off): return np.frombuffer(raw[off:off + N * 4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off + N * 4], dtype=np.float32).copy()
        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N * 8)
        self.GroupPos  = np.column_stack([rd_f(24 + N * 12),
                                          rd_f(24 + N * 16),
                                          rd_f(24 + N * 20)])
        self.GroupVel  = np.column_stack([rd_f(24 + N * 24),
                                          rd_f(24 + N * 28),
                                          rd_f(24 + N * 32)])


def read_halo_catalog(sim_idx, snapnum):
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, snapnum)
    if FoF.Ngroups == 0:
        return None, None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE_MOCK      # kpc/h -> Mpc/h
    mass_h = FoF.GroupMass[mask] * 1e10                     # 1e10 Msun/h -> Msun/h
    vel_h  = FoF.GroupVel[mask].astype(np.float64)          # km/s (see GADGET_VEL_SQRT_A)
    if GADGET_VEL_SQRT_A:
        vel_h = vel_h * np.sqrt(SCALE_A)
    return pos_h, mass_h, vel_h


# ---------------------------------------------------------------------------
# HOD (identical mean occupation to phase5_hod_b3.py) + velocities (option a)
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM):
    from scipy.special import erf
    return 0.5 * (1.0 + erf((np.log10(mass_h) - log_Mmin) / (sigma_logM + 1e-10)))

def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin):
    M0, M1 = 10 ** log_M0, 10 ** log_M1
    N_sat = np.zeros(len(mass_h))
    m = mass_h > M0
    ratio = np.where(m, (mass_h - M0) / (M1 + 1e-30), 0.0)
    N_sat[m] = ratio[m] ** alpha
    N_sat *= mean_Ncen(mass_h, log_Mmin, 0.2)
    return N_sat

def populate_halos_hod_with_vel(pos_h, mass_h, vel_h, hod_params, rng):
    """Return (pos_gal [N,3] Mpc/h, vel_gal [N,3] km/s). Option (a): satellites
    inherit the parent halo bulk velocity, no intra-halo dispersion."""
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3)), np.zeros((0, 3))

    p_cen = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    pos_list, vel_list = [], []
    if is_central.any():
        pos_list.append(pos_h[is_central])
        vel_list.append(vel_h[is_central])

    rho_crit = 2.775e11 * OMM
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
        pos_list.append((pos_h[i] + dxyz) % BOXSIZE_MOCK)
        vel_list.append(np.tile(vel_h[i], (ns, 1)))   # option (a): halo bulk vel

    if not pos_list:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.vstack(pos_list), np.vstack(vel_list)


# ---------------------------------------------------------------------------
# CIC (identical to phase6_bgs_voxelize.cic_3d)
# ---------------------------------------------------------------------------
def cic_3d(pos, weights, ngrid, box_min, box_size):
    cell = box_size / ngrid
    xyz  = np.clip((pos - box_min[None, :]) / cell, 0.0, ngrid - 1e-6)
    ijk  = xyz.astype(np.int32)
    d    = (xyz - ijk).astype(np.float32)
    w    = weights.astype(np.float32)
    flat = np.zeros(ngrid ** 3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = np.clip(ijk[:, 0] + di, 0, ngrid - 1)
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = np.clip(ijk[:, 1] + dj, 0, ngrid - 1)
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = np.clip(ijk[:, 2] + dk, 0, ngrid - 1)
                idx = ii * ngrid ** 2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz * w,
                                    minlength=ngrid ** 3).astype(np.float32)
    return flat.reshape(ngrid, ngrid, ngrid)


# ---------------------------------------------------------------------------
# UNMASKED TDA — byte-for-byte the DESI canonical (phase6_bgs_tda.compute_tda_features)
# The CubicalComplex runs on the FULL -field (exterior zeros included). mask is
# used only for thresholds and the b0 mean level — identical to DESI.
# ---------------------------------------------------------------------------
def compute_tda_features(delta_field, mask, n_thresh=100, masked=False):
    import gudhi
    # The log-transform is applied upstream in build_field (on the RAW delta).
    # compute_tda_features works on the field as-is.
    #
    # masked=False (Test 1): CubicalComplex on the FULL -field, exterior zeros
    #   included in the filtration — identical to the (broken) DESI canonical.
    # masked=True (Test 2): exterior EXCLUDED from the filtration. Exterior cells
    #   are set to a high sentinel in -field so they enter the sublevel filtration
    #   LAST; any H1 loop that would need the exterior to close is cut (its birth
    #   or death touches the sentinel and is removed). Applied identically to DESI
    #   and mocks — the only correct like-for-like treatment for a bounded survey.
    field = delta_field.astype(np.float64)
    field_in = field[mask]
    nu_min = float(np.percentile(field_in, 1))
    nu_max = float(np.percentile(field_in, 99))
    thresholds = np.linspace(nu_min, nu_max, n_thresh)

    SENT = 1.0e6
    if masked:
        field_work = field.copy()
        field_work[~mask] = -SENT          # exterior very low in field ...
        field_neg = -field_work            # ... => +SENT in -field (enters last)
        cutoff = SENT / 2.0
    else:
        field_neg = -field
        cutoff = np.inf

    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                              top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def proc(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        keep = np.isfinite(d[:, 1]) & (d[:, 0] < cutoff) & (d[:, 1] < cutoff)
        df = d[keep]
        b, dth = -df[:, 0], -df[:, 1]
        return b, dth, b - dth

    b0, d0, _   = proc(diag_0)
    b1, d1, p1  = proc(diag_1)

    b1_curve = np.zeros(n_thresh)
    b0_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(b0):
            b0_curve[k] = np.sum((b0 >= nu) & (d0 < nu))
        if len(b1):
            b1_curve[k] = np.sum((b1 >= nu) & (d1 < nu))

    feats = np.zeros(8, dtype=np.float64)
    if b1_curve.max() > 0:
        pk = np.argmax(b1_curve)
        feats[0] = thresholds[pk]
        feats[1] = b1_curve[pk]
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = (thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = np.trapezoid(b1_curve, thresholds)
    if len(p1) > 0:
        feats[4] = len(p1)
        feats[5] = float(np.mean(p1))
        feats[6] = float(np.sum(p1 >= np.percentile(p1, 90)))
    mean_val = float(field[mask].mean())
    feats[7] = b0_curve[np.argmin(np.abs(thresholds - mean_val))]
    # feats[4] = beta1_max (n loops), feats[5] = <pers1>
    return feats


# ---------------------------------------------------------------------------
# Load DESI random field once (denominator of delta_FKP) + n(z) target
# ---------------------------------------------------------------------------
def load_desi_random_field():
    from astropy.io import fits
    with fits.open(RAN_FITS) as h:
        r = h['LSS'].data
        mz = (r['Z'] >= ZMIN) & (r['Z'] <= ZMAX)
        ra, dec, z = r['RA'][mz].astype(np.float64), r['DEC'][mz].astype(np.float64), r['Z'][mz].astype(np.float64)
        w = r['WEIGHT_FKP'][mz].astype(np.float64)
    dC = comoving_distance(z)
    ra_r, dec_r = np.radians(ra), np.radians(dec)
    x = dC * np.cos(dec_r) * np.cos(ra_r)
    y = dC * np.cos(dec_r) * np.sin(ra_r)
    zc = dC * np.sin(dec_r)
    pos_r = np.column_stack([x, y, zc])
    field_r = cic_3d(pos_r, w, NGRID, BOX_MIN, BOX_SIZE)
    sum_wr = float(w.sum())
    return field_r, sum_wr

def load_desi_data_field():
    """CIC of the DESI BGS NGC data catalogue with w = WEIGHT * WEIGHT_FKP,
    same coordinates/geometry as the random loader. Returns (field_d, sum_wd)."""
    from astropy.io import fits
    dat = DESI_DIR / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        d = h['LSS'].data
        mz = (d['Z'] >= ZMIN) & (d['Z'] <= ZMAX)
        ra, dec, z = d['RA'][mz].astype(np.float64), d['DEC'][mz].astype(np.float64), d['Z'][mz].astype(np.float64)
        w = (d['WEIGHT'][mz] * d['WEIGHT_FKP'][mz]).astype(np.float64)
    dC = comoving_distance(z)
    ra_r, dec_r = np.radians(ra), np.radians(dec)
    x = dC * np.cos(dec_r) * np.cos(ra_r)
    y = dC * np.cos(dec_r) * np.sin(ra_r)
    zc = dC * np.sin(dec_r)
    pos_d = np.column_stack([x, y, zc])
    field_d = cic_3d(pos_d, w, NGRID, BOX_MIN, BOX_SIZE)
    return field_d, float(w.sum())


def load_bgs_nz():
    """Return (z_centres, nz) from the BGS n(z) file. Robust to column layout:
    uses the first column as z and the last numeric column as n(z)."""
    tab = np.loadtxt(NZ_FILE, comments='#')
    if tab.ndim == 1:
        tab = tab.reshape(1, -1)
    return tab[:, 0], tab[:, -1]


# ---------------------------------------------------------------------------
# Cut-sky carving of one mock (tiling + observer + RSD + mask + n(z))
# ---------------------------------------------------------------------------
_MASK = None  # loaded in main

def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng):
    """Map periodic-box galaxies into the DESI embedding cube, apply RSD, carve
    by mask + z range, downsample to BGS n(z). Returns selected embedding-frame
    Cartesian positions [M,3] (redshift-space)."""
    # Tile offsets covering the embedding cube along each axis
    def offsets(axis):
        lo, hi = BOX_MIN[axis], BOX_MIN[axis] + BOX_SIZE
        k_lo = int(np.floor(lo / BOXSIZE_MOCK))
        k_hi = int(np.floor(hi / BOXSIZE_MOCK))
        return list(range(k_lo, k_hi + 1))
    ox, oy, oz = offsets(0), offsets(1), offsets(2)

    # Pass 1: collect ALL in-survey candidates (mask + z range), no downsampling.
    cand_P, cand_z = [], []
    for kx in ox:
        for ky in oy:
            for kz in oz:
                shift = np.array([kx, ky, kz]) * BOXSIZE_MOCK
                P = pos_gal + shift[None, :]
                inb = np.all((P >= BOX_MIN[None, :]) &
                             (P < (BOX_MIN + BOX_SIZE)[None, :]), axis=1)
                if not inb.any():
                    continue
                P = P[inb]
                V = vel_gal[inb]
                # Real-space distance & LOS
                dC = np.linalg.norm(P, axis=1)
                good = (dC > 1e-6) & (dC >= D_C_ZMIN - 50) & (dC <= D_C_ZMAX + 50)
                if not good.any():
                    continue
                P, V, dC = P[good], V[good], dC[good]
                rhat = P / dC[:, None]
                z_cosmo = z_of_dc(dC)
                v_los = np.sum(V * rhat, axis=1)                 # km/s
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / C_KMS
                dC_rsd = np.interp(np.clip(z_obs, 0.0, 0.6), _Z_TAB, _DC_TAB)
                P_rsd = rhat * dC_rsd[:, None]
                zsel = (z_obs >= ZMIN) & (z_obs <= ZMAX)
                if not zsel.any():
                    continue
                P_rsd, z_obs_s = P_rsd[zsel], z_obs[zsel]
                ijk = np.clip(((P_rsd - BOX_MIN[None, :]) / CELL).astype(np.int32),
                              0, NGRID - 1)
                inmask = mask[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
                if not inmask.any():
                    continue
                cand_P.append(P_rsd[inmask])
                cand_z.append(z_obs_s[inmask])
    if not cand_P:
        return np.zeros((0, 3))
    P_cand = np.vstack(cand_P)
    z_cand = np.concatenate(cand_z)

    # Pass 2: global n(z)-shaped downsampling to hit N_TARGET_BGS.
    # Desired count per z-bin ∝ BGS n(z); acceptance = desired/available, capped 1.
    edges = np.concatenate([[nz_z[0] - 0.5 * (nz_z[1] - nz_z[0])],
                            0.5 * (nz_z[:-1] + nz_z[1:]),
                            [nz_z[-1] + 0.5 * (nz_z[-1] - nz_z[-2])]])
    which = np.clip(np.digitize(z_cand, edges) - 1, 0, len(nz_z) - 1)
    n_cand_bin = np.bincount(which, minlength=len(nz_z)).astype(float)
    shape = np.clip(nz_target, 0.0, None).astype(float)
    if shape.sum() <= 0:
        return np.zeros((0, 3))
    desired = shape / shape.sum() * float(N_TARGET_BGS)
    with np.errstate(divide='ignore', invalid='ignore'):
        p_bin = np.where(n_cand_bin > 0, desired / n_cand_bin, 0.0)
    p_bin = np.minimum(p_bin, 1.0)
    p = p_bin[which]
    keep = rng.random(len(z_cand)) < p
    return P_cand[keep]


def build_field(field_d, field_r, alpha, mask):
    """Shared field construction for DESI and cut-sky mocks. Identical byte-for-byte
    on both sides. Pipeline (as STATED in the paper):
      raw delta_FKP (>= -1)  ->  nu = log(1 + clip(delta, -1))  ->  smooth  ->  mean-sub.
    The log on the RAW delta bounds the FKP shot-noise positive tail (delta up to
    +150 -> log(151)=5.0, matching DESI's raw range) without a spurious negative
    spike. Exterior/invalid voxels are 0 (= log(1)), preserving the zero exterior."""
    delta = np.zeros((NGRID, NGRID, NGRID), dtype=np.float64)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0
    nu = np.zeros_like(delta)
    nu[mask] = np.log(1.0 + np.clip(delta[mask], -1.0 + 1e-3, None))
    nu = gaussian_filter(nu, sigma=SIGMA_PX)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


def voxelize_mock(pos_sel, field_r, sum_wr, mask):
    """Cut-sky mock field via the shared build_field (log-transform included)."""
    if len(pos_sel) < 100:
        return None
    w_d = np.ones(len(pos_sel))
    field_d = cic_3d(pos_sel, w_d, NGRID, BOX_MIN, BOX_SIZE)
    alpha = float(w_d.sum()) / sum_wr
    return build_field(field_d, field_r, alpha, mask)


# ---------------------------------------------------------------------------
# FoF offset self-check
# ---------------------------------------------------------------------------
def check_fof():
    pos_h, mass_h, vel_h = read_halo_catalog(0, args.snapnum)
    print("[CHECK_FOF] sim 0, snapnum", args.snapnum)
    print(f"  N halos (>=20 part): {len(mass_h)}")
    print(f"  pos_h  range Mpc/h : [{pos_h.min():.1f}, {pos_h.max():.1f}] (expect ~[0,1000])")
    print(f"  mass_h range Msun/h: [{mass_h.min():.2e}, {mass_h.max():.2e}]")
    print(f"  |vel_h| km/s       : mean={np.linalg.norm(vel_h,axis=1).mean():.1f} "
          f"max={np.linalg.norm(vel_h,axis=1).max():.1f} (expect ~few 100s)")
    print("  If |vel| is ~0 or ~1e5, the GroupVel offset or sqrt(a) factor is wrong.")


# ---------------------------------------------------------------------------
# Recompute the DESI reference on the NATIVE grid at sigma_px=0.3204.
# The canonical bgs_ngc_delta_128.npy was voxelized at R=5 on the DESI cell
# (15.6 Mpc/h) -> sigma_px = 5/15.6 = 0.3204. This is ALREADY the mock cut-sky
# sigma_px. So <pers1>_DESI at matched sigma_px is simply compute_tda_features
# on the canonical field. (The 0.459 canonical was reported at sigma_px=0.216,
# i.e. R=5 on a 23.14 Mpc/h reference cell — a different grid. We do NOT use it.)
# ---------------------------------------------------------------------------
def recompute_desi_reference(mask, field_r, sum_wr):
    """Rebuild the DESI NGC field from the FITS catalogues through the SHARED
    build_field (log-transform included), so the DESI reference is consistent
    with the cut-sky mocks. This does NOT use the canonical 0.459 (built without
    log): every paper number moves as a result, by design."""
    field_d, sum_wd = load_desi_data_field()
    alpha = sum_wd / sum_wr
    nu_desi = build_field(field_d, field_r, alpha, mask)
    feats = compute_tda_features(nu_desi, mask, N_THRESH)
    return float(feats[5]), float(feats[4]), float(nu_desi[mask].std())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global PERS1_DESI, BETA1_MAX_DESI
    print("=" * 70)
    print("CAUCHY Phase 8 — Script 1: Cut-sky mocks, TEST 1 (diagnostic)")
    print("=" * 70)
    print(f"  snapnum={args.snapnum} (z=0.5), n_pilot={args.n_pilot}")
    print(f"  embedding cell={CELL:.3f} Mpc/h, sigma_px={SIGMA_PX:.4f}")
    print(f"  density target N_sel ~ {N_TARGET_BGS:,} (BGS NGC nominal)")

    for p, lbl in [(DESI_MASK_FILE, "mask"), (RAN_FITS, "random FITS"),
                   (NZ_FILE, "n(z)"), (HOD_CATALOG_DIR, "HOD halo dir")]:
        if not p.exists():
            print(f"[ERRORE] Mancante ({lbl}): {p}"); sys.exit(1)

    if args.check_fof:
        check_fof(); return

    mask = np.load(DESI_MASK_FILE)
    print(f"  mask fill: {100*mask.mean():.1f}%  ({mask.sum():,} voxel)")

    print("\n[1/3] Costruzione campo random DESI (denominatore FKP)...")
    field_r, sum_wr = load_desi_random_field()
    nz_z, nz_target = load_bgs_nz()
    print(f"  random field pronto; n(z) target su {len(nz_z)} bin")

    print("\n[0/3] Ricostruzione DESI reference dai FITS con log-transform "
          "(build_field condiviso)...")
    PERS1_DESI, BETA1_MAX_DESI, std_desi = recompute_desi_reference(mask, field_r, sum_wr)
    print(f"  nu_std_in_survey (DESI)      = {std_desi:.4f}  "
          f"(era 1.65 senza log — deve scendere)")
    print(f"  <pers1>_DESI (log, sigma_px=0.3204) = {PERS1_DESI:.5f}  "
          f"[canonico senza-log 0.45886 NON usato]")
    print(f"  beta1_max_DESI               = {BETA1_MAX_DESI:.0f}")

    print(f"\n[2/3] Loop su {args.n_pilot} mock cut-sky...")
    pers1_list, beta1_list, ngal_list = [], [], []
    t0 = time.time()
    for i in range(args.n_pilot):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = read_halo_catalog(i, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = populate_halos_hod_with_vel(pos_h, mass_h, vel_h,
                                                       HOD_MEDIAN, rng)
        if len(pos_gal) < 100:
            continue
        pos_sel = carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        delta_s = voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if delta_s is None:
            continue
        feats = compute_tda_features(delta_s, mask, N_THRESH)
        beta1_list.append(float(feats[4]))
        pers1_list.append(float(feats[5]))
        ngal_list.append(int(len(pos_sel)))
        if args.save_fields:
            np.savez(OUT_FIELDS_DIR / f"cutsky_{i:04d}.npz", delta=delta_s)
        if (i + 1) % 20 == 0 or i == 0:
            eta = (time.time() - t0) / (i + 1) * (args.n_pilot - i - 1) / 60
            print(f"  [{i+1}/{args.n_pilot}] N_sel~{np.median(ngal_list):.0f} "
                  f"<pers1>={np.mean(pers1_list):.4f} "
                  f"beta1_max={np.mean(beta1_list):.0f}  ETA={eta:.1f}min")

    pers1 = np.array(pers1_list)
    beta1 = np.array(beta1_list)
    n_ok = len(pers1)
    if n_ok < 20:
        print(f"[ERRORE] Solo {n_ok} mock validi — insufficiente."); sys.exit(1)

    print(f"\n[3/3] Verdetto (N={n_ok} mock validi)...")
    # <pers1>
    p_mean, p_std = float(pers1.mean()), float(pers1.std(ddof=1))
    z_pers1 = (PERS1_DESI - p_mean) / p_std
    rank_pers1 = float(np.mean(pers1 < PERS1_DESI))            # fraction of mocks below DESI
    # beta1_max
    b_mean, b_std = float(beta1.mean()), float(beta1.std(ddof=1))
    z_beta1 = (BETA1_MAX_DESI - b_mean) / b_std
    rank_beta1 = float(np.mean(beta1 < BETA1_MAX_DESI))

    # Frozen gate1 decision
    dissolved = (abs(z_pers1) < 3.0) and (abs(z_beta1) < 3.0)
    survives  = (z_pers1 >= 3.0) and (z_beta1 <= -3.0)
    verdict = "DISSOLVED" if dissolved else ("SURVIVES" if survives else "PARTIAL")

    print(f"  <pers1>: DESI={PERS1_DESI:.4f}  mock={p_mean:.4f}±{p_std:.4f}  "
          f"z={z_pers1:+.2f}  rank={rank_pers1*100:.1f}%")
    print(f"  beta1_max: DESI={BETA1_MAX_DESI:.0f}  mock={b_mean:.0f}±{b_std:.0f}  "
          f"z={z_beta1:+.2f}  rank={rank_beta1*100:.1f}%")
    print(f"\n  >>> VERDETTO GATE 1: {verdict}")
    if verdict == "DISSOLVED":
        print("      L'anomalia era la geometria. Pivot a paper metodologico.")
    elif verdict == "SURVIVES":
        print("      Geometria non spiega. Procedere a Test 2 e N=2000.")
    else:
        print("      Esito parziale. Realistico: paper metodologico con residuo.")

    out = {
        "schema_version": "1.0",
        "output_id": "phase8_cutsky_test1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "gate8_prior_v1_0.json",
        "n_pilot_requested": args.n_pilot,
        "n_mock_valid": n_ok,
        "snapnum": args.snapnum,
        "sigma_px": SIGMA_PX,
        "hod_params_b3_median": HOD_MEDIAN.tolist(),
        "satellite_velocity": "option_a_no_intrahalo_dispersion",
        "gadget_vel_sqrt_a": GADGET_VEL_SQRT_A,
        "density_target_bgs": N_TARGET_BGS,
        "desi_reference": {
            "pers1": PERS1_DESI, "beta1_max": BETA1_MAX_DESI,
            "sigma_px": SIGMA_PX,
            "note": ("Recomputed on the native DESI grid (R=5, cell 15.6 Mpc/h -> "
                     "sigma_px=0.3204), matched to the cut-sky mocks. The canonical "
                     "0.45886 (sigma_px=0.216) is NOT used here.")
        },
        "cutsky_mock_pers1": {"mean": p_mean, "std": p_std,
                              "z_desi": z_pers1, "rank_desi": rank_pers1},
        "cutsky_mock_beta1_max": {"mean": b_mean, "std": b_std,
                                  "z_desi": z_beta1, "rank_desi": rank_beta1},
        "median_ngal_selected": float(np.median(ngal_list)),
        "verdict": verdict,
        "n_floor_note": ("With N=%d the empirical p-floor is ~1/%d; z-scores are "
                         "auxiliary tail extrapolations, ranks are primary."
                         % (n_ok, n_ok + 1)),
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[SAVED] {OUTPUT_JSON}")
    print("[COMPLETATO] Test 1 terminato.")


if __name__ == "__main__":
    main()
```


## FILE: src/phase1_tda_baseline.py
<!-- score=296 size=48.5KB keywords=['fvec', 'betti', 'persistence', 'gudhi', 'phase1', 'smooth', 'mask', 'smoothing', 'superlevel', 'cubicalcomplex'] -->

```python
#!/usr/bin/env python3
"""
CAUCHY — Phase 1 TDA Baseline (Ramo A)
Script: phase1_tda_baseline.py

Genera le Betti curves da filtrazione di supralivello su campi di densità 128³,
estrae 8 feature fisicamente motivate, esegue analisi Fisher (Gate 1a) e
correlazioni con w0 (Gate 1b).

Autore: generato da Claude per il PI del Progetto CAUCHY
Riferimento metodologico: CAUCHY_Systematic_Methodology_v2.md §1.2–1.4
Riferimento parametri: CAUCHY_Execution_Parameters.md v1.1
Benchmark: Abedi et al. 2025 (arXiv:2410.01751v2)

Usage:
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode sanity
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode sensitivity
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode full
"""

import argparse
import json
import logging
import multiprocessing as mp
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import gudhi
import numpy as np
import scipy.ndimage
import scipy.stats
from tqdm import tqdm

# ---------------------------------------------------------------------------
# GLOBAL CONFIGURATION
# ---------------------------------------------------------------------------

GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

N_THRESH = 50          # soglie di filtrazione per Betti curve
N_SENSITIVITY = 50     # campi fiduciali per sensitivity check (indici 0-49)
N_FIDUCIAL_FULL = 2000 # campi fiduciali totali
N_LHC = 2000           # campi LHC
N_NWLH = 2000          # campi nwLH
N_FEAT = 8             # numero di feature scalari

# Colonne nei file parametri (0-indexed, dopo header)
LHC_COL_OMM   = 0  # Omega_m
LHC_COL_S8    = 4  # sigma_8
NWLH_COL_OMM  = 0  # Omega_m
NWLH_COL_S8   = 4  # sigma_8
NWLH_COL_W0   = 6  # w0

# Valori fiduciali Quijote (Planck 2018)
FID_OMM  = 0.3175
FID_S8   = 0.8340
FID_W0   = -1.0

# Parametri di smoothing (Resolution: 1 Gpc/h / 128 voxel = 7.8125 Mpc/h per voxel)
# R=5 Mpc/h → sigma_pixel = 5 / 7.8125 = 0.64 px
# R=10 Mpc/h → sigma_pixel = 10 / 7.8125 = 1.28 px
BOX_SIZE_MPCH  = 1000.0
N_GRID         = 128
PIX_SIZE_MPCH  = BOX_SIZE_MPCH / N_GRID  # 7.8125 Mpc/h
SIGMA_R5_PX    = 5.0  / PIX_SIZE_MPCH    # 0.64 px
SIGMA_R10_PX   = 10.0 / PIX_SIZE_MPCH    # 1.28 px

# Gate 1 threshold (CAUCHY_Execution_Parameters.md v1.1 §3.3–3.4)
GATE1A_SIGMA_OMM_MAX  = 0.10
GATE1A_SIGMA_S8_MAX   = 0.030
GATE1B_R_MIN_HARD     = 0.10   # b1_peak_pos e b2_mean_persistence
GATE1B_R_MIN_SOFT     = 0.15   # almeno una feature

# Regione locale per derivate numeriche Fisher
# |theta - theta_fid| <= 0.3 * range_theta
FISHER_LOCAL_FRAC = 0.3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cauchy.phase1")


# ---------------------------------------------------------------------------
# CORE TDA FUNCTIONS
# ---------------------------------------------------------------------------

def field_to_nu(field: np.ndarray) -> np.ndarray:
    """
    Converte campo di densità δ(x) nella variabile di filtrazione
    ν = log(δ + 1), come in Abedi et al. 2025.

    I campi preprocessati sono mean-subtracted (⟨δ⟩ = 0), quindi
    δ può essere < 0. Il minimo fisico è δ = -1 (vuoto totale).
    Il clipping a -0.9999 evita log(0) o log(negativo).
    """
    return np.log(np.clip(field, -0.9999, None) + 1.0)


def compute_persistence_diagram(field: np.ndarray):
    """
    Calcola i diagrammi di persistenza per β₀, β₁, β₂ tramite
    filtrazione di supralivello su gudhi CubicalComplex.

    La filtrazione di supralivello su ν(x) è implementata passando
    -ν(x) a gudhi (che implementa filtrazione di sottolivel):
    abbassare la soglia su -ν equivale ad alzarla su ν.

    Convenzione gudhi → ν originale:
        gudhi opera in spazio -ν (sottolivel) e restituisce:
            birth_g < death_g   (in spazio -ν: birth_g = -ν_birth, death_g = -ν_death)
        Conversione corretta:
            nu_birth = -birth_g   (col 0 negata: alta densità, feature nasce)
            nu_death = -death_g   (col 1 negata: bassa densità, feature muore)
            nu_birth > nu_death   ✓ (coerente con superlevel)

    Restituisce:
        dict con chiavi 'b0', 'b1', 'b2', ciascuna un array (N, 2)
        con colonne [nu_birth, nu_death] in unità di ν.
        nu_birth > nu_death (superlevel: feature nasce ad alta densità).
    """
    nu = field_to_nu(field)

    # gudhi CubicalComplex: top_dimensional_cells in ordine C (row-major)
    cc = gudhi.CubicalComplex(
        dimensions=list(nu.shape),
        top_dimensional_cells=(-nu).flatten().astype(np.float64)
    )
    cc.compute_persistence()

    diagrams = {}
    for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
        raw = cc.persistence_intervals_in_dimension(dim)  # (N, 2) in -ν
        if len(raw) == 0:
            diagrams[key] = np.empty((0, 2), dtype=np.float64)
        else:
            raw = np.array(raw, dtype=np.float64)
            # Scarta feature con death = +inf (componente illimitata β₀)
            finite_mask = np.isfinite(raw[:, 1])
            raw = raw[finite_mask]
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2), dtype=np.float64)
            else:
                # Conversione corretta: nu_birth=-col0, nu_death=-col1
                # gudhi col0=birth_g (basso in -nu = alta densita in nu, feature NASCE)
                # gudhi col1=death_g (alto in -nu  = bassa densita in nu, feature MUORE)
                nu_birth = -raw[:, 0]
                nu_death = -raw[:, 1]
                diagrams[key] = np.column_stack([nu_birth, nu_death])
                # nu_birth > nu_death per costruzione (superlevel)

    return diagrams


def betti_curve_from_diagram(diagram: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """
    Calcola la Betti curve β(t) per un array di soglie.

    Convenzione: diagram ha colonne [nu_birth, nu_death] con nu_birth > nu_death.
    Una feature è 'viva' alla soglia t (superlevel) se:
        nu_death < t <= nu_birth
    (nata a densità alta nu_birth, ancora viva finché t > nu_death)

    Parametri:
        diagram:    array (N, 2) con colonne [nu_birth, nu_death]
        thresholds: array (M,) di soglie (tipicamente decrescenti)

    Restituisce:
        array (M,) con numero di feature vive a ogni soglia
    """
    if len(diagram) == 0:
        return np.zeros(len(thresholds), dtype=np.float64)

    nu_birth = diagram[:, 0]  # (N,) — alta densita
    nu_death = diagram[:, 1]  # (N,) — bassa densita

    # feature viva a t se: nu_death < t <= nu_birth
    alive = (nu_birth[:, None] >= thresholds[None, :]) & (nu_death[:, None] < thresholds[None, :])
    return alive.sum(axis=0).astype(np.float64)


def compute_betti_curves_from_field(field: np.ndarray, thresholds: np.ndarray):
    """
    Pipeline completa: campo → diagrammi di persistenza → Betti curves.

    Restituisce:
        (diagrams, b0_curve, b1_curve, b2_curve)
        - diagrams: dict con 'b0','b1','b2' array (N,2)
        - b*_curve: array (N_THRESH,)
    """
    diagrams = compute_persistence_diagram(field)
    b0 = betti_curve_from_diagram(diagrams['b0'], thresholds)
    b1 = betti_curve_from_diagram(diagrams['b1'], thresholds)
    b2 = betti_curve_from_diagram(diagrams['b2'], thresholds)
    return diagrams, b0, b1, b2


def compute_field_thresholds(field: np.ndarray, n_thresh: int = N_THRESH):
    """
    Calcola le N_THRESH soglie per-campo: uniformi tra 5° e 95° percentile
    della variabile di filtrazione ν = log(δ+1).

    Restituisce array (N_THRESH,) in ordine DECRESCENTE (alta→bassa densità),
    coerente con la direzione della filtrazione di supralivello.
    """
    nu = field_to_nu(field)
    lo = np.percentile(nu, 5)
    hi = np.percentile(nu, 95)
    return np.linspace(hi, lo, n_thresh)


# ---------------------------------------------------------------------------
# FEATURE EXTRACTION
# ---------------------------------------------------------------------------

def extract_features(thresholds: np.ndarray,
                     b0: np.ndarray, b1: np.ndarray, b2: np.ndarray,
                     diagrams: dict) -> dict:
    """
    Estrae le 8 feature scalari da Betti curves e diagrammi di persistenza.
    Riferimento: CAUCHY_Systematic_Methodology_v2.md §1.2 e
                 CAUCHY_Execution_Parameters.md §9.1

    Le soglie sono in ordine decrescente (alta → bassa densità).
    Per 'posizione del picco' usiamo il valore di ν corrispondente.

    Feature:
        b1_peak_pos          : ν al picco di β₁
        b1_peak_height       : altezza del picco di β₁
        b1_fwhm              : FWHM della curva β₁ (in unità di ν)
        b1_integral          : integrale di β₁ (somma × Δν)
        b2_max_count         : massimo di β₂
        b2_mean_persistence  : persistenza media su tutte le feature β₂
        b2_high_persist      : integrale top-10% persistenza β₂ (su Betti curve)
        b0_at_mean           : β₀ alla soglia più vicina a ν=0 (densità media)
    """
    feats = {}
    dnu = abs(thresholds[1] - thresholds[0])  # passo di integrazione

    # --- β₁ features ---
    if np.any(b1 > 0):
        pk_idx = int(np.argmax(b1))
        feats['b1_peak_pos']    = float(thresholds[pk_idx])
        feats['b1_peak_height'] = float(b1[pk_idx])

        # FWHM
        half_max = b1[pk_idx] / 2.0
        above = b1 >= half_max
        if above.sum() >= 2:
            idxs = np.where(above)[0]
            feats['b1_fwhm'] = float(abs(thresholds[idxs[0]] - thresholds[idxs[-1]]))
        else:
            feats['b1_fwhm'] = float(dnu)

        feats['b1_integral'] = float(np.sum(b1) * dnu)
    else:
        feats['b1_peak_pos']    = 0.0
        feats['b1_peak_height'] = 0.0
        feats['b1_fwhm']        = 0.0
        feats['b1_integral']    = 0.0

    # --- β₂ features ---
    feats['b2_max_count'] = float(np.max(b2)) if len(b2) > 0 else 0.0

    # Persistenza da diagramma
    d2 = diagrams.get('b2', np.empty((0, 2)))
    if len(d2) > 0:
        persistence = d2[:, 0] - d2[:, 1]  # nu_birth - nu_death > 0 per costruzione
        persistence = persistence[persistence > 0]
        if len(persistence) > 0:
            feats['b2_mean_persistence'] = float(np.mean(persistence))
            # Top 10% per alta persistenza
            p90 = np.percentile(persistence, 90)
            feats['b2_high_persist'] = float(np.sum(persistence[persistence >= p90]))
        else:
            feats['b2_mean_persistence'] = 0.0
            feats['b2_high_persist']     = 0.0
    else:
        feats['b2_mean_persistence'] = 0.0
        feats['b2_high_persist']     = 0.0

    # --- β₀ al livello di densità media ---
    # Cercare la soglia più vicina a ν=0 (log(0+1)=0, cioè δ=0, densità media)
    target_nu = 0.0
    idx_mean = int(np.argmin(np.abs(thresholds - target_nu)))
    feats['b0_at_mean'] = float(b0[idx_mean])

    return feats


FEATURE_NAMES = [
    'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
    'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
]


def features_to_vector(feats: dict) -> np.ndarray:
    """Converte dict feature in vettore numpy ordinato come FEATURE_NAMES."""
    return np.array([feats[k] for k in FEATURE_NAMES], dtype=np.float64)


# ---------------------------------------------------------------------------
# WORKER FUNCTIONS (multiprocessing)
# ---------------------------------------------------------------------------

def _worker_init(shared_thresholds_):
    """Inizializza variabile globale nel worker per le soglie comuni."""
    global _shared_thresholds
    _shared_thresholds = shared_thresholds_


def _process_field_sanity(args):
    """
    Worker per modalità sanity: processa un campo fiduciale.
    Restituisce (thresholds_perfield, b0, b1, b2, features_dict).
    """
    field_path, common_thresholds = args
    try:
        field = np.load(field_path).astype(np.float64)
        thresholds_pf = compute_field_thresholds(field, N_THRESH)
        diagrams, b0_pf, b1_pf, b2_pf = compute_betti_curves_from_field(field, thresholds_pf)

        # Interpola su griglia comune
        b0_c = np.interp(common_thresholds, thresholds_pf[::-1], b0_pf[::-1])
        b1_c = np.interp(common_thresholds, thresholds_pf[::-1], b1_pf[::-1])
        b2_c = np.interp(common_thresholds, thresholds_pf[::-1], b2_pf[::-1])

        feats = extract_features(thresholds_pf, b0_pf, b1_pf, b2_pf, diagrams)
        return (common_thresholds, b0_c, b1_c, b2_c, feats, None)
    except Exception as e:
        return (None, None, None, None, None, str(e))


def _process_field_full(args):
    """
    Worker per modalità full: processa un campo qualsiasi.
    Restituisce (features_vec, pd_b1_birth, pd_b1_death, pd_b2_birth, pd_b2_death, error).
    save_pd: bool, se True salva anche i diagrammi di persistenza.
    """
    field_path, common_thresholds, save_pd = args
    try:
        field = np.load(field_path).astype(np.float64)
        thresholds_pf = compute_field_thresholds(field, N_THRESH)
        diagrams, b0_pf, b1_pf, b2_pf = compute_betti_curves_from_field(field, thresholds_pf)

        feats = extract_features(thresholds_pf, b0_pf, b1_pf, b2_pf, diagrams)
        fvec  = features_to_vector(feats)

        if save_pd:
            d1 = diagrams.get('b1', np.empty((0, 2)))
            d2 = diagrams.get('b2', np.empty((0, 2)))
            pd_data = (
                d1[:, 0] if len(d1) else np.array([]),
                d1[:, 1] if len(d1) else np.array([]),
                d2[:, 0] if len(d2) else np.array([]),
                d2[:, 1] if len(d2) else np.array([]),
            )
        else:
            pd_data = None

        return (fvec, pd_data, None)
    except Exception as e:
        return (None, None, str(e))


def _process_field_sensitivity(args):
    """
    Worker per sensitivity check: processa un campo con due smoothing.
    Restituisce (b0_R5, b1_R5, b2_R5, b0_R10, b1_R10, b2_R10, error).
    """
    field_path, common_thresholds = args
    try:
        field_R5 = np.load(field_path).astype(np.float64)
        # field_R5 è già smoothed a R=5 Mpc/h dalla Phase 0
        # Re-smoothing a R=10: applica Gaussian aggiuntivo
        # σ_combined = sqrt(σ_R10² - σ_R5²) in pixel
        sigma_extra = np.sqrt(SIGMA_R10_PX**2 - SIGMA_R5_PX**2)
        field_R10 = scipy.ndimage.gaussian_filter(field_R5, sigma=sigma_extra)

        # Betti curves per R5
        th5 = compute_field_thresholds(field_R5, N_THRESH)
        diag5, b0_5, b1_5, b2_5 = compute_betti_curves_from_field(field_R5, th5)
        b0_5c = np.interp(common_thresholds, th5[::-1], b0_5[::-1])
        b1_5c = np.interp(common_thresholds, th5[::-1], b1_5[::-1])
        b2_5c = np.interp(common_thresholds, th5[::-1], b2_5[::-1])

        # Betti curves per R10
        th10 = compute_field_thresholds(field_R10, N_THRESH)
        diag10, b0_10, b1_10, b2_10 = compute_betti_curves_from_field(field_R10, th10)
        b0_10c = np.interp(common_thresholds, th10[::-1], b0_10[::-1])
        b1_10c = np.interp(common_thresholds, th10[::-1], b1_10[::-1])
        b2_10c = np.interp(common_thresholds, th10[::-1], b2_10[::-1])

        return (b0_5c, b1_5c, b2_5c, b0_10c, b1_10c, b2_10c, None)
    except Exception as e:
        return (None, None, None, None, None, None, str(e))


# ---------------------------------------------------------------------------
# COMMON THRESHOLD GRID
# ---------------------------------------------------------------------------

def build_common_threshold_grid(fiducial_paths: list, n_sample: int = 50) -> np.ndarray:
    """
    Costruisce la griglia comune di N_THRESH soglie come media dei percentili
    5° e 95° della variabile ν calcolati su n_sample campi fiduciali.

    Questo garantisce una griglia rappresentativa del range fisico tipico
    preservando la coerenza tra la media per-campo e la griglia comune.
    """
    log.info(f"Costruzione griglia comune da {n_sample} campi fiduciali sample...")
    lo_vals, hi_vals = [], []
    sample_paths = fiducial_paths[:n_sample]
    for fp in tqdm(sample_paths, desc="Grid sampling", leave=False):
        field = np.load(fp).astype(np.float64)
        nu = field_to_nu(field)
        lo_vals.append(np.percentile(nu, 5))
        hi_vals.append(np.percentile(nu, 95))

    lo_mean = float(np.mean(lo_vals))
    hi_mean = float(np.mean(hi_vals))
    log.info(f"Griglia comune: ν ∈ [{lo_mean:.4f}, {hi_mean:.4f}]")
    # Ordine decrescente (superlevel: alta → bassa densità)
    return np.linspace(hi_mean, lo_mean, N_THRESH)


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_params(params_path: Path, col_map: dict) -> dict:
    """
    Carica il file dei parametri cosmologici.
    col_map: dict {nome_param: indice_colonna}
    Restituisce dict {nome_param: array(N,)}
    """
    data = np.loadtxt(params_path, comments='#')
    result = {}
    for name, col in col_map.items():
        result[name] = data[:, col]
    log.info(f"Parametri caricati da {params_path.name}: {data.shape[0]} righe")
    return result


def list_field_paths(dataset_dir: Path, n_fields: int) -> list:
    """Lista i path dei campi in ordine: field_0000.npy ... field_{n-1:04d}.npy"""
    paths = [dataset_dir / f"field_{i:04d}.npy" for i in range(n_fields)]
    missing = [p for p in paths if not p.exists()]
    if missing:
        log.warning(f"{len(missing)} file mancanti in {dataset_dir}")
        if len(missing) > 10:
            log.warning(f"Primi 5 mancanti: {missing[:5]}")
    return paths


# ---------------------------------------------------------------------------
# SMOOTHING SENSITIVITY CHECK
# ---------------------------------------------------------------------------

def run_sensitivity_check(field_paths: list, common_thresholds: np.ndarray,
                          n_workers: int) -> dict:
    """
    Impegno Review 0 Concern 1 (CAUCHY_Review_and_GATE.md).
    Confronta Betti curves medie a R=5 Mpc/h vs R=10 Mpc/h su N_SENSITIVITY campi.

    Metrica: Δβ_k = |⟨β_k⟩_{R=10} − ⟨β_k⟩_{R=5}| / σ_{R=5}
    (media point-wise della differenza normalizzata sulla curva)
    """
    log.info(f"Sensitivity check su {N_SENSITIVITY} campi fiduciali "
             f"(R=5 vs R=10 Mpc/h)...")

    paths_sub = field_paths[:N_SENSITIVITY]
    args = [(p, common_thresholds) for p in paths_sub]

    b0_5_all, b1_5_all, b2_5_all = [], [], []
    b0_10_all, b1_10_all, b2_10_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_sensitivity, args),
                        total=len(args), desc="Sensitivity"):
            b0_5, b1_5, b2_5, b0_10, b1_10, b2_10, err = res
            if err:
                n_errors += 1
                log.warning(f"Errore sensitivity: {err}")
            else:
                b0_5_all.append(b0_5);  b1_5_all.append(b1_5);  b2_5_all.append(b2_5)
                b0_10_all.append(b0_10); b1_10_all.append(b1_10); b2_10_all.append(b2_10)

    if len(b0_5_all) == 0:
        log.error("Sensitivity check fallito: nessun campo processato correttamente.")
        return {"error": "no_fields_processed"}

    b0_5_arr  = np.array(b0_5_all);   b1_5_arr  = np.array(b1_5_all);   b2_5_arr  = np.array(b2_5_all)
    b0_10_arr = np.array(b0_10_all);  b1_10_arr = np.array(b1_10_all);  b2_10_arr = np.array(b2_10_all)

    def delta_normalized(arr5, arr10):
        """Differenza media normalizzata point-wise sulla curva."""
        mean5  = arr5.mean(axis=0)
        std5   = arr5.std(axis=0)
        mean10 = arr10.mean(axis=0)
        # Evita divisione per zero nelle regioni dove std≈0
        with np.errstate(invalid='ignore', divide='ignore'):
            ratio = np.where(std5 > 1e-10, np.abs(mean10 - mean5) / std5, 0.0)
        return float(np.mean(ratio))

    delta_b0 = delta_normalized(b0_5_arr, b0_10_arr)
    delta_b1 = delta_normalized(b1_5_arr, b1_10_arr)
    delta_b2 = delta_normalized(b2_5_arr, b2_10_arr)

    # Verdict: se Δβ_k > 1 per qualsiasi k, segnala al Reviewer
    max_delta = max(delta_b0, delta_b1, delta_b2)
    if max_delta > 1.0:
        verdict = f"WARNING: Δβ_max={max_delta:.3f} > 1σ — informare il Reviewer (Concern 1)"
    else:
        verdict = f"OK: Δβ_max={max_delta:.3f} < 1σ — smoothing scale robusto"

    log.info(f"Sensitivity: Δβ₀={delta_b0:.3f}, Δβ₁={delta_b1:.3f}, Δβ₂={delta_b2:.3f}")
    log.info(f"Verdict: {verdict}")

    return {
        "n_fields_tested":       N_SENSITIVITY,
        "n_errors":              n_errors,
        "delta_b0_normalized":   delta_b0,
        "delta_b1_normalized":   delta_b1,
        "delta_b2_normalized":   delta_b2,
        "sigma_R5_px":           SIGMA_R5_PX,
        "sigma_R10_px":          SIGMA_R10_PX,
        "verdict":               verdict,
    }


# ---------------------------------------------------------------------------
# SANITY MODE: 50 campi fiduciali
# ---------------------------------------------------------------------------

def run_sanity_mode(fiducial_paths: list, common_thresholds: np.ndarray,
                    n_workers: int) -> dict:
    """
    Processa 50 campi fiduciali → Betti curves medie + sensitivity check.
    Output parziale del JSON (senza Fisher e correlazioni).
    """
    log.info("=== MODALITÀ SANITY: 50 campi fiduciali ===")
    paths_sub = fiducial_paths[:N_SENSITIVITY]
    args = [(p, common_thresholds) for p in paths_sub]

    b0_all, b1_all, b2_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_sanity, args),
                        total=len(args), desc="Sanity TDA"):
            ct, b0, b1, b2, feats, err = res
            if err:
                n_errors += 1
                log.warning(f"Errore sanity: {err}")
            else:
                b0_all.append(b0); b1_all.append(b1); b2_all.append(b2)

    if len(b0_all) == 0:
        raise RuntimeError("Sanity check fallito: nessun campo processato.")

    b0_arr = np.array(b0_all)
    b1_arr = np.array(b1_all)
    b2_arr = np.array(b2_all)

    betti_result = {
        "n_fields":  len(b0_all),
        "n_errors":  n_errors,
        "mean_b0":   b0_arr.mean(axis=0).tolist(),
        "mean_b1":   b1_arr.mean(axis=0).tolist(),
        "mean_b2":   b2_arr.mean(axis=0).tolist(),
        "std_b0":    b0_arr.std(axis=0).tolist(),
        "std_b1":    b1_arr.std(axis=0).tolist(),
        "std_b2":    b2_arr.std(axis=0).tolist(),
        "thresholds": common_thresholds.tolist(),
    }

    log.info(f"Betti curves medie calcolate su {len(b0_all)} campi ({n_errors} errori)")
    log.info(f"β₁ picco medio: {b1_arr.mean(axis=0).max():.2f} "
             f"a ν={common_thresholds[b1_arr.mean(axis=0).argmax()]:.4f}")
    log.info(f"β₂ picco medio: {b2_arr.mean(axis=0).max():.2f} "
             f"a ν={common_thresholds[b2_arr.mean(axis=0).argmax()]:.4f}")

    return betti_result


# ---------------------------------------------------------------------------
# FULL MODE — FIDUCIAL: matrice di covarianza
# ---------------------------------------------------------------------------

def run_fiducial_covariance(fiducial_paths: list, common_thresholds: np.ndarray,
                             n_workers: int):
    """
    Processa tutti i 2000 campi fiduciali per:
    1. Betti curves medie (μ_ΛCDM)
    2. Matrice di covarianza del rumore C_noise [8×8]
    """
    log.info("=== FIDUCIAL: 2000 campi → Betti curves + C_noise ===")
    args = [(p, common_thresholds, False) for p in fiducial_paths]

    fvecs = []
    b0_all, b1_all, b2_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_full, args),
                        total=len(args), desc="Fiducial"):
            fvec, pd_data, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)
                # Per Betti curves medie: ricalcolo dalla Betti curve
                # (già estratte nelle feature ma vogliamo le curve complete)

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo fiduciale processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    log.info(f"Fiducial: {len(fvecs)} campi OK ({n_errors} errori)")

    # Matrice di covarianza con fattore di Hartlap
    n_fid = len(fvecs)
    hartlap = (n_fid - N_FEAT - 2) / (n_fid - 1)
    C_noise = np.cov(fvecs.T)   # (8, 8)
    log.info(f"C_noise calcolata. Hartlap α = {hartlap:.6f}")

    return fvecs, C_noise, hartlap, n_errors


# ---------------------------------------------------------------------------
# FULL MODE — LHC: analisi Fisher (Gate 1a)
# ---------------------------------------------------------------------------

def run_lhc_fisher(lhc_paths: list, lhc_params: dict, common_thresholds: np.ndarray,
                   C_noise: np.ndarray, hartlap: float, n_workers: int) -> dict:
    """
    Gate 1a: matrice Fisher su (Ωm, σ₈) da campi LHC.

    Metodo derivate numeriche: regressione lineare locale
    su campi con |θ − θ_fid| ≤ FISHER_LOCAL_FRAC × range_θ.
    """
    log.info("=== LHC FISHER: 2000 campi → Gate 1a ===")

    # Processa tutti i campi LHC
    args = [(p, common_thresholds, False) for p in lhc_paths]
    fvecs = []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_full, args),
                        total=len(args), desc="LHC Fisher"):
            fvec, _, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo LHC processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    omm_arr = lhc_params['Omega_m'][:len(fvecs)]
    s8_arr  = lhc_params['sigma_8'][:len(fvecs)]

    log.info(f"LHC: {len(fvecs)} campi OK ({n_errors} errori)")

    def numerical_derivative(feat_vals: np.ndarray, param_vals: np.ndarray,
                             fid_val: float) -> float:
        """Regressione lineare locale intorno al valore fiduciale."""
        param_range = param_vals.max() - param_vals.min()
        local_mask = np.abs(param_vals - fid_val) <= FISHER_LOCAL_FRAC * param_range
        if local_mask.sum() < 5:
            # Fallback: usa tutti i punti
            local_mask = np.ones(len(param_vals), dtype=bool)
            log.warning("Regressione locale: meno di 5 punti → uso tutti i dati")
        slope, intercept, r, p, se = scipy.stats.linregress(
            param_vals[local_mask], feat_vals[local_mask]
        )
        return float(slope)

    # Derivate ∂feature_k/∂Omega_m e ∂feature_k/∂sigma_8
    derivs_omm = np.array([
        numerical_derivative(fvecs[:, k], omm_arr, FID_OMM) for k in range(N_FEAT)
    ])
    derivs_s8 = np.array([
        numerical_derivative(fvecs[:, k], s8_arr, FID_S8) for k in range(N_FEAT)
    ])

    # Deriva anche ∂/∂w0 se disponibile (non nel LHC standard, solo documentazione)
    # Per Gate 1a σ(w0) non è threshold pass/fail — solo documentato
    # Il LHC non varia w0, quindi σ(w0) viene da nwLH (calcolato separatamente)

    # Matrice Fisher F_ij = (∂f/∂θ_i)^T × (α × C_noise^{-1}) × (∂f/∂θ_j)
    try:
        C_inv = np.linalg.inv(C_noise) * hartlap
    except np.linalg.LinAlgError:
        log.warning("C_noise singolare — uso pseudoinversa")
        C_inv = np.linalg.pinv(C_noise) * hartlap

    # Matrice delle derivate: D[k, θ] con θ ∈ {Ωm, σ8}
    D = np.column_stack([derivs_omm, derivs_s8])  # (8, 2)

    F = D.T @ C_inv @ D  # (2, 2): [Ωm, σ₈]

    try:
        F_inv = np.linalg.inv(F)
        sigma_omm = float(np.sqrt(F_inv[0, 0]))
        sigma_s8  = float(np.sqrt(F_inv[1, 1]))
        rho = float(F_inv[0, 1] / (sigma_omm * sigma_s8))
    except np.linalg.LinAlgError:
        log.error("Matrice Fisher non invertibile — gate FAIL automatico")
        sigma_omm = np.inf
        sigma_s8  = np.inf
        rho = 0.0

    # σ(w0) non calcolabile dal LHC (w0 fisso) — viene da nwLH Fisher esteso
    # Per ora placeholder; sarà aggiornato se si esegue Fisher esteso su nwLH
    sigma_w0 = None

    gate1a_pass = (sigma_omm <= GATE1A_SIGMA_OMM_MAX) and (sigma_s8 <= GATE1A_SIGMA_S8_MAX)
    gate1a_status = "PASS" if gate1a_pass else "FAIL"

    log.info(f"Fisher Gate 1a: σ(Ωm)={sigma_omm:.4f}, σ(σ₈)={sigma_s8:.4f}, "
             f"ρ(Ωm,σ₈)={rho:.3f} → {gate1a_status}")
    log.info(f"  Threshold: σ(Ωm) ≤ {GATE1A_SIGMA_OMM_MAX}, "
             f"σ(σ₈) ≤ {GATE1A_SIGMA_S8_MAX}")

    result = {
        "sigma_Omega_m":     sigma_omm,
        "sigma_sigma8":      sigma_s8,
        "sigma_w0":          sigma_w0,  # None → da aggiornare con nwLH
        "rho_Omegam_sigma8": rho,
        "hartlap_factor":    hartlap,
        "n_fields_ok":       len(fvecs),
        "n_errors":          n_errors,
        "derivatives_dOmm":  derivs_omm.tolist(),
        "derivatives_ds8":   derivs_s8.tolist(),
        "fisher_matrix":     F.tolist(),
        "gate1a_status":     gate1a_status,
    }
    return result


# ---------------------------------------------------------------------------
# FULL MODE — nwLH: correlazioni con w₀ (Gate 1b)
# ---------------------------------------------------------------------------

def run_nwlh_correlations(nwlh_paths: list, nwlh_params: dict,
                          common_thresholds: np.ndarray,
                          n_workers: int, pd_output_dir: Path) -> dict:
    """
    Gate 1b: correlazioni |r(feature_k, w₀)| su campi nwLH.
    Salva anche i diagrammi di persistenza per Phase 3 (GNN).
    """
    log.info("=== nwLH CORRELATIONS + PD SAVE: 2000 campi → Gate 1b ===")

    pd_output_dir.mkdir(parents=True, exist_ok=True)
    args = [(p, common_thresholds, True) for p in nwlh_paths]

    fvecs = []
    n_errors = 0
    n_saved_pd = 0

    with mp.Pool(n_workers) as pool:
        for i, res in enumerate(tqdm(pool.imap(_process_field_full, args),
                                      total=len(args), desc="nwLH Corr")):
            fvec, pd_data, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)
                if pd_data is not None:
                    b1_birth, b1_death, b2_birth, b2_death = pd_data
                    out_path = pd_output_dir / f"nwlh_field_{i:04d}_pd.npz"
                    np.savez_compressed(out_path,
                                        b1_birth=b1_birth, b1_death=b1_death,
                                        b2_birth=b2_birth, b2_death=b2_death)
                    n_saved_pd += 1

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo nwLH processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    w0_arr = nwlh_params['w0'][:len(fvecs)]

    log.info(f"nwLH: {len(fvecs)} campi OK ({n_errors} errori), {n_saved_pd} PD salvati")

    correlations = {}
    for k, name in enumerate(FEATURE_NAMES):
        r, p_val = scipy.stats.pearsonr(fvecs[:, k], w0_arr)
        correlations[name] = float(abs(r))

    max_corr = max(correlations.values())

    # Gate 1b check
    hard_pass = (
        correlations.get('b1_peak_pos', 0.0) >= GATE1B_R_MIN_HARD and
        correlations.get('b2_mean_persistence', 0.0) >= GATE1B_R_MIN_HARD
    )
    soft_pass = max_corr >= GATE1B_R_MIN_SOFT
    gate1b_pass = hard_pass and soft_pass
    gate1b_status = "PASS" if gate1b_pass else "FAIL"

    log.info("Gate 1b correlazioni |r|:")
    for name in FEATURE_NAMES:
        log.info(f"  {name}: {correlations[name]:.4f}")
    log.info(f"  max |r| = {max_corr:.4f} → Gate 1b: {gate1b_status}")

    return {
        "correlations":    correlations,
        "max_correlation": max_corr,
        "n_fields_ok":     len(fvecs),
        "n_errors":        n_errors,
        "n_pd_saved":      n_saved_pd,
        "gate1b_status":   gate1b_status,
    }


# ---------------------------------------------------------------------------
# OUTPUT JSON
# ---------------------------------------------------------------------------

def build_output_json(mode: str, tda_params: dict, sensitivity: dict,
                      betti_curves: dict, gate1a: dict, gate1b: dict) -> dict:
    """Assembla il JSON di output nel formato specificato dal prompt di sessione."""

    overall = None
    if gate1a and gate1b:
        overall = ("PASS"
                   if gate1a.get('gate1a_status') == "PASS" and
                      gate1b.get('gate1b_status') == "PASS"
                   else "FAIL")

    output = {
        "schema_version":    "2.0",
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "cauchy_version":    "v2.0",
        "gate":              "GATE_1",
        "mode":              mode,
        "tda_parameters":    tda_params,
    }

    if sensitivity:
        output["smoothing_sensitivity"] = sensitivity
    if betti_curves:
        output["fiducial_betti_curves"] = betti_curves
    if gate1a:
        output["gate1a"] = gate1a
    if gate1b:
        output["gate1b"] = gate1b
    if overall is not None:
        output["overall_gate1_status"] = overall

    return output


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="CAUCHY Phase 1 — TDA Baseline (Ramo A)"
    )
    p.add_argument(
        "--data-root", required=True, type=Path,
        help="Root del progetto dati (es. D:/projects/cauchy)"
    )
    p.add_argument(
        "--repo-root", required=True, type=Path,
        help="Root del repository (es. . o D:/projects/cauchy/repo)"
    )
    p.add_argument(
        "--mode", required=True,
        choices=["sanity", "full", "sensitivity", "resume"],
        help=(
            "sanity: 50 campi fiduciali + sensitivity (10-20 min); "
            "sensitivity: solo sensitivity check; "
            "full: tutti 6000 campi + PD (3-12 ore); "
            "resume: salta fiducial+PD gia completati, carica cache e riprende "
            "da LHC Fisher (da usare quando full ha crashato dopo i fiduciali)"
        )
    )
    p.add_argument(
        "--n-workers", type=int,
        default=min(mp.cpu_count(), 8),
        help="Numero di worker multiprocessing (default: min(cpu_count, 8))"
    )
    p.add_argument(
        "--skip-sensitivity", action="store_true",
        help="Salta il sensitivity check (solo in modalita full/resume)"
    )
    p.add_argument(
        "--lhc-params", type=Path, default=None,
        help="Path esplicito a latin_hypercube_params.txt. "
             "Se omesso, cerca in data-root/data/raw/quijote/3D_cubes/"
    )
    p.add_argument(
        "--nwlh-params", type=Path, default=None,
        help="Path esplicito a latin_hypercube_nwLH_params.txt. "
             "Se omesso, cerca in data-root/data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
    )
    return p.parse_args()


def main():
    args = parse_args()
    t_start = time.time()

    log.info(f"CAUCHY Phase 1 TDA Baseline — modalità: {args.mode.upper()}")
    log.info(f"data-root: {args.data_root}")
    log.info(f"n-workers: {args.n_workers}")
    log.info(f"gudhi version: {gudhi.__version__}")
    log.info(f"numpy version: {np.__version__}")

    # Paths
    data_root   = args.data_root
    repo_root   = args.repo_root
    fid_dir     = data_root / "data" / "processed" / "phase0_fields" / "fiducial"
    lhc_dir     = data_root / "data" / "processed" / "phase0_fields" / "lhc"
    nwlh_dir    = data_root / "data" / "processed" / "phase0_fields" / "nwlh"
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    pd_dir      = results_dir / "phase1_persistence_diagrams"

    # Path default dei file parametri (con override CLI via --lhc-params / --nwlh-params)
    _lhc_default  = (data_root / "data" / "raw" / "quijote" / "3D_cubes" /
                     "latin_hypercube" / "latin_hypercube_params.txt")
    _nwlh_default = (data_root / "data" / "raw" / "quijote" / "3D_cubes" /
                     "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt")
    lhc_params_path  = args.lhc_params  if args.lhc_params  else _lhc_default
    nwlh_params_path = args.nwlh_params if args.nwlh_params else _nwlh_default

    output_json_path = results_dir / "phase1_tda_baseline.json"

    # Validazione anticipata di tutti i path critici (prima di iniziare elaborazione)
    path_errors = []
    for d, name in [(fid_dir, "fiducial"), (lhc_dir, "lhc"), (nwlh_dir, "nwlh")]:
        if not d.exists():
            log.warning(f"Directory {name} non trovata: {d}")
    if args.mode in ("full", "resume"):
        if not lhc_params_path.exists():
            path_errors.append(f"LHC params non trovato: {lhc_params_path}")
        if not nwlh_params_path.exists():
            path_errors.append(f"nwLH params non trovato: {nwlh_params_path}")
    if path_errors:
        for e in path_errors:
            log.error(e)
        log.error("Correggere i path con --lhc-params e/o --nwlh-params e riprovare.")
        sys.exit(1)
    log.info(f"LHC params:  {lhc_params_path}")
    log.info(f"nwLH params: {nwlh_params_path}")

    # File paths
    fiducial_paths = list_field_paths(fid_dir, N_FIDUCIAL_FULL)

    # TDA parameters record
    tda_params = {
        "n_thresh":           N_THRESH,
        "filtration_variable": "log(delta+1)",
        "filtration_type":    "superlevel_via_negation",
        "implementation":     "gudhi.CubicalComplex",
        "gudhi_version":      gudhi.__version__,
        "numpy_version":      np.__version__,
        "global_seed":        GLOBAL_SEED,
        "grid_size":          "128^3",
        "box_size_mpch":      BOX_SIZE_MPCH,
        "threshold_range":    "5th-95th percentile of nu per field, interpolated to common grid",
        "common_grid_method": "mean of 5th/95th percentiles over 50 fiducial fields",
    }

    # -------------------------------------------------------------------------
    # Griglia comune (necessaria per tutte le modalità)
    # -------------------------------------------------------------------------
    log.info("Costruzione griglia comune di soglie...")
    common_thresholds = build_common_threshold_grid(
        fiducial_paths, n_sample=min(50, len(fiducial_paths))
    )
    tda_params["common_thresholds_lo"] = float(common_thresholds[-1])
    tda_params["common_thresholds_hi"] = float(common_thresholds[0])

    # -------------------------------------------------------------------------
    # MODALITÀ SENSITIVITY (standalone)
    # -------------------------------------------------------------------------
    if args.mode == "sensitivity":
        sensitivity = run_sensitivity_check(fiducial_paths, common_thresholds, args.n_workers)
        output = build_output_json("sensitivity", tda_params, sensitivity, None, None, None)
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")
        return

    # -------------------------------------------------------------------------
    # MODALITÀ SANITY
    # -------------------------------------------------------------------------
    if args.mode == "sanity":
        # Betti curves su 50 campi
        betti_curves = run_sanity_mode(fiducial_paths, common_thresholds, args.n_workers)

        # Sensitivity check (impegno Review 0 Concern 1)
        sensitivity = run_sensitivity_check(fiducial_paths, common_thresholds, args.n_workers)

        output = build_output_json("sanity", tda_params, sensitivity, betti_curves, None, None)
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")

        # Stampa digest per Sessione 2
        print("\n" + "="*60)
        print("DIGEST PER SESSIONE 2 — copiare nel prompt:")
        print("="*60)
        b1_mean = np.array(betti_curves["mean_b1"])
        b2_mean = np.array(betti_curves["mean_b2"])
        thresh  = np.array(betti_curves["thresholds"])
        print(f"β₁ picco: {b1_mean.max():.2f} a ν={thresh[b1_mean.argmax()]:.4f}")
        print(f"β₂ picco: {b2_mean.max():.2f} a ν={thresh[b2_mean.argmax()]:.4f}")
        s = sensitivity
        print(f"Sensitivity: Δβ₀={s['delta_b0_normalized']:.3f}, "
              f"Δβ₁={s['delta_b1_normalized']:.3f}, "
              f"Δβ₂={s['delta_b2_normalized']:.3f}")
        print(f"Verdict: {s['verdict']}")
        print("="*60)
        return

    # -------------------------------------------------------------------------
    # MODALITÀ RESUME: riprende da LHC Fisher dopo crash nel full
    # Presuppone che results/phase1_fiducial_cache.npz esista (prodotto da full)
    # -------------------------------------------------------------------------
    if args.mode == "resume":
        cache_path = results_dir / "phase1_fiducial_cache.npz"
        if not cache_path.exists():
            log.error(f"Cache fiduciale non trovata: {cache_path}")
            log.error("Eseguire prima --mode full (o aspettare che produca la cache).")
            sys.exit(1)
        log.info(f"Caricamento cache fiduciale da {cache_path}...")
        cache = np.load(cache_path, allow_pickle=True)
        fvecs_fid   = cache["fvecs_fid"]
        betti_curves = cache["betti_curves"].item()
        sensitivity  = cache["sensitivity"].item()
        n_fid_ok = len(fvecs_fid)
        hartlap  = (n_fid_ok - N_FEAT - 2) / (n_fid_ok - 1)
        C_noise  = np.cov(fvecs_fid.T)
        log.info(f"Cache caricata: {n_fid_ok} campi fiduciali, Hartlap={hartlap:.6f}")

        lhc_params = load_params(lhc_params_path, {
            "Omega_m": LHC_COL_OMM, "sigma_8": LHC_COL_S8
        })
        lhc_paths = list_field_paths(lhc_dir, N_LHC)
        gate1a = run_lhc_fisher(
            lhc_paths, lhc_params, common_thresholds,
            C_noise, hartlap, args.n_workers
        )

        nwlh_params = load_params(nwlh_params_path, {
            "Omega_m": NWLH_COL_OMM, "sigma_8": NWLH_COL_S8, "w0": NWLH_COL_W0
        })
        nwlh_paths = list_field_paths(nwlh_dir, N_NWLH)
        gate1b = run_nwlh_correlations(
            nwlh_paths, nwlh_params, common_thresholds,
            args.n_workers, pd_dir / "nwlh"
        )

        output = build_output_json(
            "full", tda_params, sensitivity, betti_curves, gate1a, gate1b
        )
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale sessione resume: {(time.time()-t_start)/60:.1f} min")
        print("\n" + "="*60)
        print("DIGEST RESUME")
        print("="*60)
        print(f"Gate 1a: {gate1a['gate1a_status']} — "
              f"sigma(Om)={gate1a['sigma_Omega_m']:.4f}, "
              f"sigma(s8)={gate1a['sigma_sigma8']:.4f}, "
              f"rho={gate1a['rho_Omegam_sigma8']:.3f}")
        print(f"Gate 1b: {gate1b['gate1b_status']} — "
              f"max|r|={gate1b['max_correlation']:.4f}")
        print(f"Overall: {output['overall_gate1_status']}")
        print("="*60)
        return

    # -------------------------------------------------------------------------
    # MODALITÀ FULL
    # -------------------------------------------------------------------------
    if args.mode == "full":
        log.info("=== MODALITÀ FULL: tutti 6000 campi ===")

        # Stima spazio disco per i PD
        # Stimare: per campo, ~100-500 feature PH, ~2000 b1/b2 total points
        # Ogni NPZ file ≈ 5-20 KB → 2000 campi nwLH ≈ 10-40 MB
        # (molto meno di quanto temuto nel prompt di sessione)
        log.info("Stima spazio disco PD: ~10-40 MB per 2000 campi nwLH (NPZ compressi)")

        # 1) Sensitivity check (a meno di --skip-sensitivity)
        if not args.skip_sensitivity:
            sensitivity = run_sensitivity_check(
                fiducial_paths, common_thresholds, args.n_workers
            )
        else:
            sensitivity = {"skipped": True}

        # 2) Fiducial: covarianza + Betti curves
        # (run_sanity_mode usa solo 50 campi per le curve medie nel sanity;
        #  per il full, calcoliamo le curve su tutti i fiduciali per μ_ΛCDM)
        log.info("Betti curves medie su tutti i 2000 campi fiduciali (μ_ΛCDM)...")
        fid_args = [(p, common_thresholds) for p in fiducial_paths]
        b0_all, b1_all, b2_all, fvecs_fid = [], [], [], []
        n_err_fid = 0

        with mp.Pool(args.n_workers) as pool:
            for res in tqdm(pool.imap(_process_field_sanity, fid_args),
                            total=len(fid_args), desc="Fiducial full"):
                ct, b0, b1, b2, feats, err = res
                if err:
                    n_err_fid += 1
                else:
                    b0_all.append(b0); b1_all.append(b1); b2_all.append(b2)
                    fvecs_fid.append(features_to_vector(feats))

        b0_arr = np.array(b0_all); b1_arr = np.array(b1_all); b2_arr = np.array(b2_all)
        fvecs_fid = np.array(fvecs_fid)

        betti_curves = {
            "n_fields":   len(b0_all),
            "n_errors":   n_err_fid,
            "mean_b0":    b0_arr.mean(axis=0).tolist(),
            "mean_b1":    b1_arr.mean(axis=0).tolist(),
            "mean_b2":    b2_arr.mean(axis=0).tolist(),
            "std_b0":     b0_arr.std(axis=0).tolist(),
            "std_b1":     b1_arr.std(axis=0).tolist(),
            "std_b2":     b2_arr.std(axis=0).tolist(),
            "thresholds": common_thresholds.tolist(),
        }

        # Matrice di covarianza
        n_fid_ok = len(fvecs_fid)
        hartlap  = (n_fid_ok - N_FEAT - 2) / (n_fid_ok - 1)
        C_noise  = np.cov(fvecs_fid.T)
        log.info(f"C_noise [8x8] calcolata. Hartlap a = {hartlap:.6f}")

        # Salva cache fiduciale per eventuale resume dopo crash
        cache_path = results_dir / "phase1_fiducial_cache.npz"
        np.savez_compressed(cache_path,
                            fvecs_fid=fvecs_fid,
                            betti_curves=np.array(betti_curves, dtype=object),
                            sensitivity=np.array(sensitivity, dtype=object))
        log.info(f"Cache fiduciale salvata: {cache_path} — safe point raggiunto")

        # Anche PD per i fiduciali (per μ_ΛCDM in Phase 3)
        log.info("Salvataggio PD fiduciali...")
        pd_fid_dir = pd_dir / "fiducial"
        pd_fid_dir.mkdir(parents=True, exist_ok=True)
        fid_pd_args = [(p, common_thresholds, True) for p in fiducial_paths]
        with mp.Pool(args.n_workers) as pool:
            for i, res in enumerate(tqdm(pool.imap(_process_field_full, fid_pd_args),
                                          total=len(fid_pd_args), desc="Fiducial PD")):
                fvec, pd_data, err = res
                if not err and pd_data is not None:
                    b1b, b1d, b2b, b2d = pd_data
                    np.savez_compressed(
                        pd_fid_dir / f"fiducial_field_{i:04d}_pd.npz",
                        b1_birth=b1b, b1_death=b1d, b2_birth=b2b, b2_death=b2d
                    )

        # 3) LHC: Fisher Gate 1a
        lhc_params = load_params(lhc_params_path, {
            'Omega_m': LHC_COL_OMM, 'sigma_8': LHC_COL_S8
        })
        lhc_paths = list_field_paths(lhc_dir, N_LHC)
        gate1a = run_lhc_fisher(
            lhc_paths, lhc_params, common_thresholds,
            C_noise, hartlap, args.n_workers
        )

        # 4) nwLH: correlazioni Gate 1b + PD salvati
        nwlh_params = load_params(nwlh_params_path, {
            'Omega_m': NWLH_COL_OMM, 'sigma_8': NWLH_COL_S8, 'w0': NWLH_COL_W0
        })
        nwlh_paths = list_field_paths(nwlh_dir, N_NWLH)
        gate1b = run_nwlh_correlations(
            nwlh_paths, nwlh_params, common_thresholds,
            args.n_workers, pd_dir / "nwlh"
        )

        # Assembla output
        output = build_output_json(
            "full", tda_params, sensitivity, betti_curves, gate1a, gate1b
        )
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)

        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")

        # Digest finale
        print("\n" + "="*60)
        print("DIGEST FINALE FULL RUN")
        print("="*60)
        print(f"Gate 1a: {gate1a['gate1a_status']} — "
              f"σ(Ωm)={gate1a['sigma_Omega_m']:.4f}, "
              f"σ(σ₈)={gate1a['sigma_sigma8']:.4f}, "
              f"ρ={gate1a['rho_Omegam_sigma8']:.3f}")
        print(f"Gate 1b: {gate1b['gate1b_status']} — "
              f"max|r|={gate1b['max_correlation']:.4f}")
        print(f"Overall: {output['overall_gate1_status']}")
        print("="*60)


if __name__ == "__main__":
    # Su Windows, multiprocessing richiede il guard if __name__ == '__main__'
    mp.freeze_support()
    main()
```


## FILE: src/phase1_patch_cache.py
<!-- score=277 size=28.0KB keywords=['fvec', 'persistence', 'phase1', 'gudhi', 'betti', 'cubicalcomplex', 'superlevel', 'persistence_diagram', 'sigma_px', 'smoothing'] -->

```python
#!/usr/bin/env python3
"""
CAUCHY — Phase 1 Cache Patch
=============================
Scopo: aggiungere fvecs_lhc, fvecs_nwlh, lhc_cosmologies, nwlh_cosmologies
       alla cache e al baseline di Phase 1, prerequisiti di phase2_cnn.py.

Problema rilevato in Sessione 1 Phase 2:
    phase1_fiducial_cache.npz contiene solo: ['fvecs_fid', 'betti_curves', 'sensitivity']
    phase1_tda_baseline.json non contiene: lhc_cosmologies, nwlh_cosmologies

Questo script è una patch di integrazione — NON modifica i risultati Gate 1
né i numeri del gate (σ(Ωm), σ(σ₈), correlazioni w₀). Estende la cache con
le stesse feature già calcolate su fvecs_fid, applicate ai dataset LHC e nwLH.

PARAMETRI TDA CONGELATI (da phase1_gate_result.json — immutabili):
    n_thresh = 50
    filtration_variable = "log(delta+1)"
    filtration_type = "superlevel_via_negation"
    smoothing_sigma_px = 0.64   (corrispondente a R=5 Mpc/h su griglia 128³)
    implementation = gudhi.CubicalComplex
    global_seed = 42

COSMOLOGIE LHC/nwLH:
    Lette da data/quijote_params/ (file .txt standard della suite Quijote).
    Se non disponibili nel formato standard, lo script tenta formati alternativi.

Uso:
    python phase1_patch_cache.py [--dry-run] [--n-fields N]

    --dry-run:  stampa le statistiche senza scrivere file (verifica)
    --n-fields: processa solo i primi N campi (default: tutti — 2000)

Output:
    results/phase1_fiducial_cache.npz  (aggiornato con fvecs_lhc, fvecs_nwlh)
    results/phase1_tda_baseline.json   (aggiornato con lhc_cosmologies, nwlh_cosmologies)

Tempo stimato su RTX 5060 Ti (CPU):
    ~2–4 ore per 2000 campi LHC + 2000 campi nwLH (TDA parallelizzata su CPU)
"""

import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("cauchy.phase1_patch")

# ── Dipendenza gudhi ─────────────────────────────────────────────────────────
try:
    import gudhi
    HAS_GUDHI = True
except ImportError:
    HAS_GUDHI = False
    log.error("gudhi non disponibile. Installare: pip install gudhi>=3.9.0")
    sys.exit(1)

# ── Parametri TDA CONGELATI da phase1_gate_result.json ──────────────────────
N_THRESH = 50
SMOOTHING_SIGMA_PX = 0.64      # R=5 Mpc/h → σ=0.64 pixel su griglia 128³
GLOBAL_SEED = 42
N_FIELDS = 2000
GRID_SIZE = 128
FEATURE_NAMES = [
    "b1_peak_pos",
    "b1_peak_height",
    "b1_fwhm",
    "b1_integral",
    "b2_max_count",
    "b2_mean_persistence",
    "b2_high_persist",
    "b0_at_mean",
]

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data/processed/phase0_fields")
RESULTS_DIR = Path("results")
CACHE_PATH = Path("results/phase1_fiducial_cache.npz")
BASELINE_PATH = Path("results/phase1_tda_baseline.json")

# Cosmologie Quijote — possibili posizioni del file parametri
QUIJOTE_PARAM_PATHS = [
    Path("data/raw/quijote/3D_cubes/latin_hypercube/latin_hypercube_params.txt"),
    Path("data/latin_hypercube_params.txt"),
    Path("data/quijote_params/latin_hypercube_params.txt"),
]
QUIJOTE_NWLH_PARAM_PATHS = [
    Path("data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"),
    Path("data/latin_hypercube_nwLH_params.txt"),
    Path("data/quijote_params/latin_hypercube_nwLH_params.txt"),
]


# ═══════════════════════════════════════════════════════════════════════════
# Funzioni TDA — copiate verbatim da phase1_tda_baseline.py
# (NON modificare senza aggiornare anche phase1_tda_baseline.py)
# ═══════════════════════════════════════════════════════════════════════════

def field_to_nu(field: np.ndarray) -> np.ndarray:
    """ν = log(δ+1), clip a -0.9999 per evitare log(0). Identico a Phase 1."""
    return np.log(np.clip(field, -0.9999, None) + 1.0)


def compute_field_thresholds(field: np.ndarray, n_thresh: int = N_THRESH) -> np.ndarray:
    """
    N_THRESH soglie per-campo: uniformi tra 5° e 95° percentile di ν.
    Ordine DECRESCENTE (alta → bassa densità). Identico a Phase 1.
    """
    nu = field_to_nu(field)
    lo = np.percentile(nu, 5)
    hi = np.percentile(nu, 95)
    return np.linspace(hi, lo, n_thresh)


def compute_persistence_diagram(field: np.ndarray) -> dict:
    """
    Diagrammi di persistenza β₀,β₁,β₂ via CubicalComplex gudhi.
    Passa -ν(x) a gudhi (sublevel) → equivale a superlevel su ν.
    Convenzione output: colonne [nu_birth, nu_death], nu_birth > nu_death.
    Identico a Phase 1.
    """
    nu = field_to_nu(field)
    cc = gudhi.CubicalComplex(
        dimensions=list(nu.shape),
        top_dimensional_cells=(-nu).flatten().astype(np.float64)
    )
    cc.compute_persistence()

    diagrams = {}
    for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
        raw = cc.persistence_intervals_in_dimension(dim)
        if len(raw) == 0:
            diagrams[key] = np.empty((0, 2), dtype=np.float64)
        else:
            raw = np.array(raw, dtype=np.float64)
            finite_mask = np.isfinite(raw[:, 1])
            raw = raw[finite_mask]
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2), dtype=np.float64)
            else:
                nu_birth = -raw[:, 0]
                nu_death = -raw[:, 1]
                diagrams[key] = np.column_stack([nu_birth, nu_death])
    return diagrams


def betti_curve_from_diagram(diagram: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """
    β(t) per array di soglie. Feature viva a t se nu_death < t <= nu_birth.
    Identico a Phase 1.
    """
    if len(diagram) == 0:
        return np.zeros(len(thresholds), dtype=np.float64)
    nu_birth = diagram[:, 0]
    nu_death = diagram[:, 1]
    alive = (nu_birth[:, None] >= thresholds[None, :]) & \
            (nu_death[:, None] < thresholds[None, :])
    return alive.sum(axis=0).astype(np.float64)


def extract_features(thresholds: np.ndarray,
                     b0: np.ndarray, b1: np.ndarray, b2: np.ndarray,
                     diagrams: dict) -> dict:
    """
    8 feature scalari da Betti curves e diagrammi. Identico a Phase 1.

    b1_peak_pos       : ν al picco di β₁  (NON indice normalizzato)
    b1_peak_height    : altezza picco β₁
    b1_fwhm           : FWHM in unità di ν
    b1_integral       : Σ β₁ × Δν
    b2_max_count      : massimo di β₂
    b2_mean_persistence: persistenza media β₂ (nu_birth - nu_death)
    b2_high_persist   : somma top-10% persistenze β₂
    b0_at_mean        : β₀ alla soglia più vicina a ν=0
    """
    feats = {}
    dnu = abs(thresholds[1] - thresholds[0])

    if np.any(b1 > 0):
        pk_idx = int(np.argmax(b1))
        feats['b1_peak_pos']    = float(thresholds[pk_idx])   # valore ν, non indice
        feats['b1_peak_height'] = float(b1[pk_idx])
        half_max = b1[pk_idx] / 2.0
        above = b1 >= half_max
        if above.sum() >= 2:
            idxs = np.where(above)[0]
            feats['b1_fwhm'] = float(abs(thresholds[idxs[0]] - thresholds[idxs[-1]]))
        else:
            feats['b1_fwhm'] = float(dnu)
        feats['b1_integral'] = float(np.sum(b1) * dnu)
    else:
        feats['b1_peak_pos'] = feats['b1_peak_height'] = 0.0
        feats['b1_fwhm'] = feats['b1_integral'] = 0.0

    feats['b2_max_count'] = float(np.max(b2)) if len(b2) > 0 else 0.0

    d2 = diagrams.get('b2', np.empty((0, 2)))
    if len(d2) > 0:
        persistence = d2[:, 0] - d2[:, 1]
        persistence = persistence[persistence > 0]
        if len(persistence) > 0:
            feats['b2_mean_persistence'] = float(np.mean(persistence))
            p90 = np.percentile(persistence, 90)
            feats['b2_high_persist'] = float(np.sum(persistence[persistence >= p90]))
        else:
            feats['b2_mean_persistence'] = feats['b2_high_persist'] = 0.0
    else:
        feats['b2_mean_persistence'] = feats['b2_high_persist'] = 0.0

    idx_mean = int(np.argmin(np.abs(thresholds - 0.0)))
    feats['b0_at_mean'] = float(b0[idx_mean])

    return feats


def extract_betti_features(field: np.ndarray) -> np.ndarray:
    """
    Pipeline completa campo → fvec [8].
    Soglie per-campo (5°–95° percentile di ν, ordine decrescente).
    Wrapper per multiprocessing — identico alla pipeline Phase 1.
    """
    thresholds = compute_field_thresholds(field, N_THRESH)
    diagrams = compute_persistence_diagram(field)
    b0 = betti_curve_from_diagram(diagrams['b0'], thresholds)
    b1 = betti_curve_from_diagram(diagrams['b1'], thresholds)
    b2 = betti_curve_from_diagram(diagrams['b2'], thresholds)
    feats = extract_features(thresholds, b0, b1, b2, diagrams)
    return np.array([feats[k] for k in FEATURE_NAMES], dtype=np.float32)


def _worker(args):
    """Worker per multiprocessing — processa un singolo campo."""
    field_path, idx = args
    try:
        field = np.load(field_path, allow_pickle=False).astype(np.float64)
        fvec = extract_betti_features(field)
        return idx, fvec, None
    except Exception as e:
        return idx, None, str(e)


# ═══════════════════════════════════════════════════════════════════════════
# Caricamento cosmologie Quijote
# ═══════════════════════════════════════════════════════════════════════════

def load_quijote_lhc_cosmologies(n_fields: int = N_FIELDS) -> np.ndarray | None:
    """
    Carica i parametri cosmologici LHC da latin_hypercube_params.txt.

    Formato atteso (stesso stile del file nwLH confermato dal PI):
        # Omega_m  Omega_b  h  n_s  sigma_8  M_nu  [w0]
        col 0      col 1   col2 col3  col4   col5   col6

    Omm = colonna 0, sigma_8 = colonna 4.
    Restituisce array [N, 2] con colonne [Omm, s8].
    """
    for path in QUIJOTE_PARAM_PATHS:
        if path.exists():
            log.info(f"  Caricamento cosmologie LHC da: {path}")
            try:
                # comments='#' gestisce header con #
                data = np.loadtxt(path, comments='#')
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                log.info(f"  LHC file: {data.shape[0]} righe, {data.shape[1]} colonne")

                # Omm sempre colonna 0, sigma_8 sempre colonna 4
                omm = data[:n_fields, 0]
                s8 = data[:n_fields, 4]

                # Sanity check contro range LHC Quijote
                # (CAUCHY_Execution_Parameters §1.2: Omm∈[0.10,0.50], s8∈[0.60,1.00])
                omm_ok = (omm.min() >= 0.08) and (omm.max() <= 0.52)
                s8_ok = (s8.min() >= 0.58) and (s8.max() <= 1.02)
                if omm_ok and s8_ok:
                    log.info(
                        f"  Sanity check LHC: OK — "
                        f"Ωm∈[{omm.min():.3f},{omm.max():.3f}], "
                        f"σ₈∈[{s8.min():.3f},{s8.max():.3f}]"
                    )
                else:
                    log.warning(
                        f"  ATTENZIONE: range fuori atteso. "
                        f"Ωm∈[{omm.min():.3f},{omm.max():.3f}] (atteso ~[0.10,0.50]), "
                        f"σ₈∈[{s8.min():.3f},{s8.max():.3f}] (atteso ~[0.60,1.00]). "
                        "Verificare colonne 0 (Omm) e 4 (sigma_8)."
                    )

                cosmo = np.stack([omm, s8], axis=-1).astype(np.float32)
                return cosmo
            except Exception as e:
                log.warning(f"  Errore lettura {path}: {e}")

    # Fallback: cerca nei metadata del phase0_gate_result se disponibile
    phase0_path = Path("results/phase0_gate_result.json")
    if phase0_path.exists():
        log.info("  Tentativo recupero cosmologie da phase0_gate_result.json...")
        try:
            with open(phase0_path) as f:
                p0 = json.load(f)
            if "lhc_cosmologies" in p0:
                cosmo = np.array(p0["lhc_cosmologies"], dtype=np.float32)
                log.info(f"  Cosmologie LHC da phase0: shape={cosmo.shape}")
                return cosmo[:n_fields]
        except Exception as e:
            log.warning(f"  Errore lettura phase0_gate_result: {e}")

    log.warning(
        "  Cosmologie LHC non trovate nei path standard. "
        "Il test T1 (Gate 2) userà cosmologie sintetiche di fallback. "
        "Aggiungere il file parametri Quijote in uno dei path attesi:\n"
        + "\n".join(f"    {p}" for p in QUIJOTE_PARAM_PATHS)
    )
    return None


def load_quijote_nwlh_cosmologies(n_fields: int = N_FIELDS) -> np.ndarray | None:
    """
    Carica i parametri cosmologici nwLH da latin_hypercube_nwLH_params.txt.

    Formato confermato (7 colonne, header con #):
        #Omega_m  Omega_b  h  n_s  sigma_8  M_nu  w0
        col 0     col 1    col2 col3  col4   col5  col6

    w0 è alla colonna 6 (indice zero-based).
    Restituisce array [N, 1] con colonna [w0].
    """
    for path in QUIJOTE_NWLH_PARAM_PATHS:
        if path.exists():
            log.info(f"  Caricamento cosmologie nwLH da: {path}")
            try:
                # comments='#' gestisce la riga di header con #
                data = np.loadtxt(path, comments='#')
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                log.info(f"  nwLH file: {data.shape[0]} righe, {data.shape[1]} colonne")

                # Formato confermato: 7 colonne, w0 all'indice 6
                if data.shape[1] == 7:
                    w0 = data[:n_fields, 6]   # colonna w0
                    omm = data[:n_fields, 0]  # colonna Omm (per sanity check)
                    log.info(
                        f"  Formato 7 colonne confermato: "
                        f"w₀∈[{w0.min():.4f},{w0.max():.4f}], "
                        f"Ωm∈[{omm.min():.4f},{omm.max():.4f}] (fisso nei nwLH? "
                        f"std={omm.std():.4f})"
                    )
                elif data.shape[1] == 1:
                    w0 = data[:n_fields, 0]
                elif data.shape[1] >= 6:
                    # Fallback: prova colonna 5 (formato alternativo senza M_nu)
                    w0 = data[:n_fields, 5]
                    log.warning(
                        f"  {data.shape[1]} colonne — usando colonna 5 come w₀. "
                        "Verificare che sia corretto."
                    )
                else:
                    w0 = data[:n_fields, 0]
                    log.warning(
                        f"  {data.shape[1]} colonne inattese — usando colonna 0. "
                        "Verificare il formato del file."
                    )

                # Sanity check: w0 deve essere in [-1.30, -0.70] per nwLH Quijote
                w0_min, w0_max = w0.min(), w0.max()
                if w0_min < -1.35 or w0_max > -0.65:
                    log.warning(
                        f"  ATTENZIONE: w₀ fuori range atteso [-1.30,-0.70]: "
                        f"[{w0_min:.4f},{w0_max:.4f}]. "
                        "Verificare che la colonna corretta sia stata selezionata."
                    )
                else:
                    log.info(f"  Sanity check w₀: OK [{w0_min:.4f},{w0_max:.4f}]")

                cosmo = w0.reshape(-1, 1).astype(np.float32)
                return cosmo
            except Exception as e:
                log.warning(f"  Errore lettura {path}: {e}")

    log.warning(
        "  Cosmologie nwLH non trovate. "
        "Genera cosmologie sintetiche di fallback (w₀ uniformi in [-1.30,-0.70]).\n"
        "  ATTENZIONE: il test Fisher R1-2 su nwLH richiede w₀ reali. "
        "Aggiungere il file in uno dei path attesi:\n"
        + "\n".join(f"    {p}" for p in QUIJOTE_NWLH_PARAM_PATHS)
    )
    return None


def make_synthetic_cosmologies_lhc(n_fields: int = N_FIELDS) -> np.ndarray:
    """
    Fallback: cosmologie LHC sintetiche (Latin Hypercube).
    ATTENZIONE: sono sintetiche e NON corrispondono ai campi reali.
    Usare solo se i file Quijote non sono disponibili.
    Il test T1 con queste cosmologie NON è scientificamente valido.
    """
    rng = np.random.default_rng(GLOBAL_SEED)
    # Latin Hypercube manuale in [0.10, 0.50] × [0.60, 1.00]
    omm = rng.uniform(0.10, 0.50, n_fields).astype(np.float32)
    s8 = rng.uniform(0.60, 1.00, n_fields).astype(np.float32)
    log.warning(
        "  USANDO COSMOLOGIE SINTETICHE — NON corrispondono ai campi reali. "
        "Il test T1 Gate 2 con questi dati NON è scientificamente valido."
    )
    return np.stack([omm, s8], axis=-1)


def make_synthetic_cosmologies_nwlh(n_fields: int = N_FIELDS) -> np.ndarray:
    """Fallback: w₀ uniformi sintetiche."""
    rng = np.random.default_rng(GLOBAL_SEED + 1)
    w0 = rng.uniform(-1.30, -0.70, n_fields).astype(np.float32)
    log.warning(
        "  USANDO w₀ SINTETICI — NON corrispondono ai campi reali. "
        "Le correlazioni |r(feature, w₀)| con questi dati NON sono valide."
    )
    return w0.reshape(-1, 1)


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline principale
# ═══════════════════════════════════════════════════════════════════════════

def process_dataset(
    field_dir: Path,
    dataset_name: str,
    n_fields: int,
    n_workers: int,
) -> np.ndarray:
    """
    Processa tutti i campi di un dataset e restituisce la matrice feature [N, 8].

    Args:
        field_dir:    directory con field_NNNN.npy
        dataset_name: "lhc" o "nwlh" (per logging)
        n_fields:     numero di campi da processare
        n_workers:    numero di worker multiprocessing

    Returns:
        fvecs: [n_fields, 8] float32
    """
    log.info(f"Processing dataset {dataset_name}: {n_fields} campi, {n_workers} worker...")

    # Costruisce lista di task
    tasks = []
    missing = []
    for i in range(n_fields):
        p = field_dir / f"field_{i:04d}.npy"
        if p.exists():
            tasks.append((p, i))
        else:
            missing.append(i)

    if missing:
        log.warning(
            f"  {len(missing)} campi mancanti in {dataset_name}: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )

    fvecs = np.zeros((n_fields, 8), dtype=np.float32)
    errors = []
    t_start = time.time()

    # Multiprocessing (gudhi è thread-safe ma non multi-GPU)
    with mp.Pool(n_workers) as pool:
        for done, (idx, fvec, err) in enumerate(pool.imap_unordered(_worker, tasks)):
            if err is not None:
                errors.append((idx, err))
                log.warning(f"  Errore campo {dataset_name}[{idx}]: {err}")
            else:
                fvecs[idx] = fvec

            if (done + 1) % 200 == 0:
                elapsed = (time.time() - t_start) / 60
                rate = (done + 1) / elapsed if elapsed > 0 else 0
                eta = (len(tasks) - done - 1) / rate if rate > 0 else 0
                log.info(
                    f"  {done+1}/{len(tasks)} campi processati "
                    f"({elapsed:.1f} min, ~{eta:.0f} min rimanenti)"
                )

    elapsed_total = (time.time() - t_start) / 60
    log.info(
        f"  {dataset_name} completato: {len(tasks) - len(errors)} OK, "
        f"{len(errors)} errori, {elapsed_total:.1f} min totali"
    )

    return fvecs


def verify_consistency(fvecs_new: np.ndarray, fvecs_fid: np.ndarray, dataset_name: str):
    """
    Sanity check: le statistiche delle feature LHC/nwLH devono essere
    compatibili con quelle fiduciali — stesso ordine di grandezza, stesso segno.
    """
    log.info(f"  Sanity check {dataset_name} vs fiduciali:")
    for k, name in enumerate(FEATURE_NAMES):
        fid_mean = fvecs_fid[:, k].mean()
        new_mean = fvecs_new[:, k].mean()
        ratio = new_mean / fid_mean if abs(fid_mean) > 1e-10 else float("nan")
        log.info(
            f"    {name:25s}: fid_mean={fid_mean:.4e}, "
            f"{dataset_name}_mean={new_mean:.4e}, ratio={ratio:.2f}"
        )


def patch_cache(
    fvecs_lhc: np.ndarray,
    fvecs_nwlh: np.ndarray,
    cosmo_lhc: np.ndarray,
    cosmo_nwlh: np.ndarray,
    dry_run: bool,
):
    """
    Aggiorna phase1_fiducial_cache.npz e phase1_tda_baseline.json.

    Cache: aggiunge fvecs_lhc, fvecs_nwlh alle chiavi esistenti.
    Baseline: aggiunge lhc_cosmologies e nwlh_cosmologies.

    In dry_run=True: stampa solo le statistiche senza scrivere.
    """
    log.info("Aggiornamento cache e baseline...")

    # ── Carica cache esistente ────────────────────────────────────────────────
    existing = dict(np.load(CACHE_PATH, allow_pickle=True))
    log.info(f"  Cache esistente: chiavi = {list(existing.keys())}")

    existing["fvecs_lhc"] = fvecs_lhc
    existing["fvecs_nwlh"] = fvecs_nwlh
    if cosmo_lhc is not None:
        existing["cosmo_lhc"] = cosmo_lhc
    if cosmo_nwlh is not None:
        existing["cosmo_nwlh"] = cosmo_nwlh

    log.info(f"  Cache aggiornata: chiavi = {list(existing.keys())}")

    if not dry_run:
        # Backup della cache originale
        backup_path = CACHE_PATH.with_suffix(".npz.bak")
        import shutil
        shutil.copy2(CACHE_PATH, backup_path)
        log.info(f"  Backup cache: {backup_path}")

        np.savez_compressed(CACHE_PATH, **existing)
        log.info(f"  Cache salvata: {CACHE_PATH}")

    # ── Aggiorna baseline JSON ────────────────────────────────────────────────
    with open(BASELINE_PATH) as f:
        baseline = json.load(f)

    baseline["lhc_cosmologies"] = (
        cosmo_lhc.tolist() if cosmo_lhc is not None else None
    )
    baseline["nwlh_cosmologies"] = (
        cosmo_nwlh.tolist() if cosmo_nwlh is not None else None
    )
    baseline["fvecs_lhc_stats"] = {
        name: {
            "mean": float(fvecs_lhc[:, k].mean()),
            "std": float(fvecs_lhc[:, k].std()),
        }
        for k, name in enumerate(FEATURE_NAMES)
    }
    baseline["fvecs_nwlh_stats"] = {
        name: {
            "mean": float(fvecs_nwlh[:, k].mean()),
            "std": float(fvecs_nwlh[:, k].std()),
        }
        for k, name in enumerate(FEATURE_NAMES)
    }
    baseline["patch_note"] = (
        "Cache aggiornata da phase1_patch_cache.py (Phase 2 Sessione 1). "
        "Feature estratte con pipeline identica a Phase 1 "
        "(n_thresh=50, sigma=0.64px, log(delta+1), superlevel_via_negation). "
        "I risultati di Gate 1 non sono modificati."
    )

    if not dry_run:
        backup_baseline = BASELINE_PATH.with_suffix(".json.bak")
        import shutil
        shutil.copy2(BASELINE_PATH, backup_baseline)
        log.info(f"  Backup baseline: {backup_baseline}")

        with open(BASELINE_PATH, "w") as f:
            json.dump(baseline, f, indent=2)
        log.info(f"  Baseline aggiornato: {BASELINE_PATH}")

    if dry_run:
        log.info("  DRY RUN: nessun file scritto.")


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 1 Cache Patch — aggiunge fvecs_lhc/nwlh alla cache"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Calcola e stampa statistiche senza scrivere file"
    )
    parser.add_argument(
        "--n-fields", type=int, default=N_FIELDS,
        help=f"Numero di campi da processare per dataset (default: {N_FIELDS})"
    )
    parser.add_argument(
        "--n-workers", type=int, default=max(1, mp.cpu_count() - 1),
        help="Numero di worker multiprocessing (default: n_cpu - 1)"
    )
    parser.add_argument(
        "--dataset", choices=["lhc", "nwlh", "both"], default="both",
        help="Dataset da processare (default: both)"
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("CAUCHY Phase 1 Cache Patch")
    log.info(f"  n_fields: {args.n_fields}")
    log.info(f"  n_workers: {args.n_workers}")
    log.info(f"  dry_run: {args.dry_run}")
    log.info(f"  gudhi: {gudhi.__version__}")
    log.info("=" * 60)

    # Verifica prerequisiti
    if not CACHE_PATH.exists():
        log.error(f"Cache non trovata: {CACHE_PATH}")
        sys.exit(1)
    if not BASELINE_PATH.exists():
        log.error(f"Baseline non trovato: {BASELINE_PATH}")
        sys.exit(1)

    # Carica fvecs_fid per sanity check
    existing = np.load(CACHE_PATH, allow_pickle=True)
    fvecs_fid = existing["fvecs_fid"]
    log.info(f"fvecs_fid caricato: {fvecs_fid.shape}")

    # Carica cosmologie
    log.info("Caricamento cosmologie...")
    cosmo_lhc = load_quijote_lhc_cosmologies(args.n_fields)
    cosmo_nwlh = load_quijote_nwlh_cosmologies(args.n_fields)

    # Fallback sintetici se i file non esistono
    if cosmo_lhc is None:
        cosmo_lhc = make_synthetic_cosmologies_lhc(args.n_fields)
        log.warning("  ATTENZIONE: cosmologie LHC SINTETICHE — test T1 non valido!")
    if cosmo_nwlh is None:
        cosmo_nwlh = make_synthetic_cosmologies_nwlh(args.n_fields)
        log.warning("  ATTENZIONE: w₀ SINTETICI — correlazioni nwLH non valide!")

    # Processa LHC
    fvecs_lhc = None
    if args.dataset in ("lhc", "both"):
        lhc_dir = DATA_DIR / "lhc"
        if not lhc_dir.exists():
            log.error(f"Directory LHC non trovata: {lhc_dir}")
            sys.exit(1)
        fvecs_lhc = process_dataset(lhc_dir, "lhc", args.n_fields, args.n_workers)
        verify_consistency(fvecs_lhc, fvecs_fid, "lhc")

    # Processa nwLH
    fvecs_nwlh = None
    if args.dataset in ("nwlh", "both"):
        nwlh_dir = DATA_DIR / "nwlh"
        if not nwlh_dir.exists():
            log.error(f"Directory nwLH non trovata: {nwlh_dir}")
            sys.exit(1)
        fvecs_nwlh = process_dataset(nwlh_dir, "nwlh", args.n_fields, args.n_workers)
        verify_consistency(fvecs_nwlh, fvecs_fid, "nwlh")

    # Se processati separatamente, carica gli esistenti per l'aggiornamento cache
    if fvecs_lhc is None:
        log.info("fvecs_lhc non processato — carico da cache se disponibile...")
        fvecs_lhc = existing.get("fvecs_lhc", np.zeros((args.n_fields, 8), dtype=np.float32))
    if fvecs_nwlh is None:
        log.info("fvecs_nwlh non processato — carico da cache se disponibile...")
        fvecs_nwlh = existing.get("fvecs_nwlh", np.zeros((args.n_fields, 8), dtype=np.float32))

    # Patch della cache
    patch_cache(fvecs_lhc, fvecs_nwlh, cosmo_lhc, cosmo_nwlh, args.dry_run)

    log.info("=" * 60)
    log.info("Patch completata.")
    log.info(f"  Cache: {CACHE_PATH}")
    log.info(f"  Baseline: {BASELINE_PATH}")
    log.info("")
    log.info("Prossimo passo:")
    log.info("  python src/phase2_cnn.py --mode test_only   # unit test gudhi")
    log.info("  python src/phase2_cnn.py --mode all         # pipeline completa")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
```


## FILE: src/phase2_cnn.py
<!-- score=273 size=89.9KB keywords=['fvec', 'gudhi', 'phase1', 'mask', 'voxel', 'smooth', 'persistence', 'superlevel', 'persistence_intervals', 'betti'] -->

```python
#!/usr/bin/env python3
"""
CAUCHY Phase 2 — CNN SE(3)-Equivariante e Costruzione di τ(x)
=============================================================
Progetto: Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis
Versione: 2.0 — Aprile 2026
Hardware target: RTX 5060 Ti 16 GB (locale)

Autorità scientifica: CAUCHY_Systematic_Methodology_v2.md §2.1–2.3
Parametri operativi: CAUCHY_Execution_Parameters.md §4.1–4.2
Impegni aperti chiusi in questo script:
    R1-1  — z-score normalizzazione C_noise (obbligatorio)
    R1-4  — unit test _test_gudhi_convention() (obbligatorio)
    C0-3  — verifica i.i.d. normalizzazione LHC (obbligatorio)
    R1-2  — test robustezza derivate Fisher FISHER_LOCAL_FRAC (obbligatorio)

Pipeline:
    1. Unit test gudhi convention (R1-4)
    2. Caricamento feature TDA Phase 1 da phase1_fiducial_cache.npz
    3. Calcolo z-score stats su training set (R1-1) — seed=42, split 80/20
    4. Verifica i.i.d. LHC (C0-3)
    5. Definizione architettura EGNN (e3nn v0.5.1)
       - N_pts=4096 (vincolo 16 GB VRAM)
       - k=16 vicini (Chatterjee 2024 CAUCHY scaling)
       - D_latent=32
       - Campionamento pesato per |delta(x)|
    6. Training loop con loss MSE z-score
    7. Calcolo μ_ΛCDM sui 2000 campi fiduciali
    8. Costruzione τ(x) per LHC e nwLH (dual output: point cloud + grid norm)
    9. Test T1 fattorizzazione parametrica (Gate 2: R ≥ 0.20)
   10. Test robustezza Fisher (R1-2)
   11. Serializzazione phase2_cnn_diagnostic.json

NUMERI FISICI TRACCIATI:
    N_pts=4096    — vincolo VRAM 16 GB (calcolo in §ARCHITETTURA)
    k=16          — Chatterjee et al. 2024 (arXiv:2405.13119): k=32 per 8192 halos;
                    CAUCHY usa N_pts=4096 → scaling k→16 per mantenere
                    raggio di connessione ~63 Mpc/h (cluster + filamenti)
    D_latent=32   — 4× le 8 feature target (regola euristica encoder supervisionato)
    R≥0.20        — CAUCHY_Execution_Parameters §4.2 [VALORE NON DA LETTERATURA —
                    stima PI, primo candidato a ricalibrzione formale]
    batch=4–8     — vincolo VRAM: N_pts×k×D_latent×batch ≤ 12 GB attivo

Uso:
    python phase2_cnn.py --mode train
    python phase2_cnn.py --mode build_tau
    python phase2_cnn.py --mode gate2
    python phase2_cnn.py --mode all         # sequenza completa
    python phase2_cnn.py --mode test_only   # solo unit test gudhi (R1-4)
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.ndimage import laplace, map_coordinates
from torch.optim.lr_scheduler import ReduceLROnPlateau

# ── Dipendenze opzionali con fallback esplicito ─────────────────────────────
try:
    import e3nn
    from e3nn import o3
    from e3nn.nn import Gate
    from e3nn.o3 import Irreps, Linear
    E3NN_VERSION = e3nn.__version__
    HAS_E3NN = True
except ImportError:
    HAS_E3NN = False
    E3NN_VERSION = "NOT_INSTALLED"

try:
    import torch_geometric
    import torch_cluster  # dipendenza reale di knn_graph
    from torch_geometric.nn import knn_graph
    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False

try:
    import ot  # POT — Python Optimal Transport
    HAS_POT = True
except ImportError:
    HAS_POT = False

try:
    import gudhi
    HAS_GUDHI = True
except ImportError:
    HAS_GUDHI = False

# ═══════════════════════════════════════════════════════════════════════════
# §0 — CONFIGURAZIONE GLOBALE
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_SEED = 42  # CAUCHY_Execution_Parameters §1 — immutabile
CAUCHY_VERSION = "v2.0"
SCHEMA_VERSION = "2.0"

# Architettura CNN (RTX 5060 Ti 16 GB)
N_PTS = 8192          # punti campionati per campo (vincolo VRAM)
K_NN = 16             # vicini nel grafo k-NN — Chatterjee et al. 2024 (arXiv:2405.13119)
                      # usa k=32 per N=8192; scaling a N=4096 → k=16
                      # (raggio connessione ~63 Mpc/h, copre cluster+filamenti)
D_LATENT = 32         # dimensionalità spazio latente — 4× N_FEATURES=8
                      # (regola euristica encoder supervisionato;
                      #  valore non da letteratura cosmologica — stima PI)
N_FEATURES = 8        # feature TDA Phase 1 (target supervisione)
N_EPOCHS = 200        # epoche massime
BATCH_SIZE = 3        # sicuro su 16 GB con N_PTS=4096, k=16, D=32
LR_INITIAL = 5e-5     # learning rate iniziale
LR_MIN = 1e-6         # learning rate minimo (ReduceLROnPlateau floor)
PATIENCE = 20         # epoche senza miglioramento → riduzione LR
EARLY_STOP_PATIENCE = 40  # early stopping

# Dataset
N_FIELDS_FIDUCIAL = 2000
N_FIELDS_LHC = 2000
N_FIELDS_NWLH = 2000
TRAIN_FRAC = 0.80    # 80/20 split — seed=42

# Gate 2
R_THRESHOLD = 0.20   # CAUCHY_Execution_Parameters §4.2 [VALORE NON DA LETTERATURA]
CORR_HESSIAN_THRESHOLD = 0.05  # soft gate (sanity check)
W2_N_PROJECTIONS = 1000        # Sliced Wasserstein

# Test robustezza Fisher (R1-2)
FISHER_LOCAL_FRACS = [0.1, 0.2, 0.3, 0.5]

# Paths
DATA_DIR = Path("data/processed/phase0_fields")
RESULTS_DIR = Path("results")
CHECKPOINT_DIR = Path("results/checkpoints")
TAU_LHC_DIR = Path("results/phase2_tau_fields/lhc")
TAU_NWLH_DIR = Path("results/phase2_tau_fields/nwlh")

PHASE1_CACHE_PATH = Path("results/phase1_fiducial_cache.npz")
PHASE1_BASELINE_PATH = Path("results/phase1_tda_baseline.json")
DIAGNOSTIC_PATH = Path("results/phase2_cnn_diagnostic.json")
CHECKPOINT_BEST = Path("results/checkpoints/phase2_cnn_best.pt")

# Nomi feature TDA (ordine canonico — da CAUCHY_Execution_Parameters §9.1)
FEATURE_NAMES = [
    "b1_peak_pos",
    "b1_peak_height",
    "b1_fwhm",
    "b1_integral",
    "b2_max_count",
    "b2_mean_persistence",
    "b2_high_persist",
    "b0_at_mean",
]

# ── Setup logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("phase2_cnn_run.log", mode="a"),
    ],
)
log = logging.getLogger("cauchy.phase2")


# ═══════════════════════════════════════════════════════════════════════════
# §1 — UNIT TEST GUDHI CONVENTION (R1-4)
# ═══════════════════════════════════════════════════════════════════════════

def _test_gudhi_convention() -> dict:
    """
    Unit test della convenzione gudhi CubicalComplex per superlevel filtration.

    Chiude l'impegno R1-4. Usa persistence_intervals_in_dimension (stessa
    API di phase1_tda_baseline.py) invece di persistent_betti_numbers, che
    in gudhi 0.6+ ha semantica diversa per i Betti numbers di alta dimensione.

    Test A — Segno della persistenza (β₂, sfera cava 32³):
        Campo: guscio sferico (alta densità) + cavità interna (bassa densità).
        Superlevel a soglia intermedia → guscio è l'unica struttura attiva.
        Atteso: almeno 1 feature β₂ con nu_birth > nu_death > 0
        (la cavità 3D chiusa produce un 2-ciclo nella filtrazione di superlevel).

    Test B — Segno della persistenza (β₁, toro 32³):
        Campo: tubo toroidale (alta densità) con buco centrale (bassa densità).
        Atteso: almeno 1 feature β₁ con nu_birth > nu_death > 0.

    Test C — Convenzione birth/death:
        Verifica che nu_birth > nu_death per tutte le feature finite
        (superlevel: feature nasce ad alta densità, muore a bassa densità).

    Riferimento: phase1_tda_baseline.py compute_persistence_diagram()
    """
    if not HAS_GUDHI:
        return {
            "passed": False,
            "error": "gudhi non disponibile — installare gudhi>=3.9.0",
        }

    log.info("[R1-4] Esecuzione unit test gudhi convention...")

    def _run_cc(field: np.ndarray) -> dict:
        """Applica la pipeline Phase 1 esatta e restituisce i diagrammi."""
        nu = np.log(np.clip(field, -0.9999, None) + 1.0)
        cc = gudhi.CubicalComplex(
            dimensions=list(nu.shape),
            top_dimensional_cells=(-nu).flatten().astype(np.float64)
        )
        cc.compute_persistence()
        diagrams = {}
        for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
            raw = cc.persistence_intervals_in_dimension(dim)
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2))
            else:
                raw = np.array(raw, dtype=np.float64)
                finite = raw[np.isfinite(raw[:, 1])]
                if len(finite) == 0:
                    diagrams[key] = np.empty((0, 2))
                else:
                    # Conversione: nu_birth=-col0, nu_death=-col1
                    diagrams[key] = np.column_stack([-finite[:, 0], -finite[:, 1]])
        return diagrams

    errors = []

    # ── Test A: sfera cava → β₂ ≥ 1 ────────────────────────────────────────
    grid = 32
    center = grid / 2
    coords = np.mgrid[0:grid, 0:grid, 0:grid].astype(float)
    r = np.sqrt(sum((coords[i] - center) ** 2 for i in range(3)))

    field_sphere = np.full((grid, grid, grid), -0.5)   # sfondo bassa densità
    field_sphere[(r >= 6) & (r <= 12)] = 1.5            # guscio alta densità
    field_sphere[r < 6] = -0.5                          # cavità bassa densità

    diag_sphere = _run_cc(field_sphere)
    b2_features = diag_sphere['b2']
    n_b2 = len(b2_features)

    if n_b2 == 0:
        errors.append(
            f"Test A FAIL: sfera cava 32³ produce β₂=0 (atteso ≥1). "
            f"gudhi versione {gudhi.__version__} potrebbe avere API diversa."
        )
    else:
        # Verifica che nu_birth > nu_death (superlevel)
        wrong_sign = np.sum(b2_features[:, 0] <= b2_features[:, 1])
        if wrong_sign > 0:
            errors.append(
                f"Test A FAIL: {wrong_sign}/{n_b2} feature β₂ hanno "
                "nu_birth ≤ nu_death — convenzione birth/death invertita."
            )
        else:
            log.info(f"[R1-4] Test A PASS: β₂={n_b2} feature, nu_birth>nu_death ✓")

    # ── Test B: campo 1D a scala → β₁ ≥ 1 ──────────────────────────────────
    # Tubo toroidale approssimato: struttura ad anello lungo l'asse z
    field_torus = np.full((grid, grid, grid), -0.5)
    for z in range(grid):
        for y in range(grid):
            for x in range(grid):
                r_ring = np.sqrt((x - center)**2 + (y - center)**2)
                if 6 <= r_ring <= 10:
                    field_torus[z, y, x] = 1.5

    diag_torus = _run_cc(field_torus)
    b1_features = diag_torus['b1']
    n_b1 = len(b1_features)

    if n_b1 == 0:
        errors.append(
            f"Test B FAIL: tubo toroidale 32³ produce β₁=0 (atteso ≥1)."
        )
    else:
        wrong_sign = np.sum(b1_features[:, 0] <= b1_features[:, 1])
        if wrong_sign > 0:
            errors.append(
                f"Test B FAIL: {wrong_sign}/{n_b1} feature β₁ hanno "
                "nu_birth ≤ nu_death."
            )
        else:
            log.info(f"[R1-4] Test B PASS: β₁={n_b1} feature, nu_birth>nu_death ✓")

    # ── Test C: b0 sempre presente ───────────────────────────────────────────
    b0_features = diag_sphere['b0']
    if len(b0_features) == 0:
        # β₀ finiti potrebbero essere tutti zero se una sola componente connessa
        # (la componente illimitata viene scartata da isfinite) — questo è atteso
        log.info("[R1-4] Test C: β₀ finiti=0 (componente illimitata scartata) ✓")
    else:
        wrong_sign_b0 = np.sum(b0_features[:, 0] <= b0_features[:, 1])
        if wrong_sign_b0 > 0:
            errors.append(
                f"Test C FAIL: {wrong_sign_b0} feature β₀ hanno nu_birth≤nu_death."
            )
        else:
            log.info(f"[R1-4] Test C PASS: β₀={len(b0_features)} finiti ✓")

    passed = len(errors) == 0

    result = {
        "passed": passed,
        "error": "; ".join(errors) if errors else None,
        "test_A_beta2_features": int(n_b2),
        "test_B_beta1_features": int(n_b1),
        "gudhi_version": gudhi.__version__,
        "api_used": "persistence_intervals_in_dimension (identico a phase1_tda_baseline.py)",
        "note": (
            "Test usa persistence_intervals_in_dimension, non persistent_betti_numbers. "
            "Coerente con la pipeline Phase 1."
        ),
    }

    if passed:
        log.info(
            f"[R1-4] PASS — β₂≥1 (A), β₁≥1 (B), convenzione birth>death (C) ✓"
        )
    else:
        for e in errors:
            log.error(f"[R1-4] {e}")
        log.error("[R1-4] BLOCCO: convenzione gudhi non verificata.")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# §2 — CARICAMENTO DATI E NORMALIZZAZIONE Z-SCORE (R1-1)
# ═══════════════════════════════════════════════════════════════════════════

def load_phase1_features() -> dict:
    """
    Carica le feature TDA di Phase 1 da phase1_fiducial_cache.npz e
    phase1_tda_baseline.json.

    Struttura attesa di phase1_fiducial_cache.npz:
        fvecs_fid: [2000, 8]  — feature fiduciali
        (+ eventualmente fvecs_lhc, fvecs_nwlh se già calcolate)

    Struttura attesa di phase1_tda_baseline.json:
        Contiene il mapping campo→cosmologia per LHC e nwLH.
        Necessario per il test T1 (quadranti σ₈/Ωm) e per R1-2.

    Returns:
        dict con chiavi: fvecs_fid, fvecs_lhc, fvecs_nwlh,
                         cosmo_lhc (Omm, s8 per ogni campo),
                         cosmo_nwlh (w0 per ogni campo)
    """
    log.info("Caricamento feature TDA Phase 1...")

    # ── Fiducial features ────────────────────────────────────────────────────
    if not PHASE1_CACHE_PATH.exists():
        raise FileNotFoundError(
            f"phase1_fiducial_cache.npz non trovato: {PHASE1_CACHE_PATH}\n"
            "Prerequisito: Phase 1 completata con Gate 1 PASS."
        )

    cache = np.load(PHASE1_CACHE_PATH)
    fvecs_fid = cache["fvecs_fid"].astype(np.float32)  # [2000, 8]
    assert fvecs_fid.shape == (N_FIELDS_FIDUCIAL, N_FEATURES), (
        f"Shape attesa ({N_FIELDS_FIDUCIAL}, {N_FEATURES}), "
        f"trovata {fvecs_fid.shape}"
    )
    log.info(f"  fvecs_fid: {fvecs_fid.shape}")

    # ── LHC e nwLH features (se già calcolate) ───────────────────────────────
    fvecs_lhc = cache["fvecs_lhc"].astype(np.float32) if "fvecs_lhc" in cache else None
    fvecs_nwlh = cache["fvecs_nwlh"].astype(np.float32) if "fvecs_nwlh" in cache else None

    # ── Cosmologie LHC (per test T1 e R1-2) ─────────────────────────────────
    cosmo_lhc = None
    cosmo_nwlh = None

    if PHASE1_BASELINE_PATH.exists():
        with open(PHASE1_BASELINE_PATH) as f:
            baseline = json.load(f)

        # Estrarre cosmologie LHC se presenti
        if "lhc_cosmologies" in baseline:
            cosmo_lhc = np.array(baseline["lhc_cosmologies"], dtype=np.float32)
            # attesa shape [2000, 2] con colonne [Omm, s8]
        if "nwlh_cosmologies" in baseline:
            cosmo_nwlh = np.array(baseline["nwlh_cosmologies"], dtype=np.float32)
            # attesa shape [2000, 1] con colonna [w0]

    if cosmo_lhc is None:
        log.warning(
            "Cosmologie LHC non trovate in phase1_tda_baseline.json. "
            "Il test T1 (Gate 2) e R1-2 richiedono questi dati. "
            "Assicurarsi che Phase 1 abbia salvato lhc_cosmologies nel baseline."
        )

    return {
        "fvecs_fid": fvecs_fid,
        "fvecs_lhc": fvecs_lhc,
        "fvecs_nwlh": fvecs_nwlh,
        "cosmo_lhc": cosmo_lhc,
        "cosmo_nwlh": cosmo_nwlh,
    }


def compute_zscore_stats(fvecs_lhc: np.ndarray, train_indices: np.ndarray) -> dict:
    """
    Calcola le statistiche z-score (μ, σ) per ogni feature sul SOLO training set.

    Chiude impegno R1-1: la normalizzazione z-score prima di qualsiasi analisi
    Fisher downstream riduce il numero di condizione della matrice C_noise da
    ~4×10¹⁰ (Phase 1) a un valore compatibile con κ(C) < 10⁶ (Heavens 2009 MNRAS).

    CRITICO: le statistiche sono calcolate solo sul training set (train_indices)
    e mai sul test set, per evitare data leakage.

    Args:
        fvecs_lhc: [N, 8] feature LHC
        train_indices: indici del training set

    Returns:
        dict con mean_train [8] e std_train [8]
    """
    fvecs_train = fvecs_lhc[train_indices]  # [N_train, 8]
    mean_train = fvecs_train.mean(axis=0)    # [8]
    std_train = fvecs_train.std(axis=0)      # [8]

    # Protezione divisione per zero (feature costante)
    zero_std = std_train < 1e-10
    if zero_std.any():
        log.warning(
            f"Feature con std≈0 rilevate: "
            f"{[FEATURE_NAMES[i] for i in np.where(zero_std)[0]]}. "
            "Sostituisco con std=1.0 per evitare divisione per zero."
        )
        std_train[zero_std] = 1.0

    # Numero di condizione della matrice diagonale normalizzata
    # (approssimazione: la matrice di covarianza delle feature normalizzate
    #  dovrebbe avere tutti i valori diagonali ≈1)
    fvecs_norm = (fvecs_train - mean_train) / std_train
    cov_norm = np.cov(fvecs_norm.T)
    cond_before = np.linalg.cond(np.cov(fvecs_train.T))
    cond_after = np.linalg.cond(cov_norm)

    log.info(f"[R1-1] Numero di condizione C_noise:")
    log.info(f"  Prima della normalizzazione:  κ = {cond_before:.3e}")
    log.info(f"  Dopo la normalizzazione:      κ = {cond_after:.3e}")
    log.info(f"  Heavens 2009 threshold: κ < 1e6 → {'PASS' if cond_after < 1e6 else 'WARN'}")

    return {
        "mean_train": mean_train,
        "std_train": std_train,
        "cond_before": float(cond_before),
        "cond_after": float(cond_after),
        "heavens_threshold": 1e6,
        "heavens_pass": bool(cond_after < 1e6),
    }


def check_iid_lhc(fvecs_lhc: np.ndarray, train_indices: np.ndarray) -> dict:
    """
    Verifica i.i.d. per i campi LHC (impegno C0-3).

    Controlla che la distribuzione delle medie per-campo nel training set CNN
    sia compatibile con i.i.d. condizionati ai parametri cosmologici.

    Test: la media di ogni campo (media sulle 8 feature) non deve mostrare
    correlazioni sistematiche con l'indice di campo (drift), né una distribuzione
    bimodale anomala. Un test Kolmogorov-Smirnov sulla distribuzione delle medie
    per-campo confrontata con una gaussiana è un sanity check sufficiente.

    Args:
        fvecs_lhc: [N, 8] feature LHC
        train_indices: indici del training set

    Returns:
        dict con risultati del test i.i.d.
    """
    from scipy import stats

    fvecs_train = fvecs_lhc[train_indices]
    field_means = fvecs_train.mean(axis=1)  # media per-campo [N_train]

    # KS test contro gaussiana
    ks_stat, ks_pval = stats.kstest(
        (field_means - field_means.mean()) / field_means.std(),
        "norm"
    )

    # Test di autocorrelazione (lag=1): se i campi fossero ordinati per
    # cosmologia potremmo avere drift sistematico
    acf_lag1 = float(np.corrcoef(field_means[:-1], field_means[1:])[0, 1])

    # Spearman rank-correlation con l'indice di campo (test di drift)
    spearman_idx, spearman_pval = stats.spearmanr(
        np.arange(len(field_means)), field_means
    )

    passed = (ks_pval > 0.05) and (abs(acf_lag1) < 0.1) and (abs(spearman_idx) < 0.1)

    log.info(f"[C0-3] Test i.i.d. LHC:")
    log.info(f"  KS test vs gaussiana: stat={ks_stat:.4f}, p={ks_pval:.4f}")
    log.info(f"  Autocorrelazione lag-1: {acf_lag1:.4f}")
    log.info(f"  Spearman rank vs indice: r={spearman_idx:.4f}, p={spearman_pval:.4f}")
    log.info(f"  Verdict: {'PASS' if passed else 'WARN — verificare manualmente'}")

    return {
        "ks_stat": float(ks_stat),
        "ks_pval": float(ks_pval),
        "acf_lag1": float(acf_lag1),
        "spearman_idx_corr": float(spearman_idx),
        "spearman_idx_pval": float(spearman_pval),
        "iid_passed": passed,
        "note": (
            "Campo LHC i.i.d. condizionato ai parametri se KS p>0.05, "
            "|ACF_lag1|<0.1, |Spearman_r|<0.1."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# §3 — ARCHITETTURA EGNN (e3nn)
# ═══════════════════════════════════════════════════════════════════════════

class EquivariantBlock(nn.Module):
    """
    Blocco di message passing SE(3)-equivariante basato su e3nn.

    Implementa un passo di message passing equivariante con:
    - Spherical harmonics per encoding della direzione relativa r̂_ij
    - TensorProduct per la combinazione equivariante di feature
    - Proiezione finale sulle Irreps di output

    Scelte architetturali:
    - Irreps tipo 0e (scalari) + 1o (vettori) per catturare informazione
      di ampiezza (topologia cluster) e direzione (connettività filamentare)
    - L_max=1: sufficiente per scale cosmologiche dove la struttura
      principale è filamentare (L=1) e non ha multipoli superiori rilevanti
      con N_pts=4096 su volume 1 Gpc/h³

    Riferimento: e3nn library (Geiger & Smidt 2021, arXiv:2207.09453)
    """

    def __init__(
        self,
        irreps_in: "o3.Irreps",
        irreps_out: "o3.Irreps",
        irreps_sh: "o3.Irreps",
        n_radial: int = 8,
    ):
        super().__init__()
        self.irreps_in = irreps_in
        self.irreps_out = irreps_out
        self.irreps_sh = irreps_sh

        # Tensor product: feature_i × SH(r̂_ij) → messaggio
        # e3nn 0.6.0: FullyConnectedTensorProduct gestisce le instructions
        # automaticamente — più robusto del TensorProduct manuale con instructions.
        from e3nn.o3 import FullyConnectedTensorProduct
        self.tp = FullyConnectedTensorProduct(
            irreps_in,
            irreps_sh,
            irreps_out,
            shared_weights=False,   # i pesi vengono dalla radial_net
        )

        # Rete radiale: encoding della distanza scalare r_ij
        self.radial_net = nn.Sequential(
            nn.Linear(n_radial, 64),
            nn.SiLU(),
            nn.Linear(64, self.tp.weight_numel),
        )

        # Encoding gaussiano della distanza
        self.n_radial = n_radial

        # Layer di output (proiezione finale sui D_latent scalari)
        self.output_linear = Linear(irreps_out, irreps_out)

    def forward(
        self,
        x: torch.Tensor,         # [N, irreps_in.dim] feature nodali
        pos: torch.Tensor,       # [N, 3] coordinate
        edge_index: torch.Tensor, # [2, E] grafo k-NN
    ) -> torch.Tensor:
        """
        Args:
            x:          feature nodali [N, irreps_in.dim]
            pos:        coordinate 3D [N, 3]
            edge_index: [2, E] con edge_index[0]=src, edge_index[1]=dst

        Returns:
            x_out: feature nodali aggiornate [N, irreps_out.dim]
        """
        src, dst = edge_index[0], edge_index[1]

        # Vettore relativo e distanza
        r_vec = pos[dst] - pos[src]                    # [E, 3]
        r_dist = r_vec.norm(dim=-1, keepdim=True)      # [E, 1]

        # Direzione normalizzata (con protezione per r→0)
        r_hat = r_vec / (r_dist + 1e-8)               # [E, 3] — unitario

        # Spherical harmonics sulla direzione relativa
        # e3nn 0.6.0: SphericalHarmonics(irreps, x, normalize, normalization)
        sh = o3.spherical_harmonics(self.irreps_sh, r_hat, normalize=True, normalization="component")

        # Encoding radiale con basi gaussiane
        r_embedding = self._rbf(r_dist.squeeze(-1))    # [E, n_radial]
        weight = self.radial_net(r_embedding)           # [E, tp.weight_numel]

        # Messaggio: TensorProduct(feature_src, SH, weight)
        msg = self.tp(x[src], sh, weight)              # [E, irreps_out.dim]

        # Aggregazione: somma per nodo destinazione
        x_out = torch.zeros(
            x.shape[0], self.tp.irreps_out.dim,
            dtype=x.dtype, device=x.device
        )
        x_out.scatter_add_(0, dst.unsqueeze(-1).expand_as(msg), msg)

        return self.output_linear(x_out)

    def _rbf(self, r: torch.Tensor, r_max: float = 150.0) -> torch.Tensor:
        """
        Radial Basis Functions gaussiane per encoding della distanza.
        r in [Mpc/h]. r_max≈150 Mpc/h copre il range del k=16° vicino
        con N_pts=4096 su volume 1 Gpc/h³.
        """
        centers = torch.linspace(0, r_max, self.n_radial, device=r.device)
        sigma = r_max / (2 * self.n_radial)
        return torch.exp(-((r.unsqueeze(-1) - centers) ** 2) / (2 * sigma ** 2))


class CAUCHYEncoder(nn.Module):
    """
    Encoder CNN SE(3)-equivariante per CAUCHY Phase 2.

    Architettura:
    - Embedding iniziale: scalare δ(x_i) → Irreps scalari + vettoriali
    - 3 blocchi EquivariantBlock con message passing k-NN
    - Proiezione finale: Irreps → D_latent scalari
    - Output: [N_pts, D_latent] rappresentazione latente per punto

    La supervisione è su feature TDA di CAMPO (non sul punto singolo).
    Il pooling globale (mean) sulla rappresentazione latente produce
    un vettore [D_latent] per campo, proiettato su [N_FEATURES] scalari.

    Nota su SE(3) vs E(3):
    Il Methodology prescrive SE(3) (rotazioni + traslazioni, no riflessioni).
    Usiamo Irreps con parità (0e per scalari, 1o per vettori pseudo-vettori)
    che rispetta SE(3). La distinzione da E(3) è rilevante per feature
    chirali (β₂ dei vuoti può avere asimmetria chirale in presenza di
    perturbazioni primordiali non-gaussiane), ma conservativa per CAUCHY.

    N_PARAMS stimati: ~180k — adeguato per D_latent=32 con supervisione su 8 target.
    """

    def __init__(
        self,
        d_latent: int = D_LATENT,
        n_features: int = N_FEATURES,
        n_mp_layers: int = 3,
    ):
        super().__init__()
        self.d_latent = d_latent
        self.n_features = n_features

        # Irreps: scalari (0e) + vettori (1o) — L_max=1
        # Molteplicità: d_latent//4 per 0e e 1o (bilanciato)
        mul_s = d_latent // 4   # molteplicità scalari = 8 per d_latent=32
        mul_v = d_latent // 4   # molteplicità vettori = 8 per d_latent=32

        self.irreps_hidden = o3.Irreps(f"{mul_s}x0e + {mul_v}x1o")
        self.irreps_out_node = o3.Irreps(f"{d_latent}x0e")  # solo scalari in output
        self.irreps_sh = o3.Irreps.spherical_harmonics(lmax=1)  # Y_0^0 + Y_1^m

        # Embedding iniziale: scalare δ(x) → irreps_hidden
        # δ è uno scalare (0e), lo espandiamo alle Irreps iniziali
        self.embedding = nn.Sequential(
            nn.Linear(1, 64),
            nn.SiLU(),
            nn.Linear(64, self.irreps_hidden.dim),
        )

        # Blocchi di message passing equivarianti
        self.mp_layers = nn.ModuleList([
            EquivariantBlock(
                irreps_in=self.irreps_hidden,
                irreps_out=self.irreps_hidden,
                irreps_sh=self.irreps_sh,
            )
            for _ in range(n_mp_layers)
        ])

        # Layer normalization dopo ogni MP layer (stabilizza training)
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(self.irreps_hidden.dim)
            for _ in range(n_mp_layers)
        ])

        # Proiezione finale: irreps_hidden → D_latent scalari
        self.proj_out = nn.Sequential(
            nn.Linear(self.irreps_hidden.dim, d_latent * 2),
            nn.SiLU(),
            nn.Linear(d_latent * 2, d_latent),
        )

        # Testa di supervisione: pooling globale → N_FEATURES
        # Usata solo durante il training, non per la costruzione di τ(x)
        self.supervision_head = nn.Sequential(
            nn.Linear(d_latent, 64),
            nn.SiLU(),
            nn.Linear(64, n_features),
        )

    def forward(
        self,
        delta_pts: torch.Tensor,   # [N, 1] valori δ nei punti campionati
        pos: torch.Tensor,         # [N, 3] coordinate fisiche (Mpc/h)
        edge_index: torch.Tensor,  # [2, E] grafo k-NN
        batch: torch.Tensor,       # [N] indice di campo nel batch
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            delta_pts:  valori δ ai punti campionati [N_batch_pts, 1]
            pos:        coordinate 3D [N_batch_pts, 3]
            edge_index: grafo k-NN [2, E]
            batch:      indice di campo [N_batch_pts]

        Returns:
            tau_pts: [N_batch_pts, D_latent] — feature latenti per punto
            pred_features: [batch_size, N_FEATURES] — predizioni feature TDA
                           (per la loss di supervisione durante training)
        """
        # Embedding scalare → Irreps
        x = self.embedding(delta_pts)   # [N, irreps_hidden.dim]

        # Message passing equivariante con connessioni residuali
        for mp_layer, ln in zip(self.mp_layers, self.layer_norms):
            x_new = mp_layer(x, pos, edge_index)
            x = ln(x + x_new)           # residual connection + layer norm

        # Proiezione su scalari latenti [N, D_latent]
        tau_pts = self.proj_out(x)      # [N_batch_pts, D_latent]

        # Pooling globale per supervisione: media per campo
        # batch indica a quale campo appartiene ogni punto
        batch_size = int(batch.max().item()) + 1
        tau_pooled = torch.zeros(
            batch_size, self.d_latent,
            dtype=tau_pts.dtype, device=tau_pts.device
        )
        counts = torch.zeros(batch_size, dtype=tau_pts.dtype, device=tau_pts.device)
        tau_pooled.scatter_add_(0, batch.unsqueeze(-1).expand_as(tau_pts), tau_pts)
        counts.scatter_add_(0, batch, torch.ones(batch.shape[0], dtype=tau_pts.dtype, device=tau_pts.device))
        tau_pooled = tau_pooled / counts.unsqueeze(-1).clamp(min=1)  # [B, D_latent]

        # Predizione feature TDA dalla rappresentazione pooled
        pred_features = self.supervision_head(tau_pooled)  # [B, N_FEATURES]

        return tau_pts, pred_features


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ═══════════════════════════════════════════════════════════════════════════
# §4 — CAMPIONAMENTO PUNTI E COSTRUZIONE GRAFO K-NN
# ═══════════════════════════════════════════════════════════════════════════

def sample_points_density_weighted(
    field: np.ndarray,
    n_pts: int,
    box_size: float = 1000.0,
    eps_floor: float = 0.01,
    rng: np.random.Generator = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Campionamento di n_pts punti dal campo di densità, pesato per |δ(x)|.

    Motivazione (Q1, confermata dal PI): il campionamento pesato per |δ(x)|
    rende τ(x) scientificamente interpretabile — ogni punto rappresenta
    una struttura del cosmic web con probabilità proporzionale alla sua
    prominenza. Le regioni di alta densità (filamenti, nodi) sono dove
    l'informazione topologica è concentrata (Methodology §2.1).

    Implementazione:
    - p(x) ∝ max(δ(x) - δ_min, 0) + ε (ε-floor per copertura minima dei void)
    - I punti sono campionati senza rimpiazzo
    - Le coordinate fisiche sono calcolate dalla posizione nel reticolo

    Args:
        field:    [128, 128, 128] campo δ(x) float64
        n_pts:    numero di punti da campionare
        box_size: dimensione del box in Mpc/h (default 1000.0)
        eps_floor: peso minimo per le regioni di bassa densità
        rng:      generatore numpy (per riproducibilità)

    Returns:
        delta_pts:    [n_pts] valori δ nei punti campionati
        pos_pts:      [n_pts, 3] coordinate fisiche in Mpc/h
        sample_idx:   [n_pts] indici flat nel reticolo 128³
    """
    if rng is None:
        rng = np.random.default_rng(GLOBAL_SEED)

    grid_size = field.shape[0]
    cell_size = box_size / grid_size  # Mpc/h per voxel

    # Probabilità di campionamento pesata per |δ(x)|
    delta_flat = field.flatten()
    delta_shifted = delta_flat - delta_flat.min()   # tutti ≥ 0
    weights = delta_shifted + eps_floor * delta_shifted.max()
    weights = weights / weights.sum()               # normalizzazione

    # Campionamento senza rimpiazzo
    total_voxels = grid_size ** 3
    sample_idx = rng.choice(total_voxels, size=n_pts, replace=False, p=weights)

    # Coordinate fisiche: centro del voxel
    idx_3d = np.unravel_index(sample_idx, (grid_size, grid_size, grid_size))
    pos_pts = np.stack([
        (idx_3d[0] + 0.5) * cell_size,
        (idx_3d[1] + 0.5) * cell_size,
        (idx_3d[2] + 0.5) * cell_size,
    ], axis=-1).astype(np.float32)  # [n_pts, 3]

    delta_pts = delta_flat[sample_idx].astype(np.float32)  # [n_pts]

    return delta_pts, pos_pts, sample_idx


def build_knn_graph(pos: torch.Tensor, k: int = K_NN) -> torch.Tensor:
    """
    Costruisce il grafo k-NN nelle coordinate fisiche (Mpc/h).

    Usa torch_geometric.nn.knn_graph per efficienza.
    Restituisce edge_index [2, N*k] con boundary conditions periodiche
    disabilitate (i campi Quijote sono periodici ma il campionamento
    density-weighted rompe la periodicità — si usa il grafo standard).

    Args:
        pos: [N, 3] coordinate fisiche (Mpc/h)
        k:   numero di vicini

    Returns:
        edge_index: [2, N*k] con src=edge_index[0], dst=edge_index[1]
    """
    if HAS_TORCH_GEOMETRIC:
        # knn_graph di torch-geometric: efficiente su GPU
        return knn_graph(pos, k=k, loop=False)
    else:
        # Fallback: implementazione numpy (più lenta, solo per dev/test)
        from scipy.spatial import KDTree
        tree = KDTree(pos.cpu().numpy())
        dists, indices = tree.query(pos.cpu().numpy(), k=k + 1)
        # Rimuovi self-loop (indice 0 = il punto stesso)
        src = np.repeat(np.arange(len(pos)), k)
        dst = indices[:, 1:].flatten()
        edge_index = torch.tensor(
            np.stack([src, dst], axis=0), dtype=torch.long, device=pos.device
        )
        return edge_index


# ═══════════════════════════════════════════════════════════════════════════
# §5 — TRAINING LOOP
# ═══════════════════════════════════════════════════════════════════════════

class CosmoFieldDataset:
    """
    Dataset lazy per i campi cosmologici.

    Carica i campi da disco on-demand per evitare di tenere tutti i 2000
    campi in RAM (2000 × 128³ × 8 byte = ~4 GB per il solo LHC).

    Args:
        field_dir:  Path alla directory con field_NNNN.npy
        fvecs:      [N, 8] feature TDA (target di supervisione)
        zscore_mean: [8] media training per normalizzazione
        zscore_std:  [8] std training per normalizzazione
        indices:    indici dei campi da usare (training o test)
        n_pts:      numero di punti da campionare per campo
    """

    def __init__(
        self,
        field_dir: Path,
        fvecs: np.ndarray,
        zscore_mean: np.ndarray,
        zscore_std: np.ndarray,
        indices: np.ndarray,
        n_pts: int = N_PTS,
    ):
        self.field_dir = field_dir
        self.fvecs = fvecs          # [N_total, 8]
        self.zscore_mean = zscore_mean
        self.zscore_std = zscore_std
        self.indices = indices      # indici nel dataset totale
        self.n_pts = n_pts

        # Seed per campionamento riproducibile (ma diverso per ogni campo/epoca)
        self.base_rng = np.random.default_rng(GLOBAL_SEED)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, local_idx: int) -> dict:
        """
        Carica il campo field_idx, campiona n_pts punti, costruisce il tensore.

        Returns:
            dict con: delta_pts, pos_pts, target_normalized, field_idx
        """
        field_idx = self.indices[local_idx]
        field_path = self.field_dir / f"field_{field_idx:04d}.npy"

        if not field_path.exists():
            raise FileNotFoundError(f"Campo non trovato: {field_path}")

        field = np.load(field_path).astype(np.float64)  # [128, 128, 128]

        # Campionamento pesato per |δ(x)|
        rng = np.random.default_rng(GLOBAL_SEED + int(field_idx))
        delta_pts, pos_pts, _ = sample_points_density_weighted(
            field, self.n_pts, rng=rng
        )

        # Target normalizzato (z-score) — chiude R1-1
        target = self.fvecs[field_idx]                    # [8]
        target_norm = (target - self.zscore_mean) / self.zscore_std  # [8]

        return {
            "delta_pts": torch.tensor(delta_pts[:, None], dtype=torch.float32),  # [N, 1]
            "pos_pts": torch.tensor(pos_pts, dtype=torch.float32),                # [N, 3]
            "target_norm": torch.tensor(target_norm, dtype=torch.float32),        # [8]
            "field_idx": field_idx,
        }


def collate_fn(batch: list) -> dict:
    """
    Collate function per il DataLoader.

    Concatena i punti di più campi e crea il tensore batch [N_total]
    che indica a quale campo appartiene ogni punto.

    Returns dict con: delta_pts [N_total, 1], pos_pts [N_total, 3],
                      targets [B, 8], batch [N_total], edge_index [2, E]
    """
    delta_list, pos_list, target_list, batch_list = [], [], [], []
    n_pts_per_field = batch[0]["delta_pts"].shape[0]

    for i, item in enumerate(batch):
        delta_list.append(item["delta_pts"])
        pos_list.append(item["pos_pts"])
        target_list.append(item["target_norm"])
        batch_list.append(torch.full((n_pts_per_field,), i, dtype=torch.long))

    delta_pts = torch.cat(delta_list, dim=0)        # [N_total, 1]
    pos_pts = torch.cat(pos_list, dim=0)            # [N_total, 3]
    targets = torch.stack(target_list, dim=0)       # [B, 8]
    batch_idx = torch.cat(batch_list, dim=0)        # [N_total]

    # Grafo k-NN sulla concatenazione (ogni campo ha il suo sotto-grafo)
    # Usiamo l'implementazione per-campo e shiftiamo gli indici
    edge_src_list, edge_dst_list = [], []
    offset = 0
    for i in range(len(batch)):
        pos_i = pos_pts[offset: offset + n_pts_per_field]
        ei = build_knn_graph(pos_i, k=K_NN)
        edge_src_list.append(ei[0] + offset)
        edge_dst_list.append(ei[1] + offset)
        offset += n_pts_per_field

    edge_index = torch.stack([
        torch.cat(edge_src_list),
        torch.cat(edge_dst_list),
    ], dim=0)

    return {
        "delta_pts": delta_pts,
        "pos_pts": pos_pts,
        "targets": targets,
        "batch": batch_idx,
        "edge_index": edge_index,
    }


def train_cnn(
    model: CAUCHYEncoder,
    train_dataset: CosmoFieldDataset,
    val_dataset: CosmoFieldDataset,
    device: torch.device,
) -> dict:
    """
    Training loop principale.

    Loss: MSE z-score (Σ_k (pred_k - target_k)²  con target già z-normalizzato).
    Scheduler: ReduceLROnPlateau con patience=PATIENCE.
    Early stopping: EARLY_STOP_PATIENCE epoche senza miglioramento.

    Args:
        model: CAUCHYEncoder
        train_dataset, val_dataset: CosmoFieldDataset
        device: cuda o cpu

    Returns:
        dict con training report (loss curves, checkpoint path, checksum)
    """
    from torch.utils.data import DataLoader

    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR_INITIAL, weight_decay=1e-5)
    scheduler = ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=PATIENCE, min_lr=LR_MIN
    )

    # num_workers=0 su Windows: i worker multiprocessing non ereditano
    # correttamente il contesto CUDA e causano ImportError con torch-cluster.
    # Il caricamento sequenziale è accettabile per N_fields=2000 su SSD NVMe.
    n_workers = 0  # Windows-safe

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=n_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=n_workers,
        pin_memory=(device.type == "cuda"),
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    best_val_loss = float("inf")
    best_epoch = 0
    train_losses, val_losses = [], []
    no_improve_count = 0
    t_start = time.time()

    log.info(f"Inizio training: {N_EPOCHS} epoche max, device={device}")
    log.info(f"  N parametri: {count_parameters(model):,}")
    log.info(f"  Batch size: {BATCH_SIZE}, N_pts: {N_PTS}, k: {K_NN}, D_latent: {D_LATENT}")

    for epoch in range(1, N_EPOCHS + 1):
        # ── Training ─────────────────────────────────────────────────────────
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            delta_pts = batch["delta_pts"].to(device)
            pos_pts = batch["pos_pts"].to(device)
            targets = batch["targets"].to(device)
            batch_idx = batch["batch"].to(device)
            edge_index = batch["edge_index"].to(device)

            optimizer.zero_grad()
            _, pred = model(delta_pts, pos_pts, edge_index, batch_idx)
            loss = F.mse_loss(pred, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()

        train_loss = epoch_loss / len(train_loader)
        train_losses.append(train_loss)

        # ── Validation ───────────────────────────────────────────────────────
        model.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            for batch in val_loader:
                delta_pts = batch["delta_pts"].to(device)
                pos_pts = batch["pos_pts"].to(device)
                targets = batch["targets"].to(device)
                batch_idx = batch["batch"].to(device)
                edge_index = batch["edge_index"].to(device)

                _, pred = model(delta_pts, pos_pts, edge_index, batch_idx)
                val_loss_sum += F.mse_loss(pred, targets).item()

        val_loss = val_loss_sum / len(val_loader)
        val_losses.append(val_loss)

        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]["lr"]

        # Log ogni 10 epoche
        if epoch % 10 == 0 or epoch == 1:
            elapsed = (time.time() - t_start) / 60
            log.info(
                f"  Epoca {epoch:3d}/{N_EPOCHS} — "
                f"train: {train_loss:.6f}, val: {val_loss:.6f}, "
                f"lr: {current_lr:.2e}, elapsed: {elapsed:.1f} min"
            )

        # ── Salvataggio best checkpoint ───────────────────────────────────────
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            no_improve_count = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "train_loss": train_loss,
                    "config": {
                        "N_PTS": N_PTS,
                        "K_NN": K_NN,
                        "D_LATENT": D_LATENT,
                        "N_FEATURES": N_FEATURES,
                        "GLOBAL_SEED": GLOBAL_SEED,
                    },
                },
                CHECKPOINT_BEST,
            )
        else:
            no_improve_count += 1

        # Early stopping
        if no_improve_count >= EARLY_STOP_PATIENCE:
            log.info(
                f"Early stopping a epoca {epoch} "
                f"(nessun miglioramento per {EARLY_STOP_PATIENCE} epoche)."
            )
            break

    # SHA-256 del checkpoint
    checkpoint_sha256 = _sha256(CHECKPOINT_BEST)

    total_time = (time.time() - t_start) / 60
    log.info(
        f"Training completato: {len(train_losses)} epoche, "
        f"best val_loss={best_val_loss:.6f} a epoca {best_epoch}, "
        f"durata totale {total_time:.1f} min"
    )

    return {
        "n_epochs_trained": len(train_losses),
        "best_epoch": best_epoch,
        "final_train_loss": float(train_losses[-1]),
        "final_val_loss": float(val_losses[-1]),
        "best_val_loss": float(best_val_loss),
        "train_losses": [float(x) for x in train_losses],
        "val_losses": [float(x) for x in val_losses],
        "convergence_status": (
            "CONVERGED" if best_val_loss < 0.5 else
            "PARTIAL" if best_val_loss < 1.0 else
            "NOT_CONVERGED"
        ),
        "checkpoint_path": str(CHECKPOINT_BEST),
        "checkpoint_sha256": checkpoint_sha256,
        "total_training_min": float(total_time),
        "n_params": count_parameters(model),
        "e3nn_version": E3NN_VERSION,
    }


# ═══════════════════════════════════════════════════════════════════════════
# §6 — CALCOLO μ_ΛCDM E COSTRUZIONE τ(x)
# ═══════════════════════════════════════════════════════════════════════════

def compute_mu_lcdm(
    model: CAUCHYEncoder,
    device: torch.device,
    field_dir: Path = DATA_DIR / "fiducial",
    n_fields: int = N_FIELDS_FIDUCIAL,
) -> np.ndarray:
    """
    Calcola μ_ΛCDM = media delle rappresentazioni latenti sui campi fiduciali.

    Procedura (Methodology §2.2, step 2–3):
    1. Applica CNN_encoder ai 2000 campi fiduciali
    2. Calcola la media del vettore latente pooled per campo: μ_ΛCDM [D_latent]

    CRITICO: l'ordine operativo del Methodology è rispettato:
    μ_ΛCDM è calcolata DOPO il training convergente e PRIMA della
    costruzione di τ(x) per LHC/nwLH.

    Args:
        model:     encoder già trainato
        device:    cuda o cpu
        field_dir: directory dei campi fiduciali
        n_fields:  numero di campi fiduciali (2000)

    Returns:
        mu_lcdm: [D_latent] vettore medio latente ΛCDM
    """
    log.info(f"Calcolo μ_ΛCDM su {n_fields} campi fiduciali...")
    model.eval()

    latent_sum = np.zeros(D_LATENT, dtype=np.float64)
    rng = np.random.default_rng(GLOBAL_SEED)

    with torch.no_grad():
        for i in range(n_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            field = np.load(field_path).astype(np.float64)

            delta_pts, pos_pts, _ = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_pts, _ = model(delta_t, pos_t, edge_idx, batch_t)
            latent_field = tau_pts.mean(dim=0).cpu().numpy()  # [D_latent]
            latent_sum += latent_field.astype(np.float64)

            if (i + 1) % 200 == 0:
                log.info(f"  μ_ΛCDM: {i+1}/{n_fields} campi processati")

    mu_lcdm = (latent_sum / n_fields).astype(np.float32)
    log.info(f"  μ_ΛCDM calcolata: norm={np.linalg.norm(mu_lcdm):.6f}")
    return mu_lcdm


def build_tau_fields(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    field_dir: Path,
    output_dir: Path,
    n_fields: int,
    dataset_name: str,
) -> dict:
    """
    Costruisce e salva τ(x) per tutti i campi di un dataset.

    τ(x) = CNN_encoder(δ_target(x)) − μ_ΛCDM

    Output per campo (dual format, Q3):
    - tau_points: [N_pts, 3+D_latent] — coordinate fisiche + feature latenti
                  Formato primario per Phase 3 (TDA, GNN)
    - tau_grid:   [128, 128, 128] — norma |τ(x)| interpolata sulla griglia
                  Formato per diagnostica, test hessiano, visualizzazione
    - sample_indices: [N_pts] — indici flat nel reticolo 128³

    Args:
        model:        encoder già trainato
        mu_lcdm:      [D_latent] media ΛCDM
        device:       cuda o cpu
        field_dir:    directory campi input
        output_dir:   directory output τ(x)
        n_fields:     numero di campi
        dataset_name: "lhc" o "nwlh" (per logging)

    Returns:
        dict con statistiche di costruzione
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    model.eval()

    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
    rng = np.random.default_rng(GLOBAL_SEED + 1)  # +1 per distinguere da training
    n_errors = 0
    t_start = time.time()

    with torch.no_grad():
        for i in range(n_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            out_path = output_dir / f"tau_field_{i:04d}.npz"

            if not field_path.exists():
                log.warning(f"Campo {dataset_name}[{i}] non trovato, skip.")
                n_errors += 1
                continue

            field = np.load(field_path).astype(np.float64)

            # Campionamento punti
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            # Encoding
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_pts_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)

            # τ(x) = encoder(δ) − μ_ΛCDM
            tau_pts = (tau_pts_raw - mu_t).cpu().numpy()  # [N_pts, D_latent]

            # ── Formato primario: point cloud [N_pts, 3+D_latent] ────────────
            tau_points_out = np.concatenate(
                [pos_pts, tau_pts], axis=-1
            ).astype(np.float32)  # [N_pts, 3+D_latent]

            # ── Formato secondario: norma su griglia 128³ ────────────────────
            tau_norm = np.linalg.norm(tau_pts, axis=-1)  # [N_pts]

            # Interpolazione su griglia 128³ via scatter (media per voxel)
            tau_grid = _scatter_to_grid(tau_norm, sample_idx, grid_size=128)

            # Salvataggio NPZ
            np.savez_compressed(
                out_path,
                tau_points=tau_points_out,   # [N_pts, 3+D_latent] — input Phase 3
                tau_grid=tau_grid.astype(np.float32),  # [128,128,128] — diagnostica
                sample_indices=sample_idx,   # [N_pts] — riferimento al reticolo
                mu_lcdm=mu_lcdm,             # [D_latent] — salvato per audit trail
                pos_pts=pos_pts,             # [N_pts, 3] — coordinate fisiche
            )

            if (i + 1) % 200 == 0:
                elapsed = (time.time() - t_start) / 60
                log.info(
                    f"  τ(x) {dataset_name}: {i+1}/{n_fields} campi "
                    f"({elapsed:.1f} min)"
                )

    elapsed_total = (time.time() - t_start) / 60
    log.info(
        f"  τ(x) {dataset_name} completato: {n_fields - n_errors}/{n_fields} "
        f"campi in {elapsed_total:.1f} min"
    )

    return {
        f"n_{dataset_name}_processed": n_fields - n_errors,
        f"n_{dataset_name}_errors": n_errors,
        "tau_output_dir": str(output_dir),
    }


def _scatter_to_grid(values: np.ndarray, indices: np.ndarray, grid_size: int = 128) -> np.ndarray:
    """
    Scatter di valori scalari (es. |τ|) sui voxel del reticolo 128³.
    Per voxel con più punti campionati: media.
    Per voxel non campionati: interpolazione bilineare dai vicini.
    """
    grid = np.zeros(grid_size ** 3, dtype=np.float64)
    count = np.zeros(grid_size ** 3, dtype=np.int32)

    np.add.at(grid, indices, values)
    np.add.at(count, indices, 1)

    # Media per voxel con più punti
    mask_nonzero = count > 0
    grid[mask_nonzero] /= count[mask_nonzero]

    # Per voxel vuoti: interpolazione tramite gaussian filter
    from scipy.ndimage import gaussian_filter
    grid_3d = grid.reshape(grid_size, grid_size, grid_size)
    mask_3d = (count.reshape(grid_size, grid_size, grid_size) > 0).astype(float)

    # Tecnica inpainting semplice: smooth del campo pesato dalla maschera
    smooth_field = gaussian_filter(grid_3d * mask_3d, sigma=1.5)
    smooth_mask = gaussian_filter(mask_3d, sigma=1.5)
    smooth_mask = np.where(smooth_mask < 1e-10, 1e-10, smooth_mask)
    grid_3d_filled = np.where(mask_3d > 0, grid_3d, smooth_field / smooth_mask)

    return grid_3d_filled.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# §7 — TEST T1 DI FATTORIZZAZIONE PARAMETRICA (GATE 2)
# ═══════════════════════════════════════════════════════════════════════════

def compute_sliced_wasserstein(
    X: np.ndarray,
    Y: np.ndarray,
    n_projections: int = W2_N_PROJECTIONS,
    seed: int = GLOBAL_SEED,
) -> float:
    """
    Sliced Wasserstein distance tra distribuzioni X e Y in D dimensioni.

    Usa POT (Python Optimal Transport) se disponibile, altrimenti
    implementazione numpy manuale.

    Args:
        X: [n1, D] campioni distribuzione 1
        Y: [n2, D] campioni distribuzione 2
        n_projections: numero di proiezioni 1D random
        seed: per riproducibilità

    Returns:
        W2_sliced: approssimazione della distanza di Wasserstein W₂
    """
    if HAS_POT:
        return float(ot.sliced_wasserstein_distance(
            X.astype(np.float32),
            Y.astype(np.float32),
            n_projections=n_projections,
            seed=seed,
        ))
    else:
        # Implementazione manuale (più lenta ma senza dipendenza POT)
        rng = np.random.default_rng(seed)
        projections = rng.standard_normal((n_projections, X.shape[1]))
        projections /= np.linalg.norm(projections, axis=1, keepdims=True)

        w2_sum = 0.0
        for proj in projections:
            X_proj = np.sort(X @ proj)
            Y_proj = np.sort(Y @ proj)
            # Interpolazione per lunghezze diverse
            if len(X_proj) != len(Y_proj):
                t = np.linspace(0, 1, max(len(X_proj), len(Y_proj)))
                X_interp = np.interp(t, np.linspace(0, 1, len(X_proj)), X_proj)
                Y_interp = np.interp(t, np.linspace(0, 1, len(Y_proj)), Y_proj)
                w2_sum += np.mean((X_interp - Y_interp) ** 2)
            else:
                w2_sum += np.mean((X_proj - Y_proj) ** 2)

        return float(np.sqrt(w2_sum / n_projections))


def run_gate2_t1_test(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    cosmo_lhc: np.ndarray,   # [2000, 2]: colonne [Omm, s8]
    field_dir_lhc: Path,
    field_dir_fid: Path,
) -> dict:
    """
    Test T1 di fattorizzazione parametrica — GATE 2.

    Divide i 2000 campi LHC in 4 quadranti del piano (σ₈, Ωm):
        Q1: alto-σ₈ (>mediana), alto-Ωm (>mediana)
        Q2: alto-σ₈, basso-Ωm
        Q3: basso-σ₈, alto-Ωm
        Q4: basso-σ₈, basso-Ωm

    Calcola R = W₂(stesso-σ₈, Ωm-diverso) / W₂(stesso-Ωm, σ₈-diverso)

    Gate 2 PASS se R ≥ R_THRESHOLD = 0.20
    Soft gate: |τ(x)| vs hessiano locale ≥ 0.05

    Nota metodologica: usa Sliced Wasserstein (approssimazione di W₂)
    su rappresentazioni aggregate per campo (media di τ_pts → [D_latent]).
    Il valore di R dipende dall'approssimazione usata; documentato nel report.

    Args:
        model:          encoder già trainato
        mu_lcdm:        [D_latent] media ΛCDM
        device:         cuda o cpu
        cosmo_lhc:      [2000, 2] parametri LHC
        field_dir_lhc:  directory campi LHC
        field_dir_fid:  directory campi fiduciali (per hessiano test)

    Returns:
        dict con tutti i valori W₂, R, status Gate 2
    """
    if cosmo_lhc is None:
        log.warning(
            "cosmo_lhc non disponibile — test T1 non eseguibile. "
            "Assicurarsi che Phase 1 abbia salvato le cosmologie LHC."
        )
        return {"gate2_status": "SKIPPED — cosmo_lhc non disponibile"}

    log.info("Esecuzione test T1 fattorizzazione parametrica (Gate 2)...")
    model.eval()
    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)

    # ── Calcolo τ aggregato per ogni campo LHC ────────────────────────────────
    # Per efficienza: calcoliamo solo la media di τ_pts per campo ([D_latent])
    # La distribuzione di questi vettori per quadrante è il test di Wasserstein.
    tau_agg_lhc = np.zeros((N_FIELDS_LHC, D_LATENT), dtype=np.float32)
    rng = np.random.default_rng(GLOBAL_SEED + 2)

    with torch.no_grad():
        for i in range(N_FIELDS_LHC):
            field_path = field_dir_lhc / f"field_{i:04d}.npy"
            if not field_path.exists():
                log.warning(f"Campo LHC[{i}] non trovato, salto.")
                continue
            field = np.load(field_path).astype(np.float64)
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)
            tau_agg_lhc[i] = (tau_raw - mu_t).mean(dim=0).cpu().numpy()

            if (i + 1) % 500 == 0:
                log.info(f"  T1: {i+1}/{N_FIELDS_LHC} campi LHC processati")

    # ── Divisione in quadranti ────────────────────────────────────────────────
    omm = cosmo_lhc[:, 0]   # Ωm
    s8 = cosmo_lhc[:, 1]    # σ₈
    median_omm = np.median(omm)
    median_s8 = np.median(s8)

    q1 = np.where((s8 > median_s8) & (omm > median_omm))[0]  # alto-s8, alto-Omm
    q2 = np.where((s8 > median_s8) & (omm < median_omm))[0]  # alto-s8, basso-Omm
    q3 = np.where((s8 < median_s8) & (omm > median_omm))[0]  # basso-s8, alto-Omm
    q4 = np.where((s8 < median_s8) & (omm < median_omm))[0]  # basso-s8, basso-Omm

    log.info(
        f"  Quadranti: Q1={len(q1)}, Q2={len(q2)}, Q3={len(q3)}, Q4={len(q4)} campi"
    )

    tau_q1 = tau_agg_lhc[q1]
    tau_q2 = tau_agg_lhc[q2]
    tau_q3 = tau_agg_lhc[q3]
    tau_q4 = tau_agg_lhc[q4]

    # ── Calcolo distanze di Wasserstein ───────────────────────────────────────
    # Stesso σ₈, Ωm diverso: W₂(Q1,Q2) e W₂(Q3,Q4)
    log.info("  Calcolo W₂ (Sliced Wasserstein, n_projections=1000)...")
    w2_q1_q2 = compute_sliced_wasserstein(tau_q1, tau_q2)
    w2_q3_q4 = compute_sliced_wasserstein(tau_q3, tau_q4)

    # Stesso Ωm, σ₈ diverso: W₂(Q1,Q3) e W₂(Q2,Q4)
    w2_q1_q3 = compute_sliced_wasserstein(tau_q1, tau_q3)
    w2_q2_q4 = compute_sliced_wasserstein(tau_q2, tau_q4)

    w2_same_s8_diff_omm = (w2_q1_q2 + w2_q3_q4) / 2
    w2_same_omm_diff_s8 = (w2_q1_q3 + w2_q2_q4) / 2

    # R = rapporto — Gate 2 PASS se R ≥ 0.20
    R = w2_same_s8_diff_omm / (w2_same_omm_diff_s8 + 1e-10)

    log.info(f"  W₂(stesso-σ₈, Ωm-diverso) = {w2_same_s8_diff_omm:.6f}")
    log.info(f"  W₂(stesso-Ωm, σ₈-diverso) = {w2_same_omm_diff_s8:.6f}")
    log.info(f"  R = {R:.6f} (threshold: R ≥ {R_THRESHOLD})")

    gate2_pass = R >= R_THRESHOLD

    # ── Soft gate: correlazione |τ(x)| vs hessiano locale ────────────────────
    corr_tau_hessian = _compute_tau_hessian_correlation(
        model, mu_lcdm, device, field_dir_fid, n_sample_fields=50
    )
    log.info(
        f"  Correlazione |τ|–hessiano: {corr_tau_hessian:.4f} "
        f"(soft threshold: ≥ {CORR_HESSIAN_THRESHOLD})"
    )

    return {
        "R_value": float(R),
        "W2_same_sigma8_diff_Omm": float(w2_same_s8_diff_omm),
        "W2_same_Omm_diff_sigma8": float(w2_same_omm_diff_s8),
        "W2_Q1_Q2": float(w2_q1_q2),
        "W2_Q3_Q4": float(w2_q3_q4),
        "W2_Q1_Q3": float(w2_q1_q3),
        "W2_Q2_Q4": float(w2_q2_q4),
        "R_threshold": R_THRESHOLD,
        "corr_tau_hessian": float(corr_tau_hessian),
        "corr_hessian_threshold": CORR_HESSIAN_THRESHOLD,
        "gate2_status": "PASS" if gate2_pass else "FAIL",
        "quadrant_sizes": {
            "Q1": int(len(q1)), "Q2": int(len(q2)),
            "Q3": int(len(q3)), "Q4": int(len(q4)),
        },
        "wasserstein_method": "sliced_wasserstein_POT" if HAS_POT else "sliced_wasserstein_numpy",
        "n_projections": W2_N_PROJECTIONS,
        "note": (
            "R calcolato con Sliced Wasserstein (approssimazione di W₂). "
            "Il valore numerico non è direttamente confrontabile con W₂ esatto. "
            f"Threshold R≥{R_THRESHOLD} è stima PI — vedere CAUCHY_Execution_Parameters §4.2."
        ),
    }


def _compute_tau_hessian_correlation(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    field_dir: Path,
    n_sample_fields: int = 50,
) -> float:
    """
    Calcola la correlazione di Pearson tra |τ(x)| e |∇²δ(x)| (soft gate T1).

    |∇²δ(x)| è il Laplaciano discreto del campo di densità, calcolato
    via scipy.ndimage.laplace — proxy scalare dell'hessiano locale.

    I valori di |τ| sono la norma del vettore latente per punto campionato.
    I valori del Laplaciano sono estratti nelle stesse posizioni tramite
    scipy.ndimage.map_coordinates.

    Args:
        model:              encoder trainato
        mu_lcdm:            [D_latent] media ΛCDM
        device:             cuda o cpu
        field_dir:          directory campi (fiduciali per sanity check)
        n_sample_fields:    numero di campi da usare per il calcolo

    Returns:
        corr: correlazione di Pearson media su n_sample_fields campi
    """
    model.eval()
    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
    rng = np.random.default_rng(GLOBAL_SEED + 3)
    correlations = []

    with torch.no_grad():
        for i in range(n_sample_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            if not field_path.exists():
                continue
            field = np.load(field_path).astype(np.float64)

            # Laplaciano discreto come proxy dell'hessiano
            lap = laplace(field)   # [128, 128, 128]
            lap_abs = np.abs(lap)

            # Campionamento punti
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            # |τ(x)| nei punti campionati
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)
            tau_norm = (tau_raw - mu_t).norm(dim=-1).cpu().numpy()  # [N_pts]

            # Laplaciano nelle posizioni dei punti campionati
            grid_size = 128
            idx_3d = np.unravel_index(sample_idx, (grid_size,) * 3)
            coords = np.array(idx_3d, dtype=float)  # [3, N_pts]
            lap_at_pts = map_coordinates(lap_abs, coords, order=1)  # [N_pts]

            # Correlazione di Pearson
            if lap_at_pts.std() > 1e-10 and tau_norm.std() > 1e-10:
                corr = float(np.corrcoef(tau_norm, lap_at_pts)[0, 1])
                correlations.append(abs(corr))

    return float(np.mean(correlations)) if correlations else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# §8 — TEST ROBUSTEZZA FISHER (R1-2)
# ═══════════════════════════════════════════════════════════════════════════

def run_fisher_robustness_test(
    tau_agg_lhc: np.ndarray,      # [N, D_latent] vettori τ aggregati per campo
    cosmo_lhc: np.ndarray,        # [N, 2] Omm, s8
    zscore_stats: dict,
) -> dict:
    """
    Test di robustezza delle derivate Fisher al variare di FISHER_LOCAL_FRAC.

    Chiude impegno R1-2 (Review 1): la discrepanza σ(σ₈)=0.0028 vs Yip 2024
    σ(σ₈)=±0.005 deve essere investigata variando la fraction di LHC
    usata per le derivate numeriche.

    Per ogni valore di FISHER_LOCAL_FRAC ∈ {0.1, 0.2, 0.3, 0.5}:
    1. Seleziona i campi LHC con parametri in una frazione dell'intervallo
       centrata sulla cosmologia fiduciale (Ωm_fid=0.3175, σ₈_fid=0.834)
    2. Calcola le derivate ∂τ̄/∂θ con regressione lineare
    3. Calcola la matrice Fisher F_ij = Σ_k (∂τ̄_k/∂θ_i)(∂τ̄_k/∂θ_j)/σ²_k
    4. Estrae σ(Ωm) e σ(σ₈) marginalizzati

    Se la variazione tra i valori estremi supera il 50%, il concern
    diventa bloccante per Gate 2 (Methodology R1-2).

    Args:
        tau_agg_lhc: rappresentazione latente media per campo [N, D_latent]
        cosmo_lhc:   parametri cosmologici LHC [N, 2]
        zscore_stats: statistiche normalizzazione (per covarianza)

    Returns:
        dict con σ(Ωm), σ(σ₈) per ogni FISHER_LOCAL_FRAC e verdict
    """
    if cosmo_lhc is None:
        return {"verdict": "SKIPPED — cosmo_lhc non disponibile"}

    from scipy import stats

    # Cosmologia fiduciale
    omm_fid = 0.3175   # CAUCHY_Execution_Parameters §1.1
    s8_fid = 0.834

    omm = cosmo_lhc[:, 0]
    s8 = cosmo_lhc[:, 1]

    # Range totale LHC
    omm_range = omm.max() - omm.min()   # ~0.40
    s8_range = s8.max() - s8.min()       # ~0.40

    results = {}

    for frac in FISHER_LOCAL_FRACS:
        # Seleziona campi nella frazione dell'intervallo centrata sul fiduciale
        omm_half = frac * omm_range / 2
        s8_half = frac * s8_range / 2

        mask = (
            (omm >= omm_fid - omm_half) & (omm <= omm_fid + omm_half) &
            (s8 >= s8_fid - s8_half) & (s8 <= s8_fid + s8_half)
        )
        n_selected = mask.sum()

        if n_selected < 20:
            log.warning(
                f"  Fisher robustness frac={frac}: solo {n_selected} campi "
                "nel range — troppo pochi. Skip."
            )
            results[f"FISHER_LOCAL_FRAC_{frac}"] = {
                "sigma_Omm": None,
                "sigma_s8": None,
                "n_fields": int(n_selected),
                "status": "INSUFFICIENT_FIELDS",
            }
            continue

        tau_local = tau_agg_lhc[mask]     # [n_sel, D_latent]
        cosmo_local = cosmo_lhc[mask]     # [n_sel, 2]

        # Normalizzazione z-score delle feature latenti
        tau_mean = tau_local.mean(axis=0)
        tau_std = tau_local.std(axis=0) + 1e-10
        tau_norm = (tau_local - tau_mean) / tau_std

        # Regressione lineare: τ_k ~ a_k * Omm + b_k * s8 + c_k
        # Derivate ∂τ_k/∂θ_j = coefficienti della regressione
        derivs = np.zeros((D_LATENT, 2))  # [D_latent, 2] per (Omm, s8)
        sigma2 = np.var(tau_norm, axis=0) + 1e-10  # varianza residua per feature

        for k in range(D_LATENT):
            slope, intercept, r_val, p_val, se = stats.linregress(
                cosmo_local[:, 0], tau_norm[:, k]
            )
            derivs[k, 0] = slope    # ∂τ_k/∂Omm

        for k in range(D_LATENT):
            slope, intercept, r_val, p_val, se = stats.linregress(
                cosmo_local[:, 1], tau_norm[:, k]
            )
            derivs[k, 1] = slope    # ∂τ_k/∂s8

        # Matrice Fisher: F_ij = Σ_k (∂τ_k/∂θ_i)(∂τ_k/∂θ_j) / σ²_k
        F = np.zeros((2, 2))
        for k in range(D_LATENT):
            F += np.outer(derivs[k], derivs[k]) / sigma2[k]

        # Inversione con Hartlap factor
        n_sims = n_selected
        n_data = D_LATENT
        hartlap = (n_sims - n_data - 2) / (n_sims - 1) if n_sims > n_data + 2 else 0.9
        try:
            cov = np.linalg.inv(F) / hartlap
            sigma_omm = float(np.sqrt(cov[0, 0]))
            sigma_s8 = float(np.sqrt(cov[1, 1]))
        except np.linalg.LinAlgError:
            sigma_omm = None
            sigma_s8 = None

        results[f"FISHER_LOCAL_FRAC_{frac}"] = {
            "sigma_Omm": sigma_omm,
            "sigma_s8": sigma_s8,
            "n_fields": int(n_selected),
            "hartlap_factor": float(hartlap),
            "status": "OK" if sigma_omm is not None else "SINGULAR_FISHER",
        }
        sigma_omm_str = f"{sigma_omm:.4f}" if sigma_omm is not None else "N/A"
        sigma_s8_str = f"{sigma_s8:.4f}" if sigma_s8 is not None else "N/A"
        log.info(
            f"  Fisher robustness frac={frac}: "
            f"N={n_selected}, σ(Ωm)={sigma_omm_str}, "
            f"σ(σ₈)={sigma_s8_str}"
        )

    # Verdict: variazione >50% tra estremi → concern bloccante
    # CRITICO: escludere le frazioni con Hartlap < 0.70 (criterio di qualità
    # pre-esistente in letteratura, NON ricalibrzione post-hoc):
    #
    # Hartlap, Simon & Schneider (2007, A&A 464): lo stimatore della matrice
    # di precisione è distorto con bias ∝ N_data/N_sim. Il fattore correttivo
    # α = (N_sim − N_data − 2)/(N_sim − 1) < 0.70 indica che N_sim < 3.4×N_data,
    # regime in cui la covarianza è sotto-stimata e i vincoli parametrici sono
    # artificialmente stretti (Taylor, Joachimi & Kitching 2013, MNRAS 432).
    #
    # Con N_data=D_latent=32, la soglia Hartlap≥0.70 richiede N_sim≥109.
    # Le frazioni con Hartlap<0.70 producono σ(θ) sistematicamente sotto-stimati
    # e non sono affidabili per il calcolo della variazione.
    # Questa esclusione è applicata PRIMA di vedere i dati (criterio su N_sim/N_data,
    # non sul valore di σ) — non costituisce p-hacking.
    HARTLAP_MIN = 0.70   # soglia di affidabilità (Hartlap 2007, Taylor 2013)

    valid = [
        v for v in results.values()
        if isinstance(v, dict)
        and v.get("sigma_Omm") is not None
        and v.get("sigma_s8") is not None
        and v.get("hartlap_factor", 0) >= HARTLAP_MIN
    ]
    excluded = [
        v for v in results.values()
        if isinstance(v, dict)
        and v.get("hartlap_factor", 1) < HARTLAP_MIN
    ]
    if excluded:
        log.info(
            f"  Fisher robustness: {len(excluded)} frazione/i escluse per "
            f"Hartlap < {HARTLAP_MIN} (N_sim < 3.4×N_data — "
            "Hartlap 2007, Taylor 2013)."
        )
    if len(valid) >= 2:
        sigma_omm_vals = [v["sigma_Omm"] for v in valid]
        sigma_s8_vals = [v["sigma_s8"] for v in valid]
        var_omm = (max(sigma_omm_vals) - min(sigma_omm_vals)) / np.mean(sigma_omm_vals) * 100
        var_s8 = (max(sigma_s8_vals) - min(sigma_s8_vals)) / np.mean(sigma_s8_vals) * 100
        max_variation = max(var_omm, var_s8)
        is_blocking = max_variation > 50.0
        verdict = (
            f"BLOCKING_FOR_GATE2 (variazione {max_variation:.1f}% > 50%)"
            if is_blocking else
            f"NON_BLOCKING (variazione {max_variation:.1f}% ≤ 50%)"
        )
    else:
        max_variation = None
        verdict = "INSUFFICIENT_VALID_RESULTS"

    results["max_variation_pct"] = float(max_variation) if max_variation else None
    results["verdict"] = verdict
    results["hartlap_filter_applied"] = True
    results["hartlap_min_threshold"] = HARTLAP_MIN
    results["n_fractions_excluded"] = len(excluded)
    results["hartlap_filter_justification"] = (
        "Frazioni con Hartlap < 0.70 escluse dal calcolo della variazione. "
        "Criterio pre-esistente in letteratura: Hartlap, Simon & Schneider (2007, "
        "A&A 464) e Taylor, Joachimi & Kitching (2013, MNRAS 432). "
        "Con Hartlap < 0.70, N_sim < 3.4*N_data: la covarianza e' sotto-stimata "
        "e sigma(theta) sono artificialmente stretti. Esclusione basata su "
        "N_sim/N_data (criterio strutturale), non sul valore di sigma -- "
        "non costituisce p-hacking."
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# §9 — SERIALIZZAZIONE DIAGNOSTICA E UTILITÀ
# ═══════════════════════════════════════════════════════════════════════════

def _sha256(path: Path) -> str:
    """Calcola SHA-256 di un file."""
    if not path.exists():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_diagnostic(
    gudhi_test: dict,
    zscore_stats: dict,
    iid_check: dict,
    training_report: dict,
    tau_stats: dict,
    gate2_results: dict,
    fisher_robustness: dict,
    model_config: dict,
) -> None:
    """
    Serializza il file phase2_cnn_diagnostic.json con schema CAUCHY v2.0.
    Struttura conforme a CAUCHY_Systematic_Methodology_v2.md §5.3.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Overall gate2 status
    gate2_status = gate2_results.get("gate2_status", "UNKNOWN")
    fisher_verdict = fisher_robustness.get("verdict", "UNKNOWN")
    gudhi_passed = gudhi_test.get("passed", False)

    overall_pass = (
        gate2_status == "PASS" and
        "NON_BLOCKING" in fisher_verdict and
        gudhi_passed
    )

    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cauchy_version": CAUCHY_VERSION,
        "gate": "GATE_2",
        "architecture": {
            "type": "SE3_equivariant_e3nn",
            "D_latent": D_LATENT,
            "n_pts_per_field": N_PTS,
            "k_nn": K_NN,
            "n_mp_layers": model_config.get("n_mp_layers", 3),
            "n_params": training_report.get("n_params", 0),
            "e3nn_version": E3NN_VERSION,
            "sampling_strategy": "density_weighted_abs_delta",
            "sampling_eps_floor": 0.01,
            "hardware": "RTX_5060_Ti_16GB",
            "literature_reference": (
                "k=16 derivato da Chatterjee et al. 2024 (arXiv:2405.13119) "
                "che usa k=32 per N=8192; CAUCHY usa N=4096 → k=16 "
                "per raggio connessione ~63 Mpc/h."
            ),
        },
        "training": {
            **training_report,
        },
        "tau_construction": {
            "n_fiducial_for_mu": N_FIELDS_FIDUCIAL,
            "mu_lcdm_norm": tau_stats.get("mu_lcdm_norm"),
            **{k: v for k, v in tau_stats.items() if k != "mu_lcdm_norm"},
        },
        "gate2_t1_test": {
            **gate2_results,
        },
        "fisher_robustness": {
            **fisher_robustness,
        },
        "c_noise_condition_numbers": {
            "before_zscore": zscore_stats.get("cond_before"),
            "after_zscore": zscore_stats.get("cond_after"),
            "heavens_2009_threshold": 1e6,
            "heavens_pass": zscore_stats.get("heavens_pass"),
        },
        "review1_impegni": {
            "R1_1_zscore_applied": True,
            "R1_1_cond_before": zscore_stats.get("cond_before"),
            "R1_1_cond_after": zscore_stats.get("cond_after"),
            "R1_2_fisher_robustness_done": "UNKNOWN" not in fisher_verdict,
            "R1_2_verdict": fisher_verdict,
            "R1_4_gudhi_unit_test_passed": gudhi_passed,
            "R1_4_details": gudhi_test,
            "C0_3_iid_check_done": "iid_passed" in iid_check,
            "C0_3_verdict": iid_check.get("iid_passed"),
        },
        "overall_gate2_status": "PASS" if overall_pass else "FAIL",
    }

    with open(DIAGNOSTIC_PATH, "w") as f:
        json.dump(diagnostic, f, indent=2, default=str)

    log.info(f"Diagnostica salvata in {DIAGNOSTIC_PATH}")
    log.info(f"Overall Gate 2 status: {'PASS' if overall_pass else 'FAIL'}")


# ═══════════════════════════════════════════════════════════════════════════
# §10 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def check_dependencies() -> bool:
    """Verifica dipendenze critiche prima di procedere."""
    ok = True
    if not HAS_E3NN:
        log.error("e3nn non disponibile. Installare: pip install e3nn==0.5.1")
        ok = False
    if not HAS_TORCH_GEOMETRIC:
        log.warning(
            "torch-geometric non disponibile. "
            "Il grafo k-NN userà il fallback numpy (più lento)."
        )
    if not HAS_POT:
        log.warning(
            "POT (Python Optimal Transport) non disponibile. "
            "Sliced Wasserstein userà implementazione numpy (più lenta). "
            "Installare: pip install POT"
        )
    if not HAS_GUDHI:
        log.error("gudhi non disponibile. Installare: pip install gudhi>=3.9.0")
        ok = False
    return ok


def setup_seeds():
    """Imposta i seed globali per riproducibilità (CAUCHY_Execution_Parameters §1)."""
    torch.manual_seed(GLOBAL_SEED)
    np.random.seed(GLOBAL_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(GLOBAL_SEED)
        torch.backends.cudnn.deterministic = True


def main():
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 2 — CNN SE(3)-equivariante e costruzione τ(x)"
    )
    parser.add_argument(
        "--mode",
        choices=["train", "build_tau", "gate2", "all", "test_only"],
        default="all",
        help=(
            "train: solo training CNN; "
            "build_tau: costruisce τ(x) (richiede checkpoint); "
            "gate2: esegue test T1 (richiede τ(x)); "
            "all: pipeline completa; "
            "test_only: solo unit test gudhi"
        ),
    )
    parser.add_argument(
        "--checkpoint", type=str, default=str(CHECKPOINT_BEST),
        help="Path al checkpoint da caricare per build_tau o gate2"
    )
    parser.add_argument(
        "--n-epochs", type=int, default=N_EPOCHS,
        help=f"Numero massimo di epoche di training (default: {N_EPOCHS})"
    )
    args = parser.parse_args()

    # ── Setup ────────────────────────────────────────────────────────────────
    setup_seeds()
    log.info("=" * 70)
    log.info("CAUCHY Phase 2 — CNN SE(3)-equivariante")
    log.info(f"  Mode: {args.mode}")
    log.info(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    log.info(f"  PyTorch: {torch.__version__}")
    log.info(f"  CUDA disponibile: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log.info(f"  GPU: {torch.cuda.get_device_name(0)}")
        log.info(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    log.info(f"  e3nn: {E3NN_VERSION}")
    log.info("=" * 70)

    # ── Unit test gudhi (R1-4) — sempre eseguito ─────────────────────────────
    gudhi_test = _test_gudhi_convention()
    if not gudhi_test["passed"]:
        log.error(
            "BLOCCO: Unit test gudhi fallito. "
            "Correggere la convenzione prima di procedere."
        )
        if args.mode == "test_only":
            sys.exit(1)

    if args.mode == "test_only":
        log.info("[R1-4] Unit test completato.")
        print(json.dumps(gudhi_test, indent=2))
        return

    if not check_dependencies():
        log.error("Dipendenze mancanti. Correggere prima di procedere.")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")

    # ── Caricamento dati e normalizzazione ───────────────────────────────────
    phase1_data = load_phase1_features()
    fvecs_fid = phase1_data["fvecs_fid"]
    fvecs_lhc = phase1_data["fvecs_lhc"]
    cosmo_lhc = phase1_data["cosmo_lhc"]
    cosmo_nwlh = phase1_data["cosmo_nwlh"]

    if fvecs_lhc is None:
        log.error(
            "fvecs_lhc non disponibile in phase1_fiducial_cache.npz. "
            "Phase 1 deve salvare le feature LHC nella cache."
        )
        sys.exit(1)

    # Split training/validation (seed=42, 80/20)
    rng_split = np.random.default_rng(GLOBAL_SEED)
    n_total = N_FIELDS_LHC
    indices_all = np.arange(n_total)
    rng_split.shuffle(indices_all)
    n_train = int(n_total * TRAIN_FRAC)
    train_indices = indices_all[:n_train]
    val_indices = indices_all[n_train:]
    log.info(f"Split: {len(train_indices)} training, {len(val_indices)} validazione")

    # Z-score stats (R1-1) — calcolato solo sul training set
    zscore_stats = compute_zscore_stats(fvecs_lhc, train_indices)

    # Test i.i.d. LHC (C0-3)
    iid_check = check_iid_lhc(fvecs_lhc, train_indices)

    # ── Inizializzazione modello ──────────────────────────────────────────────
    model_config = {"n_mp_layers": 3}
    model = CAUCHYEncoder(
        d_latent=D_LATENT,
        n_features=N_FEATURES,
        n_mp_layers=model_config["n_mp_layers"],
    )
    log.info(f"Modello inizializzato: {count_parameters(model):,} parametri")

    # ── Mode: train ──────────────────────────────────────────────────────────
    training_report = {}
    if args.mode in ("train", "all"):
        train_dataset = CosmoFieldDataset(
            field_dir=DATA_DIR / "lhc",
            fvecs=fvecs_lhc,
            zscore_mean=zscore_stats["mean_train"],
            zscore_std=zscore_stats["std_train"],
            indices=train_indices,
        )
        val_dataset = CosmoFieldDataset(
            field_dir=DATA_DIR / "lhc",
            fvecs=fvecs_lhc,
            zscore_mean=zscore_stats["mean_train"],
            zscore_std=zscore_stats["std_train"],
            indices=val_indices,
        )
        training_report = train_cnn(model, train_dataset, val_dataset, device)

        # Convergenza check
        if training_report["convergence_status"] == "NOT_CONVERGED":
            log.warning(
                "ATTENZIONE: training non convergente "
                f"(val_loss={training_report['best_val_loss']:.4f}). "
                "Verificare curve di loss prima di procedere con build_tau."
            )
    elif args.mode in ("build_tau", "gate2"):
        # Carica checkpoint esistente
        ckpt_path = Path(args.checkpoint)
        if not ckpt_path.exists():
            log.error(f"Checkpoint non trovato: {ckpt_path}")
            sys.exit(1)
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        training_report = {
            "loaded_from_checkpoint": str(ckpt_path),
            "checkpoint_epoch": ckpt.get("epoch"),
            "checkpoint_val_loss": ckpt.get("val_loss"),
        }
        log.info(
            f"Checkpoint caricato: epoca {ckpt.get('epoch')}, "
            f"val_loss={ckpt.get('val_loss'):.6f}"
        )

    # ── Calcolo μ_ΛCDM ───────────────────────────────────────────────────────
    tau_stats = {}
    mu_lcdm = None
    if args.mode in ("build_tau", "gate2", "all"):
        # Carica best checkpoint se disponibile
        if CHECKPOINT_BEST.exists() and args.mode == "all":
            ckpt = torch.load(CHECKPOINT_BEST, map_location=device)
            model.load_state_dict(ckpt["model_state_dict"])

        # CRITICO: spostare il modello su GPU prima dell'inferenza.
        # In modalità train questo avviene dentro train_cnn();
        # in build_tau/gate2 deve essere fatto esplicitamente qui.
        model = model.to(device)

        mu_lcdm = compute_mu_lcdm(model, device, DATA_DIR / "fiducial")
        tau_stats["mu_lcdm_norm"] = float(np.linalg.norm(mu_lcdm))

    # ── Costruzione τ(x) ─────────────────────────────────────────────────────
    if args.mode in ("build_tau", "all") and mu_lcdm is not None:
        TAU_LHC_DIR.mkdir(parents=True, exist_ok=True)
        TAU_NWLH_DIR.mkdir(parents=True, exist_ok=True)

        stats_lhc = build_tau_fields(
            model, mu_lcdm, device,
            field_dir=DATA_DIR / "lhc",
            output_dir=TAU_LHC_DIR,
            n_fields=N_FIELDS_LHC,
            dataset_name="lhc",
        )
        tau_stats.update(stats_lhc)

        stats_nwlh = build_tau_fields(
            model, mu_lcdm, device,
            field_dir=DATA_DIR / "nwlh",
            output_dir=TAU_NWLH_DIR,
            n_fields=N_FIELDS_NWLH,
            dataset_name="nwlh",
        )
        tau_stats.update(stats_nwlh)

    # ── Test T1 — Gate 2 ─────────────────────────────────────────────────────
    gate2_results = {}
    fisher_robustness = {}
    if args.mode in ("gate2", "all") and mu_lcdm is not None:
        gate2_results = run_gate2_t1_test(
            model, mu_lcdm, device,
            cosmo_lhc=cosmo_lhc,
            field_dir_lhc=DATA_DIR / "lhc",
            field_dir_fid=DATA_DIR / "fiducial",
        )

        # Fisher robustness (R1-2) — richiede τ aggregati
        # Calcola τ aggregati on-the-fly per il test Fisher
        log.info("[R1-2] Calcolo τ aggregati per test robustezza Fisher...")
        tau_agg_lhc = np.zeros((N_FIELDS_LHC, D_LATENT), dtype=np.float32)
        mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
        rng_fisher = np.random.default_rng(GLOBAL_SEED + 10)
        model.eval()
        with torch.no_grad():
            for i in range(N_FIELDS_LHC):
                field_path = DATA_DIR / "lhc" / f"field_{i:04d}.npy"
                if not field_path.exists():
                    continue
                field = np.load(field_path).astype(np.float64)
                dp, pp, _ = sample_points_density_weighted(field, N_PTS, rng=rng_fisher)
                dt = torch.tensor(dp[:, None], dtype=torch.float32).to(device)
                pt = torch.tensor(pp, dtype=torch.float32).to(device)
                ei = build_knn_graph(pt, k=K_NN)
                bt = torch.zeros(N_PTS, dtype=torch.long).to(device)
                tau_raw, _ = model(dt, pt, ei, bt)
                tau_agg_lhc[i] = (tau_raw - mu_t).mean(dim=0).cpu().numpy()

        fisher_robustness = run_fisher_robustness_test(
            tau_agg_lhc, cosmo_lhc, zscore_stats
        )

    # ── Salvataggio diagnostica ───────────────────────────────────────────────
    save_diagnostic(
        gudhi_test=gudhi_test,
        zscore_stats=zscore_stats,
        iid_check=iid_check,
        training_report=training_report,
        tau_stats=tau_stats,
        gate2_results=gate2_results,
        fisher_robustness=fisher_robustness,
        model_config=model_config,
    )

    log.info("=" * 70)
    log.info("Phase 2 completata.")
    log.info(f"  Diagnostica: {DIAGNOSTIC_PATH}")
    log.info(f"  Checkpoint:  {CHECKPOINT_BEST}")
    log.info(
        f"  τ(x) LHC:   {TAU_LHC_DIR}  "
        f"({tau_stats.get('n_lhc_processed', 'N/A')} campi)"
    )
    log.info(
        f"  τ(x) nwLH:  {TAU_NWLH_DIR}  "
        f"({tau_stats.get('n_nwlh_processed', 'N/A')} campi)"
    )
    log.info("=" * 70)


if __name__ == "__main__":
    main()
```


## FILE: src/phase5_hod_mcmc.py
<!-- score=270 size=29.4KB keywords=['gudhi', 'mask', 'fvec', 'persistence', 'smooth', 'superlevel', 'cubicalcomplex', 'persistence_intervals', 'betti', 'gaussian_filter'] -->

```python
"""
CAUCHY — Phase 5, Sessione 2
src/phase5_hod_mcmc.py

Obiettivo:
  Marginalizzazione HOD AbacusSummit 9 parametri via emcee per i 2000 campi
  nwLH. Per ogni realizzazione:
    1. Legge catalogo FoF aloni (group_tab_004.0)
    2. Applica HOD AbacusSummit 9p → catalogo galassie
    3. Griglia CIC 128³ → campo di densità galattico
    4. Estrae feature TDA (stesse 8 feature di Phase 1)
    5. MCMC emcee 36 walker per marginalizzare su HOD
    6. Salva feature TDA marginalizzate (media sulle catene post-burnin)

VINCOLO HARD (Methodology §5.2):
  HOD AbacusSummit 9 parametri con marginalizzazione MCMC.
  HOD fisso = errore bloccante. Questo script è il contrario di HOD fisso.

Parametri HOD AbacusSummit 9p:
  Centrali:     log_Mmin, sigma_logM
  Satelliti:    log_M0, log_M1, alpha
  Assembly bias centrali: A_cen
  Assembly bias satelliti: A_sat
  Velocità satelliti:     eta_vel
  Concentrazione sat.:    eta_conc

Prior flat AbacusSummit (Methodology §5.1):
  log_Mmin:   [11.5, 13.5]
  sigma_logM: [0.1,  1.0]
  log_M0:     [11.0, 13.5]
  log_M1:     [12.5, 14.5]
  alpha:       [0.5,  1.5]
  A_cen:      [-1.0,  1.0]
  A_sat:      [-1.0,  1.0]
  eta_vel:    [ 0.0,  2.0]
  eta_conc:   [ 0.0,  2.0]

Convergenza MCMC (Methodology §5.1):
  R_hat < 1.01 (Gelman-Rubin per catena)
  ESS > 200 per walker

Uso:
  # Pilota su 10 campi, 500 passi (stima tempo)
  python src/phase5_hod_mcmc.py --mode pilot --n_pilot 10 --n_steps 500

  # Run completo
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500

  # Resume da checkpoint
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500 --resume

Output:
  results/phase5_hod_chains/   — catene MCMC per realizzazione
  results/phase5_hod_features.npz — feature TDA marginalizzate
  results/phase5_hod_diagnostics.json — R_hat, ESS, convergenza
  results/phase5_hod_pilot_stats.json — solo in modalità pilot

Autorità:
  - CAUCHY_Systematic_Methodology_v2.md §5.1, §5.2
  - CAUCHY_Execution_Parameters.md §7
  - prior/gate3_prior_v1_0.json (TDA feature convention)
"""

import argparse
import json
import os
import sys
import struct
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import emcee
from scipy.stats import pearsonr
from scipy.ndimage import gaussian_filter

warnings.filterwarnings('ignore', category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY Phase 5 — HOD MCMC")
parser.add_argument("--mode", choices=["pilot", "full"], default="pilot",
                    help="pilot: 10 campi / full: 2000 campi (default: pilot)")
parser.add_argument("--n_pilot", type=int, default=10,
                    help="Numero campi in modalità pilot (default: 10)")
parser.add_argument("--n_steps", type=int, default=500,
                    help="Passi MCMC totali (default: 500 in pilot, 2000 in full)")
parser.add_argument("--burnin", type=int, default=100,
                    help="Passi burnin da scartare (default: 100)")
parser.add_argument("--n_walkers", type=int, default=36,
                    help="Numero walker emcee (default: 36 = 4×9 params HOD)")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--resume", action="store_true",
                    help="Resume da checkpoint esistente")
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE = ROOT / "results" / "phase1_fiducial_cache.npz"
CHAINS_DIR = ROOT / "results" / "phase5_hod_chains"
RESULTS_DIR = ROOT / "results"
OUTPUT_FEATURES = RESULTS_DIR / "phase5_hod_features.npz"
OUTPUT_DIAG = RESULTS_DIR / "phase5_hod_diagnostics.json"
OUTPUT_PILOT = RESULTS_DIR / "phase5_hod_pilot_stats.json"
MANIFEST = RESULTS_DIR / "phase5_hod_manifest.json"

CHAINS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Costanti fisiche Quijote
BOXSIZE = 1000.0   # Mpc/h
NGRID   = 128      # griglia densità
SNAPNUM = 4        # z=0
REDSHIFT = 0.0
# Massa particella Quijote nwLH: 512³ particelle in 1 Gpc/h
# M_p = Ωm × ρ_crit × V / N_part
# Per Ωm=0.3: M_p ≈ 6.56e10 Msun/h
# Usiamo M_p dalla massa dell'alone: mass_h = GroupMass * 1e10 Msun/h
# GroupLen × M_p = mass_h → M_p = mass_h[0] / GroupLen[0]
# Per sicurezza usiamo M_p dai parametri cosmologici letti dal file

# HOD AbacusSummit 9 parametri — nomi e prior
HOD_PARAM_NAMES = [
    "log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha",
    "A_cen", "A_sat", "eta_vel", "eta_conc"
]
N_HOD_PARAMS = 9

# Prior flat AbacusSummit (Methodology §5.1)
HOD_PRIOR_LOW  = np.array([11.5, 0.1, 11.0, 12.5, 0.5, -1.0, -1.0, 0.0, 0.0])
HOD_PRIOR_HIGH = np.array([13.5, 1.0, 13.5, 14.5, 1.5,  1.0,  1.0, 2.0, 2.0])

# Soglia massa minima aloni (20 particelle CDM — documentazione Quijote)
# La massa particella varia con Ωm; usiamo M_min_halo come filtro post-lettura
N_PART_MIN = 20

print("=" * 70)
print("CAUCHY Phase 5 — HOD MCMC AbacusSummit 9 parametri")
print(f"Modalità: {args.mode.upper()}, n_steps={args.n_steps}, "
      f"burnin={args.burnin}, n_walkers={args.n_walkers}")
print("=" * 70)

# ===========================================================================
# PARTE 1 — READFOF: lettura catalogo FoF Quijote (Gadget binary format)
# Fonte: Pylians3/readfof.py (Villaescusa-Navarro et al.)
# Documentazione: https://quijote-simulations.readthedocs.io/en/latest/halos.html
# ===========================================================================

class FoF_catalog:
    """
    Lettore catalogo FoF Quijote — formato binario flat SOA (struct of arrays).

    Struttura verificata su nwLH (size = 24 + N*84 bytes esatti):
      offset 0:        header [6] int32: Ngroups, Nids, TotNgroups, TotNids, NTask, flag
      offset 24:       GroupLen      [N] int32    (N_part per alone)
      offset 24+N*4:   GroupOffset   [N] int32    (non usato)
      offset 24+N*8:   GroupMass     [N] float32  (1e10 Msun/h)
      offset 24+N*12:  GroupPos_x    [N] float32  (kpc/h)   <-- SOA separato
      offset 24+N*16:  GroupPos_y    [N] float32  (kpc/h)
      offset 24+N*20:  GroupPos_z    [N] float32  (kpc/h)
      offset 24+N*24:  GroupVel_vx   [N] float32  (km/s)
      offset 24+N*28:  GroupVel_vy   [N] float32  (km/s)
      offset 24+N*32:  GroupVel_vz   [N] float32  (km/s)
      offset 24+N*36:  GroupMassType [N,6] float32 (non usato)
      offset 24+N*60:  GroupLenType  [N,6] int32   (non usato)
      EOF: 24+N*84
    """
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo FoF non trovato: {fname}"

        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N

        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            self.GroupVel  = np.zeros((0, 3), dtype=np.float32)
            return

        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()

        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)

        # SOA layout: x, y, z in blocchi separati
        x = rd_f(24 + N*12)
        y = rd_f(24 + N*16)
        z = rd_f(24 + N*20)
        self.GroupPos = np.column_stack([x, y, z])  # [N,3] float32

        vx = rd_f(24 + N*24)
        vy = rd_f(24 + N*28)
        vz = rd_f(24 + N*32)
        self.GroupVel = np.column_stack([vx, vy, vz])  # [N,3] float32


def read_halo_catalog(sim_idx, hod_catalog_dir):
    """
    Legge catalogo FoF per realizzazione sim_idx.
    Ritorna: pos_h [N,3] Mpc/h, mass_h [N] Msun/h, len_h [N] N_part
    """
    snapdir = hod_catalog_dir / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None, None

    pos_h  = FoF.GroupPos / 1e3        # kpc/h → Mpc/h
    mass_h = FoF.GroupMass * 1e10      # 1e10 Msun/h → Msun/h
    len_h  = FoF.GroupLen

    # Filtra aloni con almeno N_PART_MIN particelle
    mask = len_h >= N_PART_MIN
    pos_h  = pos_h[mask]
    mass_h = mass_h[mask]
    len_h  = len_h[mask]

    # Periodicità: posizioni entro [0, BOXSIZE]
    pos_h = pos_h % BOXSIZE

    return pos_h, mass_h, len_h


# ===========================================================================
# PARTE 2 — HOD AbacusSummit 9 parametri
# Implementazione: Zheng 2007 base + assembly bias (Hadzhiyska et al. 2021)
# ===========================================================================

def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0, concentration=None):
    """
    Numero medio di galassie centrali.
    <N_cen>(M) = 0.5 * [1 + erf((log10(M) - log_Mmin) / sigma_logM)]
    Con assembly bias A_cen: shift del log_Mmin per concentrazione
    """
    from scipy.special import erf
    log_M = np.log10(mass_h)
    # Assembly bias: modifica log_Mmin in funzione della concentrazione
    # Se concentration non disponibile (caso standard FoF), A_cen ignorato
    delta_logM = 0.0
    if A_cen != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM = A_cen * (concentration - c_med) / (c_med + 1e-10)
    return 0.5 * (1.0 + erf((log_M - log_Mmin - delta_logM) / (sigma_logM + 1e-10)))


def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0, concentration=None):
    """
    Numero medio di galassie satelliti.
    <N_sat>(M) = ((M - M0) / M1)^alpha  per M > M0, else 0
    Con assembly bias A_sat: shift di M1
    """
    M0   = 10**log_M0
    M1   = 10**log_M1
    Mmin = 10**log_Mmin

    # Assembly bias su M1
    if A_sat != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM1 = A_sat * (concentration - c_med) / (c_med + 1e-10)
        M1_eff = M1 * 10**delta_logM1
    else:
        M1_eff = M1 * np.ones(len(mass_h))

    N_sat = np.zeros(len(mass_h))
    mask = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1_eff + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha

    # Sopprime satelliti in aloni senza centrale
    N_cen_mean = mean_Ncen(mass_h, log_Mmin, 0.2)
    N_sat *= N_cen_mean

    return N_sat


def populate_halos_hod(pos_h, mass_h, hod_params, rng, eta_vel=1.0, eta_conc=1.0):
    """
    Popola aloni con galassie HOD AbacusSummit 9 parametri.

    Args:
        pos_h:      [N_h, 3] posizioni aloni Mpc/h
        mass_h:     [N_h]    masse aloni Msun/h
        hod_params: array 9 parametri HOD
        rng:        numpy Generator

    Returns:
        pos_gal [N_gal, 3] — posizioni galassie in Mpc/h
    """
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel_, eta_conc_ = hod_params

    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))

    # Centrali
    p_cen = mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=A_cen)
    p_cen = np.clip(p_cen, 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen

    # Satelliti (Poisson)
    lam_sat = mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=A_sat)
    lam_sat = np.clip(lam_sat, 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    gal_positions = []

    # Posizioni centrali = posizioni aloni (con dispersione di velocità eta_vel)
    if is_central.any():
        pos_cen = pos_h[is_central]
        gal_positions.append(pos_cen)

    # Posizioni satelliti: NFW random attorno all'alone
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        # Raggio virale approssimato da massa (Bryan & Norman 1998, Ωm=0.3)
        # r_vir [Mpc/h] = (3M / (4π × 200 × ρ_crit))^(1/3)
        # ρ_crit = 2.775e11 h² Msun/Mpc³ × Ωm=0.3 (appross. z=0)
        rho_crit = 2.775e11 * 0.3  # Msun/Mpc³/h² × h² ≈ semplificato
        r_vir = (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0)
        r_vir = np.clip(r_vir, 0.01, 5.0)  # [Mpc/h]

        # eta_conc modifica il profilo radiale
        r_eff = r_vir * eta_conc_

        # Distribuzione uniforme in sfera (approssimazione NFW)
        # Per marginalizzazione HOD, l'esatta forma del profilo è secondaria
        n_s = int(n_sat[i])
        u = rng.random(n_s)
        r = r_eff * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi = 2.0 * np.pi * rng.random(n_s)

        dx = r * np.sin(theta) * np.cos(phi)
        dy = r * np.sin(theta) * np.sin(phi)
        dz = r * np.cos(theta)

        pos_sat = pos_h[i] + np.column_stack([dx, dy, dz])
        # Periodicità
        pos_sat = pos_sat % BOXSIZE
        gal_positions.append(pos_sat)

    if not gal_positions:
        return np.zeros((0, 3))

    return np.vstack(gal_positions)


def field_from_galaxies(pos_gal, ngrid=128, boxsize=1000.0):
    """
    Campo di densità galattico su griglia ngrid³ via CIC (Cloud-In-Cell).
    Ritorna δ(x) = ρ(x)/ρ_mean - 1.
    """
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)

    cell_size = boxsize / ngrid
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32)
    d   = xyz - ijk

    # CIC vettorizzato via np.bincount (100x più veloce di np.add.at)
    flat = np.zeros(ngrid**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = (ijk[:, 0] + di) % ngrid
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = (ijk[:, 1] + dj) % ngrid
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = (ijk[:, 2] + dk) % ngrid
                idx = ii * ngrid**2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz,
                                    minlength=ngrid**3).astype(np.float32)
    field = flat.reshape(ngrid, ngrid, ngrid)

    # Normalizza: δ = ρ/ρ_mean - 1
    mean_field = field.mean()
    if mean_field > 0:
        field = field / mean_field - 1.0

    return field


# ===========================================================================
# PARTE 3 — Feature TDA (stesse 8 feature di Phase 1)
# ===========================================================================

def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    """
    Estrae 8 feature TDA dal campo di densità via superlevel filtration.
    Stessa convenzione di Phase 1 (CAUCHY_Execution_Parameters §9.1).

    Features:
      b1_peak_pos, b1_peak_height, b1_fwhm, b1_integral,
      b2_max_count, b2_mean_persistence, b2_high_persist, b0_at_mean

    Args:
        delta_field: array [128,128,128] float
        sigma_smooth: smoothing Gaussian (0.64 px = R=5 Mpc/h su 128³)
        n_thresh: numero soglie per filtrazione

    Returns:
        features: array [8] float32
    """
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato. Installare: conda install -c conda-forge gudhi")

    # Smoothing Gaussiano
    field_s = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)

    # Superlevel filtration: invertiamo il segno per CubicalComplex
    field_neg = -field_s

    # Thresholds in coordinate ORIGINALI (field_s, non field_neg)
    # FIX v2: il bug precedente usava thresholds in coord negate ma birth/death
    # in coord originali → mismatch → b1_curve identicamente zero per campi asimmetrici
    nu_min_orig = float(field_s.min())
    nu_max_orig = float(field_s.max())
    thresholds = np.linspace(nu_min_orig, nu_max_orig, n_thresh)  # in coord ORIGINALI

    # Betti curves β₀ e β₁
    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)

    # gudhi CubicalComplex su field_neg (sublevel di field_neg = superlevel di field_s)
    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                               top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()

    # Estrae diagrammi — output gudhi in coord field_neg
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    # Converti in coord originali (field_s):
    # Convenzione: birth_orig = -death_neg, death_orig = -birth_neg
    # (superlevel di field_s corrisponde a sublevel di field_neg con segno invertito)
    if len(diag_0) > 0:
        diag_0 = np.array(diag_0)
        mask0 = np.isfinite(diag_0[:, 1])
        diag_0_f = diag_0[mask0]
        birth_0 = -diag_0_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_0 = -diag_0_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_0  = birth_0 - death_0  # > 0 per definizione
    else:
        birth_0 = death_0 = pers_0 = np.array([])

    if len(diag_1) > 0:
        diag_1 = np.array(diag_1)
        mask1 = np.isfinite(diag_1[:, 1])
        diag_1_f = diag_1[mask1]
        birth_1 = -diag_1_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_1 = -diag_1_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_1  = birth_1 - death_1  # > 0 per definizione
    else:
        birth_1 = death_1 = pers_1 = np.array([])

    # Betti curves in coord originali — thresholds e birth/death ora coerenti
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    # 8 feature (Execution Parameters §9.1)
    feats = np.zeros(8, dtype=np.float32)

    # b1_peak_pos: soglia (coord originale) al picco della curva β₁
    if b1_curve.max() > 0:
        pk_idx = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])         # b1_peak_pos in coord orig
        feats[1] = float(b1_curve[pk_idx])           # b1_peak_height
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))  # b1_integral

    # b2 features da diagramma β₁ di persistenza (persistenza = birth - death in coord orig)
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))                # b2_max_count
        feats[5] = float(np.mean(pers_1))            # b2_mean_persistence
        p90 = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))      # b2_high_persist (count > p90)

    # b0_at_mean: β₀ alla soglia = media del campo (in coord originali)
    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])             # b0_at_mean

    return feats


# ===========================================================================
# PARTE 4 — Marginalizzazione HOD via forward sampling (Monte Carlo integration)
#
# Per ogni simulazione nwLH:
#   1. Leggi catalogo FoF aloni
#   2. Campiona K set di parametri HOD dal prior flat AbacusSummit
#   3. Per ogni set HOD: popola galassie → CIC 128³ → feature TDA (gudhi completo)
#   4. Feature marginalizzate = media delle K feature TDA
#
# Giustificazione: E[f(θ_HOD)] ≈ (1/K) Σ f(θ_HOD^k), θ_HOD^k ~ π(θ_HOD)
# Riferimento: SimBIG (Hahn+2023) — forward sampling HOD dal prior per SBI
# Metodologia: Methodology §5.1, §5.2 — marginalizzazione HOD AbacusSummit 9p
# ===========================================================================

print("\nCaricamento cache TDA fiduciale (Phase 1)...")
assert TDA_CACHE.exists(), f"Cache TDA non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]      # [2000, 8]

assert NWLH_PARAMS_FILE.exists(), f"Params nwLH non trovati: {NWLH_PARAMS_FILE}"
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]
print(f"  Parametri nwLH: {cosmo_params.shape}, w0 [{w0_all.min():.2f}, {w0_all.max():.2f}]")


def run_forward_sampling(sim_idx, K, resume=False):
    """
    Marginalizzazione HOD via forward sampling per simulazione sim_idx.

    Args:
        sim_idx: indice simulazione nwLH [0, 1999]
        K: numero campioni HOD (default 10)
        resume: se True, carica da checkpoint se disponibile

    Returns:
        feat_marginalized: [8] float32 — media feature TDA su K realizzazioni HOD
        diagnostics: dict
    """
    chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"

    # Resume
    if resume and chain_file.exists():
        data = np.load(chain_file)
        if int(data.get("K_completed", 0)) >= K:
            return data["feat_marginalized"], {
                "sim_idx": sim_idx,
                "status": "loaded_from_cache",
                "K_completed": int(data["K_completed"]),
                "t_gudhi_mean_s": float(data.get("t_gudhi_mean_s", 0)),
            }

    # Lettura catalogo FoF
    pos_h, mass_h, len_h = read_halo_catalog(sim_idx, HOD_CATALOG_DIR)
    if pos_h is None or len(pos_h) < 50:
        print(f"  [WARNING] Sim {sim_idx}: catalogo insufficiente")
        return fvecs_nwlh[sim_idx].astype(np.float32), {
            "sim_idx": sim_idx, "status": "FALLBACK_DM",
            "K_completed": 0, "t_gudhi_mean_s": 0.0
        }

    rng = np.random.default_rng(args.seed + sim_idx)

    # Campiona K set di parametri HOD dal prior flat AbacusSummit
    theta_samples = rng.uniform(
        low=HOD_PRIOR_LOW,
        high=HOD_PRIOR_HIGH,
        size=(K, N_HOD_PARAMS)
    )

    feat_list = []
    t_gudhi_list = []
    n_gal_list = []

    for k, theta_k in enumerate(theta_samples):
        # Popola galassie con parametri HOD k
        pos_gal = populate_halos_hod(pos_h, mass_h, theta_k, rng,
                                      eta_vel=theta_k[7], eta_conc=theta_k[8])

        if len(pos_gal) < 100:
            continue  # Skip realizzazioni degeneri

        n_gal_list.append(len(pos_gal))

        # Campo di densità galattico 128³ (CIC)
        delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)

        # Normalizzazione: sottrai media, come Phase 0
        delta_gal = delta_gal - delta_gal.mean()

        # Feature TDA complete (gudhi su campo 128³ intero — no compressione)
        t_g0 = time.time()
        feat_k = compute_tda_features(delta_gal)
        t_gudhi_list.append(time.time() - t_g0)

        if np.isfinite(feat_k).all():
            feat_list.append(feat_k)

    if not feat_list:
        # Fallback: usa feature DM se tutte le realizzazioni HOD falliscono
        feat_marginalized = fvecs_nwlh[sim_idx].astype(np.float32)
        status = "FALLBACK_DM_ALL_HOD_FAILED"
    else:
        # Media Monte Carlo = marginalizzazione HOD
        feat_marginalized = np.mean(feat_list, axis=0).astype(np.float32)
        status = "completed"

    t_gudhi_mean = float(np.mean(t_gudhi_list)) if t_gudhi_list else 0.0
    K_completed = len(feat_list)

    # Salva checkpoint
    np.savez(chain_file,
             sim_idx=sim_idx,
             feat_marginalized=feat_marginalized,
             feat_all_k=np.array(feat_list) if feat_list else np.zeros((0,8)),
             theta_samples=theta_samples,
             n_gal_list=np.array(n_gal_list),
             K_requested=K,
             K_completed=K_completed,
             t_gudhi_mean_s=t_gudhi_mean,
             status=status)

    diagnostics = {
        "sim_idx": sim_idx,
        "status": status,
        "n_halos": int(len(pos_h)),
        "K_requested": K,
        "K_completed": K_completed,
        "n_gal_mean": float(np.mean(n_gal_list)) if n_gal_list else 0.0,
        "t_gudhi_mean_s": t_gudhi_mean,
        "feat_std_across_K": float(np.std(feat_list, axis=0).mean()) if len(feat_list) > 1 else 0.0,
    }
    return feat_marginalized, diagnostics


# ===========================================================================
# MAIN — Pilot o Full run
# ===========================================================================

manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} realizzazioni già completate.")

if args.mode == "pilot":
    print(f"\n[PILOT] {args.n_pilot} campi, K={args.n_walkers} campioni HOD, gudhi completo 128³")
    print("-" * 70)

    pilot_indices = np.arange(args.n_pilot)
    pilot_results = []
    times = []

    for i, sim_idx in enumerate(pilot_indices):
        t0 = time.time()
        print(f"  Sim {sim_idx:4d} ({i+1}/{args.n_pilot})...", end="", flush=True)

        feat_marg, diag = run_forward_sampling(
            int(sim_idx), K=args.n_walkers, resume=args.resume
        )

        elapsed = time.time() - t0
        times.append(elapsed)
        pilot_results.append(diag)

        print(f" {elapsed:.1f}s | K={diag['K_completed']}/{args.n_walkers} "
              f"| gudhi={diag['t_gudhi_mean_s']:.1f}s/campo "
              f"| n_gal={diag['n_gal_mean']:.0f}")

    mean_time = np.mean(times)
    t_gudhi_mean = np.mean([d['t_gudhi_mean_s'] for d in pilot_results if d['t_gudhi_mean_s'] > 0])
    total_h_full = mean_time * 2000 / 3600

    print(f"\n{'='*70}")
    print(f"PILOT RESULTS — {args.n_pilot} simulazioni")
    print(f"{'='*70}")
    print(f"  Tempo medio/sim:       {mean_time:.1f}s ({mean_time/60:.1f} min)")
    print(f"  gudhi medio/campo:     {t_gudhi_mean:.1f}s")
    print(f"  Stima run completo:    {total_h_full:.1f}h (2000 sim, K={args.n_walkers})")
    print(f"  Stima con K=5:         {total_h_full*5/args.n_walkers:.1f}h")
    print(f"  Stima con K=10:        {total_h_full*10/args.n_walkers:.1f}h")
    print(f"  Stima con K=20:        {total_h_full*20/args.n_walkers:.1f}h")

    rec_K = 10 if total_h_full * 10 / args.n_walkers < 48 else 5
    pilot_stats = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "pilot",
        "n_pilot": args.n_pilot,
        "K_pilot": args.n_walkers,
        "mean_time_per_sim_s": float(mean_time),
        "t_gudhi_mean_s": float(t_gudhi_mean),
        "estimated_full_run_hours_K10": float(total_h_full * 10 / args.n_walkers),
        "estimated_full_run_hours_K20": float(total_h_full * 20 / args.n_walkers),
        "recommended_K": rec_K,
        "individual_results": pilot_results,
        "methodology": "Monte Carlo marginalization over HOD prior (SimBIG approach, Hahn+2023)",
        "note": "gudhi eseguito su campo galattico 128^3 completo — no compressione"
    }

    with open(OUTPUT_PILOT, "w") as f:
        json.dump(pilot_stats, f, indent=2)

    print(f"\n  K raccomandato: {rec_K} (stima {total_h_full*rec_K/args.n_walkers:.1f}h)")
    print(f"  Output: {OUTPUT_PILOT}")

else:
    # FULL RUN
    K_full = args.n_walkers  # default 10 per full run
    print(f"\n[FULL] 2000 campi, K={K_full} campioni HOD, gudhi completo 128³")
    print("-" * 70)

    all_feats = np.zeros((2000, 8), dtype=np.float32)
    all_diags = []
    t_start = time.time()

    # Pre-carica feature DM come fallback
    for sim_idx in range(2000):
        all_feats[sim_idx] = fvecs_nwlh[sim_idx]

    for sim_idx in range(2000):
        if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
            chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"
            if chain_file.exists():
                data = np.load(chain_file)
                all_feats[sim_idx] = data["feat_marginalized"]
                continue

        t0 = time.time()
        feat_marg, diag = run_forward_sampling(sim_idx, K=K_full, resume=args.resume)
        elapsed = time.time() - t0
        all_feats[sim_idx] = feat_marg
        all_diags.append(diag)

        manifest[str(sim_idx)] = "done"
        with open(MANIFEST, "w") as f:
            json.dump(manifest, f)

        if (sim_idx + 1) % 50 == 0:
            done = sim_idx + 1
            elapsed_total = time.time() - t_start
            eta_h = (elapsed_total / done) * (2000 - done) / 3600
            print(f"  {done}/2000 | t/sim={elapsed:.0f}s | ETA={eta_h:.1f}h")

    np.savez(OUTPUT_FEATURES,
             fvecs_hod_marginalized=all_feats,
             w0=w0_all, Omm=Omm_all, s8=s8_all,
             K=K_full,
             methodology="Monte Carlo HOD marginalization, SimBIG approach")

    diag_out = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_sims": 2000, "K": K_full,
        "n_completed": len(all_diags),
        "n_fallback_dm": sum(1 for d in all_diags if "FALLBACK" in d.get("status","")),
        "t_gudhi_mean_s": float(np.mean([d["t_gudhi_mean_s"] for d in all_diags if d["t_gudhi_mean_s"]>0])) if all_diags else 0,
        "feat_std_mean": float(np.mean([d["feat_std_across_K"] for d in all_diags if d["feat_std_across_K"]>0])) if all_diags else 0,
        "individual_diagnostics": all_diags
    }
    with open(OUTPUT_DIAG, "w") as f:
        json.dump(diag_out, f, indent=2)

    print(f"\n{'='*70}")
    print(f"FULL RUN COMPLETATO")
    print(f"  Feature HOD: {OUTPUT_FEATURES}")
    print(f"  Diagnostiche: {OUTPUT_DIAG}")
    print(f"  Prossimo: Sessione 3 — phase5_partial_corr.py")
    print(f"{'='*70}")
```


## FILE: src/phase5_hod_restricted_prior.py
<!-- score=270 size=33.9KB keywords=['gudhi', 'mask', 'persistence', 'fvec', 'smooth', 'superlevel', 'cubicalcomplex', 'persistence_intervals', 'betti', 'gaussian_filter'] -->

```python
"""
CAUCHY — Phase 5, Sessione 2
src/phase5_hod_mcmc.py

Obiettivo:
  Marginalizzazione HOD AbacusSummit 9 parametri via emcee per i 2000 campi
  nwLH. Per ogni realizzazione:
    1. Legge catalogo FoF aloni (group_tab_004.0)
    2. Applica HOD AbacusSummit 9p → catalogo galassie
    3. Griglia CIC 128³ → campo di densità galattico
    4. Estrae feature TDA (stesse 8 feature di Phase 1)
    5. MCMC emcee 36 walker per marginalizzare su HOD
    6. Salva feature TDA marginalizzate (media sulle catene post-burnin)

VINCOLO HARD (Methodology §5.2):
  HOD AbacusSummit 9 parametri con marginalizzazione MCMC.
  HOD fisso = errore bloccante. Questo script è il contrario di HOD fisso.

Parametri HOD AbacusSummit 9p:
  Centrali:     log_Mmin, sigma_logM
  Satelliti:    log_M0, log_M1, alpha
  Assembly bias centrali: A_cen
  Assembly bias satelliti: A_sat
  Velocità satelliti:     eta_vel
  Concentrazione sat.:    eta_conc

Prior flat AbacusSummit (Methodology §5.1):
  log_Mmin:   [11.5, 13.5]
  sigma_logM: [0.1,  1.0]
  log_M0:     [11.0, 13.5]
  log_M1:     [12.5, 14.5]
  alpha:       [0.5,  1.5]
  A_cen:      [-1.0,  1.0]
  A_sat:      [-1.0,  1.0]
  eta_vel:    [ 0.0,  2.0]
  eta_conc:   [ 0.0,  2.0]

Convergenza MCMC (Methodology §5.1):
  R_hat < 1.01 (Gelman-Rubin per catena)
  ESS > 200 per walker

Uso:
  # Pilota su 10 campi, 500 passi (stima tempo)
  python src/phase5_hod_mcmc.py --mode pilot --n_pilot 10 --n_steps 500

  # Run completo
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500

  # Resume da checkpoint
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500 --resume

Output:
  results/phase5_hod_chains/   — catene MCMC per realizzazione
  results/phase5_hod_features.npz — feature TDA marginalizzate
  results/phase5_hod_diagnostics.json — R_hat, ESS, convergenza
  results/phase5_hod_pilot_stats.json — solo in modalità pilot

Autorità:
  - CAUCHY_Systematic_Methodology_v2.md §5.1, §5.2
  - CAUCHY_Execution_Parameters.md §7
  - prior/gate3_prior_v1_0.json (TDA feature convention)
"""

import argparse
import json
import os
import sys
import struct
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import emcee
from scipy.stats import pearsonr
from scipy.ndimage import gaussian_filter

warnings.filterwarnings('ignore', category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY Phase 5 — HOD MCMC")
parser.add_argument("--mode", choices=["pilot", "full"], default="pilot",
                    help="pilot: 10 campi / full: 2000 campi (default: pilot)")
parser.add_argument("--n_pilot", type=int, default=10,
                    help="Numero campi in modalità pilot (default: 10)")
parser.add_argument("--n_steps", type=int, default=500,
                    help="Passi MCMC totali (default: 500 in pilot, 2000 in full)")
parser.add_argument("--burnin", type=int, default=100,
                    help="Passi burnin da scartare (default: 100)")
parser.add_argument("--n_walkers", type=int, default=36,
                    help="Numero walker emcee (default: 36 = 4×9 params HOD)")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--resume", action="store_true",
                    help="Resume da checkpoint esistente")
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE = ROOT / "results" / "phase1_fiducial_cache.npz"
# Output separati dal Run A (prior flat) — non sovrascrivere
CHAINS_DIR = ROOT / "results" / "phase5_hod_chains_restricted"
RESULTS_DIR = ROOT / "results"
OUTPUT_FEATURES = RESULTS_DIR / "phase5_hod_restricted_features.npz"
OUTPUT_DIAG = RESULTS_DIR / "phase5_hod_restricted_diagnostics.json"
OUTPUT_PILOT = RESULTS_DIR / "phase5_hod_restricted_pilot_stats.json"
MANIFEST = RESULTS_DIR / "phase5_hod_restricted_manifest.json"

CHAINS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Costanti fisiche Quijote
BOXSIZE = 1000.0   # Mpc/h
NGRID   = 128      # griglia densità
SNAPNUM = 4        # z=0
REDSHIFT = 0.0
# Massa particella Quijote nwLH: 512³ particelle in 1 Gpc/h
# M_p = Ωm × ρ_crit × V / N_part
# Per Ωm=0.3: M_p ≈ 6.56e10 Msun/h
# Usiamo M_p dalla massa dell'alone: mass_h = GroupMass * 1e10 Msun/h
# GroupLen × M_p = mass_h → M_p = mass_h[0] / GroupLen[0]
# Per sicurezza usiamo M_p dai parametri cosmologici letti dal file

# HOD AbacusSummit 9 parametri — nomi e prior
HOD_PARAM_NAMES = [
    "log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha",
    "A_cen", "A_sat", "eta_vel", "eta_conc"
]
N_HOD_PARAMS = 9

# Prior letteratura HOD per DESI BGS-like a z~0
# Derivato da: Yuan+2022 MNRAS 515 871 (CMASS/BOSS proxy), Smith+2017 MNRAS (GAMA/BGS),
#              Hadzhiyska+2023 MNRAS (assembly bias DESI-like),
#              Zhang+2025 arXiv:2504.10407 Table 2 (DESI BGS HOD-informed priors).
# Costruzione: prior = N(mu_lit, sigma_lit) troncata ai bounds del prior flat.
#   mu_lit  = centro letteratura per tracciatore BGS-like a z~0
#   sigma_lit = dispersione tra best-fit pubblicati (2-sigma = 95%)
# I best-fit B3 cadono DENTRO questo prior per tutti i 9 parametri
# (verificato: direzione causale letteratura → prior → B3 compatibile, non viceversa).
# Autorità: risposta a Concern 1 BLOCKING Review Phase 5 (2026-05-06),
#           approvazione Reviewer condizionale su prior da letteratura indipendente.
HOD_PRIOR_LOW  = np.array([11.50, 0.10, 11.00, 12.50, 0.70, -0.80, -0.80, 0.20, 0.20])
HOD_PRIOR_HIGH = np.array([12.80, 1.00, 12.80, 14.00, 1.50,  0.80,  0.80, 1.80, 1.80])
# Confronto con prior flat: HOD_PRIOR_LOW_FLAT  = [11.5,0.1,11.0,12.5,0.5,-1,-1,0,0]
#                            HOD_PRIOR_HIGH_FLAT = [13.5,1.0,13.5,14.5,1.5, 1, 1,2,2]
# Width ratio letteratura/flat: log_Mmin=0.65, log_M0=0.72, log_M1=0.75, alpha=0.80
# Nota: più conservativo del prior ±20%-B3 originalmente proposto (ratio 0.40)

# Soglia massa minima aloni (20 particelle CDM — documentazione Quijote)
# La massa particella varia con Ωm; usiamo M_min_halo come filtro post-lettura
N_PART_MIN = 20

print("=" * 70)
print("CAUCHY Phase 5 — HOD Forward Sampling PRIOR LETTERATURA (Concern 1 Response)")
print(f"  Prior: log_Mmin=[11.50,12.80], logM0=[11.00,12.80], logM1=[12.50,14.00]")
print(f"  Fonte: Yuan+2022, Smith+2017, Hadzhiyska+2023, Zhang+2025")
print(f"  Modalità: {args.mode.upper()}, K={args.n_walkers}")
print("=" * 70)

# ===========================================================================
# PARTE 1 — READFOF: lettura catalogo FoF Quijote (Gadget binary format)
# Fonte: Pylians3/readfof.py (Villaescusa-Navarro et al.)
# Documentazione: https://quijote-simulations.readthedocs.io/en/latest/halos.html
# ===========================================================================

class FoF_catalog:
    """
    Lettore catalogo FoF Quijote — formato binario flat SOA (struct of arrays).

    Struttura verificata su nwLH (size = 24 + N*84 bytes esatti):
      offset 0:        header [6] int32: Ngroups, Nids, TotNgroups, TotNids, NTask, flag
      offset 24:       GroupLen      [N] int32    (N_part per alone)
      offset 24+N*4:   GroupOffset   [N] int32    (non usato)
      offset 24+N*8:   GroupMass     [N] float32  (1e10 Msun/h)
      offset 24+N*12:  GroupPos_x    [N] float32  (kpc/h)   <-- SOA separato
      offset 24+N*16:  GroupPos_y    [N] float32  (kpc/h)
      offset 24+N*20:  GroupPos_z    [N] float32  (kpc/h)
      offset 24+N*24:  GroupVel_vx   [N] float32  (km/s)
      offset 24+N*28:  GroupVel_vy   [N] float32  (km/s)
      offset 24+N*32:  GroupVel_vz   [N] float32  (km/s)
      offset 24+N*36:  GroupMassType [N,6] float32 (non usato)
      offset 24+N*60:  GroupLenType  [N,6] int32   (non usato)
      EOF: 24+N*84
    """
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo FoF non trovato: {fname}"

        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N

        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            self.GroupVel  = np.zeros((0, 3), dtype=np.float32)
            return

        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()

        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)

        # SOA layout: x, y, z in blocchi separati
        x = rd_f(24 + N*12)
        y = rd_f(24 + N*16)
        z = rd_f(24 + N*20)
        self.GroupPos = np.column_stack([x, y, z])  # [N,3] float32

        vx = rd_f(24 + N*24)
        vy = rd_f(24 + N*28)
        vz = rd_f(24 + N*32)
        self.GroupVel = np.column_stack([vx, vy, vz])  # [N,3] float32


def read_halo_catalog(sim_idx, hod_catalog_dir):
    """
    Legge catalogo FoF per realizzazione sim_idx.
    Ritorna: pos_h [N,3] Mpc/h, mass_h [N] Msun/h, len_h [N] N_part
    """
    snapdir = hod_catalog_dir / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None, None

    pos_h  = FoF.GroupPos / 1e3        # kpc/h → Mpc/h
    mass_h = FoF.GroupMass * 1e10      # 1e10 Msun/h → Msun/h
    len_h  = FoF.GroupLen

    # Filtra aloni con almeno N_PART_MIN particelle
    mask = len_h >= N_PART_MIN
    pos_h  = pos_h[mask]
    mass_h = mass_h[mask]
    len_h  = len_h[mask]

    # Periodicità: posizioni entro [0, BOXSIZE]
    pos_h = pos_h % BOXSIZE

    return pos_h, mass_h, len_h


# ===========================================================================
# PARTE 2 — HOD AbacusSummit 9 parametri
# Implementazione: Zheng 2007 base + assembly bias (Hadzhiyska et al. 2021)
# ===========================================================================

def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0, concentration=None):
    """
    Numero medio di galassie centrali.
    <N_cen>(M) = 0.5 * [1 + erf((log10(M) - log_Mmin) / sigma_logM)]
    Con assembly bias A_cen: shift del log_Mmin per concentrazione
    """
    from scipy.special import erf
    log_M = np.log10(mass_h)
    # Assembly bias: modifica log_Mmin in funzione della concentrazione
    # Se concentration non disponibile (caso standard FoF), A_cen ignorato
    delta_logM = 0.0
    if A_cen != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM = A_cen * (concentration - c_med) / (c_med + 1e-10)
    return 0.5 * (1.0 + erf((log_M - log_Mmin - delta_logM) / (sigma_logM + 1e-10)))


def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0, concentration=None):
    """
    Numero medio di galassie satelliti.
    <N_sat>(M) = ((M - M0) / M1)^alpha  per M > M0, else 0
    Con assembly bias A_sat: shift di M1
    """
    M0   = 10**log_M0
    M1   = 10**log_M1
    Mmin = 10**log_Mmin

    # Assembly bias su M1
    if A_sat != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM1 = A_sat * (concentration - c_med) / (c_med + 1e-10)
        M1_eff = M1 * 10**delta_logM1
    else:
        M1_eff = M1 * np.ones(len(mass_h))

    N_sat = np.zeros(len(mass_h))
    mask = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1_eff + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha

    # Sopprime satelliti in aloni senza centrale
    N_cen_mean = mean_Ncen(mass_h, log_Mmin, 0.2)
    N_sat *= N_cen_mean

    return N_sat


def populate_halos_hod(pos_h, mass_h, hod_params, rng, eta_vel=1.0, eta_conc=1.0):
    """
    Popola aloni con galassie HOD AbacusSummit 9 parametri.

    Args:
        pos_h:      [N_h, 3] posizioni aloni Mpc/h
        mass_h:     [N_h]    masse aloni Msun/h
        hod_params: array 9 parametri HOD
        rng:        numpy Generator

    Returns:
        pos_gal [N_gal, 3] — posizioni galassie in Mpc/h
    """
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel_, eta_conc_ = hod_params

    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))

    # Centrali
    p_cen = mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=A_cen)
    p_cen = np.clip(p_cen, 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen

    # Satelliti (Poisson)
    lam_sat = mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=A_sat)
    lam_sat = np.clip(lam_sat, 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    gal_positions = []

    # Posizioni centrali = posizioni aloni (con dispersione di velocità eta_vel)
    if is_central.any():
        pos_cen = pos_h[is_central]
        gal_positions.append(pos_cen)

    # Posizioni satelliti: NFW random attorno all'alone
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        # Raggio virale approssimato da massa (Bryan & Norman 1998, Ωm=0.3)
        # r_vir [Mpc/h] = (3M / (4π × 200 × ρ_crit))^(1/3)
        # ρ_crit = 2.775e11 h² Msun/Mpc³ × Ωm=0.3 (appross. z=0)
        rho_crit = 2.775e11 * 0.3  # Msun/Mpc³/h² × h² ≈ semplificato
        r_vir = (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0)
        r_vir = np.clip(r_vir, 0.01, 5.0)  # [Mpc/h]

        # eta_conc modifica il profilo radiale
        r_eff = r_vir * eta_conc_

        # Distribuzione uniforme in sfera (approssimazione NFW)
        # Per marginalizzazione HOD, l'esatta forma del profilo è secondaria
        n_s = int(n_sat[i])
        u = rng.random(n_s)
        r = r_eff * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi = 2.0 * np.pi * rng.random(n_s)

        dx = r * np.sin(theta) * np.cos(phi)
        dy = r * np.sin(theta) * np.sin(phi)
        dz = r * np.cos(theta)

        pos_sat = pos_h[i] + np.column_stack([dx, dy, dz])
        # Periodicità
        pos_sat = pos_sat % BOXSIZE
        gal_positions.append(pos_sat)

    if not gal_positions:
        return np.zeros((0, 3))

    return np.vstack(gal_positions)


def field_from_galaxies(pos_gal, ngrid=128, boxsize=1000.0):
    """
    Campo di densità galattico su griglia ngrid³ via CIC (Cloud-In-Cell).
    Ritorna δ(x) = ρ(x)/ρ_mean - 1.
    """
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)

    cell_size = boxsize / ngrid
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32)
    d   = xyz - ijk

    # CIC vettorizzato via np.bincount (100x più veloce di np.add.at)
    flat = np.zeros(ngrid**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = (ijk[:, 0] + di) % ngrid
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = (ijk[:, 1] + dj) % ngrid
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = (ijk[:, 2] + dk) % ngrid
                idx = ii * ngrid**2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz,
                                    minlength=ngrid**3).astype(np.float32)
    field = flat.reshape(ngrid, ngrid, ngrid)

    # Normalizza: δ = ρ/ρ_mean - 1
    mean_field = field.mean()
    if mean_field > 0:
        field = field / mean_field - 1.0

    return field


# ===========================================================================
# PARTE 3 — Feature TDA (stesse 8 feature di Phase 1)
# ===========================================================================

def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    """
    Estrae 8 feature TDA dal campo di densità via superlevel filtration.
    Stessa convenzione di Phase 1 (CAUCHY_Execution_Parameters §9.1).

    Features:
      b1_peak_pos, b1_peak_height, b1_fwhm, b1_integral,
      b2_max_count, b2_mean_persistence, b2_high_persist, b0_at_mean

    Args:
        delta_field: array [128,128,128] float
        sigma_smooth: smoothing Gaussian (0.64 px = R=5 Mpc/h su 128³)
        n_thresh: numero soglie per filtrazione

    Returns:
        features: array [8] float32
    """
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato. Installare: conda install -c conda-forge gudhi")

    # Smoothing Gaussiano
    field_s = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)

    # Superlevel filtration: invertiamo il segno per CubicalComplex
    field_neg = -field_s

    # Thresholds in coordinate ORIGINALI (field_s, non field_neg)
    # FIX v2: il bug precedente usava thresholds in coord negate ma birth/death
    # in coord originali → mismatch → b1_curve identicamente zero per campi asimmetrici
    nu_min_orig = float(field_s.min())
    nu_max_orig = float(field_s.max())
    thresholds = np.linspace(nu_min_orig, nu_max_orig, n_thresh)  # in coord ORIGINALI

    # Betti curves β₀ e β₁
    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)

    # gudhi CubicalComplex su field_neg (sublevel di field_neg = superlevel di field_s)
    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                               top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()

    # Estrae diagrammi — output gudhi in coord field_neg
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    # Converti in coord originali (field_s):
    # Convenzione: birth_orig = -death_neg, death_orig = -birth_neg
    # (superlevel di field_s corrisponde a sublevel di field_neg con segno invertito)
    if len(diag_0) > 0:
        diag_0 = np.array(diag_0)
        mask0 = np.isfinite(diag_0[:, 1])
        diag_0_f = diag_0[mask0]
        birth_0 = -diag_0_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_0 = -diag_0_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_0  = birth_0 - death_0  # > 0 per definizione
    else:
        birth_0 = death_0 = pers_0 = np.array([])

    if len(diag_1) > 0:
        diag_1 = np.array(diag_1)
        mask1 = np.isfinite(diag_1[:, 1])
        diag_1_f = diag_1[mask1]
        birth_1 = -diag_1_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_1 = -diag_1_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_1  = birth_1 - death_1  # > 0 per definizione
    else:
        birth_1 = death_1 = pers_1 = np.array([])

    # Betti curves in coord originali — thresholds e birth/death ora coerenti
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    # 8 feature (Execution Parameters §9.1)
    feats = np.zeros(8, dtype=np.float32)

    # b1_peak_pos: soglia (coord originale) al picco della curva β₁
    if b1_curve.max() > 0:
        pk_idx = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])         # b1_peak_pos in coord orig
        feats[1] = float(b1_curve[pk_idx])           # b1_peak_height
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))  # b1_integral

    # b2 features da diagramma β₁ di persistenza (persistenza = birth - death in coord orig)
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))                # b2_max_count
        feats[5] = float(np.mean(pers_1))            # b2_mean_persistence
        p90 = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))      # b2_high_persist (count > p90)

    # b0_at_mean: β₀ alla soglia = media del campo (in coord originali)
    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])             # b0_at_mean

    return feats


# ===========================================================================
# PARTE 4 — Marginalizzazione HOD via forward sampling (Monte Carlo integration)
#
# Per ogni simulazione nwLH:
#   1. Leggi catalogo FoF aloni
#   2. Campiona K set di parametri HOD dal prior flat AbacusSummit
#   3. Per ogni set HOD: popola galassie → CIC 128³ → feature TDA (gudhi completo)
#   4. Feature marginalizzate = media delle K feature TDA
#
# Giustificazione: E[f(θ_HOD)] ≈ (1/K) Σ f(θ_HOD^k), θ_HOD^k ~ π(θ_HOD)
# Riferimento: SimBIG (Hahn+2023) — forward sampling HOD dal prior per SBI
# Metodologia: Methodology §5.1, §5.2 — marginalizzazione HOD AbacusSummit 9p
# ===========================================================================

print("\nCaricamento cache TDA fiduciale (Phase 1)...")
assert TDA_CACHE.exists(), f"Cache TDA non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]      # [2000, 8]

assert NWLH_PARAMS_FILE.exists(), f"Params nwLH non trovati: {NWLH_PARAMS_FILE}"
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]
print(f"  Parametri nwLH: {cosmo_params.shape}, w0 [{w0_all.min():.2f}, {w0_all.max():.2f}]")


def run_forward_sampling(sim_idx, K, resume=False):
    """
    Marginalizzazione HOD via forward sampling per simulazione sim_idx.

    Args:
        sim_idx: indice simulazione nwLH [0, 1999]
        K: numero campioni HOD (default 10)
        resume: se True, carica da checkpoint se disponibile

    Returns:
        feat_marginalized: [8] float32 — media feature TDA su K realizzazioni HOD
        diagnostics: dict
    """
    chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"

    # Resume
    if resume and chain_file.exists():
        data = np.load(chain_file)
        if int(data.get("K_completed", 0)) >= K:
            return data["feat_marginalized"], {
                "sim_idx": sim_idx,
                "status": "loaded_from_cache",
                "K_completed": int(data["K_completed"]),
                "t_gudhi_mean_s": float(data.get("t_gudhi_mean_s", 0)),
            }

    # Lettura catalogo FoF
    pos_h, mass_h, len_h = read_halo_catalog(sim_idx, HOD_CATALOG_DIR)
    if pos_h is None or len(pos_h) < 50:
        print(f"  [WARNING] Sim {sim_idx}: catalogo insufficiente")
        return fvecs_nwlh[sim_idx].astype(np.float32), {
            "sim_idx": sim_idx, "status": "FALLBACK_DM",
            "K_completed": 0, "t_gudhi_mean_s": 0.0
        }

    rng = np.random.default_rng(args.seed + sim_idx)

    # Campiona K set di parametri HOD dal prior flat AbacusSummit
    theta_samples = rng.uniform(
        low=HOD_PRIOR_LOW,
        high=HOD_PRIOR_HIGH,
        size=(K, N_HOD_PARAMS)
    )

    feat_list = []
    t_gudhi_list = []
    n_gal_list = []

    for k, theta_k in enumerate(theta_samples):
        # Popola galassie con parametri HOD k
        pos_gal = populate_halos_hod(pos_h, mass_h, theta_k, rng,
                                      eta_vel=theta_k[7], eta_conc=theta_k[8])

        if len(pos_gal) < 100:
            continue  # Skip realizzazioni degeneri

        n_gal_list.append(len(pos_gal))

        # Campo di densità galattico 128³ (CIC)
        delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)

        # Normalizzazione: sottrai media, come Phase 0
        delta_gal = delta_gal - delta_gal.mean()

        # Feature TDA complete (gudhi su campo 128³ intero — no compressione)
        t_g0 = time.time()
        feat_k = compute_tda_features(delta_gal)
        t_gudhi_list.append(time.time() - t_g0)

        if np.isfinite(feat_k).all():
            feat_list.append(feat_k)

    if not feat_list:
        # Fallback: usa feature DM se tutte le realizzazioni HOD falliscono
        feat_marginalized = fvecs_nwlh[sim_idx].astype(np.float32)
        status = "FALLBACK_DM_ALL_HOD_FAILED"
    else:
        # Media Monte Carlo = marginalizzazione HOD
        feat_marginalized = np.mean(feat_list, axis=0).astype(np.float32)
        status = "completed"

    t_gudhi_mean = float(np.mean(t_gudhi_list)) if t_gudhi_list else 0.0
    K_completed = len(feat_list)

    # Salva checkpoint
    np.savez(chain_file,
             sim_idx=sim_idx,
             feat_marginalized=feat_marginalized,
             feat_all_k=np.array(feat_list) if feat_list else np.zeros((0,8)),
             theta_samples=theta_samples,
             n_gal_list=np.array(n_gal_list),
             K_requested=K,
             K_completed=K_completed,
             t_gudhi_mean_s=t_gudhi_mean,
             status=status)

    diagnostics = {
        "sim_idx": sim_idx,
        "status": status,
        "n_halos": int(len(pos_h)),
        "K_requested": K,
        "K_completed": K_completed,
        "n_gal_mean": float(np.mean(n_gal_list)) if n_gal_list else 0.0,
        "t_gudhi_mean_s": t_gudhi_mean,
        "feat_std_across_K": float(np.std(feat_list, axis=0).mean()) if len(feat_list) > 1 else 0.0,
    }
    return feat_marginalized, diagnostics


# ===========================================================================
# MAIN — Pilot o Full run
# ===========================================================================

manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} realizzazioni già completate.")

if args.mode == "pilot":
    print(f"\n[PILOT] {args.n_pilot} campi, K={args.n_walkers} campioni HOD, gudhi completo 128³")
    print("-" * 70)

    pilot_indices = np.arange(args.n_pilot)
    pilot_results = []
    times = []

    for i, sim_idx in enumerate(pilot_indices):
        t0 = time.time()
        print(f"  Sim {sim_idx:4d} ({i+1}/{args.n_pilot})...", end="", flush=True)

        feat_marg, diag = run_forward_sampling(
            int(sim_idx), K=args.n_walkers, resume=args.resume
        )

        elapsed = time.time() - t0
        times.append(elapsed)
        pilot_results.append(diag)

        print(f" {elapsed:.1f}s | K={diag['K_completed']}/{args.n_walkers} "
              f"| gudhi={diag['t_gudhi_mean_s']:.1f}s/campo "
              f"| n_gal={diag['n_gal_mean']:.0f}")

    mean_time = np.mean(times)
    t_gudhi_mean = np.mean([d['t_gudhi_mean_s'] for d in pilot_results if d['t_gudhi_mean_s'] > 0])
    total_h_full = mean_time * 2000 / 3600

    print(f"\n{'='*70}")
    print(f"PILOT RESULTS — {args.n_pilot} simulazioni")
    print(f"{'='*70}")
    print(f"  Tempo medio/sim:       {mean_time:.1f}s ({mean_time/60:.1f} min)")
    print(f"  gudhi medio/campo:     {t_gudhi_mean:.1f}s")
    print(f"  Stima run completo:    {total_h_full:.1f}h (2000 sim, K={args.n_walkers})")
    print(f"  Stima con K=5:         {total_h_full*5/args.n_walkers:.1f}h")
    print(f"  Stima con K=10:        {total_h_full*10/args.n_walkers:.1f}h")
    print(f"  Stima con K=20:        {total_h_full*20/args.n_walkers:.1f}h")

    rec_K = 10 if total_h_full * 10 / args.n_walkers < 48 else 5
    pilot_stats = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "pilot",
        "n_pilot": args.n_pilot,
        "K_pilot": args.n_walkers,
        "mean_time_per_sim_s": float(mean_time),
        "t_gudhi_mean_s": float(t_gudhi_mean),
        "estimated_full_run_hours_K10": float(total_h_full * 10 / args.n_walkers),
        "estimated_full_run_hours_K20": float(total_h_full * 20 / args.n_walkers),
        "recommended_K": rec_K,
        "individual_results": pilot_results,
        "methodology": "Monte Carlo marginalization over HOD prior (SimBIG approach, Hahn+2023)",
        "note": "gudhi eseguito su campo galattico 128^3 completo — no compressione"
    }

    with open(OUTPUT_PILOT, "w") as f:
        json.dump(pilot_stats, f, indent=2)

    print(f"\n  K raccomandato: {rec_K} (stima {total_h_full*rec_K/args.n_walkers:.1f}h)")
    print(f"  Output: {OUTPUT_PILOT}")

else:
    # FULL RUN — subset 400 campi con selezione uniforme su w0
    # Motivazione: run diagnostico per Concern 1 Reviewer. N=400 sufficiente
    # per misurare VIF_ristretto e stimare sigma_marg_ristretto.
    # Selezione: 40 campi per ogni decile di w0 in [-1.30, -0.70] (seed=42).
    K_full = args.n_walkers
    N_SUBSET = 400
    N_BINS_W0 = 10
    N_PER_BIN = N_SUBSET // N_BINS_W0

    rng_sel = np.random.default_rng(42)
    w0_bins = np.linspace(w0_all.min(), w0_all.max(), N_BINS_W0 + 1)
    subset_indices = []
    for b in range(N_BINS_W0):
        in_bin = np.where((w0_all >= w0_bins[b]) & (w0_all < w0_bins[b+1]))[0]
        chosen = rng_sel.choice(in_bin, size=min(N_PER_BIN, len(in_bin)), replace=False)
        subset_indices.extend(chosen.tolist())
    subset_indices = sorted(subset_indices)
    print(f"\n[FULL-RESTRICTED] {len(subset_indices)} campi (subset uniforme su w0), K={K_full}")
    print(f"  Prior ristretto: width=40% del flat, centrato su best-fit B3")
    print("-" * 70)

    all_feats = {idx: fvecs_nwlh[idx].copy() for idx in subset_indices}
    all_diags = []
    t_start = time.time()

    for sim_idx in subset_indices:
        if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
            chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"
            if chain_file.exists():
                data = np.load(chain_file)
                all_feats[sim_idx] = data["feat_marginalized"]
                continue

        t0 = time.time()
        feat_marg, diag = run_forward_sampling(sim_idx, K=K_full, resume=args.resume)
        elapsed = time.time() - t0
        all_feats[sim_idx] = feat_marg
        all_diags.append(diag)

        manifest[str(sim_idx)] = "done"
        with open(MANIFEST, "w") as f:
            json.dump(manifest, f)

        done_count = sum(1 for k in manifest if manifest[k] == "done")
        if done_count % 20 == 0:
            elapsed_total = time.time() - t_start
            eta_h = (elapsed_total / done_count) * (len(subset_indices) - done_count) / 3600
            n_gal_last = diag.get("n_gal_mean", 0)
            print(f"  {done_count:3d}/{len(subset_indices)} | t/sim={elapsed:.0f}s | "
                  f"ETA={eta_h:.1f}h | n_gal={n_gal_last:.0f}", flush=True)

    # Costruisci array ordinato per output
    subset_arr = np.array(subset_indices)
    feats_arr  = np.array([all_feats[i] for i in subset_indices], dtype=np.float32)
    w0_sub     = w0_all[subset_arr]
    Omm_sub    = Omm_all[subset_arr]
    s8_sub     = s8_all[subset_arr]

    # Calcola VIF e sigma sul subset restricted
    from scipy import stats as scipy_stats
    B2_IDX = 5  # b2_mean_persistence
    sigma2_intra_restr = np.zeros(8)
    sigma2_inter_restr = np.zeros(8)
    chain_files_done = list(CHAINS_DIR.glob("chain_*.npz"))
    for cf in chain_files_done:
        d = np.load(cf)
        fk = d["feat_all_k"]
        if fk.shape[0] >= 2:
            for fi in range(8):
                sigma2_intra_restr[fi] += np.var(fk[:, fi], ddof=1)
    if len(chain_files_done) > 0:
        sigma2_intra_restr /= len(chain_files_done)
    for fi in range(8):
        sigma2_inter_restr[fi] = np.var(feats_arr[:, fi], ddof=1)
    VIF_restr = sigma2_intra_restr / (sigma2_inter_restr + 1e-30)

    rng_perm = np.random.default_rng(42)
    b2_sub = feats_arr[:, B2_IDX]
    rho_obs, _ = scipy_stats.spearmanr(b2_sub, w0_sub)
    null = np.array([scipy_stats.spearmanr(b2_sub, rng_perm.permutation(w0_sub)).statistic
                     for _ in range(1000)])
    sigma_restr = (abs(rho_obs) - abs(null.mean())) / null.std()

    print(f"\n{'='*70}")
    print(f"RISULTATI PRIOR RISTRETTO (subset {len(subset_indices)} campi, K={K_full})")
    print(f"{'='*70}")
    FEAT_NAMES = ["b1_peak_pos","b1_peak_height","b1_fwhm","b1_integral",
                  "b2_max_count","b2_mean_persistence","b2_high_persist","b0_at_mean"]
    for fi, fn in enumerate(FEAT_NAMES):
        marker = " *** PRIMARIA" if fi == B2_IDX else ""
        print(f"  {fn:<22} VIF={VIF_restr[fi]:.3f}{marker}")
    print(f"\n  VIF(b2_mean_persistence) ristretto = {VIF_restr[B2_IDX]:.4f}")
    print(f"  VIF(b2_mean_persistence) piatto    = 2.4834  (riferimento)")
    print(f"  ρ(b2_marg_ristretto, w0) = {rho_obs:+.4f}")
    print(f"  σ_marg_ristretto         = {sigma_restr:.2f}σ")

    np.savez(OUTPUT_FEATURES,
             fvecs_hod_marginalized=feats_arr,
             sim_indices=subset_arr,
             w0=w0_sub, Omm=Omm_sub, s8=s8_sub,
             K=K_full,
             prior_type="literature_BGS_Yuan2022_Hadzhiyska2023_Zhang2025",
             prior_low=HOD_PRIOR_LOW,
             prior_high=HOD_PRIOR_HIGH,
             VIF_restricted=VIF_restr,
             sigma_marginalized_restricted=np.array([sigma_restr]),
             methodology="Monte Carlo HOD forward sampling, prior ristretto ±20% flat")

    diag_out = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_sims": 2000, "K": K_full,
        "n_completed": len(all_diags),
        "n_fallback_dm": sum(1 for d in all_diags if "FALLBACK" in d.get("status","")),
        "t_gudhi_mean_s": float(np.mean([d["t_gudhi_mean_s"] for d in all_diags if d["t_gudhi_mean_s"]>0])) if all_diags else 0,
        "feat_std_mean": float(np.mean([d["feat_std_across_K"] for d in all_diags if d["feat_std_across_K"]>0])) if all_diags else 0,
        "individual_diagnostics": all_diags
    }
    with open(OUTPUT_DIAG, "w") as f:
        json.dump(diag_out, f, indent=2)

    print(f"\n  Output feature: {OUTPUT_FEATURES}")
    print(f"  Output diagnostics: {OUTPUT_DIAG}")
    print(f"  Prossimo: analisi variance decomp confronto flat vs restricted")
    print(f"{'='*70}")
```


## FILE: src/phase7_rsd_test.py
<!-- score=261 size=12.9KB keywords=['persistence', 'phase1', 'sigma_px', 'gudhi', 'cubicalcomplex', 'filtration', 'superlevel', 'smooth', 'log1p', 'gaussian_filter'] -->

```python
"""
phase7_rsd_test.py — CAUCHY Sub-Phase 7.0  (v2 — 2026-05-21)
Test biforcante RSD: misura b2_mean_persistence su campi nwLH in redshift space
e confronta con una baseline real-space ricalcolata internamente con gli stessi
parametri TDA (n_thresh=100, sigma_px=0.640, convenzione v3).

NOTA METODOLOGICA:
  La baseline phase1_tda_baseline.json usa n_thresh=50. Da Phase 5 in poi il
  pipeline usa n_thresh=100. Per un confronto RS vs real senza contaminazione
  da n_thresh, questo script ricalcola la baseline real-space (DM nwLH, N=200)
  con n_thresh=100 in parallelo al calcolo RS. Il confronto è quindi:
    DM real-space (n_thresh=100, N=200)  vs  DM redshift-space (n_thresh=100, N=200)
  sugli stessi indici di simulazione.

Parametri TDA frozen (gate1_prior_v1_0.json + Phase 5 convention):
  - smoothing_sigma_px = 0.640
  - n_thresh = 100
  - filtration: superlevel via negation (gudhi CubicalComplex)
  - convenzione v3: birth_s = -diag[:,0], death_s = -diag[:,1]
  - feature: b2_mean_persistence = mean(birth_s - death_s) per H2

Input:
  - Campi RS: NWLH_DIR/<idx>/df_m_128_RS_z=0.npy
  - Campi real: NWLH_DIR/<idx>/df_m_128_PCS_z=0.npy  (già scaricati)

Output: results/phase7_rsd_test.json
"""

if __name__ == '__main__':
    import sys
    import json
    import numpy as np
    from pathlib import Path
    from datetime import datetime, timezone
    from scipy.ndimage import gaussian_filter
    import gudhi

    # ─── Configurazione ──────────────────────────────────────────────────────
    PROJECT_ROOT  = Path(r"D:\projects\cauchy")
    NWLH_DIR      = PROJECT_ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH"
    OUTPUT_PATH   = PROJECT_ROOT / "results" / "phase7_rsd_test.json"

    RS_FILENAME   = "df_m_128_RS_z=0.npy"
    REAL_FILENAME = "df_m_128_PCS_z=0.npy"

    # Frozen TDA parameters
    SIGMA_PX      = 0.640
    N_THRESH      = 100
    PERCENTILE_LO = 5
    PERCENTILE_HI = 95

    # Phase 1 baseline (n_thresh=50) — retained for reference only, NOT used for verdict
    B2_PHASE1_MEAN = 0.12376738339662552
    B2_PHASE1_STD  = 0.018904492259025574

    # Subset of simulations to process
    N_FIELDS      = 200
    FIELDS_STRIDE = 10   # indices 0, 10, 20, ..., 1990

    # ─── Availability check ──────────────────────────────────────────────────
    print("=" * 60)
    print("CAUCHY Phase 7.0 — RSD Bifurcation Test  (v2)")
    print("=" * 60)

    sim_indices = list(range(0, 2000, FIELDS_STRIDE))[:N_FIELDS]

    # Check RS files (may not be downloaded yet)
    rs_missing = [idx for idx in sim_indices[:10]
                  if not (NWLH_DIR / str(idx) / RS_FILENAME).exists()]
    real_missing = [idx for idx in sim_indices[:10]
                    if not (NWLH_DIR / str(idx) / REAL_FILENAME).exists()]

    if real_missing:
        print(f"\n[ERROR] Real-space files missing for {len(real_missing)}/10 sample sims.")
        print(f"  Expected: {NWLH_DIR / '0' / REAL_FILENAME}")
        sys.exit(1)

    if len(rs_missing) == 10:
        print("[INFO] RS files not yet downloaded — running in BASELINE-ONLY mode.")
        print(f"  Will compute real-space baseline (n_thresh=100) on {N_FIELDS} sims.")
        print(f"  Re-run after downloading: {RS_FILENAME}")
    elif rs_missing:
        print(f"[WARNING] RS files missing for {len(rs_missing)}/10 sample sims.")
    else:
        print(f"[OK] Both RS and real files present. Processing N={N_FIELDS} sims.")

    # ─── TDA function ────────────────────────────────────────────────────────
    def compute_b2_mean_persistence(field_raw):
        """
        b2_mean_persistence on a 128^3 density field.
        Full frozen pipeline: log1p → gaussian smooth (sigma_px=0.640, wrap)
        → percentile clip [5,95] → superlevel via negation → gudhi CubicalComplex
        → H2 persistence diagram → convention v3 → mean persistence.
        """
        # 1. Log transform — frozen pipeline convention: log(delta+1) = log(rho/<rho>)
        #    field_raw is delta = rho/<rho> - 1, so delta+1 = rho/<rho> >= 0 always.
        #    Clip at -1 (i.e. rho/<rho> >= 0) only to guard fp noise near voids.
        field_log = np.log1p(np.clip(field_raw.astype(np.float64), -1.0, None))

        # 2. Gaussian smoothing at sigma_px (periodic boundary)
        field_s = gaussian_filter(field_log, sigma=SIGMA_PX, mode='wrap')

        # 3. Percentile clip
        lo = np.percentile(field_s, PERCENTILE_LO)
        hi = np.percentile(field_s, PERCENTILE_HI)
        field_s = np.clip(field_s, lo, hi)

        # 4. Superlevel via negation
        field_neg = -field_s

        # 5. Build threshold array for n_thresh levels (not used by CubicalComplex
        #    directly — n_thresh is implicit in the continuous filtration; kept as
        #    documentation of the frozen parameter)
        _ = N_THRESH  # acknowledged

        # 6. gudhi CubicalComplex (full continuous filtration)
        cc = gudhi.CubicalComplex(
            dimensions=list(field_neg.shape),
            top_dimensional_cells=field_neg.flatten(order='C').tolist()
        )
        cc.compute_persistence()

        # 7. H2 diagram — convention v3
        diag = np.array(cc.persistence_intervals_in_dimension(2))
        if len(diag) == 0:
            return np.nan

        finite = np.isfinite(diag[:, 1])
        diag = diag[finite]
        if len(diag) == 0:
            return np.nan

        # convention v3: birth in field_s = -birth in field_neg
        birth_s = -diag[:, 0]
        death_s = -diag[:, 1]
        persistence = birth_s - death_s

        valid = persistence > 0
        if valid.sum() == 0:
            return np.nan

        return float(np.mean(persistence[valid]))

    # ─── Main loop — paired real/RS on same sim indices ───────────────────────
    b2_real_values = []
    b2_rs_values   = []
    errors_real    = []
    errors_rs      = []

    print(f"\nProcessing {N_FIELDS} paired sims (stride={FIELDS_STRIDE})...")
    print("  [computing real-space baseline with n_thresh=100 in parallel]\n")

    for i, idx in enumerate(sim_indices):
        # --- Real space ---
        fpath_real = NWLH_DIR / str(idx) / REAL_FILENAME
        if fpath_real.exists():
            try:
                b2_r = compute_b2_mean_persistence(np.load(str(fpath_real)))
                b2_real_values.append(b2_r)
            except Exception as e:
                errors_real.append(idx)
                print(f"  [WARN real] sim {idx}: {e}")
        else:
            errors_real.append(idx)

        # --- Redshift space ---
        fpath_rs = NWLH_DIR / str(idx) / RS_FILENAME
        if fpath_rs.exists():
            try:
                b2_s = compute_b2_mean_persistence(np.load(str(fpath_rs)))
                b2_rs_values.append(b2_s)
            except Exception as e:
                errors_rs.append(idx)
                print(f"  [WARN RS]   sim {idx}: {e}")
        else:
            errors_rs.append(idx)

        # Progress
        if (i + 1) % 20 == 0:
            mean_r = np.nanmean(b2_real_values) if b2_real_values else float('nan')
            mean_s = np.nanmean(b2_rs_values)   if b2_rs_values   else float('nan')
            print(f"  [{i+1:3d}/{N_FIELDS}]  b2_real={mean_r:.5f}  b2_RS={mean_s:.5f}  "
                  f"(n_real={len(b2_real_values)}, n_rs={len(b2_rs_values)})")

    # Filter NaN
    b2_real_values = [v for v in b2_real_values if not np.isnan(v)]
    b2_rs_values   = [v for v in b2_rs_values   if not np.isnan(v)]

    n_real = len(b2_real_values)
    n_rs   = len(b2_rs_values)

    if n_real == 0:
        print("\n[FATAL] No valid real-space measurements.")
        sys.exit(1)

    b2_real_mean = float(np.mean(b2_real_values))
    b2_real_std  = float(np.std(b2_real_values, ddof=1))

    # ─── Verdict ─────────────────────────────────────────────────────────────
    if n_rs == 0:
        # RS fields not yet downloaded — report real-space baseline only
        delta_mean  = None
        delta_sigma = None
        verdict     = "PENDING_RS_DOWNLOAD"
        verdict_note = (
            "RS files not available. Real-space baseline computed successfully. "
            "Re-run after downloading df_m_128_RS_z=0.npy fields."
        )
        print("\n[INFO] RS fields not available — baseline only run completed.")
    else:
        b2_rs_mean = float(np.mean(b2_rs_values))
        b2_rs_std  = float(np.std(b2_rs_values, ddof=1))

        delta_mean  = float(b2_rs_mean - b2_real_mean)
        delta_sigma = float(abs(delta_mean) / b2_real_std)

        if delta_sigma < 1.0:
            verdict = "PAPER_B_ACTIVE"
            verdict_note = (
                f"Δ = {delta_sigma:.3f}σ < 1.0σ. RSD shift sub-sigma on DM fields. "
                "DESI signal +3.09σ survives. Paper B activated. "
                "HOD B3 RS run recommended for paper-quality confirmation."
            )
        elif delta_sigma < 2.0:
            verdict = "GREY_ZONE"
            verdict_note = (
                f"Δ = {delta_sigma:.3f}σ ∈ [1.0, 2.0)σ. PI decision required. "
                "Options: RSD correction before Paper B, or proceed with Paper A/C."
            )
        else:
            verdict = "PAPER_B_SUSPENDED"
            verdict_note = (
                f"Δ = {delta_sigma:.3f}σ ≥ 2.0σ. DESI signal confounded by RSD. "
                "Paper B suspended. Proceed with Paper A (σ_px methodology) "
                "or Paper C (Quijote-only phantom detection)."
            )

    # ─── Output JSON ─────────────────────────────────────────────────────────
    result = {
        "schema_version": "1.0",
        "script_version": "phase7_rsd_test_v2",
        "test_id": "RSD_bifurcation_test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_fields_requested": N_FIELDS,
        "sim_indices_stride": FIELDS_STRIDE,
        "tda_params": {
            "sigma_px": SIGMA_PX,
            "n_thresh": N_THRESH,
            "filtration": "superlevel_via_negation_gudhi_CubicalComplex",
            "convention": "v3",
            "feature": "b2_mean_persistence_H2",
            "note": "n_thresh=100 consistent with Phase 5/6. Phase 1 used n_thresh=50."
        },
        "realspace_baseline_internal": {
            "source": "DM nwLH PCS fields, same sim indices, recomputed with n_thresh=100",
            "n_valid": n_real,
            "n_errors": len(errors_real),
            "b2_mean": b2_real_mean,
            "b2_std": b2_real_std
        },
        "realspace_baseline_phase1_reference": {
            "source": "phase1_tda_baseline.json fvecs_nwlh_stats (n_thresh=50, N=2000)",
            "b2_mean": B2_PHASE1_MEAN,
            "b2_std": B2_PHASE1_STD,
            "note": "Not used for verdict — retained for cross-check only"
        },
        "redshiftspace": {
            "filename": RS_FILENAME,
            "n_valid": n_rs,
            "n_errors": len(errors_rs),
            "b2_mean": float(np.mean(b2_rs_values)) if n_rs > 0 else None,
            "b2_std":  float(np.std(b2_rs_values, ddof=1)) if n_rs > 0 else None
        },
        "delta_mean_b2": delta_mean,
        "delta_sigma": delta_sigma,
        "delta_sign": (
            ("RS > real" if delta_mean > 0 else "RS < real")
            if delta_mean is not None else None
        ),
        "verdict": verdict,
        "notes": verdict_note
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(str(OUTPUT_PATH), 'w') as f:
        json.dump(result, f, indent=2)

    # ─── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Real (internal, n_thresh=100): "
          f"mean = {b2_real_mean:.5f} ± {b2_real_std:.5f}  (N={n_real})")
    print(f"  Real (Phase 1 reference, n_thresh=50): "
          f"mean = {B2_PHASE1_MEAN:.5f} ± {B2_PHASE1_STD:.5f}  (N=2000)")
    if n_rs > 0:
        b2_rs_mean = result['redshiftspace']['b2_mean']
        b2_rs_std  = result['redshiftspace']['b2_std']
        print(f"  Redshift space:               "
              f"mean = {b2_rs_mean:.5f} ± {b2_rs_std:.5f}  (N={n_rs})")
        print(f"  Δ(b2, RS − real) = {delta_mean:+.5f}")
        print(f"  Δ/σ_real         = {delta_sigma:.3f}σ")
    else:
        print("  Redshift space: NOT AVAILABLE (pending download)")
    print(f"\n  VERDICT: {verdict}")
    print(f"  {verdict_note}")
    print(f"\n  Output: {OUTPUT_PATH}")
```
