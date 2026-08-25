#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 3
src/paper1_mask_erosion.py

TEST DI EROSIONE DELLA MASCHERA (protocollo v2 §9.4)
Caveat bloccante n.1 del record congelato.

DOMANDA
-------
L'inversione di segno del deficit a R >= 20 Mpc/h e' fisica o e' un artefatto
di contaminazione di bordo?

IL PROBLEMA
-----------
`build_nu` applica `gaussian_filter` all'INTERO cubo, con zeri fuori maschera,
e solo dopo riazzera l'esterno. I voxel vicini al bordo ricevono quindi segnale
dal vuoto esterno. Il footprint NGC ha profondita' mediana di soli 3 voxel:

  R (Mpc/h)   sigma_px   voxel con w < 0.99   w medio
      5        0.3204          7.8%           0.998
     10        0.6408         25.8%           0.959
     20        1.2817         49.6%           0.916
     30        1.9225         66.9%           0.882

(w = frazione del peso del kernel proveniente da DENTRO la maschera.)

IL TEST
-------
Modalita' **restrict** (primaria): il campo nu viene costruito con la maschera
PIENA — lo smoothing usa tutta l'informazione disponibile — ma la FILTRAZIONE
viene ristretta alla maschera EROSA. Si escludono cosi' dalla topologia proprio
i voxel che hanno ricevuto contaminazione, senza degradare il campo altrove.

Modalita' **rebuild** (secondaria): la maschera erosa viene usata gia' nella
costruzione del campo. Risponde a una domanda diversa ("e se la survey fosse
piu' piccola?") e ha una propria contaminazione di bordo: e' un controllo, non
il test principale.

Erosione euclidea: `distance_transform_edt(mask) > k`, isotropa come il kernel.

ESITO ATTESO E CRITERIO
-----------------------
Se il segno di D = <N_H1(mock)> - N_H1(DESI) resta NEGATIVO a R20/R30 per tutti
i livelli di erosione, l'inversione e' robusta e pubblicabile. Se il segno si
inverte o svanisce erodendo, era un artefatto di bordo e quei punti escono.

Un test preliminare su campi surrogati (stessa fase, PDF diverse) indica che
l'effetto di bordo e' in gran parte MODO COMUNE: la risposta differenziale a
R30 resta +28.3% -> +27.8% eliminando il 44% dei voxel. Questo test lo verifica
sui campi veri.

USO
---
  # test standard (~4 h su 200 mock: R5 di controllo + R20 + R30, erosioni 0/2/3)
  python src\\paper1_mask_erosion.py --project_root D:\\projects\\cauchy --region NGC --k 200

  # solo diagnostica geometrica, nessuna TDA (secondi)
  python src\\paper1_mask_erosion.py ... --stage diag

  # piu' leggero
  python src\\paper1_mask_erosion.py ... --k 100 --sigma_scales 4.0,6.0 --erosions 0,3

  # controllo secondario
  python src\\paper1_mask_erosion.py ... --mode rebuild --k 100

Riprendibile: rilanciare lo stesso comando riparte da dove si era fermato.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt


def tag_for(scale):
    """1.0 -> R5, 2.0 -> R10, 4.0 -> R20 ..."""
    return f"R{int(round(scale * 5))}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--sigma_scales", default="1.0,4.0,6.0",
                    help="moltiplicatori di sigma_px (1.0=R5, 4.0=R20, 6.0=R30)")
    ap.add_argument("--erosions", default="0,2,3",
                    help="livelli di erosione in voxel")
    ap.add_argument("--mode", choices=["restrict", "rebuild"], default="restrict")
    ap.add_argument("--stage", choices=["all", "diag"], default="all")
    args = ap.parse_args()

    scales = [float(x) for x in args.sigma_scales.split(",")]
    erosions = [int(x) for x in args.erosions.split(",")]

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

    print("=" * 74)
    print(f"CAUCHY Paper 1 - EROSIONE MASCHERA  |  {args.region}  "
          f"K={args.k}  modo={args.mode}")
    print("=" * 74)
    P1.cleanup_tmp(cache_dir, out_dir)

    G = P1.setup_region(M, args.region, desi_dir, fld_dir)
    mask_full = G["mask"]
    sigma0 = M.SIGMA_PX

    # ---- maschere erose (euclidee) e diagnostica ---------------------------
    dist = distance_transform_edt(mask_full)
    masks = {}
    print(f"\n{'erosione':>9s} {'voxel':>9s} {'% pieno':>8s} | "
          + " ".join(f"{'w@'+tag_for(s):>9s}" for s in scales))
    for er in erosions:
        m = mask_full if er == 0 else (dist > er)
        masks[er] = m
        ws = []
        for s in scales:
            w = gaussian_filter(mask_full.astype(np.float64), sigma=sigma0 * s)[m]
            ws.append(w.mean())
        print(f"{er:>9d} {int(m.sum()):>9d} {100*m.sum()/mask_full.sum():7.1f}% | "
              + " ".join(f"{w:9.4f}" for w in ws))
        if m.sum() < 20000:
            print(f"    [avviso] erosione {er}: pochi voxel residui, risultato fragile")
    print("\n  w = frazione del peso del kernel proveniente da dentro la maschera piena")
    print("      (w -> 1 significa contaminazione di bordo trascurabile)")

    diag = {"mask_full_voxels": int(mask_full.sum()),
            "median_depth_voxels": float(np.median(dist[mask_full])),
            "max_depth_voxels": float(dist.max()),
            "levels": {str(er): {"voxels": int(masks[er].sum()),
                                 "frac_of_full": float(masks[er].sum() / mask_full.sum()),
                                 "w_mean": {tag_for(s): float(gaussian_filter(
                                     mask_full.astype(np.float64),
                                     sigma=sigma0 * s)[masks[er]].mean())
                                     for s in scales}}
                       for er in erosions}}
    if args.stage == "diag":
        P1.atomic_write_text(out_dir / f"paper1_erosion_diag_{args.region}.json",
                             json.dumps(diag, indent=2))
        print(f"\n[scritto] paper1_erosion_diag_{args.region}.json")
        return

    # ---- riferimento DESI a ogni (scala, erosione) -------------------------
    alpha = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], G["field_r"], alpha, mask_full, M.NGRID)
    print("\n  DESI:")
    desi = {}
    for s in scales:
        nu_full = P1.build_nu(desi_delta, mask_full, sigma0 * s)
        for er in erosions:
            m = masks[er]
            nu = nu_full if args.mode == "restrict" else \
                P1.build_nu(desi_delta, m, sigma0 * s)
            r, _ = P1.tda_full(nu, m, M.N_THRESH, False)
            desi[(s, er)] = r
            print(f"    {tag_for(s):>4s} er={er}: N_H1={r['N_H1']:8.0f}  "
                  f"b1_peak={r['b1_peak']:7.0f}")

    # ---- mock ---------------------------------------------------------------
    P1.validate_cache(cache_dir, M.NGRID)
    files = sorted(cache_dir.glob("delta_*.npy"))[:args.k]
    if not files:
        sys.exit("[FATAL] cache vuota.")
    jsonl = out_dir / f"per_mock_{args.region}_erosion_{args.mode}.jsonl"
    done = P1.read_jsonl(jsonl)
    need = {f"{tag_for(s)}_er{er}" for s in scales for er in erosions}
    todo = [fp for fp in files
            if not (fp.stem in done and need <= set(done[fp.stem].get("cells", {})))]
    print(f"\n  mock in cache: {len(files)}   da fare: {len(todo)}")

    t0 = time.time()
    for j, fp in enumerate(todo):
        try:
            delta = np.load(fp).astype(np.float64)
            cells = {}
            for s in scales:
                nu_full = P1.build_nu(delta, mask_full, sigma0 * s) \
                    if args.mode == "restrict" else None
                for er in erosions:
                    m = masks[er]
                    nu = nu_full if args.mode == "restrict" else \
                        P1.build_nu(delta, m, sigma0 * s)
                    r, _ = P1.tda_full(nu, m, M.N_THRESH, False)
                    cells[f"{tag_for(s)}_er{er}"] = {"N_H1": r["N_H1"],
                                                     "b1_peak": r["b1_peak"]}
            P1.append_jsonl(jsonl, {"key": fp.stem, "mode": args.mode,
                                    "ts": P1._now(), "cells": cells})
        except KeyboardInterrupt:
            print("\n  [interrotto] risultati salvati; rilancia per riprendere.")
            raise
        except Exception as e:
            print(f"  [{fp.stem}] ERRORE: {type(e).__name__}: {e} - salto")
            continue
        if (j + 1) % 5 == 0 or j == 0:
            el = time.time() - t0
            print(f"  [{j+1}/{len(todo)}]  ({el/(j+1):.0f}s/mock, "
                  f"ETA {el/(j+1)*(len(todo)-j-1)/3600:.1f} h)")

    # ---- report -------------------------------------------------------------
    rec = P1.read_jsonl(jsonl)
    rows = [v for v in rec.values() if v.get("mode") == args.mode]
    print("\n" + "=" * 74)
    print(f"REPORT — modo {args.mode}, {len(rows)} mock")
    print("=" * 74)
    print(f"{'R':>5s} {'eros':>5s} {'voxel%':>7s} | {'DESI':>8s} {'mock':>9s} "
          f"{'±':>7s} | {'D':>9s} {'D/base':>8s} {'z':>7s}")
    print("-" * 74)

    out = {"schema_version": "1.0", "script": "paper1_mask_erosion.py",
           "protocol": "v2 §9.4 - caveat bloccante n.1", "timestamp": P1._now(),
           "region": args.region, "mode": args.mode, "n_mocks": len(rows),
           "diagnostics": diag, "results": {}}
    signs = {}
    for s in scales:
        for er in erosions:
            key = f"{tag_for(s)}_er{er}"
            vals = np.array([r["cells"][key]["N_H1"] for r in rows
                             if key in r.get("cells", {})])
            if vals.size < 3:
                continue
            d = desi[(s, er)]["N_H1"]
            mu, sd = vals.mean(), vals.std(ddof=1)
            D = mu - d
            z = (d - mu) / sd
            print(f"{tag_for(s):>5s} {er:>5d} "
                  f"{100*masks[er].sum()/mask_full.sum():6.1f}% | {d:8.0f} {mu:9.1f} "
                  f"{sd:7.1f} | {D:+9.1f} {100*D/mu:+7.2f}% {z:+7.2f}")
            out["results"][key] = {"R": tag_for(s), "erosion": er,
                                   "n_mocks": int(vals.size),
                                   "voxel_frac": float(masks[er].sum()/mask_full.sum()),
                                   "desi_N_H1": float(d), "mock_mean": float(mu),
                                   "mock_std": float(sd), "D": float(D),
                                   "D_frac": float(D/mu), "z": float(z)}
            signs.setdefault(tag_for(s), []).append(np.sign(D))
        print("-" * 74)

    print("\nSTABILITA' DEL SEGNO DI D SOTTO EROSIONE:")
    verdict = {}
    for R, sg in signs.items():
        stable = len(set(sg)) == 1
        verdict[R] = "STABILE" if stable else "INSTABILE"
        mark = "OK  " if stable else "*** "
        print(f"  {mark}{R:>5s}: segni {[int(x) for x in sg]} -> {verdict[R]}")
    out["sign_stability"] = verdict
    out["notes"] = (
        "Modo 'restrict': nu costruito con maschera piena (smoothing su tutta "
        "l'informazione), filtrazione ristretta alla maschera erosa -> esclude dalla "
        "topologia i voxel contaminati dal bordo. Modo 'rebuild': maschera erosa usata "
        "gia' nella costruzione del campo (controllo secondario, ha una propria "
        "contaminazione di bordo). Criterio: se il segno di D resta invariato a "
        "R>=20 per tutte le erosioni, l'inversione di segno del deficit e' robusta.")
    P1.atomic_write_text(out_dir / f"paper1_erosion_{args.region}_{args.mode}.json",
                         json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[scritto] paper1_erosion_{args.region}_{args.mode}.json")
    print("\n[fine]")


if __name__ == "__main__":
    main()
