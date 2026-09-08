#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_giunzione_ladder.py — assembla la scala di erosione PER REALIZZAZIONE
giungendo registri diversi, e ne misura sigma(P).

Serve perche' k=0, k=1 e k=2 non stanno nello stesso file: per_mock_*_erosion_restrict.jsonl
porta er0, er2, er3 e NON er1; il k=1 per realizzazione sta solo in fase3_mock.jsonl.

Tre regole, tutte bloccanti:
  UNIONE      i registri di fase 3 si leggono per unione, mai last-wins (record 49). Se due
              record danno valori DIVERSI per la stessa realizzazione e la stessa chiave, e'
              un conflitto e lo strumento si ferma.
  CONTROLLO   la giunzione e' valida solo se i due registri parlano della stessa cosa: per le
              realizzazioni in comune, la chiave di controllo deve coincidere ESATTAMENTE con
              il k=0 dell'altro file. Un solo scarto ferma tutto.
  BERSAGLIO   il deficit ricalcolato a k=0 deve riprodurre quello congelato.

P e sigma(P) NON sono ricalcolati qui: si importano da paper2_prominenza_v1, che e' l'unica
implementazione della grandezza.

Uso:
    python paper2_giunzione_ladder.py selftest
    python paper2_giunzione_ladder.py ispeziona --file results\\paper2\\fase3_mock.jsonl
    python paper2_giunzione_ladder.py giungi ^
        --k0-file results\\paper1\\per_mock_NGC_R5.jsonl --k0-chiave base.N_H1 ^
        --k1-file results\\paper2\\fase3_mock.jsonl --k1-chiave points.FID.N_H1_k1 ^
        --k2-file results\\paper1\\per_mock_NGC_erosion_restrict.jsonl --k2-chiave cells.R5_er2.N_H1 ^
        --controllo-file results\\paper2\\fase3_mock.jsonl --controllo-chiave points.FID.N_H1_k0 ^
        --desi-k0 28256 --desi-k1 ... --desi-k2 ... ^
        --bersaglio-k0-pp 20.26 --etichetta NGC --out logs\\giunzione.jsonl
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from paper2_prominenza_v1 import prominenza  # unica implementazione della grandezza
except ImportError:
    sys.stderr.write("RIFIUTO: paper2_prominenza_v1.py non e' accanto a questo script.\n")
    raise

CANDIDATI_INDICE = ("idx", "index", "i", "mock", "mock_id", "mock_index",
                    "realisation", "realization", "seed", "n_mock", "mock_idx")


class Rifiuto(Exception):
    pass


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(flatten(v, key))
            elif not isinstance(v, list):
                out[key] = v
    return out


def righe(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except Exception:
                raise Rifiuto(f"{os.path.basename(path)} riga {i}: JSON malformato")


def trova_indice(path, dichiarata=None):
    piatti = [flatten(r) for _, r in righe(path)]
    if not piatti:
        raise Rifiuto(f"{os.path.basename(path)}: vuoto")
    if dichiarata:
        mancanti = sum(1 for p in piatti if dichiarata not in p)
        if mancanti:
            raise Rifiuto(f"{os.path.basename(path)}: la chiave indice '{dichiarata}' manca in "
                          f"{mancanti} record su {len(piatti)}")
        return dichiarata
    cand = [c for c in CANDIDATI_INDICE
            if all(c in p and isinstance(p[c], int) and not isinstance(p[c], bool) for p in piatti)]
    if len(cand) == 0:
        raise Rifiuto(f"{os.path.basename(path)}: nessuna chiave indice riconosciuta fra "
                      f"{CANDIDATI_INDICE}; dichiarala con --*-indice")
    if len(cand) > 1:
        raise Rifiuto(f"{os.path.basename(path)}: chiave indice ambigua fra {cand}; dichiarala")
    return cand[0]


def leggi_unione(path, chiavi, chiave_indice):
    """Unione, mai last-wins. Valori diversi per la stessa (realizzazione, chiave) = conflitto."""
    per_idx = {}
    conflitti = []
    n_righe = 0
    for n, rec in righe(path):
        piatto = flatten(rec)
        n_righe += 1
        idx = piatto[chiave_indice]
        slot = per_idx.setdefault(idx, {})
        for k in chiavi:
            v = piatto.get(k)
            if v is None:
                continue
            v = float(v)
            if k in slot and slot[k] != v:
                conflitti.append({"riga": n, "idx": idx, "chiave": k,
                                  "avuto": slot[k], "nuovo": v})
            else:
                slot[k] = v
    if conflitti:
        c = conflitti[0]
        raise Rifiuto(f"{os.path.basename(path)}: {len(conflitti)} conflitti nell'unione; "
                      f"primo alla riga {c['riga']}, idx {c['idx']}, chiave {c['chiave']}: "
                      f"{c['avuto']} contro {c['nuovo']}")
    return per_idx, n_righe


def cmd_ispeziona(args):
    piatti = [flatten(r) for _, r in righe(args.file)]
    print(f"file    : {os.path.abspath(args.file)}")
    print(f"record  : {len(piatti)}")
    cand = [c for c in CANDIDATI_INDICE
            if all(c in p and isinstance(p[c], int) and not isinstance(p[c], bool) for p in piatti)]
    print(f"indice  : candidati {cand if cand else 'NESSUNO'}")
    for c in cand:
        valori = [p[c] for p in piatti]
        print(f"          '{c}': {len(set(valori))} distinti su {len(valori)}, "
              f"min {min(valori)} max {max(valori)}")
    chiavi = {}
    for p in piatti:
        for k in p:
            chiavi[k] = chiavi.get(k, 0) + 1
    print("chiavi  : (conteggio su record)")
    for k in sorted(chiavi):
        print(f"          {chiavi[k]:6d}  {k}")
    return 0


def cmd_giungi(args):
    try:
        sorgenti = {
            "k0": (args.k0_file, args.k0_chiave, args.k0_indice),
            "k1": (args.k1_file, args.k1_chiave, args.k1_indice),
            "k2": (args.k2_file, args.k2_chiave, args.k2_indice),
        }
        tabelle = {}
        for nome, (path, chiave, ind) in sorgenti.items():
            if not os.path.isfile(path):
                raise Rifiuto(f"file inesistente: {path}")
            ki = trova_indice(path, ind)
            chiavi = [chiave]
            if nome == "k1" and args.controllo_file == path:
                chiavi.append(args.controllo_chiave)
            per_idx, n_righe = leggi_unione(path, chiavi, ki)
            tabelle[nome] = {"per_idx": per_idx, "chiave": chiave, "indice": ki,
                             "n_righe": n_righe, "path": path}
            print(f"{nome}: {os.path.basename(path)}  righe {n_righe}  "
                  f"realizzazioni {len(per_idx)}  indice '{ki}'")

        # controllo di validita' della giunzione
        n_ctrl = n_scarti = 0
        primo_scarto = None
        if args.controllo_file:
            if args.controllo_file == args.k1_file:
                ctrl = {i: v.get(args.controllo_chiave)
                        for i, v in tabelle["k1"]["per_idx"].items()}
            else:
                ki = trova_indice(args.controllo_file, args.controllo_indice)
                per_idx, _ = leggi_unione(args.controllo_file, [args.controllo_chiave], ki)
                ctrl = {i: v.get(args.controllo_chiave) for i, v in per_idx.items()}
            for i, v in ctrl.items():
                base = tabelle["k0"]["per_idx"].get(i, {}).get(args.k0_chiave)
                if v is None or base is None:
                    continue
                n_ctrl += 1
                if v != base:
                    n_scarti += 1
                    if primo_scarto is None:
                        primo_scarto = (i, base, v)
            if n_ctrl == 0:
                raise Rifiuto("il controllo non ha nessuna realizzazione in comune con k0: "
                              "la giunzione non e' verificabile")
            if n_scarti:
                raise Rifiuto(f"controllo fallito: {n_scarti} scarti su {n_ctrl} realizzazioni; "
                              f"primo idx {primo_scarto[0]}: k0 {primo_scarto[1]} contro "
                              f"controllo {primo_scarto[2]}. I due registri non sono lo stesso "
                              f"trattamento e P non si assembla da qui.")
            print(f"controllo: {n_ctrl} realizzazioni confrontate, 0 scarti")

        comuni = sorted(set(tabelle["k0"]["per_idx"]) & set(tabelle["k1"]["per_idx"])
                        & set(tabelle["k2"]["per_idx"]))
        comuni = [i for i in comuni
                  if all(tabelle[n]["per_idx"][i].get(tabelle[n]["chiave"]) is not None
                         for n in ("k0", "k1", "k2"))]
        if len(comuni) < 3:
            raise Rifiuto(f"solo {len(comuni)} realizzazioni hanno tutti e tre i livelli")
        print(f"giunzione: {len(comuni)} realizzazioni con k0, k1 e k2")

        N0 = [tabelle["k0"]["per_idx"][i][args.k0_chiave] for i in comuni]
        N1 = [tabelle["k1"]["per_idx"][i][args.k1_chiave] for i in comuni]
        N2 = [tabelle["k2"]["per_idx"][i][args.k2_chiave] for i in comuni]

        r = prominenza(N0, N1, N2, args.desi_k0, args.desi_k1, args.desi_k2)

        if args.bersaglio_k0_pp is not None:
            scarto = abs(r["D_k0_pp"] - args.bersaglio_k0_pp)
            if scarto > args.bersaglio_tolleranza_pp:
                raise Rifiuto(f"bersaglio k=0: ricalcolato {r['D_k0_pp']:.4f} pp contro "
                              f"{args.bersaglio_k0_pp} pp, scarto {scarto:.4f} > "
                              f"{args.bersaglio_tolleranza_pp}")
            print(f"bersaglio: D(k=0) {r['D_k0_pp']:.4f} pp contro {args.bersaglio_k0_pp} pp  OK")
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    print()
    print(f"{args.etichetta}  n = {r['n']}")
    print(f"  deficit  k0 {r['D_k0_pp']:7.3f} pp   k1 {r['D_k1_pp']:7.3f} pp   k2 {r['D_k2_pp']:7.3f} pp")
    print(f"  P        {r['P_pp']:+.4f} pp   (curvatura {r['P_curvatura_pp']:+.5f}, "
          f"corretta {r['P_corretta_pp']:+.4f})")
    print(f"  sigma    appaiata {r['sem_appaiata_pp']:.4f}   jackknife {r['sem_jackknife_pp']:.4f}"
          f"   non appaiata {r['sem_non_appaiata_pp']:.4f}  (x{r['guadagno_appaiamento']:.1f})")
    print(f"  correlaz k0-k1 {r['r_k0_k1']:.4f}   k1-k2 {r['r_k1_k2']:.4f}")
    print(f"  soglie   successo < {r['soglia_successo_pp']:.4f} pp   "
          f"fallimento > {r['soglia_fallimento_pp']:.4f} pp")
    print(f"  le due zone distano {r['separazione_zone_sigma']:.1f} sigma", end="  ")
    print("[REGOLA VALIDA]" if r["separazione_zone_sigma"] >= 3.0 else "[REGOLA NON DECIDE]")

    if args.out:
        r = dict(r)
        r.update({"etichetta": args.etichetta, "n_comuni": len(comuni),
                  "controllo_n": n_ctrl, "controllo_scarti": n_scarti,
                  "sorgenti": {n: {"file": os.path.abspath(t["path"]), "chiave": t["chiave"],
                                   "indice": t["indice"], "righe": t["n_righe"]}
                               for n, t in tabelle.items()},
                  "desi": [args.desi_k0, args.desi_k1, args.desi_k2]})
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  registro: {os.path.abspath(args.out)}")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="giunzione_")

    def scrivi(nome, records):
        p = os.path.join(base, nome)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
        return p

    basi = [35000 + 137 * i - 3 * i * i for i in range(30)]
    # k0 in un file, k2 in un altro, k1 spezzato su DUE record per realizzazione
    f_k0 = scrivi("per_mock.jsonl", [{"idx": i, "base": {"N_H1": b}} for i, b in enumerate(basi)])
    f_k2 = scrivi("erosion.jsonl", [{"idx": i, "cells": {"R5_er2": {"N_H1": b + 200}}}
                                    for i, b in enumerate(basi)])
    fase3 = []
    for i, b in enumerate(basi):
        fase3.append({"idx": i, "points": {"FID": {"N_H1_k0": b}}})          # solo k0
        fase3.append({"idx": i, "points": {"FID": {"N_H1_k1": b + 900}}})    # solo k1
    f_k1 = scrivi("fase3_mock.jsonl", fase3)

    ok("1 indice trovato da solo", trova_indice(f_k0) == "idx")

    per_idx, n_righe = leggi_unione(f_k1, ["points.FID.N_H1_k0", "points.FID.N_H1_k1"], "idx")
    ok("2 unione: 60 righe diventano 30 realizzazioni", n_righe == 60 and len(per_idx) == 30)
    ok("3 unione: entrambe le chiavi sopravvivono",
       all(len(v) == 2 for v in per_idx.values()))
    ok("4 last-wins avrebbe perso k0", per_idx[0]["points.FID.N_H1_k0"] == basi[0]
       and per_idx[0]["points.FID.N_H1_k1"] == basi[0] + 900)

    class A:
        pass

    def a_giungi(**kw):
        a = A()
        a.k0_file, a.k0_chiave, a.k0_indice = f_k0, "base.N_H1", None
        a.k1_file, a.k1_chiave, a.k1_indice = f_k1, "points.FID.N_H1_k1", None
        a.k2_file, a.k2_chiave, a.k2_indice = f_k2, "cells.R5_er2.N_H1", None
        a.controllo_file, a.controllo_chiave, a.controllo_indice = f_k1, "points.FID.N_H1_k0", None
        a.desi_k0 = a.desi_k1 = a.desi_k2 = 28000.0
        a.bersaglio_k0_pp = None; a.bersaglio_tolleranza_pp = 0.05
        a.etichetta = "TEST"; a.out = None
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    ok("5 giunzione completa: esito 0", cmd_giungi(a_giungi()) == 0)

    # il controllo deve mordere
    fase3_rotto = list(fase3)
    fase3_rotto[0] = {"idx": 0, "points": {"FID": {"N_H1_k0": basi[0] + 7}}}
    f_rotto = scrivi("fase3_rotto.jsonl", fase3_rotto)
    ok("6 controllo fallito: rifiuto",
       cmd_giungi(a_giungi(k1_file=f_rotto, controllo_file=f_rotto)) == 2)

    # conflitto nell'unione
    f_conf = scrivi("conflitto.jsonl", fase3 + [{"idx": 3, "points": {"FID": {"N_H1_k1": 1.0}}}])
    try:
        leggi_unione(f_conf, ["points.FID.N_H1_k1"], "idx")
        ok("7 conflitto nell'unione: rifiuto", False)
    except Rifiuto as e:
        ok("7 conflitto nell'unione: rifiuto", "conflitti" in str(e))

    # intersezione parziale
    f_corto = scrivi("corto.jsonl", [{"idx": i, "cells": {"R5_er2": {"N_H1": basi[i] + 200}}}
                                     for i in range(5)])
    a = a_giungi(k2_file=f_corto, out=os.path.join(base, "logs", "g.jsonl"))
    ok("8 intersezione parziale accettata", cmd_giungi(a) == 0)
    with open(a.out, encoding="utf-8") as fh:
        r_out = json.loads(fh.readline())
    ok("9 il registro riporta n_comuni = 5", r_out["n_comuni"] == 5)
    ok("10 il registro riporta 0 scarti di controllo", r_out["controllo_scarti"] == 0)

    # bersaglio
    ok("11 bersaglio sbagliato: rifiuto", cmd_giungi(a_giungi(bersaglio_k0_pp=99.0)) == 2)
    per_idx0, _ = leggi_unione(f_k0, ["base.N_H1"], "idx")
    N0 = [per_idx0[i]["base.N_H1"] for i in sorted(per_idx0)]
    D0 = 100.0 * (sum(N0) / len(N0) - 28000.0) / (sum(N0) / len(N0))
    ok("12 bersaglio giusto: passa", cmd_giungi(a_giungi(bersaglio_k0_pp=round(D0, 2))) == 0)

    # l'implementazione di P e' quella importata, non una copia locale
    import paper2_prominenza_v1 as mod
    ok("13 P importata da paper2_prominenza_v1",
       os.path.basename(mod.__file__).startswith("paper2_prominenza_v1"))
    r1 = prominenza([1000.0, 1010.0, 1020.0], [1900.0, 1910.0, 1920.0],
                    [1200.0, 1210.0, 1220.0], 800.0, 800.0, 800.0)
    r2 = prominenza([1000.0, 1010.0, 1020.0], [1500.0, 1510.0, 1520.0],
                    [1200.0, 1210.0, 1220.0], 800.0, 800.0, 800.0)
    ok("14 la funzione importata risponde agli ingressi", abs(r1["P_pp"] - r2["P_pp"]) > 1.0)

    # registro append-only senza CRLF
    cmd_giungi(a)
    with open(a.out, "rb") as fh:
        raw = fh.read()
    ok("15 registro: due righe, nessun CRLF",
       raw.decode("utf-8").count("\n") == 2 and b"\r\n" not in raw)

    # file inesistente
    ok("16 file inesistente: rifiuto",
       cmd_giungi(a_giungi(k1_file=os.path.join(base, "non-esiste.jsonl"),
                           controllo_file=None)) == 2)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_i = sub.add_parser("ispeziona")
    p_i.add_argument("--file", required=True)
    p_i.set_defaults(func=cmd_ispeziona)

    p_g = sub.add_parser("giungi")
    for k in ("k0", "k1", "k2"):
        p_g.add_argument(f"--{k}-file", required=True)
        p_g.add_argument(f"--{k}-chiave", required=True)
        p_g.add_argument(f"--{k}-indice", default=None)
    p_g.add_argument("--controllo-file", default=None)
    p_g.add_argument("--controllo-chiave", default=None)
    p_g.add_argument("--controllo-indice", default=None)
    p_g.add_argument("--desi-k0", type=float, required=True)
    p_g.add_argument("--desi-k1", type=float, required=True)
    p_g.add_argument("--desi-k2", type=float, required=True)
    p_g.add_argument("--bersaglio-k0-pp", type=float, default=None)
    p_g.add_argument("--bersaglio-tolleranza-pp", type=float, default=0.05)
    p_g.add_argument("--etichetta", default="")
    p_g.add_argument("--out", default=None)
    p_g.set_defaults(func=cmd_giungi)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
