#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_tab12_restrizione.py

Da quale restrizione della maschera vengono i numeri della Tabella 12 del
Paper 1?

LA DOMANDA
----------
Paper 1, Tabella 12, «Five independent diagnostics of the same small-scale
property (NGC)», riga 1: «in-mask excess kurtosis of nu — mocks +3.90, DESI
+0.20». La passata a un punto su 2000 realizzazioni misura, a footprint pieno,
+2.818 e -0.438: il valore di DESI cambia perfino di SEGNO. A field_r > P10
misura +4.512 e +0.590. Nessuna delle due riproduce la coppia pubblicata, a
nessun n provato (2000, 200, 100, 50, 60).

step6 pero' calcola QUATTRO restrizioni — footprint pieno, erosione 2 voxel,
field_r > P5, field_r > P10 — e la passata ne ha registrate due. Le altre due
stanno solo in results/paper1/paper1_step6_<REG>.json.

Questo strumento le legge tutte e dice quale, se una, riproduce la coppia.

LA TOLLERANZA E' LA QUOTAZIONE
------------------------------
+3.90 e +0.20 hanno due decimali: ammettono mezza unita' dell'ultima cifra,
0.005. Regola dichiarata prima di leggere, la stessa dei record 54 e 56.

TRE ESITI, DA LEGGERE DIVERSAMENTE
----------------------------------
  una restrizione riproduce  -> la correzione al manoscritto e' di ETICHETTA:
                                la riga va marcata con la sua restrizione
                                invece che «in-mask».
  nessuna riproduce          -> il numero non viene da step6, e va cercato
                                nello script che l'ha prodotto prima di
                                sostituirlo con qualunque altro.
  piu' di una riproduce      -> la coppia non identifica una restrizione, e
                                l'etichetta da sola non basterebbe comunque.

NON CALCOLA NULLA: legge un JSON gia' scritto.

USO
    python src\\paper2_tab12_restrizione.py selftest
    python src\\paper2_tab12_restrizione.py leggi --region NGC
    python src\\paper2_tab12_restrizione.py leggi --region SGC
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Tabella 12 del Paper 1, riga 1. (valore, decimali quotati)
TAB12_KURT_MOCK = (3.90, 2)
TAB12_KURT_DESI = (0.20, 2)
# Riga 2, per riferimento: r_f non e' ricostruibile da step6, che scarta p01.
TAB12_RF = "mocks 5.6, DESI 3.22 -- non verificabile qui: step6 non espone p01"

ROOT_DEFAULT = r"D:\projects\cauchy"


def ammesso(decimali):
    return 0.5 * 10.0 ** (-decimali)


def riproduce(valore, quotato_e_decimali):
    q, d = quotato_e_decimali
    if valore is None:
        return False, float("inf")
    scarto = abs(float(valore) - q)
    return scarto <= ammesso(d) * (1 + 1e-9), scarto / ammesso(d)


def estrai(rep):
    """restrizione -> {campo: {chiave: {desi, mock_mean, mock_std, z, rank}}}"""
    op = rep.get("onepoint") or {}
    return op.get("restrictions") or {}, op.get("n_fields")


def leggi(root, region):
    p = Path(root) / "results" / "paper1" / ("paper1_step6_%s.json" % region)
    if not p.is_file():
        raise SystemExit("RIFIUTO: file inesistente: %s" % p)
    rep = json.loads(p.read_text(encoding="utf-8"))
    restr, n_fields = estrai(rep)
    if not restr:
        raise SystemExit("RIFIUTO: %s non contiene il blocco onepoint" % p.name)

    print("=" * 88)
    print("TABELLA 12, RIGA 1: da quale restrizione?  |  %s  |  n_fields = %s"
          % (region, n_fields))
    print("quotato: mock %+.2f, DESI %+.2f   ammesso %.3f (mezza unita' di due decimali)"
          % (TAB12_KURT_MOCK[0], TAB12_KURT_DESI[0], ammesso(2)))
    print("=" * 88)
    print("%-24s %10s %10s %10s %8s %10s" %
          ("restrizione", "voxel", "kurt mock", "kurt DESI", "z", "verdetto"))
    print("-" * 88)

    vincitrici = []
    righe = {}
    for label in restr:
        r = restr[label]
        nu = (r.get("nu") or {}).get("kurt_excess") or {}
        mm, dd, zz = nu.get("mock_mean"), nu.get("desi"), nu.get("z")
        okm, dm = riproduce(mm, TAB12_KURT_MOCK)
        okd, dd_ = riproduce(dd, TAB12_KURT_DESI)
        verdetto = "SI" if (okm and okd) else ("mock" if okm else ("DESI" if okd else "-"))
        if okm and okd:
            vincitrici.append(label)
        righe[label] = {"n_voxel": r.get("n_voxels"),
                        "frac_of_full": r.get("frac_of_full"),
                        "kurt_mock_mean": mm, "kurt_desi": dd, "z": zz,
                        "mezze_unita_mock": dm, "mezze_unita_desi": dd_,
                        "riproduce_riga1": bool(okm and okd)}
        print("%-24s %10s %10s %10s %8s %10s" % (
            label[:24],
            "%d" % r["n_voxels"] if r.get("n_voxels") is not None else "?",
            "%+.4f" % mm if mm is not None else "?",
            "%+.4f" % dd if dd is not None else "?",
            "%+.2f" % zz if zz is not None else "?",
            verdetto))

    print()
    if len(vincitrici) == 1:
        print("  ESITO: la riga 1 viene da '%s'." % vincitrici[0])
        print("  La correzione al manoscritto e' di ETICHETTA: la riga va marcata")
        print("  con quella restrizione invece che «in-mask».")
    elif not vincitrici:
        print("  ESITO: NESSUNA delle restrizioni di step6 riproduce la coppia.")
        print("  Il +3.90/+0.20 non viene da qui. Va cercato nello script che l'ha")
        print("  prodotto PRIMA di sostituirlo con qualunque altro valore: proporre")
        print("  un numero al posto di uno di provenienza ignota sarebbe peggio")
        print("  dell'ambiguita' che si vuole togliere.")
        vicine = sorted(righe, key=lambda k: righe[k]["mezze_unita_mock"])[:2]
        for v in vicine:
            print("    piu' vicina: %-22s mock a %.1f mezze unita', DESI a %.1f"
                  % (v, righe[v]["mezze_unita_mock"], righe[v]["mezze_unita_desi"]))
    else:
        print("  ESITO: %d restrizioni riproducono la coppia: %s."
              % (len(vincitrici), ", ".join(vincitrici)))
        print("  L'etichetta da sola non identificherebbe comunque la misura.")

    print("\n  riga 2 della tabella: %s" % TAB12_RF)
    return righe, vincitrici


def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_tab12_restrizione")

    chk("i valori quotati sono quelli della Tabella 12",
        TAB12_KURT_MOCK == (3.90, 2) and TAB12_KURT_DESI == (0.20, 2))
    chk("ammesso a due decimali e' 0.005", ammesso(2) == 0.005)

    chk("3.9049 riproduce +3.90", riproduce(3.9049, TAB12_KURT_MOCK)[0])
    chk("3.9051 non riproduce +3.90", not riproduce(3.9051, TAB12_KURT_MOCK)[0])
    chk("il limite esatto riproduce", riproduce(3.905, TAB12_KURT_MOCK)[0])
    chk("None non riproduce e da' distanza infinita",
        riproduce(None, TAB12_KURT_MOCK) == (False, float("inf")))

    # le misure vere della passata NON devono riprodurre la coppia
    chk("footprint pieno (misurato +2.8175) non riproduce",
        not riproduce(2.8175, TAB12_KURT_MOCK)[0])
    chk("P10 (misurato +4.5116) non riproduce",
        not riproduce(4.5116, TAB12_KURT_MOCK)[0])
    chk("DESI a footprint pieno (-0.4382) e' perfino di segno opposto",
        not riproduce(-0.4382, TAB12_KURT_DESI)[0] and -0.4382 < 0 < TAB12_KURT_DESI[0])

    # estrazione
    finto = {"onepoint": {"n_fields": 200, "restrictions": {
        "footprint pieno": {"n_voxels": 307805, "frac_of_full": 1.0,
                            "nu": {"kurt_excess": {"desi": -0.4382,
                                                   "mock_mean": 2.8175,
                                                   "mock_std": 0.4581, "z": -7.1}}},
        "field_r > P10": {"n_voxels": 277024, "frac_of_full": 0.9,
                          "nu": {"kurt_excess": {"desi": 0.5896,
                                                 "mock_mean": 4.5116,
                                                 "mock_std": 0.7382, "z": -5.3}}}}}}
    restr, n = estrai(finto)
    chk("estrai trova le restrizioni e n_fields", len(restr) == 2 and n == 200)
    chk("estrai su un report senza onepoint da' vuoto", estrai({}) == ({}, None))

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "results" / "paper1"
        d.mkdir(parents=True)
        (d / "paper1_step6_NGC.json").write_text(json.dumps(finto), encoding="utf-8")
        righe, vinc = leggi(td, "NGC")
        chk("sulle due restrizioni vere nessuna riproduce la riga 1", vinc == [], vinc)
        chk("le distanze sono calcolate per entrambe",
            all("mezze_unita_mock" in v for v in righe.values()))
        try:
            leggi(td, "SGC")
            chk("regione assente: rifiuto", False, "non ha rifiutato")
        except SystemExit as e:
            chk("regione assente: rifiuto", "inesistente" in str(e))

        finto2 = json.loads(json.dumps(finto))
        finto2["onepoint"]["restrictions"]["erosione 2 voxel"] = {
            "n_voxels": 250000, "frac_of_full": 0.81,
            "nu": {"kurt_excess": {"desi": 0.2001, "mock_mean": 3.8998,
                                   "mock_std": 0.6, "z": -6.0}}}
        (d / "paper1_step6_NGC.json").write_text(json.dumps(finto2), encoding="utf-8")
        righe2, vinc2 = leggi(td, "NGC")
        chk("una restrizione che riproduce viene trovata",
            vinc2 == ["erosione 2 voxel"], vinc2)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("leggi")
    l.add_argument("--root", default=ROOT_DEFAULT)
    l.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "leggi":
        leggi(a.root, a.region)
        return 0
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
