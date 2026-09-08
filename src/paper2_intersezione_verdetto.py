#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_intersezione_verdetto.py — emette il verdetto del §3.2 (record 24).

SOLA LETTURA. Non scrive nulla se non gli si passa --out.

COSA FA
  Legge i due registri della passata 1 e della passata 2, calcola R = rms dei
  due residui del blocco A per emisfero e livello, il rapporto rho, la sua
  mediana, e applica la regola del record 24:

    mediana(rho) <= 1/3   IDENTIFIED   il residuo E' il canale voxel di bordo
    mediana(rho) >= 2/3   REFUTED      non lo e'
    in mezzo              PARTIAL      si riporta col numero, NON si arrotonda
                                       e il budget NON si riderivà

  I tre casi sono esaustivi e le soglie non si muovono.

DUE DENOMINATORI, ED E' UNA SCELTA CHE VA DICHIARATA
  Il record 24 definisce R "calcolata esattamente come il pavimento (f)", che
  include la sottrazione del canale voxel. Sull'intersezione quella sottrazione
  e' nulla per costruzione, quindi in passata 2 le due definizioni coincidono;
  in passata 1 NO, e li' il denominatore giusto e' il pavimento DEPOSITATO
  (10.1, 17.7, 20.2, 32.5), non l'escursione grezza.
  Si riportano ENTRAMBI. Se dessero verdetti diversi il codice lo dice e si
  ferma senza sceglierne uno: sarebbe una decisione da registrare, non da
  prendere qui.

IL CANCELLO
  D6 si riverifica sui record: n_valid_voxels identico ai dodici punti della
  passata 2. E' gia' stato controllato durante il run, ma un analizzatore che
  non ricontrolla il proprio input si fida di un'altra esecuzione.

UN CONTROLLO IN PIU', NON CHIESTO DAL RECORD
  Il segno dei residui del blocco A. Nella misura depositata erano entrambi
  NEGATIVI in NGC (-10.0, -10.3), il che il documento chiama "offset costante".
  Se sull'intersezione cambiano segno, l'offset non e' quello che si credeva, e
  va guardato prima di scriverne. Si riporta e basta: nessuna soglia, perche'
  nessuna era dichiarata.

Uso:
  python src\\paper2_intersezione_verdetto.py
  python src\\paper2_intersezione_verdetto.py --out results\\paper2\\fase3_intersezione_verdetto.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

# Pavimento (f) DEPOSITATO, dalla Fase 3. E' il denominatore alternativo.
PAVIMENTO = {("NGC", 1): 10.1, ("NGC", 0): 17.7,
             ("SGC", 1): 20.2, ("SGC", 0): 32.5}
# Non attribuito, per dire quanto pesa il pavimento.
NON_ATTRIBUITO = {("NGC", 1): 41.2, ("NGC", 0): 59.8,
                  ("SGC", 1): 53.3, ("SGC", 0): 41.5}
IDENT, REFUT = 1.0 / 3.0, 2.0 / 3.0


def carica(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"[FATAL] manca {path}")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def blocco_a(recs, region, ki):
    """(A1, A3) in gauge regauged, e il fiduciale.

    Sul blocco A il fiduciale e' il gauge `derived`: A1 e A3 in `derived` sono
    dilatazioni pure, che per la Proposizione 2 riproducono il fiduciale. Se non
    coincidono fra loro, la Proposizione 2 non vale su questa geometria e il
    residuo non e' definito: si dichiara e ci si ferma."""
    key = "N_H1" if ki == 1 else "N_H1_k0"
    reg = {r["point"]: r for r in recs
           if r.get("region") == region and r.get("gauge") == "regauged"}
    der = {r["point"]: r for r in recs
           if r.get("region") == region and r.get("gauge") == "derived"}
    if not all(p in reg for p in ("A1", "A3")):
        sys.exit(f"[FATAL] {region}: A1 o A3 mancano in gauge regauged.")
    if not all(p in der for p in ("A1", "A3")):
        sys.exit(f"[FATAL] {region}: A1 o A3 mancano in gauge derived: il "
                 f"fiduciale del blocco A non e' determinabile.")
    f1, f3 = der["A1"][key], der["A3"][key]
    if f1 != f3:
        sys.exit(f"[FATAL] {region} k={ki}: le due dilatazioni pure danno "
                 f"{f1} e {f3}. La Proposizione 2 non vale qui e il residuo "
                 f"del blocco A non e' definito.")
    return (reg["A1"][key] - f1, reg["A3"][key] - f1), f1


def rms(v):
    return math.sqrt(sum(x * x for x in v) / len(v))


def gate_d6(recs, region):
    n = {r["n_valid_voxels"] for r in recs if r.get("region") == region}
    if len(n) != 1:
        sys.exit(f"[FATAL] D6 sui record: {region} ha n_valid_voxels {sorted(n)}. "
                 f"Con maschera fissa e' costante per costruzione. Record 24.")
    return n.pop()


def main():
    p = argparse.ArgumentParser(description="§3.2, verdetto (record 24)")
    p.add_argument("--pass1", default="results/paper2/fase3_maskpass1.jsonl")
    p.add_argument("--pass2", default="results/paper2/fase3_intersezione.jsonl")
    p.add_argument("--out", default=None)
    a = p.parse_args()

    r1, r2 = carica(a.pass1), carica(a.pass2)
    print("=" * 78)
    print("§3.2 — maschera-intersezione, verdetto secondo il record 24")
    print("=" * 78)

    out = {"schema": "paper2_intersezione_verdetto_v1", "cases": {}}
    for reg in ("NGC", "SGC"):
        v = gate_d6(r2, reg)
        print(f"  [D6] {reg}: n_valid_voxels = {v}, identico ai punti della "
              f"passata 2.")
        out.setdefault("d6", {})[reg] = v

    print(f"\n  {'caso':<9} {'A1,A3 int.':>12} {'R_int':>7} "
          f"{'A1,A3 dep.':>12} {'R_dep':>7} {'pav.':>6} "
          f"{'rho/R_dep':>10} {'rho/pav':>8}")
    rho_dep, rho_pav = [], []
    segni = {}
    for reg in ("NGC", "SGC"):
        for ki in (1, 0):
            d2, fid2 = blocco_a(r2, reg, ki)
            d1, fid1 = blocco_a(r1, reg, ki)
            R2, R1 = rms(d2), rms(d1)
            pav = PAVIMENTO[(reg, ki)]
            rho_dep.append(R2 / R1)
            rho_pav.append(R2 / pav)
            segni[f"{reg}_k{ki}"] = {"intersezione": list(d2), "depositata": list(d1)}
            print(f"  {reg}_k{ki:<6} {str(d2):>12} {R2:>7.2f} "
                  f"{str(d1):>12} {R1:>7.2f} {pav:>6.1f} "
                  f"{R2/R1:>10.3f} {R2/pav:>8.3f}")
            out["cases"][f"{reg}_k{ki}"] = {
                "residui_intersezione": list(d2), "R_intersezione": R2,
                "residui_depositata": list(d1), "R_depositata": R1,
                "pavimento_depositato": pav, "fid_intersezione": fid2,
                "rho_vs_R_dep": R2 / R1, "rho_vs_pavimento": R2 / pav}

    def verdetto(m):
        return "IDENTIFIED" if m <= IDENT else ("REFUTED" if m >= REFUT else "PARTIAL")

    m1, m2 = statistics.median(rho_dep), statistics.median(rho_pav)
    v1, v2 = verdetto(m1), verdetto(m2)
    print(f"\n  mediana rho contro R depositata = {m1:.4f}  ->  {v1}")
    print(f"  mediana rho contro pavimento (f) = {m2:.4f}  ->  {v2}")
    out.update(median_rho_vs_R_dep=m1, median_rho_vs_pavimento=m2,
               verdict_vs_R_dep=v1, verdict_vs_pavimento=v2,
               thresholds={"identified": IDENT, "refuted": REFUT})

    if v1 != v2:
        out["verdict"] = None
        print("\n  [FATAL] i due denominatori danno verdetti DIVERSI. Sceglierne")
        print("  uno adesso sarebbe prendere la lettura che conviene. Va")
        print("  registrata una decisione, non presa qui.")
        if a.out:
            Path(a.out).open("a", encoding="utf-8").write(
                json.dumps(out, sort_keys=True) + "\n")
        return 3

    out["verdict"] = v1
    print(f"\n  VERDETTO: {v1}")
    if v1 == "PARTIAL":
        print("""
  Il canale voxel di bordo CONTRIBUISCE ma non domina: il residuo del blocco A
  si dimezza sull'intersezione, non crolla. L'ipotesi del §3.2 del referee e'
  confermata a meta'.
  Per la regola del record 24 il budget NON si riderivà: il sistematico resta
  41.9-60.3 e la classificazione E2 resta un'affermazione a ~1 sigma. Un
  parziale non si arrotonda al verdetto favorevole.""")
    elif v1 == "IDENTIFIED":
        print("""
  Il residuo non attribuito E' il canale voxel di bordo. Il pavimento (f) e il
  non attribuito si ridervano sull'intersezione, e con essi il sistematico.""")
    else:
        print("""
  Il residuo NON e' il canale voxel di bordo. L'ipotesi del referee raggiunge i
  dieci regressori gia' falliti, e il residuo resta non identificato.""")

    print("\n  --- segno dei residui del blocco A, non richiesto dal record ---")
    for nm, d in segni.items():
        s2 = "entrambi +" if all(x > 0 for x in d["intersezione"]) else (
            "entrambi -" if all(x < 0 for x in d["intersezione"]) else "misti")
        s1 = "entrambi +" if all(x > 0 for x in d["depositata"]) else (
            "entrambi -" if all(x < 0 for x in d["depositata"]) else "misti")
        flag = "  <- CAMBIA" if s1 != s2 and "misti" not in (s1, s2) else ""
        print(f"  {nm:<9} depositata {s1:<11} intersezione {s2:<11}{flag}")
    print("  Nessuna soglia era dichiarata su questo: si riporta e basta.")
    out["segni"] = segni

    if a.out:
        Path(a.out).open("a", encoding="utf-8").write(
            json.dumps(out, sort_keys=True) + "\n")
        print(f"\n  [scritto] {a.out}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
