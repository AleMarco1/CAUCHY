#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2b_outliers.py

V2b - ANATOMIA DELLA DISCREPANZA DI DISPERSIONE

Contesto (esito di paper1_rev_v2v3.py):
  - trovato il per-mock di M26: results\\phase9_likeforlike_arrays.npz['beta1_max']
    2000 valori, 35424.78 +/- 444.81  (= tabella battery di M26)
  - nostro ensemble: 35436.69 +/- 312.99
  - il 90% dei valori e' IDENTICO mock per mock; Spearman 0.951 vs Pearson 0.759
  - le nostre distribuzioni hanno curtosi in eccesso +40 (NGC) e +27 (SGC)
    con sigma robuste 261 e 171 contro sigma grezze 313 e 198

Conclusione operativa: non e' seeding, non e' density matching. La differenza
vive in ~200 mock, e in entrambe le catene una coda patologica governa sigma.

QUESTO SCRIPT RISPONDE A TRE DOMANDE
------------------------------------
D1  QUALI mock differiscono, di quanto, e con quale sigma_px sono stati girati.
    Ipotesi principale: un sottoinsieme e' stato processato a sigma_px diverso
    (finestre parallele su scale multiple) e non appartiene all'ensemble R5.
D2  QUALI mock sono patologici (coda sinistra estrema), e se l'insieme dei
    patologici coincide con quello dei discrepanti.
D3  COSA succede a sigma, z e rank sotto tre trattamenti dichiarabili:
    ensemble completo / esclusi i discrepanti / esclusi i patologici.
    Il rank deve restare 1/2001 in tutti e tre: e' la verifica che la
    statistica primaria della revisione e' immune al problema.

Solo lettura. Scrive un unico report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2b_outliers.py
  python src\\paper1_rev_v2b_outliers.py --m26_npz results\\phase9_likeforlike_arrays.npz
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np

DESI = {"NGC": 28256.0, "SGC": 15122.0}
NH1_KEY = "base.N_H1"
ATOL = 0.5            # tolleranza per dire "identico"
ROBUST_Z = 5.0        # soglia di patologia in unita' di sigma_MAD


# ---------------------------------------------------------------- io
def read_jsonl_raw(path):
    recs, bad = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                bad += 1
    return recs, bad


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return x


# ---------------------------------------------------------------- statistica
def robust_scale(v):
    med = float(np.median(v))
    mad = float(1.4826 * np.median(np.abs(v - med)))
    return med, (mad if mad > 0 else float(v.std(ddof=1)))


def summarize(v, desi, label):
    v = np.asarray(v, float)
    n = v.size
    sd = float(v.std(ddof=1))
    below = int((v < desi).sum())
    return {
        "trattamento": label, "n": n,
        "mean": float(v.mean()), "std": sd,
        "std_err": sd / np.sqrt(2.0 * (n - 1)),
        "min": float(v.min()),
        "z": (desi - float(v.mean())) / sd,
        "n_sotto_desi": below,
        "rank": f"{below + 1}/{n + 1}",
        "margine_al_minimo": float(v.min()) - desi,
        "margine_in_sigma": (float(v.min()) - desi) / sd,
    }


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--m26_npz",
                    default="results\\phase9_likeforlike_arrays.npz")
    ap.add_argument("--m26_key", default="beta1_max")
    ap.add_argument("--max_print", type=int, default=40)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    our_dir = root / "results" / "paper1"
    rep = {"script": "paper1_rev_v2b_outliers.py", "regioni": {}}

    # ============================================================ 0. schema
    print("=" * 78)
    print("0 - SCHEMA GREZZO  (tutte le chiavi, comprese quelle non numeriche)")
    print("=" * 78)
    raw = {}
    for reg in ("NGC", "SGC"):
        p = our_dir / f"per_mock_{reg}_R5.jsonl"
        if not p.exists():
            print(f"  [!] {p} non trovato")
            continue
        recs, bad = read_jsonl_raw(p)
        raw[reg] = [flatten(r) for r in recs]
        print(f"\n  {reg}: {len(recs)} record ({bad} scartati)")
        if raw[reg]:
            print("  primo record:")
            for k, v in sorted(raw[reg][0].items()):
                print(f"    {k:<24s} = {v!r}")
    if not raw:
        print("\nNessun JSONL. Verifica --project_root.")
        return
    rep["chiavi_grezze"] = sorted(raw[next(iter(raw))][0].keys())

    # cerca una chiave identificativa del mock
    id_key = None
    r0 = raw[next(iter(raw))]
    for k in r0[0].keys():
        vals = [rec.get(k) for rec in r0]
        if any(isinstance(v, str) for v in vals):
            if len(set(map(str, vals))) == len(vals):
                id_key = k
                break
        elif all(isinstance(v, (int, float)) and not isinstance(v, bool)
                 for v in vals):
            iv = [int(v) for v in vals]
            if len(set(iv)) == len(iv) and min(iv) >= 0 and max(iv) < 10 * len(iv):
                id_key = k
                break
    print(f"\n  chiave identificativa del mock: "
          f"{id_key if id_key else 'NESSUNA -> allineamento posizionale'}")
    rep["chiave_id"] = id_key

    # ============================================================ 1. sigma_px
    print("\n" + "=" * 78)
    print("1 - INTEGRITA' DELL'ENSEMBLE: sigma_px e' costante?")
    print("=" * 78)
    rep["sigma_px"] = {}
    for reg, recs in raw.items():
        sp = np.array([float(r.get("sigma_px", np.nan)) for r in recs])
        uniq, cnt = np.unique(np.round(sp[np.isfinite(sp)], 6),
                              return_counts=True)
        print(f"\n  {reg}: {len(uniq)} valore/i distinto/i di sigma_px")
        for u, c in zip(uniq, cnt):
            print(f"    sigma_px = {u:<12.6f}  ->  {c} mock")
        if len(uniq) > 1:
            print("    *** ENSEMBLE MISTO: mock girati a scale diverse ***")
        rep["sigma_px"][reg] = {"valori": uniq.tolist(),
                                "conteggi": cnt.tolist(),
                                "misto": bool(len(uniq) > 1)}

    # ============================================================ 2. npz M26
    print("\n" + "=" * 78)
    print("2 - CONTENUTO DEL FILE M26")
    print("=" * 78)
    _parts = [q for q in args.m26_npz.replace("\\", "/").split("/") if q]
    npz_path = (Path(args.m26_npz) if Path(args.m26_npz).is_absolute()
                else root.joinpath(*_parts))
    m26 = None
    if not npz_path.exists():
        print(f"  [!] {npz_path} non trovato")
    else:
        z = np.load(npz_path, allow_pickle=True)
        print(f"  {npz_path}")
        for k in z.files:
            a = np.asarray(z[k])
            extra = ""
            if a.ndim == 1 and a.size and a.dtype.kind in "fi":
                extra = (f"  mediana={np.median(a):.4g}  "
                         f"min={a.min():.4g}  max={a.max():.4g}")
            print(f"    {k:<28s} shape={str(a.shape):<12s} "
                  f"dtype={a.dtype}{extra}")
        rep["npz_chiavi"] = list(z.files)
        if args.m26_key in z.files:
            m26 = np.asarray(z[args.m26_key], float)

    # ============================================================ 3. per regione
    for reg, recs in raw.items():
        ours = np.array([float(flatten(r).get(NH1_KEY, np.nan))
                         if NH1_KEY not in r else float(r[NH1_KEY])
                         for r in recs])
        if not np.isfinite(ours).all():
            ours = np.array([float(r.get(NH1_KEY, np.nan)) for r in recs])
        sp = np.array([float(r.get("sigma_px", np.nan)) for r in recs])
        ids = ([str(r.get(id_key)) for r in recs] if id_key
               else [str(i) for i in range(len(recs))])
        desi = DESI[reg]
        R = {}

        print("\n" + "=" * 78)
        print(f"3.{reg} - ANATOMIA")
        print("=" * 78)

        # --- D2: patologici -------------------------------------------------
        med, sig = robust_scale(ours)
        rz = (ours - med) / sig
        patol = np.where(rz < -ROBUST_Z)[0]
        print(f"\n  D2 - MOCK PATOLOGICI  (z robusto < -{ROBUST_Z:.0f}, "
              f"mediana={med:.0f}, sigma_MAD={sig:.1f})")
        print(f"    trovati: {patol.size} su {ours.size} "
              f"({100 * patol.size / ours.size:.2f}%)")
        if patol.size:
            order = patol[np.argsort(ours[patol])]
            print(f"\n    {'#':>5s} {'id':>8s} {'N_H1':>10s} {'z_rob':>8s} "
                  f"{'sigma_px':>10s}")
            for i in order[:args.max_print]:
                print(f"    {i:>5d} {ids[i]:>8s} {ours[i]:>10.0f} "
                      f"{rz[i]:>8.1f} {sp[i]:>10.5f}")
            if order.size > args.max_print:
                print(f"    ... e altri {order.size - args.max_print}")
        R["patologici"] = {"n": int(patol.size),
                           "indici": patol.tolist(),
                           "valori": ours[patol].tolist(),
                           "mediana_robusta": med, "sigma_mad": sig}

        # --- D1: discrepanti ------------------------------------------------
        disc = np.array([], dtype=int)
        if m26 is not None and reg == "NGC" and m26.size == ours.size:
            d = ours - m26
            same = np.isclose(ours, m26, rtol=0.0, atol=ATOL)
            disc = np.where(~same)[0]
            print(f"\n  D1 - DISCREPANTI vs M26  (|differenza| > {ATOL})")
            print(f"    identici   : {int(same.sum())} "
                  f"({100 * same.mean():.1f}%)")
            print(f"    discrepanti: {disc.size}")
            if disc.size:
                print(f"    differenza sui discrepanti: "
                      f"mediana {np.median(d[disc]):+.0f}, "
                      f"range [{d[disc].min():+.0f}, {d[disc].max():+.0f}]")
                print(f"    di questi, patologici da noi: "
                      f"{len(set(disc.tolist()) & set(patol.tolist()))}")
                order = disc[np.argsort(np.abs(d[disc]))[::-1]]
                print(f"\n    {'#':>5s} {'id':>8s} {'nostro':>10s} "
                      f"{'M26':>10s} {'diff':>9s} {'sigma_px':>10s}")
                for i in order[:args.max_print]:
                    print(f"    {i:>5d} {ids[i]:>8s} {ours[i]:>10.0f} "
                          f"{m26[i]:>10.0f} {d[i]:>+9.0f} {sp[i]:>10.5f}")
                if order.size > args.max_print:
                    print(f"    ... e altri {order.size - args.max_print}")

                # M26 e' piu' o meno patologico di noi?
                med_m, sig_m = robust_scale(m26)
                pat_m = int((((m26 - med_m) / sig_m) < -ROBUST_Z).sum())
                print(f"\n    coda patologica: noi {patol.size} mock, "
                      f"M26 {pat_m} mock")
                print(f"    sigma robusta  : noi {sig:.1f}, M26 {sig_m:.1f}")
                print(f"    sigma grezza   : noi {ours.std(ddof=1):.1f}, "
                      f"M26 {m26.std(ddof=1):.1f}")
                R["m26"] = {"n_identici": int(same.sum()),
                            "n_discrepanti": int(disc.size),
                            "indici_discrepanti": disc.tolist(),
                            "diff_mediana": float(np.median(d[disc])),
                            "n_patologici_m26": pat_m,
                            "sigma_robusta_m26": sig_m,
                            "sigma_robusta_nostra": sig}
        elif reg == "NGC":
            print("\n  D1 - confronto con M26 non eseguito "
                  "(npz assente o dimensioni diverse)")

        # --- D3: trattamenti ------------------------------------------------
        print(f"\n  D3 - SIGMA, z E RANK SOTTO TRE TRATTAMENTI")
        print(f"    DESI {reg} = {desi:.0f}")
        treat = [("completo", np.ones(ours.size, bool))]
        if patol.size:
            m = np.ones(ours.size, bool); m[patol] = False
            treat.append((f"esclusi {patol.size} patologici", m))
        if disc.size:
            m = np.ones(ours.size, bool); m[disc] = False
            treat.append((f"esclusi {disc.size} discrepanti", m))
        if patol.size and disc.size:
            m = np.ones(ours.size, bool)
            m[patol] = False; m[disc] = False
            treat.append(("esclusi entrambi", m))

        print(f"\n    {'trattamento':<28s} {'N':>5s} {'media':>9s} "
              f"{'sigma':>7s} {'z':>8s} {'rank':>10s} {'min-DESI':>9s}")
        R["trattamenti"] = []
        for label, m in treat:
            s = summarize(ours[m], desi, label)
            print(f"    {label:<28s} {s['n']:>5d} {s['mean']:>9.1f} "
                  f"{s['std']:>7.1f} {s['z']:>+8.2f} {s['rank']:>10s} "
                  f"{s['margine_al_minimo']:>+9.0f}")
            R["trattamenti"].append(s)

        # il denominatore cambia per costruzione al variare di N: cio' che
        # conta e' la POSIZIONE, cioe' quanti mock scendono sotto DESI.
        pos = {t["n_sotto_desi"] for t in R["trattamenti"]}
        print(f"\n    mock sotto DESI in ogni trattamento: {sorted(pos)}")
        print(f"    DESI resta il valore piu' estremo ovunque: "
              f"{'SI' if pos == {0} else 'NO'}")
        print(f"    escursione di z: "
              f"{min(t['z'] for t in R['trattamenti']):+.2f} .. "
              f"{max(t['z'] for t in R['trattamenti']):+.2f}")
        R["desi_sempre_estremo"] = bool(pos == {0})
        R["posizioni_sotto_desi"] = sorted(pos)

        # --- coerenza fra canali -------------------------------------------
        print(f"\n  COERENZA: i patologici lo sono anche in null e remap?")
        for ch in ("null.N_H1", "remap.N_H1"):
            vals = np.array([float(r.get(ch, np.nan)) for r in recs])
            if not np.isfinite(vals).any():
                continue
            mc, sc = robust_scale(vals[np.isfinite(vals)])
            rzc = (vals - mc) / sc
            pc = set(np.where(rzc < -ROBUST_Z)[0].tolist())
            inter = len(pc & set(patol.tolist()))
            print(f"    {ch:<12s}: {len(pc)} patologici, "
                  f"{inter} in comune con base "
                  f"({100 * inter / max(patol.size, 1):.0f}% dei nostri)")
            R.setdefault("coerenza_canali", {})[ch] = {
                "n_patologici": len(pc), "in_comune_con_base": inter}

        rep["regioni"][reg] = json.loads(json.dumps(R, default=jsonable))

    outp = our_dir / "rev_v2b_outliers_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()
