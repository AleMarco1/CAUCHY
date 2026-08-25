#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 4
src/paper1_mirror_likeforlike.py

ESPERIMENTO SPECULARE LIKE-FOR-LIKE
(raffinamento post-registrazione del protocollo v2 §7)

IL PROBLEMA
-----------
Il test primario (§4) rimappa ogni mock sulla scala di quantili **grezza** di
DESI: bersaglio a singola realizzazione. Lo speculare (§7) rimappa DESI sulla
scala **media** dei 2000 mock: bersaglio molto piu' liscio. Le due operazioni
non sono dello stesso tipo, quindi f_1p e g_1p non sono confrontabili.

E' lo stesso errore di disegno gia' trovato e corretto nel null test
(`paper1_null_mockmock.py`), dove il bersaglio medio produceva un bias di
-4.54 +/- 1.07 loop mentre quello a singola realizzazione da' -0.88 +/- 2.14.

Sintomo nei dati: il deficit corretto in avanti e' stabile (23.69% +/- 2.60%
su sette scale), quello speculare no (14.67% +/- 8.32%).

LA CORREZIONE
-------------
Rimappare DESI sulla scala **grezza di un singolo mock**, ripetendo su un
campione di mock bersaglio e mediando. Si ottiene:
  * g_1p con vere barre d'errore (dispersione fra bersagli), non un numero solo;
  * simmetria esatta col test primario: singola realizzazione contro singola
    realizzazione, in entrambi i versi.

Bersagli: indici equispaziati sull'intera cache (deterministico, nessun seme).

EFFICIENZA
----------
La rimappatura agisce sul delta GREZZO, che non dipende dallo smoothing:
per ogni bersaglio si rimappa UNA volta e si filtra a tutte le scale.
Costo ~ n_targets x n_scale valutazioni TDA (50 x 7 ~ 50 min).

USO
---
  python src\\paper1_mirror_likeforlike.py --project_root D:\\projects\\cauchy --region NGC

  # piu' bersagli, barre piu' strette
  python src\\paper1_mirror_likeforlike.py ... --n_targets 100

  # solo alcune scale
  python src\\paper1_mirror_likeforlike.py ... --sigma_scales 1.0,4.0,6.0

Riprendibile: rilanciare lo stesso comando riparte da dove si era fermato.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def tag_for(scale):
    return f"R{int(round(scale * 5))}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--n_targets", type=int, default=50,
                    help="quanti mock usare come bersaglio (default 50)")
    ap.add_argument("--sigma_scales", default="1.0,2.0,2.4,3.0,3.4,4.0,6.0",
                    help="moltiplicatori di sigma_px (R5,R10,R12,R15,R17,R20,R30)")
    args = ap.parse_args()

    scales = [float(x) for x in args.sigma_scales.split(",")]
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
    print(f"CAUCHY Paper 1 - SPECULARE like-for-like  |  {args.region}  "
          f"bersagli={args.n_targets}")
    print("=" * 74)
    P1.cleanup_tmp(cache_dir, out_dir)

    G = P1.setup_region(M, args.region, desi_dir, fld_dir)
    mask = G["mask"]
    sigma0 = M.SIGMA_PX

    # ---- campo DESI --------------------------------------------------------
    alpha = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], G["field_r"], alpha, mask, M.NGRID)

    print("\n  DESI, riferimento a ogni scala:")
    desi_ref = {}
    for s in scales:
        r, _ = P1.tda_full(P1.build_nu(desi_delta, mask, sigma0 * s), mask,
                           M.N_THRESH, False)
        desi_ref[tag_for(s)] = r
        print(f"    {tag_for(s):>4s}: N_H1 = {r['N_H1']:8.0f}   b1_peak = {r['b1_peak']:7.0f}")

    # ---- speculare VECCHIO (scala media) per confronto ----------------------
    all_files = sorted(cache_dir.glob("delta_*.npy"))
    lad_p = out_dir / f"null_ladder_{args.region}_n{len(all_files)}.npy"
    mirror_old = {}
    if lad_p.exists():
        Q0 = np.load(lad_p)
        p0 = (np.arange(Q0.size, dtype=np.float64) + 0.5) / Q0.size
        d_old = P1.remap_delta(desi_delta, mask, Q0, p0)
        print("\n  speculare VECCHIO (bersaglio = scala media dei mock):")
        for s in scales:
            r, _ = P1.tda_full(P1.build_nu(d_old, mask, sigma0 * s), mask,
                               M.N_THRESH, False)
            mirror_old[tag_for(s)] = r["N_H1"]
            print(f"    {tag_for(s):>4s}: N_H1 = {r['N_H1']:8.0f}")
    else:
        print(f"\n  [avviso] scala media non trovata ({lad_p.name}); confronto omesso")

    # ---- bersagli: indici equispaziati sulla cache -------------------------
    if not all_files:
        sys.exit("[FATAL] cache vuota.")
    n_t = min(args.n_targets, len(all_files))
    idx = np.unique(np.round(np.linspace(0, len(all_files) - 1, n_t)).astype(int))
    targets = [all_files[i] for i in idx]
    print(f"\n  bersagli: {len(targets)} mock equispaziati "
          f"({targets[0].stem} ... {targets[-1].stem})")

    jsonl = out_dir / f"per_target_{args.region}_mirror_lfl.jsonl"
    done = P1.read_jsonl(jsonl)
    need = {tag_for(s) for s in scales}
    todo = [fp for fp in targets
            if not (fp.stem in done and need <= set(done[fp.stem].get("cells", {})))]
    print(f"  gia' fatti: {len(targets)-len(todo)}   da fare: {len(todo)}")

    t0 = time.time()
    for j, fp in enumerate(todo):
        try:
            # scala GREZZA del mock bersaglio
            lad = np.sort(np.load(fp).astype(np.float64)[mask])
            p = (np.arange(lad.size, dtype=np.float64) + 0.5) / lad.size
            # la rimappatura e' sul delta grezzo: UNA volta per tutte le scale
            d_remap = P1.remap_delta(desi_delta, mask, lad, p)
            cells = {}
            for s in scales:
                r, _ = P1.tda_full(P1.build_nu(d_remap, mask, sigma0 * s), mask,
                                   M.N_THRESH, False)
                cells[tag_for(s)] = {"N_H1": r["N_H1"], "b1_peak": r["b1_peak"]}
            P1.append_jsonl(jsonl, {"key": fp.stem, "ts": P1._now(), "cells": cells})
        except KeyboardInterrupt:
            print("\n  [interrotto] risultati salvati; rilancia per riprendere.")
            raise
        except Exception as e:
            print(f"  [{fp.stem}] ERRORE: {type(e).__name__}: {e} - salto")
            continue
        if (j + 1) % 5 == 0 or j == 0:
            el = time.time() - t0
            print(f"  [{j+1}/{len(todo)}]  ({el/(j+1):.0f}s/bersaglio, "
                  f"ETA {el/(j+1)*(len(todo)-j-1)/60:.0f} min)")

    # ---- report -------------------------------------------------------------
    rec = P1.read_jsonl(jsonl)
    rows = list(rec.values())
    print("\n" + "=" * 96)
    print(f"REPORT — speculare like-for-like, {len(rows)} bersagli")
    print("=" * 96)
    print(f"{'R':>5s} | {'DESI':>7s} {'mirror lfl':>11s} {'sd':>6s} {'SEM':>5s} | "
          f"{'g_1p lfl':>9s} {'±':>7s} | {'g_1p vecchio':>12s} | {'D corr lfl':>11s} {'%':>7s}")
    print("-" * 96)

    out = {"schema_version": "1.0", "script": "paper1_mirror_likeforlike.py",
           "protocol": "v2 §7 - raffinamento POST-REGISTRAZIONE (§12)",
           "timestamp": P1._now(), "region": args.region,
           "n_targets": len(rows), "target_selection": "indici equispaziati sulla cache",
           "desi_reference": desi_ref, "results": {}}

    for s in scales:
        tg = tag_for(s)
        vals = np.array([r["cells"][tg]["N_H1"] for r in rows
                         if tg in r.get("cells", {})])
        if vals.size < 3:
            continue
        # baseline mock dal run primario corrispondente
        rep = out_dir / f"paper1_remap_{args.region}_{tg}.json"
        base = D = None
        if rep.exists():
            j0 = json.loads(rep.read_text())
            base = j0["mock_baseline_mean"]
            D = j0["D"]
        d0 = desi_ref[tg]["N_H1"]
        mu, sd = vals.mean(), vals.std(ddof=1)
        sem = sd / np.sqrt(vals.size)
        g_new = (mu - d0) / D if D else float("nan")
        g_sem = sem / abs(D) if D else float("nan")
        g_old = ((mirror_old[tg] - d0) / D) if (tg in mirror_old and D) else float("nan")
        Dc = (base - mu) if base is not None else float("nan")
        print(f"{tg:>5s} | {d0:7.0f} {mu:11.1f} {sd:6.1f} {sem:5.1f} | "
              f"{g_new:+9.3f} {g_sem:7.3f} | {g_old:+12.3f} | {Dc:11.1f} "
              f"{100*Dc/base if base else float('nan'):+6.2f}%")
        out["results"][tg] = {
            "R": tg, "sigma_px": sigma0 * s, "n_targets": int(vals.size),
            "desi_N_H1": float(d0), "mirror_lfl_mean": float(mu),
            "mirror_lfl_std": float(sd), "mirror_lfl_sem": float(sem),
            "mirror_old_meanladder": mirror_old.get(tg),
            "mock_baseline_mean": base, "D": D,
            "g_1p_lfl": float(g_new), "g_1p_lfl_sem": float(g_sem),
            "g_1p_old": float(g_old), "D_corrected_mirror_lfl": float(Dc),
            "D_corrected_mirror_lfl_frac": float(Dc / base) if base else None}

    fr = [out["results"][t]["D_corrected_mirror_lfl_frac"] for t in out["results"]
          if out["results"][t]["D_corrected_mirror_lfl_frac"] is not None]
    if fr:
        fr = 100 * np.array(fr)
        print("-" * 96)
        print(f"\n  Deficit corretto speculare (like-for-like): media {fr.mean():.2f}%  "
              f"sd {fr.std(ddof=1):.2f}%  [{fr.min():.2f}% .. {fr.max():.2f}%]")
        print(f"  Confronto: corretto AVANTI = 23.69% +/- 2.60%")
        print(f"             speculare VECCHIO (scala media) = 14.67% +/- 8.32%")
        out["summary"] = {"corrected_mirror_lfl_mean_pct": float(fr.mean()),
                          "corrected_mirror_lfl_sd_pct": float(fr.std(ddof=1))}

    out["notes"] = (
        "Speculare simmetrico al test primario: DESI viene rimappato sulla scala di "
        "quantili GREZZA di singoli mock (bersaglio a singola realizzazione), non sulla "
        "scala media dei 2000. La dispersione fra bersagli fornisce barre d'errore su "
        "g_1p, che nella versione pre-registrata era un numero singolo senza incertezza. "
        "Se il deficit corretto speculare converge verso quello in avanti (~24%), la "
        "discordanza avanti/speculare era un artefatto di asimmetria del bersaglio.")
    P1.atomic_write_text(out_dir / f"paper1_mirror_lfl_{args.region}.json",
                         json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[scritto] paper1_mirror_lfl_{args.region}.json")
    print("\n[fine]")


if __name__ == "__main__":
    main()
