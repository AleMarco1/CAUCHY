"""
CAUCHY — MN-26-2100-P revision, referee point R1.4
src/rev1_r14_monotone.py

"How can we ensure that the log-transform erases as little useful physical
signal as possible?"

Two measurements, no new pipeline:

  TEST A — exact monotone invariance.
      beta1_max depends on the filtered field ONLY through the order in which
      cells enter the superlevel filtration. Any strictly monotone remap of the
      filtered field therefore leaves it unchanged, to the unit. We verify this
      on the DESI field with two aggressively non-affine monotone maps
      (rank-order -> N(0,1) quantiles; exponential). <pers1> is NOT invariant:
      the contrast is the quantitative basis of the connectivity/amplitude
      distinction of Sections 3.1 / 5.3.

  TEST B — width of the one open channel.
      In this pipeline the transform is applied BEFORE smoothing, so
      T(smooth(.)) != smooth(T(.)) and the CHOICE of monotone map can move the
      count. We replace log by the Box-Cox family
          T_eps(delta) = [(1+delta)^eps - 1] / eps ,   T_0 = log(1+delta)
      which contains the log (eps -> 0) and the identity (eps = 1) as members,
      applied IDENTICALLY to data and mocks, and report how far the DEFICIT
      moves. Box-Cox is a family of FIXED maps: unlike a per-field rank remap it
      does not equalise the one-point distribution between data and mocks, so it
      measures the transform channel and nothing else.

Design rules enforced by the script itself:
  * No reimplementation. The paper's own build_field / compute_tda_features are
    imported from src/phase8_cutsky_mocks.py and used verbatim.
  * A hard assertion checks that the eps=0 branch of the local Box-Cox builder
    reproduces P8.build_field byte-for-byte, so eps=0 IS the paper's pipeline.
  * A reproduction gate: the DESI beta1_max at eps=0 must equal BETA1MAX_REF
    (28256) before any new number is written out.

Run from the project root (D:\\projects\\cauchy) with the `cauchy` env active.

  Step 1 (seconds):   python src\\rev1_r14_monotone.py --mode inspect
  Step 2 (minutes):   python src\\rev1_r14_monotone.py --mode testA
  Step 3 (long):      python src\\rev1_r14_monotone.py --mode testB --n_mocks 30 ^
                          --mock_dir data\\processed\\paper1_mock_deltas\\NGC

Output: results/revision/rev1_r14_monotone_{inspect,testA,testB}.json
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.stats import rankdata, norm, spearmanr

# --------------------------------------------------------------------------
# Frozen reference values (manuscript Section 5, corrected ensemble).
# The script refuses to write results if the eps=0 reproduction misses these.
# --------------------------------------------------------------------------
BETA1MAX_REF = 28256
PERS1_REF = 0.7246
REPRO_TOL = 0            # exact match required on the count

ROOT = Path.cwd()
SRC = ROOT / "src"
OUT_DIR = ROOT / "results" / "revision"

parser = argparse.ArgumentParser()
parser.add_argument("--mode",
                    choices=["inspect", "testA", "provenance", "deltastats", "testB"],
                    required=True)
parser.add_argument("--n_mocks", type=int, default=30)
parser.add_argument("--mock_dir", type=str, default="")
parser.add_argument("--frozen", type=str,
                    default="results/phase9_ngc_clean_beta1.npz",
                    help="npz containing the frozen like-for-like beta1_max ensemble")
parser.add_argument("--frozen_key", type=str, default="beta1_max",
                    help="Key of the frozen beta1_max array inside --frozen")
parser.add_argument("--n_check", type=int, default=5)
parser.add_argument("--eps", type=str, default="0.0,0.25,0.5,1.0")
parser.add_argument("--no_cache", action="store_true",
                    help="Ignore the cached DESI CIC fields and reload from FITS.")
parser.add_argument("--skip_repro_gate", action="store_true",
                    help="Diagnostic only. Never use for a number that enters the paper.")
ARGS = parser.parse_args()

OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))


def stamp():
    return datetime.now(timezone.utc).isoformat()


def dump(name, payload):
    p = OUT_DIR / f"rev1_r14_monotone_{name}.json"
    payload["timestamp"] = stamp()
    payload["script"] = "src/rev1_r14_monotone.py"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n[OUT] {p}")


# --------------------------------------------------------------------------
# Import the paper's pipeline verbatim
# --------------------------------------------------------------------------
def load_pipeline():
    import phase8_cutsky_mocks as P8
    for attr in ("build_field", "compute_tda_features", "load_desi_random_field",
                 "load_desi_data_field", "NGRID", "SIGMA_PX", "N_THRESH",
                 "DESI_MASK_FILE"):
        if not hasattr(P8, attr):
            sys.exit(f"[ERRORE] phase8_cutsky_mocks non espone '{attr}'. "
                     f"Fermati e segnalalo: la pipeline e' cambiata.")
    return P8


# --------------------------------------------------------------------------
# Loading the DESI CIC fields from the FITS costs ~3.5 min. Cache them: the
# eps=0 reproduction gate runs on every mode and would catch a stale cache.
# --------------------------------------------------------------------------
def load_desi_cached(P8):
    cache = OUT_DIR / "desi_inputs_cache.npz"
    if cache.exists() and not ARGS.no_cache:
        z = np.load(cache)
        print(f"      (cache: {cache.name})")
        return z["field_d"], z["field_r"], float(z["alpha"])
    field_r, sum_wr = P8.load_desi_random_field()
    field_d, sum_wd = P8.load_desi_data_field()
    alpha = sum_wd / sum_wr
    np.savez(cache, field_d=field_d, field_r=field_r, alpha=np.float64(alpha))
    print(f"      (cache scritta: {cache.name})")
    return field_d, field_r, alpha


def raw_delta(field_d, field_r, alpha, mask, P8):
    """The delta of Eq. (1), exactly as build_field computes it internally."""
    delta = np.zeros((P8.NGRID,) * 3, dtype=np.float64)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0
    return delta


# --------------------------------------------------------------------------
# Box-Cox family. eps = 0 must be byte-identical to P8.build_field.
# --------------------------------------------------------------------------
def transform(delta_in_mask, eps):
    x = 1.0 + np.clip(delta_in_mask, -1.0 + 1e-3, None)
    if eps == 0.0:
        return np.log(x)
    return (np.power(x, eps) - 1.0) / eps


def build_field_eps(field_d, field_r, alpha, mask, eps, P8):
    """Mirror of P8.build_field with the transform swapped. Every other line,
    including the clip, the smoothing call, the exterior zeroing and the
    in-mask mean subtraction, is identical."""
    delta = np.zeros((P8.NGRID,) * 3, dtype=np.float64)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0
    nu = np.zeros_like(delta)
    nu[mask] = transform(delta[mask], eps)
    nu = gaussian_filter(nu, sigma=P8.SIGMA_PX)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


def field_from_delta(delta_raw, mask, eps, P8):
    """Same construction starting from a stored RAW contrast field."""
    delta = np.asarray(delta_raw, dtype=np.float64).copy()
    delta[~mask] = 0.0
    nu = np.zeros_like(delta)
    nu[mask] = transform(delta[mask], eps)
    nu = gaussian_filter(nu, sigma=P8.SIGMA_PX)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


def beta1_pers1(field, mask, P8):
    f = P8.compute_tda_features(field, mask, P8.N_THRESH, masked=True)
    return int(f[4]), float(f[5])


# --------------------------------------------------------------------------
# Kernel diagnostics: how sub-pixel is the smoothing?
# --------------------------------------------------------------------------
def kernel_weights(sigma_px):
    imp = np.zeros((11, 11, 11))
    imp[5, 5, 5] = 1.0
    k = gaussian_filter(imp, sigma=sigma_px)
    return {
        "sigma_px": float(sigma_px),
        "scipy_truncate": 4.0,
        "kernel_radius_voxels": int(4.0 * sigma_px + 0.5),
        "central_voxel_weight_3d": float(k[5, 5, 5]),
        "six_face_neighbours_total": float(6 * k[4, 5, 5]),
        "remainder": float(1.0 - k[5, 5, 5] - 6 * k[4, 5, 5]),
    }



# --------------------------------------------------------------------------
# Provenance gate: are the stored raw-delta mocks the ones behind the frozen
# like-for-like ensemble? Rebuilding nu at eps=0 from a stored delta must
# reproduce the frozen beta1_max for that index. Without this the Box-Cox
# numbers would not be like-for-like with the paper (defect D10).
# --------------------------------------------------------------------------
def load_frozen_beta1(path):
    p = Path(path)
    if not p.exists():
        return None, None, f"file assente: {p}"
    obj = np.load(p, allow_pickle=True)
    keys = list(obj.files) if hasattr(obj, "files") else ["<npy>"]
    # Explicit key wins: the auto-detection below is only a fallback, and a
    # stale ensemble of the right shape would pass it silently.
    if hasattr(obj, "files") and ARGS.frozen_key in keys:
        a = np.asarray(obj[ARGS.frozen_key])
        if a.ndim == 1 and a.size >= 100:
            return keys, (ARGS.frozen_key, a), None
        return keys, None, f"'{ARGS.frozen_key}' non e' un array 1D utilizzabile"
    best = None
    for k in keys:
        a = np.asarray(obj[k]) if hasattr(obj, "files") else np.asarray(obj)
        if a.ndim == 1 and a.size >= 100 and np.issubdtype(a.dtype, np.number):
            med = float(np.median(a))
            if 2.0e4 < med < 6.0e4:
                if best is None or a.size > best[1].size:
                    best = (k, a)
    if best is None:
        return keys, None, "nessun array 1D compatibile con beta1_max"
    return keys, best, None


def provenance_gate(mock_files, mask, P8, n_check, frozen_path):
    keys, best, err = load_frozen_beta1(frozen_path)
    print(f"  frozen: {frozen_path}")
    print(f"  chiavi: {keys}")
    if err:
        print(f"  [ATTENZIONE] {err} — gate NON eseguibile.")
        return {"status": "not_run", "error": err, "keys": keys}
    kname, arr = best
    print(f"  array scelto: '{kname}' n={arr.size} "
          f"media={arr.mean():.1f} std={arr.std(ddof=1):.1f}")
    rows = []
    ok = True
    for i in range(min(n_check, len(mock_files))):
        d = np.load(mock_files[i])
        nu = field_from_delta(d, mask, 0.0, P8)
        n, _ = beta1_pers1(nu, mask, P8)
        ref = int(round(float(arr[i]))) if i < arr.size else None
        match = (ref is not None and n == ref)
        ok = ok and match
        rows.append({"file": mock_files[i].name, "recomputed": n,
                     "frozen": ref, "delta": (n - ref) if ref is not None else None,
                     "match": bool(match)})
        print(f"    {mock_files[i].name}: ricalcolato={n:7d}  congelato={ref}  "
              f"{'OK' if match else 'DIVERSO'}")
    return {"status": "pass" if ok else "fail", "frozen_key": kname,
            "frozen_n": int(arr.size), "checks": rows}


def mode_provenance():
    print("=" * 72)
    print("R1.4 — PROVENANCE GATE sui delta grezzi dei mock")
    print("=" * 72)
    P8 = load_pipeline()
    mask = np.load(P8.DESI_MASK_FILE)
    mock_dir = Path(ARGS.mock_dir)
    if not mock_dir.exists():
        sys.exit(f"[ERRORE] --mock_dir inesistente: {mock_dir}")
    mock_files = sorted(mock_dir.glob("*.npy"))
    print(f"  {len(mock_files)} file in {mock_dir}\n")
    res = provenance_gate(mock_files, mask, P8, ARGS.n_check, ARGS.frozen)
    print(f"\n  ESITO: {res['status'].upper()}")
    if res["status"] != "pass":
        print("  Non usare questi delta per il TEST B finche' non e' chiarito.")
    dump("provenance", {"mock_dir": str(mock_dir), "frozen": ARGS.frozen,
                        "result": res})


# --------------------------------------------------------------------------
# MODE: deltastats — amplitude of the raw FKP contrast, data vs mocks.
# Section 4.1 quotes "spikes up to delta ~ +150" and a std ratio of ~31; both
# are checkable directly and neither should be left unverified in a reply that
# is about the transform.
# --------------------------------------------------------------------------
def mode_deltastats():
    print("=" * 72)
    print("R1.4 — AMPIEZZA DEL CONTRASTO GREZZO (verifica dei numeri di 4.1)")
    print("=" * 72)
    P8 = load_pipeline()
    mask = np.load(P8.DESI_MASK_FILE)

    print("\n[1/2] DESI...")
    field_d, field_r, alpha = load_desi_cached(P8)
    dd = raw_delta(field_d, field_r, alpha, mask, P8)[mask]
    desi = {"min": float(dd.min()), "max": float(dd.max()),
            "std": float(dd.std()), "mean": float(dd.mean())}
    print(f"      delta DESI: min={desi['min']:+.4f} max={desi['max']:+.2f} "
          f"std={desi['std']:.4f}")

    mock_dir = Path(ARGS.mock_dir) if ARGS.mock_dir else (
        ROOT / "data" / "processed" / "paper1_mock_deltas" / "NGC")
    files = sorted(mock_dir.glob("*.npy"))[:ARGS.n_mocks]
    if not files:
        sys.exit(f"[ERRORE] nessun .npy in {mock_dir}")
    print(f"\n[2/2] {len(files)} mock da {mock_dir}...")
    mx, sd = [], []
    for f in files:
        a = np.load(f)[mask]
        mx.append(float(a.max()))
        sd.append(float(a.std()))
    mx = np.array(mx); sd = np.array(sd)
    ratio = sd / desi["std"]
    print(f"      max(delta) per mock: mediana={np.median(mx):.1f}  "
          f"min={mx.min():.1f}  max={mx.max():.1f}")
    print(f"      std(delta) per mock: mediana={np.median(sd):.2f}")
    print(f"      rapporto std mock/dati: mediana={np.median(ratio):.2f}  "
          f"intervallo=[{ratio.min():.2f}, {ratio.max():.2f}]")
    dump("deltastats", {
        "desi_raw_delta": desi,
        "mock_dir": str(mock_dir), "n_mocks": len(files),
        "mock_max_delta": {"median": float(np.median(mx)),
                           "min": float(mx.min()), "max": float(mx.max())},
        "mock_std_delta": {"median": float(np.median(sd)),
                           "min": float(sd.min()), "max": float(sd.max())},
        "std_ratio_mock_over_desi": {"median": float(np.median(ratio)),
                                     "min": float(ratio.min()),
                                     "max": float(ratio.max())},
        "paper_claims_to_check": {"section_4_1_spike": 150,
                                  "section_4_1_std_ratio": 31},
    })


# --------------------------------------------------------------------------
# MODE: inspect
# --------------------------------------------------------------------------
def mode_inspect():
    print("=" * 72)
    print("R1.4 — INSPECT")
    print("=" * 72)
    P8 = load_pipeline()
    print(f"  NGRID={P8.NGRID}  SIGMA_PX={P8.SIGMA_PX:.5f}  N_THRESH={P8.N_THRESH}")

    kw = kernel_weights(P8.SIGMA_PX)
    print("\n  Kernel discretizzato alla scala canonica:")
    for k, v in kw.items():
        print(f"    {k:28s} {v}")

    mask = np.load(P8.DESI_MASK_FILE)
    print(f"\n  mask: {mask.shape} {mask.dtype}  in-survey={int(mask.sum()):,}")

    cands = [Path(ARGS.mock_dir)] if ARGS.mock_dir else [
        ROOT / "data" / "processed" / "paper1_mock_deltas" / "NGC",
        ROOT / "results" / "phase8_test2_fields",
        ROOT / "results" / "phase8_cutsky_fields",
    ]
    report = {"pipeline": {"sigma_px": float(P8.SIGMA_PX), "ngrid": int(P8.NGRID)},
              "kernel": kw, "candidates": []}

    for d in cands:
        entry = {"dir": str(d), "exists": d.exists()}
        print(f"\n  --- {d}")
        if not d.exists():
            print("      (assente)")
            report["candidates"].append(entry)
            continue
        files = sorted(list(d.glob("*.npy")) + list(d.glob("*.npz")))
        entry["n_files"] = len(files)
        print(f"      {len(files)} file")
        if not files:
            report["candidates"].append(entry)
            continue
        f0 = files[0]
        entry["first_file"] = f0.name
        obj = np.load(f0)
        arrays = {}
        if hasattr(obj, "files"):
            entry["npz_keys"] = list(obj.files)
            print(f"      chiavi npz: {list(obj.files)}")
            for k in obj.files:
                a = np.asarray(obj[k])
                if a.ndim == 3:
                    arrays[k] = a
        else:
            arrays["<npy>"] = np.asarray(obj)
        for k, a in arrays.items():
            ins = a[mask] if a.shape == mask.shape else a.ravel()
            ext = a[~mask] if a.shape == mask.shape else np.array([np.nan])
            info = {
                "shape": list(a.shape), "dtype": str(a.dtype),
                "in_mask_min": float(ins.min()), "in_mask_max": float(ins.max()),
                "in_mask_mean": float(ins.mean()), "in_mask_std": float(ins.std()),
                "exterior_unique_first": float(ext[0]) if ext.size else None,
                "exterior_is_constant": bool(np.ptp(ext) == 0) if ext.size else None,
            }
            # a RAW contrast has min ~ -1 and a long positive tail;
            # a filtered nu has min ~ -1..-3 and max of order a few.
            info["looks_like"] = ("raw delta" if info["in_mask_max"] > 20
                                  else "nu (transformed/smoothed)")
            entry.setdefault("arrays", {})[k] = info
            print(f"      [{k}] shape={a.shape} dtype={a.dtype}")
            print(f"           in-mask  min={info['in_mask_min']:+.4f} "
                  f"max={info['in_mask_max']:+.4f} mean={info['in_mask_mean']:+.6f} "
                  f"std={info['in_mask_std']:.4f}")
            print(f"           exterior costante={info['exterior_is_constant']} "
                  f"valore={info['exterior_unique_first']}")
            print(f"           -> sembra: {info['looks_like']}")
        report["candidates"].append(entry)

    print("\n  Serve una directory con 'raw delta' per il TEST B.")
    dump("inspect", report)


# --------------------------------------------------------------------------
# MODE: testA
# --------------------------------------------------------------------------
def mode_testA():
    print("=" * 72)
    print("R1.4 — TEST A: invarianza esatta sotto rimappatura monotona")
    print("=" * 72)
    P8 = load_pipeline()
    mask = np.load(P8.DESI_MASK_FILE)

    print("\n[1/3] Ricostruzione DESI dalla pipeline del paper (build_field)...")
    t0 = time.time()
    field_d, field_r, alpha = load_desi_cached(P8)
    nu_paper = P8.build_field(field_d, field_r, alpha, mask)

    nu_eps0 = build_field_eps(field_d, field_r, alpha, mask, 0.0, P8)
    identical = bool(np.array_equal(nu_paper, nu_eps0))
    print(f"      build_field_eps(eps=0) == build_field : {identical}")
    if not identical:
        sys.exit("[ERRORE] Il ramo eps=0 non riproduce build_field. "
                 "Fermati: la famiglia Box-Cox non e' ancorata alla pipeline.")

    n0, p0 = beta1_pers1(nu_paper, mask, P8)
    print(f"      beta1_max = {n0}   <pers1> = {p0:.4f}   ({time.time()-t0:.0f}s)")

    gate_ok = (abs(n0 - BETA1MAX_REF) <= REPRO_TOL)
    print(f"      gate di riproduzione (atteso {BETA1MAX_REF}): "
          f"{'OK' if gate_ok else 'FALLITO'}")
    if not gate_ok and not ARGS.skip_repro_gate:
        sys.exit("[STOP] La riproduzione non torna. Riportami i due numeri "
                 "prima di andare avanti: nessun risultato nuovo e' affidabile "
                 "finche' la baseline non si riproduce.")

    print("\n[2/3] Rimappature monotone del campo FILTRATO...")
    vals = nu_paper[mask].astype(np.float64)

    # The discretized field contains exact ties. A map is monotone in the sense
    # that matters for a filtration only if it maps tied cells to tied values:
    # 'average' does, 'ordinal' breaks them and is kept as a diagnostic of how
    # much the tie structure alone is worth.
    uq, cnt = np.unique(vals, return_counts=True)
    ties = {"n_values": int(vals.size), "n_distinct": int(uq.size),
            "n_cells_in_tied_groups": int(cnt[cnt > 1].sum()),
            "n_tied_groups": int((cnt > 1).sum()),
            "max_multiplicity": int(cnt.max())}
    print(f"      pareggi nel campo: {ties['n_cells_in_tied_groups']} celle "
          f"in {ties['n_tied_groups']} gruppi (max molteplicita' "
          f"{ties['max_multiplicity']})")

    maps = {}
    ra = rankdata(vals, method="average")
    maps["rank_to_gaussian"] = norm.ppf((ra - 0.5) / len(ra))
    maps["exp_3x"] = np.exp(3.0 * vals)
    maps["cube"] = np.sign(vals) * np.abs(vals) ** 3
    ro = rankdata(vals, method="ordinal")
    maps["rank_to_gaussian_tiebreak"] = norm.ppf((ro - 0.5) / len(ro))

    results = {}
    for name, newvals in maps.items():
        # strict monotonicity check on the actual values used
        order_in = np.argsort(vals, kind="stable")
        assert np.all(np.diff(newvals[order_in]) >= 0), f"{name} non e' monotona"
        f = np.zeros_like(nu_paper, dtype=np.float64)
        f[mask] = newvals
        n, p = beta1_pers1(f.astype(np.float32), mask, P8)
        results[name] = {"beta1_max": n, "pers1": p,
                         "d_beta1_max": n - n0,
                         "pers1_ratio": p / p0 if p0 else None}
        print(f"      {name:18s} beta1_max={n:7d} ({n-n0:+d})   "
              f"<pers1>={p:.4f}  (x{p/p0:.3g})")

    print("\n[3/3] Kernel...")
    kw = kernel_weights(P8.SIGMA_PX)
    print(f"      peso del voxel centrale = {kw['central_voxel_weight_3d']:.4f}")

    dump("testA", {
        "baseline": {"beta1_max": n0, "pers1": p0,
                     "reference_beta1_max": BETA1MAX_REF,
                     "reference_pers1": PERS1_REF,
                     "reproduction_gate_passed": gate_ok,
                     "eps0_equals_build_field": identical},
        "monotone_remaps": results,
        "ties": ties,
        "kernel": kw,
    })


# --------------------------------------------------------------------------
# MODE: testB
# --------------------------------------------------------------------------
def mode_testB():
    print("=" * 72)
    print("R1.4 — TEST B: famiglia Box-Cox, ampiezza del canale aperto")
    print("=" * 72)
    P8 = load_pipeline()
    mask = np.load(P8.DESI_MASK_FILE)
    eps_list = [float(x) for x in ARGS.eps.split(",")]
    if 0.0 not in eps_list:
        sys.exit("[ERRORE] eps=0 (il log) deve essere nella lista: e' la baseline.")

    mock_dir = Path(ARGS.mock_dir)
    if not mock_dir.exists():
        sys.exit(f"[ERRORE] --mock_dir inesistente: {mock_dir}. "
                 f"Lancia prima --mode inspect.")
    mock_files = sorted(mock_dir.glob("*.npy"))[:ARGS.n_mocks]
    if not mock_files:
        sys.exit(f"[ERRORE] Nessun .npy in {mock_dir}.")
    print(f"  {len(mock_files)} mock da {mock_dir}")
    print(f"  eps = {eps_list}")

    print("\n[1/3] Lato DESI...")
    field_d, field_r, alpha = load_desi_cached(P8)
    nu_paper = P8.build_field(field_d, field_r, alpha, mask)
    assert np.array_equal(nu_paper, build_field_eps(field_d, field_r, alpha, mask, 0.0, P8))
    n_ref, p_ref = beta1_pers1(nu_paper, mask, P8)
    gate_ok = (abs(n_ref - BETA1MAX_REF) <= REPRO_TOL)
    print(f"      eps=0: beta1_max={n_ref} (atteso {BETA1MAX_REF}) -> "
          f"{'OK' if gate_ok else 'FALLITO'}")
    if not gate_ok and not ARGS.skip_repro_gate:
        sys.exit("[STOP] baseline non riprodotta.")

    desi = {}
    nu_by_eps = {}
    for eps in eps_list:
        f = build_field_eps(field_d, field_r, alpha, mask, eps, P8)
        n, p = beta1_pers1(f, mask, P8)
        desi[str(eps)] = {"beta1_max": n, "pers1": p}
        nu_by_eps[eps] = f[mask].astype(np.float64)
        print(f"      eps={eps:<5} beta1_max={n:7d}  <pers1>={p:.4f}")

    print("\n[2/3] Correlazione di rango fra i campi filtrati "
          "(1.0 = canale chiuso)...")
    spear = {}
    for eps in eps_list:
        if eps == 0.0:
            continue
        rho = float(spearmanr(nu_by_eps[0.0], nu_by_eps[eps]).statistic)
        spear[str(eps)] = rho
        print(f"      rho_S(eps=0, eps={eps}) = {rho:.8f}")

    print("\n[3/3] Lato mock...")
    # provenance / like-for-like check on the first mock
    a0 = np.load(mock_files[0])
    ins = a0[mask]
    print(f"      primo mock: in-mask min={ins.min():+.4f} max={ins.max():+.4f} "
          f"esterno={float(a0[~mask][0]):+.6g}")
    if ins.min() < -1.0 - 1e-6 or ins.max() < 20:
        sys.exit("[ERRORE] I file in --mock_dir non sembrano contrasti grezzi "
                 "(atteso min ~ -1 e coda positiva ampia). Fermati e riportamelo.")

    print("\n      Provenance gate (like-for-like con l'ensemble congelato):")
    prov = provenance_gate(mock_files, mask, P8, ARGS.n_check, ARGS.frozen)
    if prov["status"] != "pass" and not ARGS.skip_repro_gate:
        sys.exit("[STOP] I delta grezzi non riproducono l'ensemble congelato. "
                 "Riportami l'output del gate: usarli comunque violerebbe "
                 "il like-for-like.")

    mocks = {str(e): [] for e in eps_list}
    t0 = time.time()
    for i, fpath in enumerate(mock_files):
        d = np.load(fpath)
        for eps in eps_list:
            f = field_from_delta(d, mask, eps, P8)
            n, _ = beta1_pers1(f, mask, P8)
            mocks[str(eps)].append(n)
        el = time.time() - t0
        print(f"      [{i+1}/{len(mock_files)}] {fpath.name}  "
              f"eps0={mocks['0.0'][-1]}  ({el/(i+1):.0f}s/mock)")

    summary = {}
    base_deficit = None
    base_arr = np.array(mocks["0.0"], dtype=float)
    for eps in eps_list:
        arr = np.array(mocks[str(eps)], dtype=float)
        # Paired shift: the same mocks at two eps, so the per-mock difference
        # is far better determined than the difference of the two means.
        dpair = arr - base_arr
        d_beta = desi[str(eps)]["beta1_max"]
        deficit = float(arr.mean() - d_beta)
        if eps == 0.0:
            base_deficit = deficit
        summary[str(eps)] = {
            "desi_beta1_max": d_beta,
            "mock_mean": float(arr.mean()),
            "mock_std": float(arr.std(ddof=1)),
            "n_mocks": int(arr.size),
            "deficit": deficit,
            "deficit_frac_of_mock_mean": deficit / float(arr.mean()),
            "mock_paired_shift_mean": float(dpair.mean()),
            "mock_paired_shift_sem": (float(dpair.std(ddof=1) / np.sqrt(dpair.size))
                                      if dpair.size > 1 else 0.0),
            "desi_shift_vs_log": d_beta - desi["0.0"]["beta1_max"],
        }
    for eps in eps_list:
        s = summary[str(eps)]
        s["deficit_shift_vs_log"] = s["deficit"] - base_deficit
        s["deficit_shift_pct_vs_log"] = 100.0 * (s["deficit"] - base_deficit) / base_deficit
        print(f"\n      eps={eps}: DESI={s['desi_beta1_max']} "
              f"({s['desi_shift_vs_log']:+d})  "
              f"mock={s['mock_mean']:.1f}+-{s['mock_std']:.1f}  "
              f"[shift appaiato {s['mock_paired_shift_mean']:+.1f} "
              f"+- {s['mock_paired_shift_sem']:.1f}]")
        print(f"              deficit={s['deficit']:.1f} "
              f"({s['deficit_frac_of_mock_mean']*100:.1f}%)  "
              f"shift vs log = {s['deficit_shift_pct_vs_log']:+.2f}%")

    dump("testB", {
        "mock_dir": str(mock_dir),
        "eps_list": eps_list,
        "reproduction_gate_passed": gate_ok,
        "provenance_gate": prov,
        "desi": desi,
        "spearman_vs_log": spear,
        "mock_beta1_max_per_eps": mocks,
        "summary": summary,
        "kernel": kernel_weights(P8.SIGMA_PX),
    })


if __name__ == "__main__":
    if not SRC.exists():
        sys.exit(f"[ERRORE] Lancia dalla root del progetto. Cwd attuale: {ROOT}")
    {"inspect": mode_inspect, "testA": mode_testA,
     "provenance": mode_provenance, "deltastats": mode_deltastats,
     "testB": mode_testB}[ARGS.mode]()
