#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n10b_control.py

N10b - LA RANDOMIZZAZIONE DELLE FASI E' IMPARZIALE?

IL PROBLEMA
-----------
N10 (pilota, n=10) ha dato:
    DESI  28256 -> 33711 +/- 197   (+19.3%)
    mock  35362 -> 39121 +/- 496   (+10.6%)
    frazione del deficit attribuibile allo spettro: 76%

Ma la randomizzazione produce un campo NON nullo fuori maschera: modi che
codificavano il bordo rientrano all'interno. N_H1 sale in ENTRAMBI i casi, e le
due salite differiscono (19.3% contro 10.6%). Se la distorsione dipendesse
dallo spettro, il rapporto fra i due deficit non sarebbe pulito.

PERCHE' LA MISURA OVVIA NON SERVE
---------------------------------
Misurare quanta potenza esce dalla maschera non risponde. Per Parseval la
potenza totale si conserva: dopo la randomizzazione si sparge sul cubo e dentro
maschera ne resta circa mask.mean() ~ 14.7%. Ma un riscalamento uniforme e'
MONOTONO, quindi non cambia N_H1 di un solo generatore. La perdita di varianza
e' irrilevante per costruzione: e' il lemma stesso a garantirlo.

LA MISURA GIUSTA: IDEMPOTENZA
-----------------------------
Un campo gia' a fasi casuali, randomizzato di nuovo, non dovrebbe cambiare
N_H1: non c'e' altra informazione di fase da distruggere. Quindi

    N_H1(PR(PR(x))) ~ N_H1(PR(x))   -> la trasformazione e' imparziale sui
        campi gaussiani, e la salita alla PRIMA applicazione e' contenuto di
        fase reale
    N_H1(PR(PR(x)))  >  N_H1(PR(x)) -> la salita e' artefatto della maschera e
        va sottratta

Il test si esegue separatamente su DESI e sui mock, cosi' si vede anche se la
distorsione dipende dallo spettro - che e' il punto che conta, visto che le due
salite differiscono di un fattore due.

DIAGNOSTICA DI CONTORNO
-----------------------
  - nu e' davvero nullo fuori maschera? (l'ho assunto, non verificato)
  - frazione di potenza dentro maschera, prima e dopo
  - momenti dentro maschera, prima e dopo: documentano cosa fa la
    trasformazione, senza che nessuno di essi incida su N_H1

Append-only JSONL, resumable. Usa gudhi: e' un secondo processo accanto a N2.

USO
---
  python src\\paper1_rev_n10b_control.py
  python src\\paper1_rev_n10b_control.py --n_rep 10 --n_mock 5
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

DESI_NH1 = 28256.0
NH1 = "base.N_H1"
MIN_IDX = 200


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


def phase_randomize(nu, rng):
    F = np.fft.rfftn(nu.astype(np.float64))
    A = np.abs(F)
    W = np.fft.rfftn(rng.standard_normal(nu.shape))
    aW = np.abs(W)
    aW[aW == 0] = 1.0
    return np.fft.irfftn(A * (W / aW), s=nu.shape).astype(np.float32)


def diag(nu, mask):
    """Diagnostica di contorno: nessuna di queste quantita' incide su N_H1,
    servono a documentare cosa fa la trasformazione."""
    a = nu.astype(np.float64)
    tot = float((a ** 2).sum())
    inm = float((a[mask] ** 2).sum())
    v = a[mask]
    s = float(v.std())
    out = a[~mask]
    return {"frazione_potenza_in_maschera": inm / tot if tot > 0 else np.nan,
            "sigma_in": s,
            "kurt_in": float(((v - v.mean()) ** 4).mean() / s ** 4 - 3.0)
            if s > 0 else np.nan,
            "skew_in": float(((v - v.mean()) ** 3).mean() / s ** 3)
            if s > 0 else np.nan,
            "max_abs_fuori": float(np.abs(out).max()) if out.size else 0.0,
            "sigma_fuori": float(out.std()) if out.size else 0.0}


def stats(v):
    v = np.asarray(v, float)
    if v.size == 0:
        return {}
    return {"n": int(v.size), "mean": float(v.mean()),
            "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "sem": float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--n_rep", type=int, default=10,
                    help="realizzazioni per stadio su DESI")
    ap.add_argument("--n_mock", type=int, default=5)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--seed", type=int, default=777)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    fdir = res / "phase8_test2_fields"
    outj = res / "paper1" / "n10b_control_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)
    nu_d = np.load(res / "paper1" / "n1_desi_nu_NGC.npy")

    def nh1(x):
        return float(M.compute_tda_features(x, mask, M.N_THRESH,
                                            masked=True)[4])

    print("=" * 78)
    print("N10b - IDEMPOTENZA DELLA RANDOMIZZAZIONE")
    print("=" * 78)

    # ------------------------------------------------ 0. nu e' nullo fuori?
    print("\n[0] IL CAMPO E' DAVVERO NULLO FUORI MASCHERA?  (l'avevo assunto)")
    d0 = diag(nu_d, mask)
    print(f"  DESI: max|nu| fuori maschera = {d0['max_abs_fuori']:.6g}   "
          f"sd fuori = {d0['sigma_fuori']:.6g}")
    print(f"        frazione di potenza dentro maschera = "
          f"{100*d0['frazione_potenza_in_maschera']:.4f}%")
    print(f"        (maschera = {100*mask.mean():.2f}% dei voxel)")
    if d0["max_abs_fuori"] > 1e-6:
        print(f"  *** nu NON e' nullo fuori maschera. La filtrazione lo")
        print(f"      sostituisce comunque con la sentinella, quindi N_H1 non")
        print(f"      ne risente, ma lo SPETTRO usato dalla randomizzazione")
        print(f"      include quei valori. Da dichiarare. ***")

    # ------------------------------------------------ 1. catena su DESI
    print(f"\n[1] DESI: originale -> PR -> PR(PR)   ({args.n_rep} realizzazioni)")
    done = {(r["tipo"], r["idx"], r.get("stadio")) for r in read_jsonl(outj)}
    v0 = nh1(nu_d)
    print(f"  stadio 0 (originale): N_H1 = {v0:.0f}   "
          f"{'OK' if abs(v0-DESI_NH1) < 0.5 else '*** non riproduce 28256 ***'}")
    if abs(v0 - DESI_NH1) > 0.5:
        return

    t0 = time.time()
    for k in range(args.n_rep):
        if ("desi", k, 2) in done:
            continue
        r1 = np.random.default_rng(args.seed + k)
        p1 = phase_randomize(nu_d, r1)
        n1 = nh1(p1)
        d1 = diag(p1, mask)
        r2 = np.random.default_rng(args.seed + 50000 + k)
        p2 = phase_randomize(p1, r2)
        n2 = nh1(p2)
        d2 = diag(p2, mask)
        append_jsonl(outj, {"tipo": "desi", "idx": k, "stadio": 2,
                            "N_H1_pr1": n1, "N_H1_pr2": n2,
                            "diag_pr1": d1, "diag_pr2": d2})
        if k == 0 or (k + 1) % 5 == 0:
            print(f"    [{k+1}/{args.n_rep}] PR={n1:.0f}  PR(PR)={n2:.0f}  "
                  f"delta2={n2-n1:+.0f}   {(time.time()-t0)/(k+1):.1f} s/coppia")

    # ------------------------------------------------ 2. catena sui mock
    files = [(int(p.stem.split("_")[1]), p)
             for p in sorted(fdir.glob("test2_*.npz"))]
    files = [(i, p) for i, p in files if i >= args.min_idx][:args.n_mock]
    print(f"\n[2] MOCK: {len(files)} campi, stessa catena")
    for i, p in files:
        if ("mock", i, 2) in done:
            continue
        nu = np.load(p)["delta"]
        m0 = nh1(nu)
        r1 = np.random.default_rng(args.seed + 20000 + i)
        p1 = phase_randomize(nu, r1)
        m1 = nh1(p1)
        r2 = np.random.default_rng(args.seed + 70000 + i)
        p2 = phase_randomize(p1, r2)
        m2 = nh1(p2)
        append_jsonl(outj, {"tipo": "mock", "idx": i, "stadio": 2,
                            "N_H1_orig": m0, "N_H1_pr1": m1, "N_H1_pr2": m2,
                            "diag_orig": diag(nu, mask),
                            "diag_pr1": diag(p1, mask)})
        print(f"    idx {i}: orig={m0:.0f}  PR={m1:.0f} ({100*(m1-m0)/m0:+.1f}%)"
              f"  PR(PR)={m2:.0f} ({100*(m2-m1)/m1:+.1f}%)")

    # ------------------------------------------------ analisi
    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    recs = read_jsonl(outj)
    D = [r for r in recs if r["tipo"] == "desi"]
    Mk = [r for r in recs if r["tipo"] == "mock"]
    if len(D) < 3 or len(Mk) < 2:
        print("  campioni troppo piccoli.")
        return

    d1 = stats([r["N_H1_pr1"] for r in D])
    d2 = stats([r["N_H1_pr2"] for r in D])
    m0 = stats([r["N_H1_orig"] for r in Mk])
    m1 = stats([r["N_H1_pr1"] for r in Mk])
    m2 = stats([r["N_H1_pr2"] for r in Mk])

    print(f"\n  {'':>10s} {'originale':>12s} {'PR':>16s} {'PR(PR)':>16s}")
    print(f"  {'DESI':>10s} {DESI_NH1:>12.0f} "
          f"{d1['mean']:>10.0f}+/-{d1['sem']:<5.0f} "
          f"{d2['mean']:>10.0f}+/-{d2['sem']:<5.0f}")
    print(f"  {'mock':>10s} {m0['mean']:>12.0f} "
          f"{m1['mean']:>10.0f}+/-{m1['sem']:<5.0f} "
          f"{m2['mean']:>10.0f}+/-{m2['sem']:<5.0f}")

    dd = d2["mean"] - d1["mean"]
    dm = m2["mean"] - m1["mean"]
    sdd = np.sqrt(d1["sem"] ** 2 + d2["sem"] ** 2)
    sdm = np.sqrt(m1["sem"] ** 2 + m2["sem"] ** 2)
    print(f"\n  SALITA ALLA PRIMA APPLICAZIONE (contenuto di fase + artefatto):")
    print(f"    DESI {d1['mean']-DESI_NH1:+.0f}  ({100*(d1['mean']-DESI_NH1)/DESI_NH1:+.1f}%)")
    print(f"    mock {m1['mean']-m0['mean']:+.0f}  "
          f"({100*(m1['mean']-m0['mean'])/m0['mean']:+.1f}%)")
    print(f"\n  SALITA ALLA SECONDA (solo artefatto: le fasi erano gia' casuali):")
    print(f"    DESI {dd:+.0f} +/- {sdd:.0f}   ({dd/sdd if sdd else 0:+.1f} sigma)")
    print(f"    mock {dm:+.0f} +/- {sdm:.0f}   ({dm/sdm if sdm else 0:+.1f} sigma)")

    ok_d = abs(dd) < 3 * sdd if sdd > 0 else False
    ok_m = abs(dm) < 3 * sdm if sdm > 0 else False
    print(f"\n  LETTURA:")
    if ok_d and ok_m:
        print(f"    La seconda applicazione non cambia nulla in nessuno dei due")
        print(f"    casi: la trasformazione e' IMPARZIALE sui campi gaussiani.")
        print(f"    Quindi la salita alla prima applicazione e' contenuto di")
        print(f"    fase reale, e il 76% di N10 regge.")
    else:
        art_d = dd if not ok_d else 0.0
        art_m = dm if not ok_m else 0.0
        print(f"    La seconda applicazione sposta ancora N_H1: c'e' un")
        print(f"    ARTEFATTO della maschera, stimabile in {art_d:+.0f} (DESI)")
        print(f"    e {art_m:+.0f} (mock).")
        d_or = m0["mean"] - DESI_NH1
        d_pr = m1["mean"] - d1["mean"]
        d_corr = (m1["mean"] - art_m) - (d1["mean"] - art_d)
        print(f"    deficit dopo PR              : {d_pr:.0f}")
        print(f"    deficit dopo PR, corretto    : {d_corr:.0f}")
        print(f"    frazione spettrale grezza    : {100*d_pr/d_or:.1f}%")
        print(f"    frazione spettrale corretta  : {100*d_corr/d_or:.1f}%")
        print(f"    -> se le due frazioni differiscono di poco, la correzione")
        print(f"       e' cosmetica; se molto, va applicata e dichiarata.")

    print(f"\n  diagnostica (nessuna incide su N_H1, documenta la trasformazione):")
    for nome, rs, k in (("DESI PR", D, "diag_pr1"), ("mock orig", Mk, "diag_orig"),
                        ("mock PR", Mk, "diag_pr1")):
        vals = [r[k] for r in rs if k in r]
        if not vals:
            continue
        print(f"    {nome:>10s}: potenza in maschera "
              f"{100*np.mean([v['frazione_potenza_in_maschera'] for v in vals]):>6.2f}%"
              f"   sigma_in {np.mean([v['sigma_in'] for v in vals]):>7.4f}"
              f"   kurt_in {np.mean([v['kurt_in'] for v in vals]):>+7.3f}")

    atomic_write_json(res / "paper1" / "n10b_control_report.json", {
        "script": "paper1_rev_n10b_control.py",
        "desi": {"orig": DESI_NH1, "pr1": d1, "pr2": d2,
                 "delta2": float(dd), "sem_delta2": float(sdd)},
        "mock": {"orig": m0, "pr1": m1, "pr2": m2,
                 "delta2": float(dm), "sem_delta2": float(sdm)},
        "imparziale_desi": bool(ok_d), "imparziale_mock": bool(ok_m),
        "nu_nullo_fuori_maschera": bool(d0["max_abs_fuori"] <= 1e-6),
        "diag_desi_originale": d0})
    print(f"\n  report: {res/'paper1'/'n10b_control_report.json'}")


if __name__ == "__main__":
    main()
