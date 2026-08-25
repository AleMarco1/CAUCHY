#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2c_provenance.py

V2c - PROVENIENZA DEL BLOCCO 0-199 E NATURA DEI MOCK PATOLOGICI

Contesto (esito di v2v3 e v2b):
  - sigma_px costante: 0.320422 (NGC), 0.336055 (SGC). Ensemble non misto.
  - discrepanti vs M26 = ESATTAMENTE gli indici 0-199, blocco contiguo.
  - sigma robuste quasi identiche: noi 264.6, M26 269.8 (2%).
    Tutta la differenza 313 vs 445 sta nel conteggio della coda:
    4 mock patologici da noi, 16 in M26.
  - patologici NGC {139, 598, 1430, 1666}, SGC {598, 1022, 1430, 1666}:
    TRE COINCIDONO fra emisferi con geometrie diverse.

TRE DOMANDE
-----------
D1  ALLINEAMENTO. Finora il confronto JSONL<->npz era POSIZIONALE. L'npz ha
    un array 'index' e il JSONL un campo 'key'. Se i primi 200 slot non
    contengono gli stessi mock, l'intera lettura del blocco 0-199 cade.
    Questo e' il primo controllo e blocca tutto il resto.

D2  PROVENIENZA. I campi 'tag' e 'ts' del JSONL datano ogni record. Se i
    record 0-199 portano tag o timestamp diversi dal resto, il blocco viene
    da un run precedente (o da una versione precedente del codice) che
    l'auto-resume append-only ha poi saltato. Sarebbe un difetto di
    integrita' nostro, da correggere rigenerando quei 200.

D3  NATURA DEI PATOLOGICI. L'npz porta w0, Om, s8 per mock. Se i patologici
    sono cosmologie estreme del Latin hypercube sono membri LEGITTIMI
    dell'ensemble e vanno tenuti (quotando la dispersione robusta accanto
    alla grezza). Se sono cosmologie ordinarie con campi rotti sono GUASTI e
    vanno esclusi con una regola dichiarata. La decisione cambia i numeri
    del paper e non va presa a occhio.

Solo lettura. Scrive un unico report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2c_provenance.py
"""

import argparse
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

DESI = {"NGC": 28256.0, "SGC": 15122.0}
NH1 = "base.N_H1"
ATOL = 0.5
ROBUST_Z = 5.0
PATOL = {"NGC": [139, 598, 1430, 1666], "SGC": [598, 1022, 1430, 1666]}


# ---------------------------------------------------------------- io
def read_jsonl(path):
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
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def as_int_id(x):
    """Estrae un intero da 'key': accetta 12, '12', 'mock_0012', 'NGC_0012'."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return int(x)
    m = re.findall(r"\d+", str(x))
    return int(m[-1]) if m else None


def fmt_ts(t):
    """Normalizza un timestamp epoch o ISO in stringa leggibile."""
    import datetime as dt
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        v = float(t)
        if v > 1e11:          # millisecondi
            v /= 1000.0
        try:
            return dt.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(t)
    return str(t)


def ts_sortkey(t):
    import datetime as dt
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        v = float(t)
        return v / 1000.0 if v > 1e11 else v
    s = str(t)
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:26], f).timestamp()
        except Exception:
            pass
    return float("nan")


def robust_scale(v):
    med = float(np.median(v))
    mad = float(1.4826 * np.median(np.abs(v - med)))
    return med, (mad if mad > 0 else float(v.std(ddof=1)))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--m26_npz", default="results\\phase9_likeforlike_arrays.npz")
    ap.add_argument("--max_print", type=int, default=30)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    our_dir = root / "results" / "paper1"
    rep = {"script": "paper1_rev_v2c_provenance.py"}

    # ============================================================ npz
    print("=" * 78)
    print("NPZ DI M26 - CONTENUTO COMPLETO")
    print("=" * 78)
    parts = [q for q in args.m26_npz.replace("\\", "/").split("/") if q]
    npz_path = (Path(args.m26_npz) if Path(args.m26_npz).is_absolute()
                else root.joinpath(*parts))
    if not npz_path.exists():
        print(f"  [!] {npz_path} non trovato")
        return
    z = np.load(npz_path, allow_pickle=True)
    Z = {}
    for k in z.files:
        a = np.asarray(z[k])
        Z[k] = a
        if a.ndim == 0:
            print(f"  {k:<18s} scalare = {a.item()!r}")
        elif a.dtype.kind in "fi" and a.size:
            print(f"  {k:<18s} shape={str(a.shape):<10s} dtype={a.dtype}  "
                  f"min={a.min():<12.6g} med={np.median(a):<12.6g} "
                  f"max={a.max():<12.6g}")
        else:
            print(f"  {k:<18s} shape={str(a.shape):<10s} dtype={a.dtype}")
    rep["npz"] = {k: (Z[k].tolist() if Z[k].size <= 8 else
                      {"shape": list(Z[k].shape), "dtype": str(Z[k].dtype)})
                  for k in Z}

    m26 = np.asarray(Z["beta1_max"], float)
    m_idx = np.asarray(Z["index"]).ravel() if "index" in Z else None
    cosmo = {k: np.asarray(Z[k], float).ravel()
             for k in ("w0", "Om", "s8") if k in Z}

    # ============================================================ D1
    print("\n" + "=" * 78)
    print("D1 - ALLINEAMENTO: il join per identificatore conferma la posizione?")
    print("=" * 78)
    if m_idx is None:
        print("  npz senza array 'index' -> resta solo l'allineamento posizionale")
    else:
        mono = bool(np.all(np.diff(m_idx.astype(float)) == 1))
        print(f"  npz['index']: primi valori {m_idx[:6].tolist()} ... "
              f"ultimi {m_idx[-3:].tolist()}")
        print(f"  strettamente crescente di 1: {'SI' if mono else 'NO'}")

    results = {}
    for reg in ("NGC", "SGC"):
        p = our_dir / f"per_mock_{reg}_R5.jsonl"
        if not p.exists():
            print(f"\n  [!] {p} non trovato")
            continue
        recs, bad = read_jsonl(p)
        flat = [flatten(r) for r in recs]
        vals = np.array([float(f.get(NH1, np.nan)) for f in flat])
        keys = [f.get("key") for f in flat]
        kint = np.array([as_int_id(k) if as_int_id(k) is not None else -1
                         for k in keys])
        tags = [f.get("tag") for f in flat]
        tss = [f.get("ts") for f in flat]
        results[reg] = dict(recs=recs, flat=flat, vals=vals, keys=keys,
                            kint=kint, tags=tags, tss=tss, bad=bad)

        print(f"\n  {reg}: {len(recs)} record ({bad} scartati)")
        print(f"    esempi di 'key': {keys[:3]} ... {keys[-2:]}")
        pos_ok = bool(np.all(kint == np.arange(len(kint))))
        print(f"    key == posizione nel file per ogni record: "
              f"{'SI' if pos_ok else 'NO'}")
        if not pos_ok:
            fuori = np.where(kint != np.arange(len(kint)))[0]
            print(f"    *** {fuori.size} record fuori ordine; primi: "
                  f"{fuori[:10].tolist()} ***")
            print(f"    -> l'analisi posizionale precedente va RIFATTA sul join")
        print(f"    id duplicati: "
              f"{len(kint) - len(set(kint.tolist()))}")
        print(f"    id mancanti in 0..{len(kint)-1}: "
              f"{sorted(set(range(len(kint))) - set(kint.tolist()))[:10]}")

    # ============================================================ D2
    print("\n" + "=" * 78)
    print("D2 - PROVENIENZA: i record 0-199 vengono da un run diverso?")
    print("=" * 78)
    rep["provenienza"] = {}
    for reg, R in results.items():
        print(f"\n  --- {reg} ---")
        tag_c = Counter(map(str, R["tags"]))
        print(f"    tag distinti: {len(tag_c)}")
        for t, c in tag_c.most_common(10):
            idx = [i for i, x in enumerate(R["tags"]) if str(x) == t]
            print(f"      {t!r:<28s} {c:>5d} record   "
                  f"indici {min(idx)}..{max(idx)}")

        tsk = np.array([ts_sortkey(t) for t in R["tss"]], float)
        finite = np.isfinite(tsk)
        print(f"\n    timestamp leggibili: {int(finite.sum())}/{len(tsk)}")
        if finite.any():
            print(f"      primo record : {fmt_ts(R['tss'][0])}")
            print(f"      record 199   : {fmt_ts(R['tss'][199])}"
                  if len(tsk) > 199 else "")
            print(f"      record 200   : {fmt_ts(R['tss'][200])}"
                  if len(tsk) > 200 else "")
            print(f"      ultimo       : {fmt_ts(R['tss'][-1])}")
            if len(tsk) > 200 and finite[:200].any() and finite[200:].any():
                a = np.nanmedian(tsk[:200])
                b = np.nanmedian(tsk[200:])
                gap = (b - a) / 3600.0
                print(f"\n      mediana ts blocco 0-199   : {fmt_ts(a)}")
                print(f"      mediana ts blocco 200-fine: {fmt_ts(b)}")
                print(f"      separazione: {gap:+.2f} ore")
                sep = bool(finite[:200].all() and finite[200:].all()
                           and (tsk[:200].max() < tsk[200:].min()
                                or tsk[:200].min() > tsk[200:].max()))
                print(f"      i due blocchi sono temporalmente DISGIUNTI: "
                      f"{'SI  *** run separato confermato ***' if sep else 'NO'}")
                rep["provenienza"][reg] = {
                    "tag": dict(tag_c), "gap_ore": gap, "blocchi_disgiunti": sep,
                    "ts_mediano_0_199": fmt_ts(a), "ts_mediano_200_fine": fmt_ts(b)}

        # salti temporali maggiori: rivelano i confini fra run
        if finite.all() and len(tsk) > 10:
            d = np.diff(tsk)
            big = np.where(d > max(60.0, 20 * np.median(d[d > 0])))[0]
            if big.size:
                print(f"\n    interruzioni (salto >> passo tipico), "
                      f"prime {min(big.size, 8)}:")
                for i in big[:8]:
                    print(f"      fra record {i} e {i+1}: "
                          f"{d[i]/60:.1f} min di stacco")
                rep.setdefault("interruzioni", {})[reg] = big[:20].tolist()

    # ============================================================ D2b
    print("\n" + "=" * 78)
    print("D2b - IL BLOCCO 0-199 CONFRONTATO CON M26 (solo NGC)")
    print("=" * 78)
    if "NGC" in results and m26.size == results["NGC"]["vals"].size:
        v = results["NGC"]["vals"]
        d = v - m26
        same = np.isclose(v, m26, rtol=0.0, atol=ATOL)
        blk = slice(0, 200)
        print(f"  identici nel blocco 0-199   : {int(same[blk].sum())}/200")
        print(f"  identici nel resto 200-1999 : {int(same[200:].sum())}/1800")
        print(f"\n  differenza (nostro - M26) sul blocco 0-199:")
        print(f"    mediana {np.median(d[blk]):+.1f}   media {d[blk].mean():+.1f}"
              f"   sd {d[blk].std(ddof=1):.1f}")
        print(f"    range [{d[blk].min():+.0f}, {d[blk].max():+.0f}]")
        print(f"    nostro piu' basso in {int((d[blk] < 0).sum())}/200 casi")
        med_m, sig_m = robust_scale(m26)
        pm = np.where((m26 - med_m) / sig_m < -ROBUST_Z)[0]
        print(f"\n  patologici di M26: {pm.size} -> indici {pm.tolist()}")
        print(f"    di cui nel blocco 0-199: "
              f"{int((pm < 200).sum())}   fuori blocco: {int((pm >= 200).sum())}")
        print(f"  patologici nostri NGC: {PATOL['NGC']}")
        print(f"\n  {'idx':>5s} {'nostro':>9s} {'M26':>9s} {'diff':>8s}"
              + ("  " + "".join(f"{k:>9s}" for k in cosmo) if cosmo else ""))
        for i in pm[:args.max_print]:
            extra = "".join(f"{cosmo[k][i]:>9.4f}" for k in cosmo) if cosmo else ""
            print(f"  {i:>5d} {v[i]:>9.0f} {m26[i]:>9.0f} {d[i]:>+8.0f}  {extra}")

        # cosa sarebbe la nostra sigma adottando M26 sul blocco
        w = v.copy(); w[blk] = m26[blk]
        print(f"\n  se adottassimo i valori M26 su 0-199:")
        print(f"    sigma {w.std(ddof=1):.1f}  (ora {v.std(ddof=1):.1f}, "
              f"M26 {m26.std(ddof=1):.1f})")
        print(f"    -> {'riproduce M26' if abs(w.std(ddof=1) - m26.std(ddof=1)) < 5 else 'NON riproduce M26: la differenza non e solo il blocco'}")
        rep["blocco_0_199"] = {
            "identici_blocco": int(same[blk].sum()),
            "identici_resto": int(same[200:].sum()),
            "diff_mediana": float(np.median(d[blk])),
            "diff_sd": float(d[blk].std(ddof=1)),
            "patologici_m26": pm.tolist(),
            "patologici_m26_nel_blocco": int((pm < 200).sum()),
            "sigma_con_valori_m26_sul_blocco": float(w.std(ddof=1)),
        }

    # ============================================================ D3
    print("\n" + "=" * 78)
    print("D3 - I PATOLOGICI SONO COSMOLOGIE ESTREME O CAMPI ROTTI?")
    print("=" * 78)
    if not cosmo:
        print("  npz senza w0/Om/s8: test non eseguibile")
    else:
        allp = sorted(set(PATOL["NGC"]) | set(PATOL["SGC"]))
        cond = sorted(set(PATOL["NGC"]) & set(PATOL["SGC"]))
        print(f"  patologici NGC {PATOL['NGC']}")
        print(f"  patologici SGC {PATOL['SGC']}")
        print(f"  CONDIVISI fra i due emisferi: {cond}")
        print(f"\n  posizione nel Latin hypercube (percentile entro i 2000 mock):")
        head = f"  {'idx':>5s} {'emisferi':>10s}"
        for k in cosmo:
            head += f" {k:>8s} {'pct':>5s}"
        print(head)
        rep["cosmologia_patologici"] = {}
        for i in allp:
            where = ("NGC+SGC" if i in cond
                     else ("NGC" if i in PATOL["NGC"] else "SGC"))
            line = f"  {i:>5d} {where:>10s}"
            entry = {"emisferi": where}
            for k, a in cosmo.items():
                pct = 100.0 * (a < a[i]).mean()
                line += f" {a[i]:>8.4f} {pct:>5.1f}"
                entry[k] = {"valore": float(a[i]), "percentile": float(pct)}
            print(line)
            rep["cosmologia_patologici"][str(i)] = entry

        print(f"\n  LETTURA:")
        print(f"    percentili estremi (<5 o >95) su s8/Om -> cosmologie di")
        print(f"      frontiera: membri LEGITTIMI, da TENERE, con dispersione")
        print(f"      robusta quotata accanto alla grezza.")
        print(f"    percentili centrali -> campi ROTTI: si esclude con regola")
        print(f"      dichiarata (|z_robusto| > 5) applicata a tutto l'ensemble.")

        # regressione N_H1 ~ cosmologia: anticipo di N1
        if "NGC" in results:
            v = results["NGC"]["vals"]
            print(f"\n  correlazione N_H1 x cosmologia sull'ensemble "
                  f"(anticipo di N1):")
            for k, a in cosmo.items():
                m = np.isfinite(a) & np.isfinite(v)
                r = float(np.corrcoef(a[m], v[m])[0, 1])
                ra = np.argsort(np.argsort(a[m])); rv = np.argsort(np.argsort(v[m]))
                rs = float(np.corrcoef(ra, rv)[0, 1])
                print(f"    {k:>4s}: Pearson {r:+.3f}   Spearman {rs:+.3f}")
                rep.setdefault("corr_cosmologia", {})[k] = {"pearson": r,
                                                            "spearman": rs}

    outp = our_dir / "rev_v2c_provenance_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()
