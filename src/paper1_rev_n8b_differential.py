#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n8b_differential.py

N8b - LA MASCHERA PRESERVA IL CONFRONTO FRA DUE CAMPI?

PERCHE' SERVE
-------------
N8 ha misurato il bias ASSOLUTO indotto dalla maschera: densita' di loop sotto
maschera contro densita' sul campo intero. Esito su 128^3, 240 configurazioni:

  w_bar riduce la dispersione del bias del 16.2% soltanto
    (profondita' 2.2%, superficie/volume 7.4%)
  bias a w_bar = 0.99: da -0.212 (guscio) a -0.411 (cuneo)
    escursione 0.199, MAGGIORE della dispersione residua che w_bar lascia

Conclusione: a w_bar fissata la FORMA determina il bias piu' di w_bar. Il
criterio non e' trasferibile fra topologie, e "survey-independent" deve uscire
dal testo.

MA il caso d'uso del paper e' DIFFERENZIALE: DESI e mock attraverso la STESSA
maschera. Un bias comune si cancella. Quindi il risultato di N8 non intacca la
misura su DESI - intacca l'affermazione di generalita'.

La domanda che valida davvero l'uso del paper e' un'altra:

    la maschera distorce allo stesso modo due campi con statistiche diverse?

  SI  -> il confronto DESI-mock e' protetto qualunque sia il bias assoluto, e
         il paper puo' dirlo con una misura invece che per assunzione
  NO  -> la maschera contamina proprio il confronto, e il bias differenziale
         va propagato nella banda sistematica di Sez. 6.3

IL DISEGNO
----------
Due campi con LO STESSO rumore bianco e pendenza spettrale diversa: sono la
coppia piu' simile possibile a meno dello spettro, quindi il confronto isola
l'effetto della maschera sulla differenza e non sulla realizzazione.

    Delta_vero  = rho_A(cubo intero) / rho_B(cubo intero) - 1
    Delta_masch = rho_A(maschera)    / rho_B(maschera)    - 1
    bias differenziale = Delta_masch - Delta_vero

Il campo A e' quello gia' calcolato da N8 (pendenza -1.5): questo script
calcola solo il campo B e ricombina. Serve quindi che n8_masks_128.jsonl esista.

AUTOCONTROLLI
-------------
  1. le configurazioni di A e B devono appaiarsi una a una su
     (forma, spessore, sigma, realizzazione)
  2. Delta_vero deve essere significativamente diverso da zero, altrimenti il
     test non ha potere: due campi indistinguibili non possono rivelare una
     distorsione del confronto
  3. il bias differenziale deve tendere a zero per w_bar -> 1

USO
---
  python src\\paper1_rev_n8b_differential.py --ngrid 64      # pilota
  python src\\paper1_rev_n8b_differential.py
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

SIGMA_FID = 0.3204385518606827
SHAPES = ("slab", "shell", "tube", "wedge", "slab_holes")


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_jsonl(path):
    recs = []
    if not Path(path).exists():
        return recs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
        f.flush(); os.fsync(f.fileno())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--ngrid", type=int, default=128)
    ap.add_argument("--n_real", type=int, default=2)
    ap.add_argument("--n_thresh", type=int, default=100)
    ap.add_argument("--slope_a", type=float, default=-1.5,
                    help="pendenza usata da N8 (per etichettare)")
    ap.add_argument("--slope_b", type=float, default=-2.3)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    # riuso le funzioni di N8 senza duplicarle
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "n8", str(root / "src" / "paper1_rev_n8_masks.py"))
    n8 = importlib.util.module_from_spec(spec)
    sys.argv = [sys.argv[0]]          # N8 fa argparse all'import di main, non qui
    spec.loader.exec_module(n8)

    n = args.ngrid
    ja = res / "paper1" / f"n8_masks_{n}.jsonl"
    jb = res / "paper1" / f"n8b_masks_{n}_B.jsonl"
    A = read_jsonl(ja)
    if not A:
        print(f"[FATAL] {ja} non trovato: esegui prima N8 alla stessa griglia.")
        return
    print("=" * 78)
    print(f"N8b - BIAS DIFFERENZIALE   griglia {n}^3")
    print("=" * 78)
    print(f"  campo A: pendenza {args.slope_a} (da N8, {len(A)} config)")
    print(f"  campo B: pendenza {args.slope_b} (calcolato qui)")

    thick = sorted({r["T"] for r in A if r["shape"] != "__full__"})
    sigmas = sorted({r["sigma"] for r in A})
    reals = sorted({r["real"] for r in A})
    print(f"  spessori {thick}   sigma {[round(s,4) for s in sigmas]}   "
          f"realizzazioni {reals}")

    done = {(r["shape"], r["T"], round(r["sigma"], 6), r["real"])
            for r in read_jsonl(jb)}
    t0 = time.time(); cnt = 0
    for real in reals:
        f0 = n8.gaussian_field(n, seed=1000 + real, slope=args.slope_b)
        for sigma in sigmas:
            fs = gaussian_filter(f0, sigma=sigma, mode="constant", cval=0.0)
            full = np.ones((n, n, n), bool)
            if ("__full__", 0, round(sigma, 6), real) not in done:
                v = float(M.compute_tda_features(fs.astype(np.float32), full,
                                                 args.n_thresh, masked=False)[4])
                append_jsonl(jb, {"shape": "__full__", "T": 0, "sigma": sigma,
                                  "real": real, "N_H1": v,
                                  "rho": v / full.sum()})
                cnt += 1
            for shape in SHAPES:
                for T in thick:
                    if (shape, T, round(sigma, 6), real) in done:
                        continue
                    mk = n8.make_mask(shape, n, T,
                                      np.random.default_rng(7 + real))
                    if mk.sum() < 2000:
                        continue
                    st = n8.mask_stats(mk, sigma)
                    v = float(M.compute_tda_features(fs.astype(np.float32), mk,
                                                     args.n_thresh,
                                                     masked=True)[4])
                    append_jsonl(jb, {"shape": shape, "T": T, "sigma": sigma,
                                      "real": real, "N_H1": v,
                                      "rho": v / mk.sum(), **st})
                    cnt += 1
                    if cnt % 20 == 0:
                        print(f"    [{cnt}] {shape:>10s} T={T:>2d} "
                              f"sigma={sigma:.3f}   "
                              f"{(time.time()-t0)/cnt:.1f} s/config")

    # ---------------------------------------------------------- analisi
    B = read_jsonl(jb)
    key = lambda r: (r["shape"], r["T"], round(r["sigma"], 6), r["real"])
    dA = {key(r): r for r in A}
    dB = {key(r): r for r in B}
    common = sorted(set(dA) & set(dB), key=lambda k: (k[0], k[2], k[1]))
    print(f"\n  configurazioni appaiate A/B: {len(common)}")
    if len(common) < 20:
        print("  troppe poche per l'analisi.")
        return

    refA = {(k[2], k[3]): dA[k]["rho"] for k in common if k[0] == "__full__"}
    refB = {(k[2], k[3]): dB[k]["rho"] for k in common if k[0] == "__full__"}
    rows = []
    for k in common:
        if k[0] == "__full__":
            continue
        sr = (k[2], k[3])
        if sr not in refA or sr not in refB:
            continue
        d_true = refA[sr] / refB[sr] - 1.0
        d_mask = dA[k]["rho"] / dB[k]["rho"] - 1.0
        rows.append({"shape": k[0], "T": k[1], "sigma": k[2], "real": k[3],
                     "w_bar": dA[k]["w_bar"], "depth": dA[k]["depth_median"],
                     "delta_true": d_true, "delta_mask": d_mask,
                     "bias_diff": d_mask - d_true,
                     "bias_abs_A": dA[k]["rho"] / refA[sr] - 1.0,
                     "bias_abs_B": dB[k]["rho"] / refB[sr] - 1.0})

    dt = np.array([r["delta_true"] for r in rows])
    bd = np.array([r["bias_diff"] for r in rows])
    ba = np.array([r["bias_abs_A"] for r in rows])
    w = np.array([r["w_bar"] for r in rows])

    print("\n" + "=" * 78)
    print("AUTOCONTROLLI")
    print("=" * 78)
    print(f"  2. Delta_vero (differenza fra i due campi senza maschera): "
          f"{dt.mean():+.4f} +/- {dt.std(ddof=1):.4f}")
    if abs(dt.mean()) < 0.05:
        print(f"     *** i due campi sono troppo simili: il test ha poca")
        print(f"         potenza. Aumenta la separazione con --slope_b. ***")
    else:
        print(f"     OK: i campi differiscono del {100*abs(dt.mean()):.1f}%, "
              f"abbastanza per rivelare una distorsione del confronto.")
    hi = bd[w > 0.998]
    if hi.size:
        print(f"  3. bias differenziale a w_bar > 0.998: {hi.mean():+.4f} "
              f"+/- {hi.std(ddof=1) if hi.size>1 else 0:.4f}  ({hi.size} config)")

    print("\n" + "=" * 78)
    print("IL RISULTATO: IL BIAS SI CANCELLA NEL CONFRONTO?")
    print("=" * 78)
    print(f"  bias ASSOLUTO (campo A):        {ba.mean():+.4f} +/- "
          f"{ba.std(ddof=1):.4f}")
    print(f"  bias DIFFERENZIALE (A vs B):    {bd.mean():+.4f} +/- "
          f"{bd.std(ddof=1):.4f}")
    canc = 1.0 - bd.std(ddof=1) / ba.std(ddof=1)
    print(f"  cancellazione: {100*canc:.1f}% della dispersione del bias")
    print(f"                 assoluto sparisce nel confronto")

    print(f"\n  per forma, a w_bar >= 0.99:")
    print(f"    {'forma':>12s} {'n':>4s} {'bias assoluto':>15s} "
          f"{'bias differenziale':>19s}")
    per_shape = {}
    for shape in SHAPES:
        s = [r for r in rows if r["shape"] == shape and r["w_bar"] >= 0.99]
        if len(s) < 2:
            continue
        a = np.array([r["bias_abs_A"] for r in s])
        b = np.array([r["bias_diff"] for r in s])
        print(f"    {shape:>12s} {len(s):>4d} {a.mean():>+15.4f} "
              f"{b.mean():>+19.4f}")
        per_shape[shape] = {"n": len(s), "bias_abs": float(a.mean()),
                            "bias_diff": float(b.mean())}
    if len(per_shape) >= 2:
        va = [v["bias_abs"] for v in per_shape.values()]
        vd = [v["bias_diff"] for v in per_shape.values()]
        print(f"\n    escursione fra forme: assoluto {max(va)-min(va):.4f}, "
              f"differenziale {max(vd)-min(vd):.4f}")

    # Il giudizio va dato NEL REGIME DI VALIDITA' dichiarato dal paper
    # (w_bar >= 0.99). Mescolarci le configurazioni a w_bar basso, dove il
    # differenziale e' grande per costruzione, rende il verdetto fuorviante.
    sel = w >= 0.99
    bd99, ba99 = bd[sel], ba[sel]
    print(f"\n  RISTRETTO AL REGIME DI VALIDITA' (w_bar >= 0.99, "
          f"{int(sel.sum())} config):")
    if sel.sum() >= 3:
        print(f"    bias assoluto      {ba99.mean():+.4f} +/- {ba99.std(ddof=1):.4f}")
        print(f"    bias differenziale {bd99.mean():+.4f} +/- {bd99.std(ddof=1):.4f}")
        print(f"    cancellazione      "
              f"{100*(1-bd99.std(ddof=1)/ba99.std(ddof=1)):.1f}%")

    print("\n  LETTURA:")
    if sel.sum() >= 3 and abs(bd99.mean()) < 0.03 and \
            bd99.std(ddof=1) < 0.4 * ba99.std(ddof=1):
        print("    Il bias si cancella largamente nel confronto: la maschera")
        print("    distorce i due campi allo stesso modo. Il confronto")
        print("    DESI-mock e' protetto, e ora si puo' dirlo con una misura")
        print("    invece che per assunzione. Cade l'affermazione di")
        print("    trasferibilita' del criterio, non il risultato.")
    else:
        print(f"    Il bias NON si cancella: resta un differenziale di")
        print(f"    {bd.mean():+.4f} +/- {bd.std(ddof=1):.4f}. La maschera")
        print(f"    contamina il CONFRONTO, non solo i valori assoluti, e va")
        print(f"    propagato nella banda sistematica di Sez. 6.3.")
        m = np.abs(bd) > 0.02
        if m.any():
            print(f"    Il differenziale supera il 2% in {int(m.sum())}/"
                  f"{bd.size} configurazioni, tipicamente a w_bar "
                  f"{np.median(w[m]):.4f}.")

    atomic_write_json(res / "paper1" / f"n8b_report_{n}.json", {
        "script": "paper1_rev_n8b_differential.py", "ngrid": n,
        "slope_a": args.slope_a, "slope_b": args.slope_b,
        "n_config": len(rows),
        "delta_true_mean": float(dt.mean()), "delta_true_sd": float(dt.std(ddof=1)),
        "bias_abs_mean": float(ba.mean()), "bias_abs_sd": float(ba.std(ddof=1)),
        "bias_diff_mean": float(bd.mean()), "bias_diff_sd": float(bd.std(ddof=1)),
        "cancellazione": float(canc), "per_forma": per_shape,
        "regime_valido": {
            "n": int(sel.sum()),
            "bias_abs_mean": float(ba99.mean()) if sel.sum() else None,
            "bias_diff_mean": float(bd99.mean()) if sel.sum() else None,
            "bias_diff_sd": float(bd99.std(ddof=1)) if sel.sum() > 1 else None}})
    print(f"\n  report: {res/'paper1'/('n8b_report_'+str(n)+'.json')}")


if __name__ == "__main__":
    main()
