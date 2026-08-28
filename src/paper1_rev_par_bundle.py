#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_par_bundle.py

PACCHETTO ESEGUIBILE IN PARALLELO A paper1_rev_n2_persistence.py

SICUREZZA DEL PARALLELISMO
--------------------------
N2 legge results/phase8_test2_fields/*.npz, appende a
results/paper1/n2_persistence_NGC.jsonl e scrive n2_report_NGC.json,
saturando una CPU con gudhi.

Questo script:
  - LEGGE  results/paper1/per_mock_{NGC,SGC}_R5.jsonl
           results/paper1/n1b_spectra_NGC.jsonl
           results/paper1/n1c_bands_NGC.jsonl
           data/raw/quijote/.../latin_hypercube_nwLH_params.txt
           al massimo --n_tie campi .npz (sola lettura, default 3)
  - SCRIVE un solo file: results/paper1/rev_par_report.json
  - NON tocca n2_persistence_NGC.jsonl ne' n2_report_NGC.json
  - non usa gudhi ne' FFT di campi 128^3: secondi di CPU

QUATTRO PUNTI
-------------
A. R3.3 - "Statistically independent channels" (Sez. 4.2).
   Il referee indica lui stesso il test: la correlazione mock-per-mock fra
   momenti e N_H1. N1b l'ha gia' misurata su 1800 mock:
       sigma dentro maschera  r = -0.792
       curtosi                r = +0.779
   I canali NON sono indipendenti. Qui si completa con l'asimmetria, le
   correlazioni fra i tre canali (base/null/remap) e fra le otto feature,
   per sostituire la frase con la formulazione che il referee propone in
   subordine: i canali coesistono e il primo non spiega il secondo.

B. R3.6(iii) - coerenza di Fig. 1. Il referee osserva che il picco dei mock
   rimappati e' a ~13000 mentre il testo dice "at nu = 0 the matched mocks
   carry 7162 +/- 183 loops". Il JSONL contiene il campo 'curves': si guarda
   dove cade davvero il picco della curva di Betti e quanto vale a nu ~ 0, e
   si distingue il picco della CURVA dal picco del RESIDUO.

C. TETTO NON LINEARE. Il limite "il deficit e' 5.8x l'escursione cosmologica
   massima" (paper1_variance_decomposition.md §4) vale al primo ordine, con
   R^2 = 0.26. Un referee chiedera' se termini quadratici e incrociati
   possano fare di piu'. Si misura invece di argomentarlo: modello con 7
   lineari + 7 quadratici + 21 incrociati, R^2 in validazione incrociata, ed
   escursione massima sulle 2000 cosmologie campionate.

D. R1 minore 3 - pareggi. Il clip a -1+1e-3 in build_field produce molti voxel
   identici; il referee chiede come sono trattati i pareggi nella filtrazione.
   Si misura la frazione di voxel esattamente al valore di clip, e quella dei
   valori duplicati, su pochi campi.

USO
---
  python src\\paper1_rev_par_bundle.py
"""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

NH1 = "base.N_H1"
FEATS = ("N_H1", "b1_peak", "b1_integral", "b1_fwhm", "mean_pers1",
         "n_pers_top10", "peak_nu", "b0_at_mean")
CHANNELS = ("base", "null", "remap")
COSMO = ("Om", "Ob", "h", "ns", "s8", "Mnu", "w0")
DESI_NH1 = 28256.0


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


def corr_ci(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 8 or np.std(x[m]) == 0 or np.std(y[m]) == 0:
        return None
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    if not np.isfinite(r):
        return None
    r = min(max(r, -0.999999), 0.999999)
    zf = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - 3)
    return {"r": r, "n": n, "sigma": float(abs(zf) / se),
            "ic95": [float(np.tanh(zf - 1.96 * se)),
                     float(np.tanh(zf + 1.96 * se))]}


def cv_r2(X, y, k=5, seed=1):
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    order = rng.permutation(n)
    pred = np.empty(n)
    for f in np.array_split(order, k):
        tr = np.setdiff1d(order, f)
        A = np.column_stack([np.ones(tr.size), X[tr]])
        b, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        pred[f] = np.column_stack([np.ones(f.size), X[f]]) @ b
    return 1.0 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--n_tie", type=int, default=3)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    rep = {"script": "paper1_rev_par_bundle.py"}

    # dati per-mock
    recs = read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")
    if not recs:
        print("[FATAL] per_mock_NGC_R5.jsonl non trovato")
        return
    def as_int_id(x, fallback):
        """'key' e' una stringa tipo 'delta_0000': si estraggono le cifre."""
        if isinstance(x, bool) or x is None:
            return fallback
        if isinstance(x, (int, float)):
            return int(x)
        d = re.findall(r"\d+", str(x))
        return int(d[-1]) if d else fallback

    key = np.array([as_int_id(r.get("key"), i) for i, r in enumerate(recs)])

    # VERIFICA CRITICA: n1b, n1c e n2 convertivano 'key' dentro un try/except
    # con ripiego sulla POSIZIONE nel file. Va bene solo se posizione e cifre
    # coincidono per ogni record; altrimenti quegli script hanno appaiato
    # spettri e N_H1 di mock diversi.
    pos_ok = bool(np.array_equal(key, np.arange(key.size)))
    print(f"\n  chiave 'key': esempi {[r.get('key') for r in recs[:2]]}")
    print(f"  key == posizione nel file per ogni record: "
          f"{'SI' if pos_ok else 'NO'}")
    if not pos_ok:
        bad = np.where(key != np.arange(key.size))[0]
        print(f"  *** {bad.size} record fuori posto (primi: {bad[:8].tolist()}).")
        print(f"      N1b, N1c e N2 hanno usato la posizione come indice:")
        print(f"      i loro risultati vanno RICALCOLATI. ***")
    rep["chiave_posizionale_ok"] = pos_ok
    ch = {}
    for c in CHANNELS:
        for f in FEATS:
            v = np.array([float(r.get(c, {}).get(f, np.nan)) for r in recs])
            if np.isfinite(v).sum() > 10:
                ch[f"{c}.{f}"] = v
    y = ch.get("base.N_H1")
    print("=" * 78)
    print(f"PACCHETTO PARALLELO   ({len(recs)} mock, {len(ch)} colonne)")
    print("=" * 78)

    # ============================================================ A
    print("\n" + "=" * 78)
    print("A - R3.3: I CANALI SONO STATISTICAMENTE INDIPENDENTI?")
    print("=" * 78)
    print("  Test indicato dal referee: correlazione mock-per-mock fra i")
    print("  momenti del campo e N_H1.\n")

    mom = {}
    for src, keys in ((res / "paper1" / "n1b_spectra_NGC.jsonl",
                       ("sigma_in_mask", "kurt_in_mask")),
                      (res / "paper1" / "n1c_bands_NGC.jsonl",
                       ("sigma_in_mask", "kurt_in_mask", "skew_in_mask"))):
        for r in read_jsonl(src):
            i = r.get("idx")
            if i is None:
                continue
            mom.setdefault(i, {}).update({k: r[k] for k in keys if k in r})
    if mom:
        idx = sorted(set(mom) & set(key.tolist()))
        pos = {k: j for j, k in enumerate(key)}
        yy = np.array([y[pos[i]] for i in idx])
        print(f"  {'momento':>16s} {'r con N_H1':>12s} {'IC95%':>20s} "
              f"{'n':>6s}")
        rep["A_momenti"] = {}
        for k in ("sigma_in_mask", "kurt_in_mask", "skew_in_mask"):
            x = np.array([mom[i].get(k, np.nan) for i in idx], float)
            c = corr_ci(x, yy)
            if c:
                print(f"  {k:>16s} {c['r']:>+12.4f} "
                      f"[{c['ic95'][0]:>+7.4f},{c['ic95'][1]:>+7.4f}] "
                      f"{c['n']:>6d}")
                rep["A_momenti"][k] = c
        mx = max((abs(v["r"]) for v in rep["A_momenti"].values()), default=0)
        print(f"\n  correlazione massima in modulo: {mx:.3f}")
        print(f"  -> {'I CANALI NON SONO INDIPENDENTI' if mx > 0.3 else 'compatibili con indipendenza'}")
        print(f"     La frase 'statistically independent channels' va")
        print(f"     sostituita con 'coesistono e il primo non spiega il")
        print(f"     secondo', come il referee propone in subordine.")
    else:
        print("  [!] n1b/n1c non trovati: eseguirli prima")

    print("\n  correlazioni fra i tre canali (stessa feature):")
    rep["A_canali"] = {}
    for f in FEATS:
        cols = {c: ch.get(f"{c}.{f}") for c in CHANNELS if f"{c}.{f}" in ch}
        if len(cols) < 2:
            continue
        s = f"  {f:>14s}: "
        for a in CHANNELS:
            for b in CHANNELS:
                if a < b and a in cols and b in cols:
                    c = corr_ci(cols[a], cols[b])
                    if c:
                        s += f"{a}-{b} {c['r']:+.3f}   "
                        rep["A_canali"][f"{f}:{a}-{b}"] = c["r"]
        print(s)

    print("\n  correlazioni fra le feature del canale base:")
    names = [f"base.{f}" for f in FEATS
             if f"base.{f}" in ch and np.nanstd(ch[f"base.{f}"]) > 0]
    print("        " + "".join(f"{n.split('.')[1][:9]:>10s}" for n in names))
    Mx = np.column_stack([ch[n] for n in names])
    ok = np.all(np.isfinite(Mx), axis=1)
    C = np.corrcoef(Mx[ok].T)
    for i, n in enumerate(names):
        print(f"  {n.split('.')[1][:7]:>7s}" +
              "".join(f"{C[i, j]:>10.3f}" for j in range(len(names))))
    rep["A_feature_corr"] = {"nomi": names, "matrice": C.tolist()}
    off = C[~np.eye(len(C), dtype=bool)]
    print(f"\n  |correlazione| mediana fuori diagonale: {np.median(abs(off)):.3f}")
    print(f"  -> le otto feature non sono otto misure indipendenti.")

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - R3.6(iii): DOVE CADE DAVVERO IL PICCO DELLA CURVA DI BETTI")
    print("=" * 78)
    cur = recs[0].get("curves")
    print(f"  campo 'curves' nel primo record: "
          f"{type(cur).__name__}"
          + (f", chiavi {list(cur.keys())}" if isinstance(cur, dict) else
             f", lunghezza {len(cur)}" if hasattr(cur, "__len__") else ""))
    rep["B_curves_tipo"] = str(type(cur))
    for c in CHANNELS:
        pk = ch.get(f"{c}.peak_nu")
        bp = ch.get(f"{c}.b1_peak")
        b0 = ch.get(f"{c}.b0_at_mean")
        if pk is None:
            continue
        print(f"\n  canale {c}:")
        print(f"    peak_nu   : {np.nanmean(pk):+.4f} +/- {np.nanstd(pk):.4f}"
              f"   (nu del picco della curva di Betti-1)")
        if bp is not None:
            print(f"    b1_peak   : {np.nanmean(bp):.0f} +/- {np.nanstd(bp):.0f}"
                  f"   (valore al picco)")
        if b0 is not None:
            print(f"    b0_at_mean: {np.nanmean(b0):.0f} +/- {np.nanstd(b0):.0f}")
        rep.setdefault("B_picco", {})[c] = {
            "peak_nu_mean": float(np.nanmean(pk)),
            "peak_nu_std": float(np.nanstd(pk)),
            "b1_peak_mean": float(np.nanmean(bp)) if bp is not None else None}
    print(f"\n  LETTURA: se peak_nu del canale remap NON e' ~0, allora la frase")
    print(f"  'at nu = 0 the matched mocks carry 7162 +/- 183 loops' si")
    print(f"  riferisce al valore della curva a nu=0, NON al suo picco, mentre")
    print(f"  Fig.1 mostra il picco a ~13000. Le due cose vanno distinte")
    print(f"  esplicitamente nel testo, come il referee chiede.")

    # ============================================================ C
    print("\n" + "=" * 78)
    print("C - TETTO NON LINEARE ALL'ESCURSIONE COSMOLOGICA")
    print("=" * 78)
    q = root / "data" / "raw" / "quijote"
    pf = None
    for cand in (q / "3D_cubes" / "latin_hypercube_nwLH" /
                 "latin_hypercube_nwLH_params.txt",
                 q / "latin_hypercube_nwLH_params.txt"):
        if cand.exists():
            pf = cand
            break
    if pf is None:
        hits = sorted(root.rglob("*nwLH*params*.txt"))
        pf = hits[0] if hits else None
    if pf is None:
        print("  [!] tabella dei parametri non trovata: sezione saltata")
    else:
        tab = np.loadtxt(pf)
        n = min(tab.shape[0], y.size)
        P = tab[:n, :7]
        yy = y[:n]
        m = np.isfinite(yy) & np.all(np.isfinite(P), axis=1)
        P, yy = P[m], yy[m]
        # scarta le colonne costanti (es. Mnu = 0 ovunque): standardizzarle
        # produce NaN e fa fallire lstsq
        vary = P.std(0, ddof=1) > 0
        if not vary.all():
            drop = [COSMO[i] for i in range(7) if not vary[i]]
            print(f"  colonne costanti scartate: {drop}")
        P = P[:, vary]
        npar = P.shape[1]
        Ps = (P - P.mean(0)) / P.std(0, ddof=1)

        quad = [Ps[:, i] ** 2 for i in range(npar)]
        cross = [Ps[:, i] * Ps[:, j]
                 for i in range(npar) for j in range(i + 1, npar)]
        Xlin = Ps
        Xful = np.column_stack([Ps] + quad + cross)

        out = {}
        nlin, nful = Xlin.shape[1], Xful.shape[1]
        for nome, X in ((f"lineare ({nlin})", Xlin),
                        (f"completo ({nful})", Xful)):
            A = np.column_stack([np.ones(X.shape[0]), X])
            b, *_ = np.linalg.lstsq(A, yy, rcond=None)
            pred = A @ b
            r2 = 1 - ((yy - pred) ** 2).sum() / ((yy - yy.mean()) ** 2).sum()
            r2c = cv_r2(X, yy)
            span = float(pred.max() - pred.min())
            deficit = float(yy.mean()) - DESI_NH1
            print(f"\n  modello {nome}:  n={X.shape[0]}")
            print(f"    R^2 in campione {r2:.4f}   R^2 validato {r2c:.4f}")
            print(f"    escursione predetta sulle 2000 cosmologie: {span:.0f}")
            print(f"    deficit osservato: {deficit:.0f}   "
                  f"rapporto {deficit/span:.2f}x")
            out[nome] = {"r2": float(r2), "r2_cv": float(r2c),
                         "escursione": span, "deficit": deficit,
                         "rapporto": deficit / span}
        rep["C_tetto"] = out
        rl, rf = out[f"lineare ({nlin})"], out[f"completo ({nful})"]
        print(f"\n  LETTURA: il tetto passa da {rl['rapporto']:.1f}x a "
              f"{rf['rapporto']:.1f}x aggiungendo")
        print(f"  quadratici e incrociati. Se il R^2 validato NON migliora, i")
        print(f"  termini non lineari sono rumore e l'escursione maggiore e'")
        print(f"  overfitting: in tal caso citare il modello lineare e dire che")
        print(f"  l'estensione non lineare non aggiunge potere predittivo.")

    # ============================================================ D
    print("\n" + "=" * 78)
    print("D - R1 minore 3: PAREGGI PRODOTTI DAL CLIP A -1+1e-3")
    print("=" * 78)
    mask_f = (root / "data" / "processed" / "phase6_fields" /
              "bgs_ngc_mask_128.npy")
    fdir = res / "phase8_test2_fields"
    if not (mask_f.exists() and fdir.exists()):
        print("  [!] maschera o campi non trovati: sezione saltata")
    else:
        mask = np.load(mask_f).astype(bool)
        cand = [res / "paper1" / "n1_desi_nu_NGC.npy"]
        cand += sorted(fdir.glob("test2_*.npz"))[-args.n_tie:]
        rep["D_pareggi"] = {}
        for p in cand:
            if not p.exists():
                continue
            v = (np.load(p) if p.suffix == ".npy" else np.load(p)["delta"])
            vi = v[mask]
            u, cnt = np.unique(vi, return_counts=True)
            dup = float((cnt[cnt > 1].sum() - (cnt > 1).sum()) / vi.size)
            top = int(cnt.max())
            print(f"  {p.name:>28s}: {vi.size} voxel, {u.size} valori distinti,"
                  f" duplicati {100*dup:.3f}%, molteplicita' max {top}")
            rep["D_pareggi"][p.name] = {"n_voxel": int(vi.size),
                                        "n_distinti": int(u.size),
                                        "frazione_duplicati": dup,
                                        "molteplicita_max": top}
        print(f"\n  LETTURA: dopo la lisciatura gaussiana il clip non produce")
        print(f"  piu' valori identici in massa. Se la frazione di duplicati e'")
        print(f"  trascurabile, la risposta a R1 minore 3 e' che i pareggi sono")
        print(f"  numericamente irrilevanti - da dire con il numero, non con")
        print(f"  un'affermazione.")

    atomic_write_json(res / "paper1" / "rev_par_report.json", rep)
    print("\n" + "=" * 78)
    print(f"report: {res/'paper1'/'rev_par_report.json'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
