#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 6
src/paper1_fkp_asymmetry.py

DIAGNOSTICO DELL'ASIMMETRIA DI PESATURA FKP

IL PROBLEMA
-----------
La pipeline pesa i tre ingredienti in modo diverso:
    dati DESI   -> WEIGHT * WEIGHT_FKP
    random DESI -> WEIGHT_FKP
    mock        -> np.ones(...)          <-- nessun peso

Per DESI il peso FKP compare al numeratore e al denominatore di
delta = (n_d - alpha*n_r)/(alpha*n_r) e si cancella. Per i mock no: dove il
campo random pesato e' piccolo il denominatore collassa e delta esplode.
Effetto misurato (200 mock, NGC):

    delta max   : DESI  125   mock 4274
    log(1+delta): DESI 4.84   mock 8.36
    delta media : DESI -0.03  mock +6.73
    delta var   : DESI  2.92  mock 2918

Il docstring di `build_field` dichiara che il log serve a limitare la coda FKP
"al range di DESI": sul lato mock non ci riesce.

LA DOMANDA
----------
I voxel patologici sono al BORDO della maschera (e allora il test di erosione
li ha gia' gestiti) o sono sparsi nel volume (e allora serve una limitazione
esplicita nel manoscritto)?

E soprattutto: il deficit sopravvive se li si esclude dalla filtrazione?

STAGE
-----
  diag : nessuna TDA, pochi secondi.
         - profilo di field_r entro maschera e sue code
         - dove stanno i voxel a denominatore basso: distanza dal bordo e
           raggio dall'osservatore, confrontati con tutti i voxel in maschera
         - quali voxel producono i delta estremi dei mock e quanto pesano
         - statistiche a un punto di DESI e mock ESCLUDENDO i voxel sospetti:
           se la differenza si riduce, l'anomalia a un punto e' in parte
           l'artefatto di pesatura
  tda  : il test decisivo. Costruisce nu con la maschera PIENA e restringe la
         FILTRAZIONE ai voxel con denominatore sopra soglia (stessa tecnica
         di paper1_mask_erosion.py --mode restrict). Se il deficit resta,
         l'artefatto non lo guida.
  all  : entrambi.

USO
---
  # diagnostica veloce
  python src\\paper1_fkp_asymmetry.py --project_root D:\\projects\\cauchy --region NGC --stage diag

  # test decisivo (~40 min su 100 mock, 3 tagli)
  python src\\paper1_fkp_asymmetry.py --project_root D:\\projects\\cauchy --region NGC --k 100

  # su piu' scale
  python src\\paper1_fkp_asymmetry.py ... --sigma_scales 1.0,2.0
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt


def pct(x, p):
    return float(np.percentile(np.asarray(x, dtype=np.float64), p))


def summarize(x, label):
    x = np.asarray(x, dtype=np.float64)
    return {"label": label, "n": int(x.size), "mean": float(x.mean()),
            "std": float(x.std(ddof=1)) if x.size > 1 else 0.0,
            "median": float(np.median(x)), "p01": pct(x, 1), "p05": pct(x, 5),
            "p95": pct(x, 95), "p99": pct(x, 99),
            "min": float(x.min()), "max": float(x.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--k", type=int, default=100, help="mock per lo stage tda")
    ap.add_argument("--n_diag", type=int, default=20, help="mock per lo stage diag")
    ap.add_argument("--cuts", default="0,1,5,10",
                    help="percentili di field_r da ESCLUDERE (0 = nessun taglio)")
    ap.add_argument("--sigma_scales", default="1.0")
    ap.add_argument("--stage", choices=["all", "diag", "tda"], default="all")
    args = ap.parse_args()

    cuts = [float(c) for c in args.cuts.split(",")]
    scales = [float(s) for s in args.sigma_scales.split(",")]

    root = Path(args.project_root).resolve()
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import paper1_remap as P1
    except Exception as e:
        sys.exit(f"[FATAL] import fallito: {e}")

    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"
    cache_dir = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    out_dir = root / "results" / "paper1"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print(f"CAUCHY Paper 1 - ASIMMETRIA FKP  |  {args.region}")
    print("=" * 76)
    G = P1.setup_region(M, args.region, desi_dir, fld_dir)
    mask = G["mask"]
    field_r = np.asarray(G["field_r"], dtype=np.float64)
    alpha_desi = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], field_r, alpha_desi, mask, M.NGRID)

    rin = field_r[mask]
    report = {"schema_version": "1.0", "script": "paper1_fkp_asymmetry.py",
              "region": args.region, "timestamp": P1._now(),
              "field_r_in_mask": summarize(rin, "field_r entro maschera")}

    # --- geometria: distanza dal bordo e raggio dall'osservatore -------------
    dist_edge = distance_transform_edt(mask)
    ng = M.NGRID
    ax = (np.arange(ng) + 0.5) * M.CELL
    bx = np.asarray(M.BOX_MIN, dtype=np.float64)
    X = (ax[:, None, None] + bx[0])
    Y = (ax[None, :, None] + bx[1])
    Z = (ax[None, None, :] + bx[2])
    radius = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)

    print(f"\n  voxel in maschera: {int(mask.sum())}")
    print(f"  field_r entro maschera: mediana {np.median(rin):.3f}  "
          f"p01 {pct(rin,1):.4f}  p10 {pct(rin,10):.3f}  max {rin.max():.1f}")

    # --- dove stanno i voxel a denominatore basso ---------------------------
    print("\n" + "-" * 76)
    print("DOVE STANNO I VOXEL A DENOMINATORE BASSO")
    print("-" * 76)
    print(f"{'taglio':>8s} {'soglia field_r':>15s} {'n voxel':>9s} | "
          f"{'dist.bordo med.':>16s} {'raggio med.':>12s}")
    de_all = float(np.median(dist_edge[mask]))
    ra_all = float(np.median(radius[mask]))
    print(f"{'(tutti)':>8s} {'-':>15s} {int(mask.sum()):>9d} | "
          f"{de_all:16.2f} {ra_all:12.1f}")
    low_info = {}
    for c in cuts:
        if c <= 0:
            continue
        thr = pct(rin, c)
        sel = mask & (field_r <= thr)
        low_info[str(c)] = {
            "threshold_field_r": thr, "n_voxels": int(sel.sum()),
            "median_dist_edge": float(np.median(dist_edge[sel])),
            "median_radius": float(np.median(radius[sel])),
            "frac_within_2vox_of_edge": float((dist_edge[sel] <= 2).mean()),
            "frac_all_within_2vox": float((dist_edge[mask] <= 2).mean())}
        print(f"{c:7.0f}% {thr:15.5f} {int(sel.sum()):>9d} | "
              f"{low_info[str(c)]['median_dist_edge']:16.2f} "
              f"{low_info[str(c)]['median_radius']:12.1f}")
    report["low_denominator_geometry"] = low_info
    if low_info:
        k0 = list(low_info)[-1]
        print(f"\n  entro 2 voxel dal bordo: {100*low_info[k0]['frac_within_2vox_of_edge']:.1f}% "
              f"dei voxel a basso denominatore, contro "
              f"{100*low_info[k0]['frac_all_within_2vox']:.1f}% di tutti")
        print("  -> se il primo numero e' molto maggiore, l'artefatto e' di bordo")
        print("     e l'erosione lo ha gia' gestito")

    # --- chi produce i delta estremi dei mock -------------------------------
    print("\n" + "-" * 76)
    print("CHI PRODUCE I DELTA ESTREMI DEI MOCK")
    print("-" * 76)
    files = sorted(cache_dir.glob("delta_*.npy"))[:args.n_diag]
    if not files:
        sys.exit("[FATAL] cache vuota.")
    desi_max = float(desi_delta[mask].max())
    print(f"  soglia = max(delta) di DESI = {desi_max:.1f}")
    rows = []
    for fp in files:
        a = np.load(fp).astype(np.float64)
        ext = mask & (a > desi_max)
        r = {"key": fp.stem, "n_extreme": int(ext.sum()),
             "frac_extreme": float(ext.sum() / mask.sum()),
             "max_delta": float(a[mask].max())}
        if ext.sum():
            r["median_field_r_extreme"] = float(np.median(field_r[ext]))
            r["median_dist_edge_extreme"] = float(np.median(dist_edge[ext]))
            r["frac_extreme_in_lowest_1pct"] = float(
                (field_r[ext] <= pct(rin, 1)).mean())
        rows.append(r)
    ne = np.array([r["n_extreme"] for r in rows])
    print(f"  voxel con delta > {desi_max:.0f} : mediana {np.median(ne):.0f} per mock "
          f"({100*np.median(ne)/mask.sum():.4f}% della maschera)")
    if any("median_field_r_extreme" in r for r in rows):
        mf = np.array([r["median_field_r_extreme"] for r in rows
                       if "median_field_r_extreme" in r])
        md = np.array([r["median_dist_edge_extreme"] for r in rows
                       if "median_dist_edge_extreme" in r])
        f1 = np.array([r["frac_extreme_in_lowest_1pct"] for r in rows
                       if "frac_extreme_in_lowest_1pct" in r])
        print(f"  field_r mediano in quei voxel : {np.median(mf):.4f}  "
              f"(mediana globale {np.median(rin):.3f})")
        print(f"  distanza dal bordo mediana    : {np.median(md):.2f} voxel  "
              f"(globale {de_all:.2f})")
        print(f"  frazione nel 1% piu' basso di field_r: {100*np.median(f1):.1f}%")
    report["extreme_voxels"] = rows

    # --- statistiche a un punto con e senza i voxel sospetti ----------------
    print("\n" + "-" * 76)
    print("STATISTICHE A UN PUNTO ESCLUDENDO I VOXEL A BASSO DENOMINATORE")
    print("-" * 76)
    print(f"{'taglio':>8s} | {'DESI var':>10s} {'mock var':>11s} {'rapporto':>9s} | "
          f"{'DESI max':>9s} {'mock max':>10s}")
    op = {}
    for c in cuts:
        sel = mask if c <= 0 else (mask & (field_r > pct(rin, c)))
        dv = desi_delta[sel]
        mvar, mmax = [], []
        for fp in files:
            a = np.load(fp).astype(np.float64)[sel]
            mvar.append(a.var())
            mmax.append(a.max())
        op[str(c)] = {"n_voxels": int(sel.sum()),
                      "desi_var": float(dv.var()), "desi_max": float(dv.max()),
                      "mock_var_mean": float(np.mean(mvar)),
                      "mock_max_mean": float(np.mean(mmax)),
                      "var_ratio": float(np.mean(mvar) / dv.var())}
        print(f"{c:7.0f}% | {dv.var():10.3f} {np.mean(mvar):11.1f} "
              f"{op[str(c)]['var_ratio']:8.1f}x | {dv.max():9.1f} {np.mean(mmax):10.1f}")
    report["onepoint_by_cut"] = op
    print("\n  se il rapporto delle varianze crolla tagliando, l'anomalia a un punto")
    print("  in delta e' guidata dai voxel a denominatore piccolo")

    # --- STAGE TDA: il deficit sopravvive escludendoli? ---------------------
    if args.stage in ("all", "tda"):
        print("\n" + "=" * 76)
        print("TEST DECISIVO — filtrazione ristretta ai voxel a denominatore alto")
        print("=" * 76)
        tda_files = sorted(cache_dir.glob("delta_*.npy"))[:args.k]
        res = {}
        for s in scales:
            sig = M.SIGMA_PX * s
            tag = f"R{int(round(s*5))}"
            nu_desi_full = P1.build_nu(desi_delta, mask, sig)
            for c in cuts:
                sel = mask if c <= 0 else (mask & (field_r > pct(rin, c)))
                d_r, _ = P1.tda_full(nu_desi_full, sel, M.N_THRESH, False)
                vals = []
                t0 = time.time()
                for i, fp in enumerate(tda_files):
                    a = np.load(fp).astype(np.float64)
                    r, _ = P1.tda_full(P1.build_nu(a, mask, sig), sel, M.N_THRESH, False)
                    vals.append(r["N_H1"])
                    if (i + 1) % 25 == 0:
                        print(f"    {tag} taglio {c:.0f}%: {i+1}/{len(tda_files)} "
                              f"({(time.time()-t0)/(i+1):.1f}s/mock)")
                v = np.array(vals)
                D = v.mean() - d_r["N_H1"]
                res[f"{tag}_cut{c:g}"] = {
                    "R": tag, "cut_pct": c, "n_voxels": int(sel.sum()),
                    "n_mocks": int(v.size), "desi_N_H1": d_r["N_H1"],
                    "mock_mean": float(v.mean()), "mock_std": float(v.std(ddof=1)),
                    "D": float(D), "D_frac": float(D / v.mean()),
                    "z": float((d_r["N_H1"] - v.mean()) / v.std(ddof=1))}
                r0 = res[f"{tag}_cut{c:g}"]
                print(f"  {tag} taglio {c:4.0f}% ({int(sel.sum()):>7d} vox): "
                      f"DESI {r0['desi_N_H1']:7.0f}  mock {r0['mock_mean']:8.1f}  "
                      f"D/base {100*r0['D_frac']:+6.2f}%  z {r0['z']:+6.2f}")
        report["tda_by_cut"] = res
        print("\n  se D/base e z restano stabili al crescere del taglio,")
        print("  il deficit NON e' guidato dall'asimmetria di pesatura")

    report["notes"] = (
        "L'asimmetria e' nella pipeline originale: voxelize_mock usa np.ones() "
        "mentre load_desi_data_field usa WEIGHT*WEIGHT_FKP e load_desi_random_field "
        "usa WEIGHT_FKP. build_field e' invece identico sui due lati. Per DESI il "
        "peso FKP si cancella fra numeratore e denominatore, per i mock no. Il "
        "test primario di remapping controlla gia' l'effetto a livello di "
        "distribuzione marginale (imponendo ai mock la PDF di DESI il deficit non "
        "si riduce); questo script verifica il residuo spaziale.")
    P1.atomic_write_text(out_dir / f"paper1_fkp_asymmetry_{args.region}.json",
                         json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n[scritto] paper1_fkp_asymmetry_{args.region}.json")
    print("\n[fine]")


if __name__ == "__main__":
    main()
