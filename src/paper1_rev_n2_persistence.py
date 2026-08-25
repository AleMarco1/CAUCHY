#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n2_persistence.py

N2 - IL DEFICIT IN FUNZIONE DI UN TAGLIO IN PERSISTENZA

Referee 1 §3 (l'editore lo elenca fra i test decisivi calcolabili dai dati in
mano): "Il manoscritto localizza il deficit in SOGLIA DI NASCITA ma mai in
PERSISTENZA: e' indispensabile mostrare il deficit in funzione di un taglio
p > eps. Se il 20% mancante vive nelle coppie a bassa persistenza,
l'interpretazione corretta e' 'deficit di fluttuazioni transienti a scala di
voxel' - compatibile con effetti di campionamento - non 'connettivita' del web
cosmico'. Questo singolo grafico cambierebbe il peso di tutto il paper."

PERCHE' N1 HA ALZATO LA POSTA
-----------------------------
N1 ha trovato che il miglior predittore di N_H1 e' f_three_q (r = +0.826): il
deficit vive alle scale piu' piccole. E' esattamente lo scenario che Referee 1
teme. N2 e' ora il rischio principale del paper.

LA SCELTA DI DISEGNO CHE DECIDE IL RISULTATO
--------------------------------------------
Il lemma di invarianza monotona vale per N_H1 TOTALE. N_H1(p > eps) NON e'
invariante: dipende dalla scala del campo. E i due campi hanno scale diverse:
sigma dentro maschera 2.686 (DESI) contro 2.077 (mock), +29%.

  -> A eps ASSOLUTO fisso, DESI trattiene relativamente piu' coppie e il
     deficit apparente si riduce per un artefatto di normalizzazione.

La scelta coerente col codice esistente e' AUTONORMALIZZARE:
compute_tda_features fissa gia' la griglia di soglie della curva di Betti sui
percentili 1 e 99 del campo dentro maschera. Si usa lo stesso intervallo
(R_f = p99 - p1) come unita' per eps.

Si calcolano ENTRAMBE le versioni e si riportano affiancate: se la conclusione
cambia fra le due, e' un risultato da dichiarare, non un dettaglio da scegliere
in silenzio.

COSA VIENE MISURATO
-------------------
Per DESI e per ogni mock, il diagramma di persistenza H1 sotto la filtrazione
mascherata IDENTICA a compute_tda_features (masked=True, stesso sentinella,
stesso cutoff), poi:

    N_H1(eps) = numero di coppie con persistenza > eps

e la quantita' che risponde a Referee 1:

    frazione del deficit che SOPRAVVIVE al taglio
      = [media_mock(eps) - DESI(eps)] / [media_mock(0) - DESI(0)]

  frazione ~ costante al crescere di eps  -> il deficit e' nelle coppie
    persistenti: interpretazione strutturale RAFFORZATA
  frazione che crolla verso 0             -> il deficit e' nel rumore vicino
    alla diagonale: interpretazione "fluttuazioni a scala di voxel", e la
    lettura strutturale CADE

AUTOCONTROLLO
-------------
A eps = 0 il conteggio deve riprodurre ESATTAMENTE il valore congelato: 28256
per DESI, e il valore in per_mock_NGC_R5.jsonl per ogni mock. Se non lo fa, lo
script si ferma.

Sorgente: results/phase8_test2_fields/test2_XXXX.npz['delta'] (contiene nu),
indici >= 200 (0-199 sono i cubi del run con HOD diverso).
Append-only JSONL, resumable. ~8 s per campo: 1800 campi ~ 4 h, interrompibile.

USO
---
  python src\\paper1_rev_n2_persistence.py --k 20      # validazione
  python src\\paper1_rev_n2_persistence.py --k 600     # sufficiente
  python src\\paper1_rev_n2_persistence.py             # tutti i 1800
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
SENT = 1.0e6

# griglia di eps autonormalizzato, in unita' di R_f = p99 - p1 del campo
EPS_NORM = [0.0, 0.001, 0.002, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03,
            0.04, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
# griglia di eps assoluto, in unita' di nu
EPS_ABS = [0.0, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15,
           0.20, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50, 2.00]


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


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def h1_persistence(nu, mask):
    """Diagramma H1 sotto la filtrazione mascherata, identica a
    compute_tda_features(masked=True). Restituisce (nascite, persistenze, R_f).
    R_f = p99 - p1 del campo dentro maschera, la stessa scala che il codice
    esistente usa per la griglia di soglie della curva di Betti."""
    import gudhi
    field = nu.astype(np.float64)
    fin = field[mask]
    p1v, p99v = np.percentile(fin, 1), np.percentile(fin, 99)
    R_f = float(p99v - p1v)

    fw = field.copy()
    fw[~mask] = -SENT
    fneg = -fw
    cutoff = SENT / 2.0

    cc = gudhi.CubicalComplex(dimensions=list(fneg.shape),
                              top_dimensional_cells=fneg.flatten())
    cc.compute_persistence()
    d = np.asarray(cc.persistence_intervals_in_dimension(1))
    if d.size == 0:
        return np.array([]), np.array([]), R_f
    keep = np.isfinite(d[:, 1]) & (d[:, 0] < cutoff) & (d[:, 1] < cutoff)
    df = d[keep]
    birth = -df[:, 0]
    death = -df[:, 1]
    return birth, birth - death, R_f


def counts(pers, R_f):
    """N_H1(eps) sulle due griglie."""
    cn = [int((pers > e * R_f).sum()) for e in EPS_NORM]
    ca = [int((pers > e).sum()) for e in EPS_ABS]
    return cn, ca


def summarize(nu, mask):
    birth, pers, R_f = h1_persistence(nu, mask)
    cn, ca = counts(pers, R_f)
    out = {"n_tot": int(pers.size), "R_f": R_f,
           "cnt_norm": cn, "cnt_abs": ca,
           "pers_median": float(np.median(pers)) if pers.size else np.nan,
           "pers_p90": float(np.percentile(pers, 90)) if pers.size else np.nan,
           "pers_max": float(pers.max()) if pers.size else np.nan,
           "pers_mean": float(pers.mean()) if pers.size else np.nan}
    if pers.size:
        # nascita mediana delle coppie sopra e sotto la mediana di persistenza
        m = pers > np.median(pers)
        out["birth_median_high_pers"] = float(np.median(birth[m]))
        out["birth_median_low_pers"] = float(np.median(birth[~m]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--analyze_only", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    fields = res / "phase8_test2_fields"
    outj = res / "paper1" / "n2_persistence_NGC.jsonl"
    desi_cache = res / "paper1" / "n1_desi_nu_NGC.npy"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)

    print("=" * 78)
    print("N2 - DEFICIT IN FUNZIONE DEL TAGLIO IN PERSISTENZA")
    print("=" * 78)

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(fl.get("key", j))
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    # ---------------------------------------------------- DESI
    print("\n[A] DESI")
    if not desi_cache.exists():
        print("  [FATAL] cache del campo nu di DESI assente: esegui prima N1b")
        return
    nu_d = np.load(desi_cache)
    dsum = summarize(nu_d, mask)
    print(f"  coppie H1 finite a eps=0: {dsum['n_tot']}   "
          f"atteso {DESI_NH1:.0f}   "
          f"{'OK' if abs(dsum['n_tot']-DESI_NH1)<0.5 else '*** FALLITO ***'}")
    if abs(dsum["n_tot"] - DESI_NH1) > 0.5:
        print("  Il diagramma non riproduce il valore congelato: la filtrazione")
        print("  replicata non e' identica a compute_tda_features. Mi fermo.")
        return
    print(f"  R_f (p99-p1 dentro maschera) = {dsum['R_f']:.5f}")
    print(f"  persistenza: mediana {dsum['pers_median']:.5f}  "
          f"p90 {dsum['pers_p90']:.5f}  max {dsum['pers_max']:.4f}")
    print(f"  nascita mediana: coppie ad alta persistenza "
          f"{dsum['birth_median_high_pers']:+.4f}, a bassa "
          f"{dsum['birth_median_low_pers']:+.4f}")

    # ---------------------------------------------------- mock
    if not args.analyze_only:
        allf = [(int(p.stem.split("_")[1]), p)
                for p in sorted(fields.glob("test2_*.npz"))]
        usable = [(i, p) for i, p in allf if i >= args.min_idx]
        done = {r["idx"] for r in read_jsonl(outj)}
        todo = [(i, p) for i, p in usable if i not in done]
        if args.k > 0:
            todo = todo[:args.k]
        print(f"\n[B] MOCK: {len(usable)} disponibili, {len(done)} fatti, "
              f"{len(todo)} da fare")
        t0 = time.time()
        for n, (i, p) in enumerate(todo, 1):
            s = summarize(np.load(p)["delta"], mask)
            exp = nh1.get(i, np.nan)
            if np.isfinite(exp) and abs(s["n_tot"] - exp) > 0.5:
                print(f"  *** idx {i}: eps=0 da' {s['n_tot']} ma il JSONL dice "
                      f"{exp:.0f}. Mi fermo. ***")
                return
            s["idx"] = i
            append_jsonl(outj, s)
            if n == 1 or n % 25 == 0:
                el = time.time() - t0
                print(f"    [{n}/{len(todo)}] idx={i}  n_tot={s['n_tot']}  "
                      f"{el/n:.1f} s/campo  ETA "
                      f"{el/n*(len(todo)-n)/60:.0f} min")
        if todo:
            print(f"  fatto in {(time.time()-t0)/60:.1f} min")

    # ---------------------------------------------------- analisi
    print("\n[C] ANALISI")
    recs = [r for r in read_jsonl(outj) if r["idx"] in nh1]
    if len(recs) < 20:
        print(f"  solo {len(recs)} mock: troppo pochi.")
        return
    print(f"  mock: {len(recs)}")

    rep = {"script": "paper1_rev_n2_persistence.py", "n_mock": len(recs),
           "desi": dsum, "eps_norm": EPS_NORM, "eps_abs": EPS_ABS,
           "tabelle": {}}

    for tag, key, grid, unita in (("AUTONORMALIZZATO", "cnt_norm", EPS_NORM,
                                   "in unita' di R_f"),
                                  ("ASSOLUTO", "cnt_abs", EPS_ABS,
                                   "in unita' di nu")):
        Cm = np.array([r[key] for r in recs], float)      # (n_mock, n_eps)
        Cd = np.array(dsum[key], float)
        d0 = float(Cm[:, 0].mean()) - Cd[0]

        print("\n" + "-" * 78)
        print(f"  TAGLIO {tag}  ({unita})")
        print("-" * 78)
        print(f"    {'eps':>8s} {'mock medio':>11s} {'sd':>8s} {'DESI':>9s} "
              f"{'deficit':>9s} {'def.%':>7s} {'sopravv.':>9s} "
              f"{'rank':>11s} {'z':>7s}")
        rows = []
        for j, e in enumerate(grid):
            mm = Cm[:, j]
            mu, sd = float(mm.mean()), float(mm.std(ddof=1))
            dv = Cd[j]
            defi = mu - dv
            fracdef = defi / mu if mu > 0 else np.nan
            surv = defi / d0 if d0 else np.nan
            below = int((mm < dv).sum())
            z = (dv - mu) / sd if sd > 0 else np.nan
            print(f"    {e:>8.4f} {mu:>11.1f} {sd:>8.1f} {dv:>9.0f} "
                  f"{defi:>9.0f} {100*fracdef:>6.1f}% {100*surv:>8.1f}% "
                  f"{below+1:>5d}/{len(recs)+1:<5d} {z:>+7.1f}")
            rows.append({"eps": e, "mock_mean": mu, "mock_sd": sd,
                         "desi": float(dv), "deficit": defi,
                         "deficit_frac": fracdef, "sopravvivenza": surv,
                         "rank": f"{below+1}/{len(recs)+1}",
                         "n_sotto": below, "z": float(z)})
        rep["tabelle"][tag] = rows

        # lettura
        surv = np.array([r["sopravvivenza"] for r in rows])
        fdef = np.array([r["deficit_frac"] for r in rows])
        nsub = np.array([r["n_sotto"] for r in rows])
        # ultimo eps con almeno 200 coppie residue nei mock
        okj = np.where(np.array([r["mock_mean"] for r in rows]) > 200)[0]
        jmax = int(okj[-1]) if okj.size else 0
        print(f"\n    lettura (fino a eps={grid[jmax]:.4f}, oltre il quale i "
              f"conteggi si assottigliano):")
        print(f"      sopravvivenza del deficit: da {100*surv[0]:.0f}% a "
              f"{100*surv[jmax]:.0f}%")
        print(f"      deficit frazionario:       da {100*fdef[0]:.1f}% a "
              f"{100*fdef[jmax]:.1f}%")
        print(f"      mock sotto DESI: sempre 0? "
              f"{'SI' if nsub[:jmax+1].max() == 0 else 'NO -> ' + str(nsub[:jmax+1].max())}")
        if surv[jmax] > 0.7:
            print(f"      -> IL DEFICIT E' NELLE COPPIE PERSISTENTI.")
            print(f"         L'interpretazione strutturale e' RAFFORZATA:")
            print(f"         il taglio rimuove rumore e il deficit resta.")
        elif surv[jmax] < 0.3:
            print(f"      -> IL DEFICIT E' NEL RUMORE VICINO ALLA DIAGONALE.")
            print(f"         L'interpretazione corretta e' 'deficit di")
            print(f"         fluttuazioni transienti a scala di voxel',")
            print(f"         compatibile con effetti di campionamento: la")
            print(f"         lettura strutturale CADE, come Referee 1 temeva.")
        else:
            print(f"      -> INTERMEDIO: il deficit e' distribuito su tutte le")
            print(f"         persistenze. Da quotare come tale, con la curva")
            print(f"         completa in figura invece di un enunciato binario.")

    # confronto fra le due normalizzazioni
    sn = np.array([r["sopravvivenza"] for r in rep["tabelle"]["AUTONORMALIZZATO"]])
    sa = np.array([r["sopravvivenza"] for r in rep["tabelle"]["ASSOLUTO"]])
    print("\n" + "=" * 78)
    print("CONFRONTO FRA LE DUE NORMALIZZAZIONI")
    print("=" * 78)
    print(f"  sopravvivenza a meta' griglia: autonormalizzato "
          f"{100*sn[len(sn)//2]:.0f}%, assoluto {100*sa[len(sa)//2]:.0f}%")
    print(f"  Se differiscono molto, la conclusione dipende dalla")
    print(f"  normalizzazione: va dichiarato quale e' primaria (autonormalizzato,")
    print(f"  per coerenza con la griglia di soglie della curva di Betti) e")
    print(f"  riportata l'altra come controllo.")
    rep["confronto_normalizzazioni"] = {
        "sopravvivenza_norm": sn.tolist(), "sopravvivenza_abs": sa.tolist()}

    atomic_write_json(res / "paper1" / "n2_report_NGC.json", rep)
    print(f"\n  report: {res/'paper1'/'n2_report_NGC.json'}")


if __name__ == "__main__":
    main()
