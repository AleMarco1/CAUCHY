#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 — diagnostica del residuo di Delta D. ESPLORATIVA.

QUESTA NON E' UNA MISURA
------------------------
Otto punti (dieci con il blocco A) e una decina di regressori candidati: e' una
battuta di pesca, e va letta come tale. Le significativita' NON sono corrette
per look-elsewhere, e con dieci candidati su otto punti ci si aspetta per puro
caso un regressore a 2 sigma.

  REGOLA, dichiarata prima di guardare: qualunque cosa esca da qui NON si adotta
  come termine del budget. Si usa solo per formulare UNA predizione, che va poi
  verificata su un dato che non e' stato usato per formularla — il blocco A, un
  emisfero contro l'altro, o un punto nuovo. Senza quella conferma, il residuo
  resta "non attribuito" e nel manoscritto ci va cosi'.

COSA CERCA
  Dopo aver sottratto il canale dei voxel con la pendenza MISURATA SU D — che
  non e' quella del lato dati: misurata +0.045 (NGC k=1) contro s = 0.1009, cioe'
  il 45%, mentre in SGC e' il 104% — resta un residuo di ~50 generatori rms fra i
  punti. Il tiling e' verificato a zero (repliche costanti, escursione 0.2%),
  sigma_px e' costante per costruzione, il carving vale 7 sulla media e la
  Prop. 2' 25. Il residuo non e' nessuno di questi.

PERCHE' LA PENDENZA SI MISURA SU D E NON SI PRENDE DAL LATO DATI
  D = <N_mock> - N_DESI, e i due lati condividono la maschera: se rispondessero
  allo stesso modo al conteggio dei voxel, il canale si cancellerebbe in D. Non
  si cancella (7-12 sigma), ma si cancella IN PARTE, e la parte dipende
  dall'emisfero. Usare s del lato dati sbaglierebbe di un fattore due in NGC.

Uso:
    python src\\paper2_fase3_residuo.py diag --region NGC
    python src\\paper2_fase3_residuo.py diag --region SGC --with-block-a
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def build_table(a, region, ki):
    """Una riga per punto, con tutte le quantita' gia' misurate."""
    # --- lato dati (3.1) -----------------------------------------------------
    D = {}
    for r in load_jsonl(a.data):
        if r.get("region") != region:
            continue
        nm = "FID" if (r.get("gate") == "d3" or r.get("gauge") == "fid") \
            else r.get("point")
        if r.get("gauge") in ("regauged", "fid") and nm:
            D[nm] = r
    if "FID" not in D:
        sys.exit(f"[FATAL] fiduciale assente in {a.data} per {region}")

    # --- lato mock (3.2): media per punto ------------------------------------
    Mk = {}
    for r in load_jsonl(a.mock):
        if r.get("region") != region or r.get("smoke") \
                or r.get("carve_reseed") is not None:
            continue
        for p, v in r["points"].items():
            Mk.setdefault(p, []).append(v)

    # --- tiling nel gauge dell'emendamento 13 --------------------------------
    T = {}
    for r in load_jsonl(a.tiling):
        if r.get("region") == region and r.get("gauge") == "amend13":
            T[r["point"]] = r
    if not T:
        print(f"  [avviso] nessun record di tiling con gauge amend13 in {a.tiling}: "
              f"i regressori del tiling non entrano.")

    # --- Delta D dall'analisi 3.4 (ULTIMO record della regione) --------------
    an = [r for r in load_jsonl(a.analisi) if r.get("region") == region]
    if not an:
        sys.exit(f"[FATAL] nessun record di analisi per {region} in {a.analisi}")
    per = an[-1]["levels"][f"k{ki}"]["per_point"]

    pts = [p for p in per]
    if a.with_block_a:
        # A1 e A3 non sono in per_point: il 3.4 li esclude perche' non sono
        # punti di misura. Qui servono, e valgono doppio: la Prop. 2 dice che il
        # segnale fisico e' NULLO, quindi il loro Delta D e' tutto artefatto.
        for p in ("A1", "A3"):
            if p in D and p in Mk:
                pts.append(p)

    key = f"N_H1_k{ki}"
    fidD, fidM = D["FID"], Mk["FID"]
    n = len(fidM)
    rows = []
    for p in pts:
        if p not in D or p not in Mk:
            continue
        dm = np.array([v[key] for v in Mk[p]], float)
        fm = np.array([v[key] for v in fidM], float)
        d = dm - fm
        dd_desi = D[p]["N_H1" if ki == 1 else "N_H1_k0"] \
            - fidD["N_H1" if ki == 1 else "N_H1_k0"]
        row = {
            "pt": p,
            "dD": (per[p]["estimate"] if p in per
                   else float(d.mean() - dd_desi)),
            "sem": (per[p]["sem"] if p in per
                    else float(d.std(ddof=1) / np.sqrt(len(d)))),
            "dV": D[p]["n_valid_voxels"] - fidD["n_valid_voxels"],
            "d_nsel": float(np.mean([v["n_sel"] for v in Mk[p]])
                            - np.mean([v["n_sel"] for v in fidM])),
            "d_dmed": D[p].get("d_med_voxel", np.nan)
                      - fidD.get("d_med_voxel", np.nan),
            "du": D[p].get("grid_shift_vs_fid", {}).get("max", np.nan),
            "d_occ": D[p].get("occupancy_gal_per_voxel", np.nan)
                     - fidD.get("occupancy_gal_per_voxel", np.nan),
            "d_alpha": D[p].get("alpha_fkp", np.nan) - fidD.get("alpha_fkp", np.nan),
        }
        for k in (0, 1, 2, 3):
            lp, lf = D[p].get("ladder", {}), fidD.get("ladder", {})
            if str(k) in lp and str(k) in lf:
                row[f"d_wbar{k}"] = lp[str(k)]["wbar"] - lf[str(k)]["wbar"]
        if p in T and "FID" in T:
            row["d_indip"] = T[p]["independent_fraction"] - T["FID"]["independent_fraction"]
            row["d_multmean"] = T[p]["mult_mean"] - T["FID"]["mult_mean"]
            row["d_multmax"] = float(T[p]["mult_max"] - T["FID"]["mult_max"])
        rows.append(row)
    return rows, n


def wls(x, y, w):
    """Pendenza per l'origine, pesata. Il residuo e' definito rispetto al
    fiduciale, quindi in x = 0 deve valere y = 0: nessuna intercetta."""
    sxx = float(np.sum(w * x * x))
    if sxx <= 0:
        return np.nan, np.nan
    sl = float(np.sum(w * x * y) / sxx)
    return sl, float(1.0 / np.sqrt(sxx))


def cmd_diag(a):
    for ki, lab in ((1, "k=1  PRIMARIO"), (0, "k=0")):
        rows, n = build_table(a, a.region, ki)
        pts = [r["pt"] for r in rows]
        dD = np.array([r["dD"] for r in rows], float)
        sem = np.array([r["sem"] for r in rows], float)
        w = 1.0 / sem ** 2
        dV = np.array([r["dV"] for r in rows], float)

        print("=" * 78)
        print(f"residuo di Delta D — {a.region}, {lab},  {len(pts)} punti, "
              f"n = {n} mock")
        print("=" * 78)
        print("  ESPLORATIVA: significativita' NON corrette per look-elsewhere.")
        print("  Nulla di quanto esce qui entra nel budget senza una conferma")
        print("  su un dato che non e' stato usato per formularlo.\n")

        # --- passo 1: canale voxel, pendenza MISURATA SU D -------------------
        sl, se = wls(dV, dD, w)
        res = dD - sl * dV
        print(f"  canale voxel: dD/dV = {sl:+.5f} +- {se:.5f} ({sl/se:+.1f} sd)")
        print(f"    rms del residuo: {np.sqrt(np.mean(dD**2)):.1f} -> "
              f"{np.sqrt(np.mean(res**2)):.1f} generatori")
        print(f"    {'pt':>4} {'dD':>8} {'dV':>7} {'atteso':>8} {'residuo':>8} "
              f"{'res/sem':>8}")
        for r, y, v, e in zip(rows, dD, dV, res):
            print(f"    {r['pt']:>4} {y:+8.1f} {v:+7.0f} {sl*v:+8.1f} {e:+8.1f} "
                  f"{e/r['sem']:+8.2f}")

        # --- passo 2: il residuo contro ogni candidato -----------------------
        cands = [k for k in rows[0]
                 if k not in ("pt", "dD", "sem", "dV")
                 and not np.isnan(rows[0][k])]
        print(f"\n  residuo contro {len(cands)} candidati, uno alla volta:")
        print(f"    {'regressore':>12} {'pendenza':>14} {'sd':>7} {'r':>7} "
              f"{'rms dopo':>9}")
        out = []
        for c in cands:
            x = np.array([r.get(c, np.nan) for r in rows], float)
            if np.any(~np.isfinite(x)) or np.allclose(x, 0):
                continue
            s2, e2 = wls(x, res, w)
            if not np.isfinite(s2):
                continue
            rr = res - s2 * x
            rho = float(np.corrcoef(x, res)[0, 1])
            out.append((abs(s2 / e2), c, s2, e2, rho,
                        float(np.sqrt(np.mean(rr ** 2)))))
        for z, c, s2, e2, rho, rms in sorted(out, reverse=True):
            print(f"    {c:>12} {s2:+14.5g} {z:7.1f} {rho:+7.3f} {rms:9.1f}")

        if out:
            z, c, s2, e2, rho, rms = sorted(out, reverse=True)[0]
            print(f"\n  migliore: {c} a {z:.1f} sd, rms {np.sqrt(np.mean(res**2)):.1f}"
                  f" -> {rms:.1f}")
            if z < 3:
                print("  Sotto 3 sd su una ricerca fra piu' candidati: NON e' un"
                      " risultato.")
            else:
                print("  PREDIZIONE DA VERIFICARE ALTROVE, non da adottare: se il")
                print("  canale e' quello, la stessa pendenza deve valere sull'altro")
                print("  emisfero e sul blocco A, dove il segnale fisico e' nullo.")
        print()
    return 0


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("diag")
    q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    q.add_argument("--data", default="results/paper2/fase3.jsonl")
    q.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
    q.add_argument("--analisi", default="results/paper2/fase3_analisi.jsonl")
    q.add_argument("--tiling", default=None)
    q.add_argument("--with-block-a", action="store_true",
                   help="include A1 e A3: la' il segnale fisico e' NULLO per la "
                        "Prop. 2, quindi il loro Delta D e' tutto artefatto")
    a = p.parse_args()
    if a.tiling is None:
        a.tiling = f"results/paper2/item15a_g13_{a.region}.jsonl"
    return cmd_diag(a)


if __name__ == "__main__":
    sys.exit(main())
