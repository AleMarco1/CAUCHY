#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n4n5.py

N4 - STABILITA' DI TABELLA 3 RISPETTO ALLA SCELTA P10  (R2.6, R3.min3)
N5 - INCERTEZZE OMOGENEE PER L'ESPERIMENTO SPECCHIO    (R3.6iv, R2.min1)

SICUREZZA DEL PARALLELISMO CON paper1_rev_n2_persistence.py
-----------------------------------------------------------
N2 satura una CPU con gudhi e legge in sequenza phase8_test2_fields/*.npz.

Questo script:
  - non usa gudhi ne' FFT: solo momenti, secondi di CPU
  - legge al massimo --k campi (default 200, ~1.7 GB) dalla stessa directory
  - SCRIVE un solo file: results/paper1/rev_n4n5_report.json
  - NON tocca n2_persistence_NGC.jsonl ne' n2_report_NGC.json

L'unica contesa e' l'I/O su disco. Se l'ETA di N2 peggiora sensibilmente,
interrompi questo e rilancialo dopo: e' idempotente.

N4 - COSA CHIEDE IL REFEREE
---------------------------
R2 §6: "Il taglio dei 'clean voxels' (P10 della densita' dei random), i livelli
di erosione, e soprattutto la soglia w_bar >= 0.99 sono tutti fissati a
posteriori sugli stessi dati [...] la scelta P10 va accompagnata da una verifica
di stabilita' (P5, P15) per le conclusioni di Tabella 3."
R3 minore 3: "Sez. 4.2: dichiarare la stabilita' dei momenti di Tabella 3
rispetto alla scelta P10 (P5/P15)."

Tabella 3 contiene MOMENTI, non N_H1: niente gudhi.

AUTOCONTROLLO OBBLIGATORIO
--------------------------
La maschera costruita al P10 della densita' dei random deve riprodurre
bgs_ngc_mask_128.npy. Se non la riproduce, il "P10" dichiarato nel paper non e'
cio' che il codice ha usato, ed e' una discrepanza da conoscere PRIMA di
rispondere a R2.6. Lo script lo misura invece di assumerlo.

N5 - COSA CHIEDE IL REFEREE
---------------------------
R3.6(iv): "L'esperimento specchio usa 50 mock contro i 2000 del forward:
quotare l'incertezza di g1p in modo omogeneo."
Con n = 50 l'errore standard sulla media e' sigma/sqrt(50) = 0.141*sigma,
contro 0.022*sigma a n = 2000: un fattore 6.3. Se i due numeri sono quotati
entrambi come "+/- sigma" o entrambi come "+/- SEM" senza dire quale, il
confronto e' fuorviante. Qui si calcolano entrambe le convenzioni per
ciascuna quantita', cosi' il testo puo' dichiararle esplicitamente.

USO
---
  python src\\paper1_rev_n4n5.py
  python src\\paper1_rev_n4n5.py --k 400
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

PCTS = (5, 10, 15)
NH1 = "base.N_H1"


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


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def moments(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size < 10:
        return {}
    m, s = float(v.mean()), float(v.std(ddof=1))
    return {"n": int(v.size), "mean": m, "std": s,
            "skew": float(((v - m) ** 3).mean() / s ** 3) if s > 0 else np.nan,
            "kurt": float(((v - m) ** 4).mean() / s ** 4 - 3.0) if s > 0 else np.nan,
            "p1": float(np.percentile(v, 1)),
            "p99": float(np.percentile(v, 99))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--min_idx", type=int, default=200)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    rep = {"script": "paper1_rev_n4n5.py"}

    # ================================================================ N4-A
    print("=" * 78)
    print("N4-A - LE MASCHERE A P5 / P10 / P15")
    print("=" * 78)
    frozen_p = (root / "data" / "processed" / "phase6_fields" /
                "bgs_ngc_mask_128.npy")
    frozen = np.load(frozen_p).astype(bool)
    print(f"  maschera congelata: {frozen_p}")
    print(f"    riempimento {100*frozen.mean():.4f}%  "
          f"({int(frozen.sum())} voxel)")

    rcache = res / "paper1" / "n4_random_field.npy"
    if rcache.exists():
        field_r = np.load(rcache)
        print(f"  campo dei random da cache: {rcache}")
    else:
        print("  caricamento del campo dei random dai FITS (qualche minuto)...")
        field_r, _ = M.load_desi_random_field()
        rcache.parent.mkdir(parents=True, exist_ok=True)
        np.save(rcache, field_r)
        print(f"  messo in cache: {rcache}")

    pos = field_r[field_r > 0]
    print(f"\n  densita' dei random: {pos.size} voxel non nulli "
          f"({100*pos.size/field_r.size:.2f}% della griglia)")
    masks = {}
    print(f"\n  {'soglia':>8s} {'valore':>14s} {'voxel':>9s} {'riemp.%':>9s} "
          f"{'concordanza con la congelata':>30s}")
    for p in PCTS:
        thr = float(np.percentile(pos, p))
        m = field_r > thr
        agree = float((m == frozen).mean())
        jac = float((m & frozen).sum() / max((m | frozen).sum(), 1))
        masks[p] = m
        print(f"  {'P'+str(p):>8s} {thr:>14.6g} {int(m.sum()):>9d} "
              f"{100*m.mean():>9.4f} "
              f"{'identica' if agree == 1.0 else f'{100*agree:.4f}% voxel, Jaccard {jac:.4f}':>30s}")
        rep.setdefault("maschere", {})[f"P{p}"] = {
            "soglia": thr, "n_voxel": int(m.sum()),
            "riempimento_pct": 100 * float(m.mean()),
            "concordanza": agree, "jaccard": jac}

    j10 = rep["maschere"]["P10"]["jaccard"]
    print(f"\n  AUTOCONTROLLO: la maschera P10 riproduce la congelata? "
          f"{'SI' if j10 > 0.999 else 'NO'}   (Jaccard {j10:.4f})")
    if j10 <= 0.999:
        print(f"  *** Il 'P10 della densita' dei random' dichiarato nel paper")
        print(f"      NON e' la maschera congelata. La verifica di stabilita'")
        print(f"      chiesta da R2.6 va formulata sulla definizione VERA, che")
        print(f"      va prima identificata: qui P5/P10/P15 sono comunque")
        print(f"      calcolati e danno l'ordine di grandezza dell'effetto. ***")
    rep["p10_riproduce_congelata"] = bool(j10 > 0.999)

    # ================================================================ N4-B
    print("\n" + "=" * 78)
    print("N4-B - MOMENTI SOTTO LE TRE MASCHERE")
    print("=" * 78)
    desi_p = res / "paper1" / "n1_desi_nu_NGC.npy"
    fdir = res / "phase8_test2_fields"
    if not desi_p.exists():
        print("  [!] campo nu di DESI non in cache: esegui prima N1b")
        return
    nu_d = np.load(desi_p)

    files = [(int(p.stem.split("_")[1]), p)
             for p in sorted(fdir.glob("test2_*.npz"))]
    files = [(i, p) for i, p in files if i >= args.min_idx][:args.k]
    print(f"  DESI + {len(files)} mock (sottoinsieme: serve la STABILITA',")
    print(f"  non il valore al terzo decimale)")

    rep["momenti"] = {}
    for p in PCTS:
        mk = masks[p] & frozen if not rep["p10_riproduce_congelata"] else masks[p]
        md = moments(nu_d[masks[p]])
        rows = []
        for i, fp in files:
            try:
                nu = np.load(fp)["delta"]
            except Exception:
                continue
            rows.append(moments(nu[masks[p]]))
        if not rows:
            continue
        agg = {}
        for k in ("mean", "std", "skew", "kurt"):
            v = np.array([r[k] for r in rows if k in r], float)
            agg[k] = {"mock_mean": float(np.nanmean(v)),
                      "mock_sd": float(np.nanstd(v, ddof=1)),
                      "desi": float(md.get(k, np.nan))}
            agg[k]["z"] = ((agg[k]["desi"] - agg[k]["mock_mean"]) /
                           agg[k]["mock_sd"] if agg[k]["mock_sd"] > 0 else np.nan)
        rep["momenti"][f"P{p}"] = {"n_mock": len(rows), "agg": agg,
                                   "desi_full": md}
        print(f"\n  --- P{p}   ({int(masks[p].sum())} voxel, {len(rows)} mock)")
        print(f"      {'momento':>8s} {'mock':>14s} {'sd':>10s} {'DESI':>12s} "
              f"{'z':>8s}")
        for k in ("mean", "std", "skew", "kurt"):
            a = agg[k]
            print(f"      {k:>8s} {a['mock_mean']:>14.5f} {a['mock_sd']:>10.5f} "
                  f"{a['desi']:>12.5f} {a['z']:>+8.2f}")

    print("\n  STABILITA' (variazione di z fra P5 e P15):")
    for k in ("mean", "std", "skew", "kurt"):
        zs = [rep["momenti"][f"P{p}"]["agg"][k]["z"] for p in PCTS
              if f"P{p}" in rep["momenti"]]
        if len(zs) == 3:
            print(f"    {k:>8s}: z = {zs[0]:+.2f} / {zs[1]:+.2f} / {zs[2]:+.2f}"
                  f"   escursione {max(zs)-min(zs):+.2f}")
    print("\n  -> se l'escursione di z e' piccola rispetto a z stesso, le")
    print("     conclusioni di Tabella 3 sono stabili e la posteriorita' della")
    print("     scelta P10 e' innocua per quei numeri. Va comunque DICHIARATA,")
    print("     come R2.6 chiede in via principale.")

    # ================================================================ N5
    print("\n" + "=" * 78)
    print("N5 - INCERTEZZE OMOGENEE  (R3.6iv)")
    print("=" * 78)
    print("  Con n=50 l'errore standard sulla media e' sigma/sqrt(50) =")
    print("  0.1414*sigma; a n=2000 e' 0.0224*sigma. Fattore 6.3.")

    # cerca l'output dell'esperimento specchio
    pat = re.compile(r"mirror|specchio|g1p", re.I)
    cands = []
    for pth in (res).rglob("*.json"):
        if pth.stat().st_size > 50e6:
            continue
        try:
            txt = pth.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if pat.search(txt) or pat.search(pth.name):
            cands.append(pth)
    print(f"\n  file candidati per l'esperimento specchio: {len(cands)}")
    rep["file_specchio"] = [str(c) for c in cands[:10]]
    for c in cands[:6]:
        print(f"    {c}")
        try:
            J = json.load(open(c, encoding="utf-8"))
        except Exception:
            continue
        for k, v in sorted(flatten(J).items()):
            if pat.search(k) or (isinstance(v, (int, float))
                                 and re.search(r"g1p|mirror", k, re.I)):
                print(f"      {k} = {v}")

    # incertezze omogenee dai JSONL
    print(f"\n  incertezze dai JSONL, in entrambe le convenzioni:")
    print(f"    {'grandezza':>22s} {'n':>6s} {'media':>12s} {'sd':>10s} "
          f"{'SEM':>10s}")
    rep["incertezze"] = {}
    for reg in ("NGC", "SGC"):
        recs = read_jsonl(res / "paper1" / f"per_mock_{reg}_R5.jsonl")
        if not recs:
            continue
        for ch in ("base", "null", "remap"):
            v = np.array([float(r.get(ch, {}).get("N_H1", np.nan))
                          for r in recs])
            v = v[np.isfinite(v)]
            if v.size < 10:
                continue
            sd = float(v.std(ddof=1))
            sem = sd / np.sqrt(v.size)
            nome = f"{reg} {ch}.N_H1"
            print(f"    {nome:>22s} {v.size:>6d} {v.mean():>12.2f} "
                  f"{sd:>10.2f} {sem:>10.2f}")
            rep["incertezze"][nome] = {"n": int(v.size), "mean": float(v.mean()),
                                       "sd": sd, "sem": float(sem)}
        # differenza null - base: il canale del test nullo
        b = np.array([float(r.get("base", {}).get("N_H1", np.nan)) for r in recs])
        nl = np.array([float(r.get("null", {}).get("N_H1", np.nan)) for r in recs])
        d = (nl - b)[np.isfinite(nl - b)]
        if d.size > 10:
            sd = float(d.std(ddof=1))
            print(f"    {reg+' null-base':>22s} {d.size:>6d} {d.mean():>12.2f} "
                  f"{sd:>10.2f} {sd/np.sqrt(d.size):>10.2f}")
            rep["incertezze"][f"{reg} null-base"] = {
                "n": int(d.size), "mean": float(d.mean()), "sd": sd,
                "sem": float(sd / np.sqrt(d.size))}

    print("\n  -> nel testo, ogni incertezza va etichettata esplicitamente come")
    print("     sd dell'ensemble o SEM, e per il specchio va indicato n=50")
    print("     accanto al numero. E' l'unica cosa che R3.6(iv) chiede.")

    atomic_write_json(res / "paper1" / "rev_n4n5_report.json", rep)
    print("\n" + "=" * 78)
    print(f"report: {res/'paper1'/'rev_n4n5_report.json'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
