#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 5
src/paper1_step6_onepoint_betti.py

STEP 6 (v2) — Statistiche a un punto e curve di Betti (protocollo v2 §2-§3)
NOVITA' v2: le statistiche a un punto sono calcolate su PIU' RESTRIZIONI della
maschera (footprint pieno, erosione, taglio su field_r) per separare il segnale
dall'artefatto di pesatura FKP, che vive nei voxel di bordo a denominatore piccolo.

Risponde alla domanda del canovaccio originale mai eseguita:
  "A QUALE livello di densita' mancano i loop?"

NESSUN CALCOLO TDA. Legge le curve e i diagrammi gia' salvati da
paper1_remap.py v3 (`curves_<REGION>_<TAG>/curves_XXXX.npz`) e i campi delta
dalla cache. E' quindi leggero e si puo' lanciare in parallelo ad altri run.

COSA PRODUCE
------------
1. CURVE DI BETTI
   beta1(nu) di DESI contro la banda dei mock, su griglia comune.
   Le soglie della pipeline sono ADATTIVE per campo (linspace(P1,P99) della nu
   di quel campo), quindi le curve di campi diversi vivono su griglie diverse e
   NON sono mediabili cosi' come sono. Si interpola su due griglie comuni:
     - ASSOLUTA : nu fisico            -> dove sta il deficit in densita'
     - NORMALIZZATA: t in [0,1] con t=0 a P1 e t=1 a P99 del campo
                                        -> separa la FORMA dall'ampiezza
   Curve calcolate per base / remap / null, quindi anche il confronto
   PURAMENTE DI FASE (DESI vs mock rimappati sulla PDF di DESI).

2. STATISTICHE A UN PUNTO (§2)
   Momenti 1-4 su delta e su nu entro maschera, funzione di eccedenza,
   percentili, e rango empirico di DESI in ciascuna statistica.

3. DISTANZE ROBUSTE FRA PDF (caveat n.6)
   L'RMS in delta e' dominato dalla coda (delta fino a +150). Qui si affiancano:
     - distanza di Kolmogorov-Smirnov (max |CDF - CDF|): adimensionale, robusta
     - Wasserstein-1 su log(1+delta): comprime la coda
     - mediana di |Q_a - Q_b|: insensibile agli estremi
     - Wasserstein-1 ristretto ai quantili centrali 5-95%

4. LA TRANSIZIONE R10 -> R12 (caveat n.7)
   peak_nu di DESI salta da +0.89 a -2.37 e la risposta one-point cambia segno.
   Confronto diretto delle forme normalizzate per capire se la curva diventa
   bimodale (argmax che salta fra due massimi vicini) o se e' una transizione
   reale.

USO
---
  # tutto quello che trova (default: tutti i tag disponibili)
  python src\\paper1_step6_onepoint_betti.py --project_root D:\\projects\\cauchy --region NGC

  # solo alcune scale, e piu' campi per le statistiche a un punto
  python src\\paper1_step6_onepoint_betti.py ... --tags R5,R10,R12 --n_onepoint 500

  # solo curve, salta le statistiche a un punto (non legge la cache: velocissimo)
  python src\\paper1_step6_onepoint_betti.py ... --stage curves
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

N_COMMON = 120          # punti della griglia comune
N_OUT = 120             # punti salvati nel JSON


# ---------------------------------------------------------------------------
def moments(x):
    """Momenti 1-4 (curtosi in eccesso), robusti a input grandi."""
    x = np.asarray(x, dtype=np.float64)
    mu = x.mean()
    d = x - mu
    v = (d ** 2).mean()
    s = np.sqrt(v)
    return {"mean": float(mu), "var": float(v), "std": float(s),
            "skew": float((d ** 3).mean() / s ** 3) if s > 0 else 0.0,
            "kurt_excess": float((d ** 4).mean() / s ** 4 - 3.0) if s > 0 else 0.0,
            "median": float(np.median(x)),
            "p01": float(np.percentile(x, 1)), "p99": float(np.percentile(x, 99)),
            "max": float(x.max()), "min": float(x.min())}


def ladder_distances(Qa, Qb):
    """Distanze fra due scale di quantili ORDINATE della stessa lunghezza."""
    Qa = np.asarray(Qa, dtype=np.float64)
    Qb = np.asarray(Qb, dtype=np.float64)
    n = Qa.size
    d = Qa - Qb
    lo, hi = int(0.05 * n), int(0.95 * n)
    # KS: max distanza fra CDF. Con scale ordinate equivale a confrontare
    # le posizioni relative; si stima su una griglia comune di valori.
    grid = np.linspace(min(Qa[0], Qb[0]), max(Qa[-1], Qb[-1]), 2000)
    Fa = np.searchsorted(Qa, grid, side="right") / n
    Fb = np.searchsorted(Qb, grid, side="right") / n
    la, lb = np.log1p(np.clip(Qa, -1 + 1e-3, None)), np.log1p(np.clip(Qb, -1 + 1e-3, None))
    return {"rms": float(np.sqrt((d ** 2).mean())),
            "ks": float(np.abs(Fa - Fb).max()),
            "w1_log": float(np.abs(la - lb).mean()),
            "median_abs": float(np.median(np.abs(d))),
            "w1_central_5_95": float(np.abs(d[lo:hi]).mean())}


def interp_curve(th, cv, grid):
    """Interpola una curva su una griglia; fuori dal supporto -> NaN."""
    th = np.asarray(th, dtype=np.float64)
    cv = np.asarray(cv, dtype=np.float64)
    if th[0] > th[-1]:
        th, cv = th[::-1], cv[::-1]
    out = np.interp(grid, th, cv, left=np.nan, right=np.nan)
    return out


def nanband(M):
    """media / std / n valido lungo asse 0 ignorando i NaN."""
    with np.errstate(invalid="ignore"):
        mu = np.nanmean(M, axis=0)
        sd = np.nanstd(M, axis=0, ddof=1)
    n = np.sum(~np.isnan(M), axis=0)
    return mu, sd, n


def dn(a):
    """array -> lista JSON-safe."""
    return [None if (x is None or not np.isfinite(x)) else float(x) for x in np.asarray(a)]


# ---------------------------------------------------------------------------
def analyse_tag(out_dir, region, tag, n_curves):
    cdir = out_dir / f"curves_{region}_{tag}"
    dpath = out_dir / f"curves_DESI_{region}_{tag}.npz"
    if not cdir.exists() or not dpath.exists():
        return None
    files = sorted(cdir.glob("curves_*.npz"))
    if n_curves:
        files = files[:n_curves]
    if not files:
        return None

    D = np.load(dpath)
    th_d, b1_d, b0_d = D["thresholds"], D["b1_curve"], D["b0_curve"]
    if th_d[0] > th_d[-1]:
        th_d, b1_d, b0_d = th_d[::-1], b1_d[::-1], b0_d[::-1]

    # --- griglie comuni ---
    grid_abs = np.linspace(float(th_d[0]), float(th_d[-1]), N_COMMON)   # riferimento: DESI
    grid_nrm = np.linspace(0.0, 1.0, N_COMMON)

    b1_d_abs = interp_curve(th_d, b1_d, grid_abs)
    b1_d_nrm = interp_curve(np.linspace(0, 1, th_d.size), b1_d, grid_nrm)

    acc = {k: {"abs": [], "nrm": []} for k in ("base", "remap", "null")}
    peaks = {k: [] for k in ("base", "remap", "null")}
    pers = {k: [] for k in ("base", "remap", "null")}
    for fp in files:
        try:
            Z = np.load(fp)
        except Exception:
            continue
        for k in ("base", "remap", "null"):
            kt, kc = f"{k}__thresholds", f"{k}__b1_curve"
            if kt not in Z.files:
                continue
            th, cv = np.asarray(Z[kt], float), np.asarray(Z[kc], float)
            if th[0] > th[-1]:
                th, cv = th[::-1], cv[::-1]
            acc[k]["abs"].append(interp_curve(th, cv, grid_abs))
            acc[k]["nrm"].append(interp_curve(np.linspace(0, 1, th.size), cv, grid_nrm))
            peaks[k].append(float(th[int(np.argmax(cv))]))
            kb, kd = f"{k}__h1_birth", f"{k}__h1_death"
            if kb in Z.files and Z[kb].size:
                pers[k].append(float(np.mean(np.asarray(Z[kb], float) -
                                             np.asarray(Z[kd], float))))

    res = {"tag": tag, "n_mock_curves": len(files),
           "grid_abs": dn(grid_abs), "grid_norm": dn(grid_nrm),
           "desi": {"b1_abs": dn(b1_d_abs), "b1_norm": dn(b1_d_nrm),
                    "thresholds_range": [float(th_d[0]), float(th_d[-1])],
                    "peak_nu": float(th_d[int(np.argmax(b1_d))]),
                    "b1_peak": float(b1_d.max()), "N_H1": int(D["h1_birth"].size)
                    if "h1_birth" in D.files else None}}

    for k in ("base", "remap", "null"):
        if not acc[k]["abs"]:
            continue
        mu_a, sd_a, n_a = nanband(np.vstack(acc[k]["abs"]))
        mu_n, sd_n, _ = nanband(np.vstack(acc[k]["nrm"]))
        res[k] = {"b1_abs_mean": dn(mu_a), "b1_abs_std": dn(sd_a),
                  "b1_abs_nvalid": [int(x) for x in n_a],
                  "b1_norm_mean": dn(mu_n), "b1_norm_std": dn(sd_n),
                  "peak_nu_mean": float(np.mean(peaks[k])),
                  "peak_nu_std": float(np.std(peaks[k], ddof=1)) if len(peaks[k]) > 1 else 0.0,
                  "mean_pers_mean": float(np.mean(pers[k])) if pers[k] else None}
        # differenza DESI - mock, in unita' di sigma_mock
        with np.errstate(invalid="ignore", divide="ignore"):
            diff = b1_d_abs - mu_a
            z = np.where(sd_a > 0, diff / sd_a, np.nan)
        res[k]["diff_abs"] = dn(diff)
        res[k]["diff_abs_z"] = dn(z)
        fin = np.isfinite(z)
        if fin.any():
            i = int(np.nanargmin(z))
            res[k]["most_deficient"] = {"nu": float(grid_abs[i]), "z": float(z[i]),
                                        "desi": float(b1_d_abs[i]), "mock": float(mu_a[i])}
            j = int(np.nanargmax(np.abs(diff)))
            res[k]["max_abs_diff"] = {"nu": float(grid_abs[j]), "diff": float(diff[j])}
    return res


# ---------------------------------------------------------------------------
def build_restrictions(mask, field_r, specs):
    """Costruisce i sottoinsiemi di maschera su cui calcolare le statistiche."""
    from scipy.ndimage import distance_transform_edt
    out = []
    dist = None
    rin = field_r[mask]
    for spec in specs:
        spec = spec.strip().lower()
        if spec in ("none", "full", "0"):
            out.append(("footprint pieno", mask))
        elif spec.startswith("erosion"):
            k = int(spec.replace("erosion", ""))
            if dist is None:
                dist = distance_transform_edt(mask)
            out.append((f"erosione {k} voxel", dist > k))
        elif spec.startswith("fieldr"):
            p = float(spec.replace("fieldr", ""))
            thr = float(np.percentile(rin, p))
            out.append((f"field_r > P{p:g}", mask & (field_r > thr)))
        else:
            print(f"    [avviso] restrizione '{spec}' non riconosciuta, ignorata")
    return out


def onepoint_stats(M, P1, G, field_r, cache_dir, desi_delta, n_fields, specs):
    """
    Statistiche a un punto su piu' restrizioni della maschera.

    IMPORTANTE: nu viene costruito SEMPRE con la maschera PIENA (lo smoothing
    usa tutta l'informazione disponibile) e solo DOPO si restringe l'insieme
    dei voxel su cui si calcolano le statistiche. Stessa logica del
    --mode restrict di paper1_mask_erosion.py.
    """
    mask = G["mask"]
    files = sorted(cache_dir.glob("delta_*.npy"))[:n_fields]
    if not files:
        return None
    subsets = build_restrictions(mask, field_r, specs)
    print(f"  statistiche a un punto su {len(files)} mock, "
          f"{len(subsets)} restrizioni")

    nu_desi_full = P1.build_nu(desi_delta, mask, M.SIGMA_PX)

    # precarico i mock una volta sola: delta + nu a maschera piena
    print("    lettura campi e costruzione nu ...")
    mock_d, mock_n = [], []
    for i, fp in enumerate(files):
        a = np.load(fp).astype(np.float64)
        mock_d.append(a)
        mock_n.append(P1.build_nu(a, mask, M.SIGMA_PX))
        if (i + 1) % 25 == 0:
            print(f"      {i+1}/{len(files)}")

    keys = ["mean", "var", "skew", "kurt_excess", "median", "p99", "max"]
    out = {"n_fields": len(files), "sigma_px": float(M.SIGMA_PX),
           "restrictions": {}}

    for label, sel in subsets:
        n_sel = int(sel.sum())
        xd, nd = desi_delta[sel], nu_desi_full[sel]
        md_d, mn_d = moments(xd), moments(nd)
        rows_d = [moments(a[sel]) for a in mock_d]
        rows_n = [moments(a[sel]) for a in mock_n]

        def rank_of(val, arr):
            arr = np.asarray(arr, float)
            sd = arr.std(ddof=1)
            return {"desi": float(val), "mock_mean": float(arr.mean()),
                    "mock_std": float(sd),
                    "z": float((val - arr.mean()) / sd) if sd > 0 else None,
                    "rank": f"{int((arr <= val).sum())}/{arr.size}"}

        Qd = np.sort(xd)
        dists = [ladder_distances(np.sort(a[sel]), Qd) for a in mock_d[:25]]
        half = len(mock_d) // 2
        mm = [ladder_distances(np.sort(mock_d[i][sel]), np.sort(mock_d[i + half][sel]))
              for i in range(min(20, half))]
        agg = {k: float(np.mean([x[k] for x in dists])) for k in dists[0]}
        agg_mm = {k: float(np.mean([x[k] for x in mm])) for k in mm[0]} if mm else None

        out["restrictions"][label] = {
            "n_voxels": n_sel, "frac_of_full": float(n_sel / mask.sum()),
            "delta": {k: rank_of(md_d[k], [r[k] for r in rows_d]) for k in keys},
            "nu": {k: rank_of(mn_d[k], [r[k] for r in rows_n]) for k in keys},
            "var_ratio_delta": float(np.mean([r["var"] for r in rows_d]) / md_d["var"]),
            "var_ratio_nu": float(np.mean([r["var"] for r in rows_n]) / mn_d["var"]),
            "pdf_distance": {"mock_to_desi": agg, "mock_to_mock": agg_mm,
                             "ratio": {k: (agg[k] / agg_mm[k] if agg_mm and agg_mm[k] else None)
                                       for k in agg}}}
        print(f"    [{label}] {n_sel} voxel ({100*n_sel/mask.sum():.1f}%)  "
              f"var mock/DESI: delta {out['restrictions'][label]['var_ratio_delta']:.1f}x  "
              f"nu {out['restrictions'][label]['var_ratio_nu']:.2f}x")
    return out


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--tags", default="", help="es. R5,R10,R12 (default: tutti trovati)")
    ap.add_argument("--n_curves", type=int, default=0, help="0 = tutte")
    ap.add_argument("--n_onepoint", type=int, default=200)
    ap.add_argument("--stage", choices=["all", "curves", "onepoint"], default="all")
    ap.add_argument("--restrictions", default="none,erosion2,fieldr5,fieldr10",
                    help="restrizioni della maschera per le statistiche a un punto")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    sys.path.insert(0, str(root / "src"))
    out_dir = root / "results" / "paper1"

    print("=" * 74)
    print(f"CAUCHY Paper 1 - STEP 6: curve di Betti + statistiche a un punto  |  {args.region}")
    print("=" * 74)

    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]
    else:
        tags = sorted({p.name.replace(f"curves_{args.region}_", "")
                       for p in out_dir.glob(f"curves_{args.region}_*") if p.is_dir()},
                      key=lambda t: int(t.lstrip("R")) if t.lstrip("R").isdigit() else 999)
    print(f"  scale trovate: {tags}")

    report = {"schema_version": "1.0", "script": "paper1_step6_onepoint_betti.py",
              "protocol": "v2 §2-§3", "region": args.region, "curves": {}}

    for tg in tags:
        print(f"\n  --- {tg} ---")
        r = analyse_tag(out_dir, args.region, tg, args.n_curves)
        if r is None:
            print("    curve non trovate, salto")
            continue
        report["curves"][tg] = r
        print(f"    curve mock: {r['n_mock_curves']}   DESI peak_nu = {r['desi']['peak_nu']:+.4f}")
        for k in ("base", "remap"):
            if k in r:
                md = r[k].get("most_deficient")
                print(f"    {k:>5s}: peak_nu mock = {r[k]['peak_nu_mean']:+.4f} "
                      f"+/- {r[k]['peak_nu_std']:.4f}", end="")
                if md:
                    print(f"   deficit max a nu={md['nu']:+.3f} (z={md['z']:+.1f})")
                else:
                    print()

    if args.stage in ("all", "onepoint"):
        print("\n  --- statistiche a un punto ---")
        try:
            import phase8_cutsky_mocks as M
            import paper1_remap as P1
            G = P1.setup_region(M, args.region, root / "data" / "raw" / "desi_dr1",
                                root / "data" / "processed" / "phase6_fields")
            alpha = G["sum_wd"] / G["sum_wr"]
            desi_delta = P1.compute_delta(G["field_d"], G["field_r"], alpha,
                                          G["mask"], M.NGRID)
            cache = root / "data" / "processed" / "paper1_mock_deltas" / args.region
            specs = [x for x in args.restrictions.split(",") if x.strip()]
            op = onepoint_stats(M, P1, G, np.asarray(G["field_r"], float),
                                cache, desi_delta, args.n_onepoint, specs)
            if op:
                report["onepoint"] = op
                print("\n    === EVOLUZIONE DEL CONFRONTO CON LA RESTRIZIONE ===")
                print(f"    {'restrizione':>22s} {'vox%':>6s} | "
                      f"{'var mock/DESI delta':>20s} {'nu':>7s} | {'KS ratio':>9s}")
                for lab, r in op["restrictions"].items():
                    ksr = r["pdf_distance"]["ratio"].get("ks")
                    print(f"    {lab:>22s} {100*r['frac_of_full']:5.1f}% | "
                          f"{r['var_ratio_delta']:19.1f}x {r['var_ratio_nu']:6.2f}x | "
                          f"{ksr if ksr else float('nan'):8.2f}x")
                print("\n    === STATISTICHE IN NU (campo che entra in filtrazione) ===")
                for lab, r in op["restrictions"].items():
                    print(f"    --- {lab} ---")
                    for k, v in r["nu"].items():
                        z = v["z"]
                        if z is None:
                            continue
                        print(f"      {k:12s}: DESI {v['desi']:+11.4f}  "
                              f"mock {v['mock_mean']:+11.4f}  z={z:+8.2f}  {v['rank']}")
        except Exception as e:
            print(f"    [avviso] statistiche a un punto non eseguite: {type(e).__name__}: {e}")

    # transizione R10 -> R12
    if "R10" in report["curves"] and "R12" in report["curves"]:
        a, b = report["curves"]["R10"], report["curves"]["R12"]
        report["transition_R10_R12"] = {
            "desi_peak_nu": [a["desi"]["peak_nu"], b["desi"]["peak_nu"]],
            "desi_b1_peak": [a["desi"]["b1_peak"], b["desi"]["b1_peak"]],
            "mock_peak_nu": [a.get("base", {}).get("peak_nu_mean"),
                             b.get("base", {}).get("peak_nu_mean")],
            "note": ("Se il peak_nu dei mock e' stabile mentre quello di DESI salta, "
                     "la transizione e' specifica di DESI. Se la curva normalizzata ha "
                     "due massimi quasi uguali, il salto e' dell'argmax, non della forma.")}
        print(f"\n  transizione R10->R12: DESI peak_nu "
              f"{a['desi']['peak_nu']:+.3f} -> {b['desi']['peak_nu']:+.3f}   "
              f"mock {a.get('base',{}).get('peak_nu_mean',float('nan')):+.3f} -> "
              f"{b.get('base',{}).get('peak_nu_mean',float('nan')):+.3f}")

    p = out_dir / f"paper1_step6_{args.region}.json"
    p.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    sz = p.stat().st_size / 1024
    print(f"\n[scritto] {p.name}  ({sz:.0f} KB)")
    print("\n[fine]")


if __name__ == "__main__":
    main()
