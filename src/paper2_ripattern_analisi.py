#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_ripattern_analisi.py - il test del ripattern contro la soglia dichiarata.
Item 3.2d, referee §4.6. SOLA LETTURA.

LA QUANTITA'
------------
    Delta_ripattern = | Delta D^rand - Delta D^std |

Il lato dati e' identico nei due bracci, quindi si cancella e resta la sola
differenza fra i contrasti del lato mock. E poiche' i semi sono APPAIATI, la
differenza si calcola PER REALIZZAZIONE:

    delta_i = [N_i^rand(B5) - N_i^rand(B1)] - [N_i^std(B5) - N_i^std(B1)]

La media di delta_i ha una SEM molto piu' piccola della differenza di due medie
non appaiate: l'appaiamento e' la ragione per cui il test costa 200 mock e non
2000. Si riportano ENTRAMBE, appaiata e non, cosi' si vede quanto morde.

LA SOGLIA, dichiarata nell'item 3.2d PRIMA del run
--------------------------------------------------
    Delta_ripattern < 53 generatori  ->  il ripattern non guida la risposta AP,
                                         il termine (d) resta zero PER MISURA.
    Delta_ripattern >= 53            ->  (d) entra nel budget e il budget va
                                         riderivato ai quattro livelli.

53 e' 3*sigma_Delta/sqrt(200), la soglia di rilevabilita' in vigore. La quantita'
qui e' una differenza di differenze, il cui errore per propagazione NON appaiata
sarebbe sqrt(2) volte piu' grande, cioe' 75. Dei due candidati si e' scelto il
piu' stretto, prima di guardare qualunque numero.

TRAPPOLE EVITATE
----------------
  * FUSIONE per (regione, indice), non last-wins: fase3_mock.jsonl ha piu'
    record per realizzazione.
  * Il braccio si distingue per il campo `replica_randomise` DEPOSITATO, non per
    il nome del file: un registro non e' il suo percorso.
  * Chiave assente = errore, non None.
  * Le realizzazioni si intersecano sugli INDICI: appaiare per posizione
    darebbe coppie sbagliate se un indice manca da un lato.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys

DEFAULT_STD = os.path.join("results", "paper2", "fase3_mock.jsonl")
DEFAULT_RAND = os.path.join("results", "paper2", "fase3_mock_ripattern.jsonl")

SOGLIA = 53.0
PUNTI = ("B1", "B5")
CAMPI = ("N_H1_k0", "N_H1_k1")
D5C_SOGLIA = 28


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def read_jsonl(path):
    if not os.path.isfile(path):
        fail("registro assente: %s" % path)
    with open(path, "rb") as fh:
        raw = fh.read()
    out = []
    for i, ln in enumerate(raw.replace(b"\r\n", b"\n").split(b"\n"), start=1):
        if ln.strip():
            try:
                out.append(json.loads(ln.decode("utf-8")))
            except Exception as exc:
                fail("%s riga %d non e' JSON: %s" % (path, i, exc))
    return out


def merge(records, want_rand):
    """{(regione, indice): {punto: {campo: valore}}}, UNENDO i punti.

    `want_rand` seleziona il braccio dal campo depositato, non dal file.
    """
    out, conflicts = {}, []
    for r in records:
        if r.get("smoke"):
            continue
        if bool(r.get("replica_randomise", False)) != want_rand:
            continue
        k = (r.get("region"), r.get("index"))
        pts = r.get("points")
        if not isinstance(pts, dict):
            continue
        slot = out.setdefault(k, {})
        for name, d in pts.items():
            if not isinstance(d, dict):
                continue
            cur = slot.setdefault(name, {})
            for f, v in d.items():
                if f in cur and cur[f] != v:
                    conflicts.append((k, name, f, cur[f], v))
                cur[f] = v
    return out, conflicts


def contrasti(merged, region, field):
    """{indice: N(B5) - N(B1)} sulle realizzazioni che hanno entrambi i punti."""
    out, incompleti = {}, []
    for (reg, idx), pts in merged.items():
        if reg != region:
            continue
        if not all(p in pts and field in pts[p] for p in PUNTI):
            incompleti.append(idx)
            continue
        out[idx] = float(pts["B5"][field]) - float(pts["B1"][field])
    return out, sorted(incompleti)


def stat(xs):
    m = st.mean(xs)
    sd = st.stdev(xs) if len(xs) > 1 else 0.0
    sem = sd / math.sqrt(len(xs)) if xs else float("nan")
    return m, sd, sem


def cmd_inspect(args):
    for lab, path, want in (("STANDARD", args.std, False),
                            ("RANDOMIZZATO", args.rand, True)):
        recs = read_jsonl(path)
        m, conf = merge(recs, want)
        print("=== %s  %s ===" % (lab, path))
        print("  record nel file            : %d" % len(recs))
        print("  record del braccio cercato : %d" % len(m))
        for reg in ("NGC", "SGC"):
            idx = sorted(i for (r, i) in m if r == reg)
            if idx:
                print("    %s: %d realizzazioni, %d..%d, punti %s"
                      % (reg, len(idx), idx[0], idx[-1],
                         sorted({p for (r, i), v in m.items() if r == reg
                                 for p in v})))
        seeds = sorted({r.get("rot_seed") for r in recs
                        if bool(r.get("replica_randomise", False)) == want})
        print("  rot_seed                   : %s" % seeds)
        print("  conflitti di fusione       : %d" % len(conf))
    return 0


def cmd_run(args):
    std, cs = merge(read_jsonl(args.std), False)
    rnd, cr = merge(read_jsonl(args.rand), True)
    if cs or cr:
        print("[avviso] conflitti di fusione: standard %d, randomizzato %d"
              % (len(cs), len(cr)))

    print("=" * 80)
    print("Item 3.2d - ripattern del tiling. Soglia DICHIARATA: %.0f generatori"
          % SOGLIA)
    print("=" * 80)

    verdetti = []
    for region in args.regions:
        for field in CAMPI:
            a, inc_s = contrasti(std, region, field)
            b, inc_r = contrasti(rnd, region, field)
            common = sorted(set(a) & set(b))
            if len(common) < 2:
                print("\n%s %s: realizzazioni in comune insufficienti (%d)"
                      % (region, field, len(common)))
                continue
            da = [a[i] for i in common]
            db = [b[i] for i in common]
            dd = [b[i] - a[i] for i in common]

            ma, sda, sema = stat(da)
            mb, sdb, semb = stat(db)
            md, sdd, semd = stat(dd)
            # non appaiata, per confronto
            sem_np = math.sqrt(sema ** 2 + semb ** 2)
            rho = st.correlation(da, db) if len(da) > 2 else float("nan")

            print("")
            print("-" * 80)
            print("%s   %s   realizzazioni appaiate: %d%s"
                  % (region, field, len(common),
                     ("   (solo standard: %d, solo rand: %d)"
                      % (len(set(a) - set(b)), len(set(b) - set(a))))
                     if set(a) != set(b) else ""))
            print("-" * 80)
            print("  Delta D standard      : %+9.2f +- %5.2f   (sd %6.1f)"
                  % (ma, sema, sda))
            print("  Delta D randomizzato  : %+9.2f +- %5.2f   (sd %6.1f)"
                  % (mb, semb, sdb))
            print("  differenza APPAIATA   : %+9.2f +- %5.2f   (sd %6.1f, t %+.2f)"
                  % (md, semd, sdd, md / semd if semd else float("nan")))
            print("  la stessa NON appaiata: %+9.2f +- %5.2f"
                  % (mb - ma, sem_np))
            print("  correlazione fra bracci: %.4f   -> l'appaiamento riduce la "
                  "SEM di %.1fx" % (rho, sem_np / semd if semd else float("nan")))
            dentro = abs(md) < SOGLIA
            print("")
            print("  |Delta_ripattern| = %.2f   contro soglia %.0f   ->  %s"
                  % (abs(md), SOGLIA,
                     "SOTTO: il ripattern non guida la risposta"
                     if dentro else "SOPRA: (d) entra nel budget"))
            print("  in unita' della propria SEM: %.1f"
                  % (abs(md) / semd if semd else float("nan")))
            verdetti.append((region, field, md, semd, dentro))

    print("")
    print("=" * 80)
    print("  %-6s %-10s %12s %8s %10s" % ("reg", "livello", "Delta_rip", "SEM", "verdetto"))
    for region, field, md, semd, dentro in verdetti:
        print("  %-6s %-10s %+12.2f %8.2f %10s"
              % (region, field, md, semd, "sotto" if dentro else "SOPRA"))
    tutti = all(v[4] for v in verdetti)
    print("")
    print("  ESITO: %s" % (
        "il termine (d) resta ZERO, per misura e non per argomento."
        if tutti else
        "almeno un livello SUPERA la soglia: (d) entra nel budget, che va "
        "riderivato ai quattro livelli."))
    if not tutti:
        print("  La predizione dichiarata nell'item 3.2d e' SMENTITA. Si registra "
              "come smentita.")
    return 0


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    import random
    rng = random.Random(11)
    SHIFT = 40.0

    def rec(reg, i, b1, b5, rand):
        d = {"region": reg, "index": i, "points": {
            "B1": {"N_H1_k0": b1, "N_H1_k1": b1 - 3000.0},
            "B5": {"N_H1_k0": b5, "N_H1_k1": b5 - 3000.0}}}
        if rand:
            d["replica_randomise"] = True
            d["rot_seed"] = 20260905
        return d

    with tempfile.TemporaryDirectory() as td:
        ps = os.path.join(td, "s.jsonl")
        pr = os.path.join(td, "r.jsonl")
        with open(ps, "w", encoding="utf-8", newline="") as fs, \
                open(pr, "w", encoding="utf-8", newline="") as fr:
            for i in range(200):
                base = 35000 + rng.gauss(0, 300)
                d_std = -200.0 + rng.gauss(0, 160)
                # il braccio randomizzato differisce di SHIFT, con rumore
                # APPAIATO: e' cosi' che si comportano due bracci a semi comuni
                fs.write(json.dumps(rec("NGC", i, base, base + d_std, False)) + "\n")
                fr.write(json.dumps(
                    rec("NGC", i, base, base + d_std + SHIFT
                        + rng.gauss(0, 20), True)) + "\n")

        std, _ = merge(read_jsonl(ps), False)
        rnd, _ = merge(read_jsonl(pr), True)
        chk("1  il braccio si distingue dal CAMPO, non dal file",
            len(std) == 200 and len(rnd) == 200,
            "std=%d rand=%d" % (len(std), len(rnd)))
        chk("1b il file standard non contiene record randomizzati",
            len(merge(read_jsonl(ps), True)[0]) == 0)

        a, _ = contrasti(std, "NGC", "N_H1_k0")
        b, _ = contrasti(rnd, "NGC", "N_H1_k0")
        dd = [b[i] - a[i] for i in sorted(set(a) & set(b))]
        md, sdd, semd = stat(dd)
        chk("2  lo spostamento iniettato viene recuperato",
            abs(md - SHIFT) < 4 * semd, "%.2f contro %.1f (SEM %.2f)"
            % (md, SHIFT, semd))

        ma, _, sema = stat([a[i] for i in sorted(a)])
        mb, _, semb = stat([b[i] for i in sorted(b)])
        sem_np = math.sqrt(sema ** 2 + semb ** 2)
        chk("3  l'appaiamento riduce la SEM di almeno 5x",
            sem_np / semd > 5.0, "%.1fx  (appaiata %.2f, non appaiata %.2f)"
            % (sem_np / semd, semd, sem_np))
        chk("3b la media appaiata e quella non appaiata COINCIDONO",
            abs(md - (mb - ma)) < 1e-9,
            "%.6f contro %.6f" % (md, mb - ma))

        # indici che non combaciano: si INTERSECA, non si appaia per posizione
        with open(pr, "a", encoding="utf-8", newline="") as fr:
            fr.write(json.dumps(rec("NGC", 999, 1.0, 2.0, True)) + "\n")
        rnd2, _ = merge(read_jsonl(pr), True)
        b2, _ = contrasti(rnd2, "NGC", "N_H1_k0")
        common = set(a) & set(b2)
        chk("4  un indice presente da un lato solo viene ESCLUSO",
            999 in b2 and 999 not in common and len(common) == 200)

        # fusione: due record per la stessa realizzazione
        with open(pr, "a", encoding="utf-8", newline="") as fr:
            fr.write(json.dumps({"region": "NGC", "index": 0,
                                 "replica_randomise": True,
                                 "points": {"B7": {"N_H1_k0": 1.0}}}) + "\n")
        rnd3, _ = merge(read_jsonl(pr), True)
        chk("5  la fusione UNISCE i punti invece di sostituirli",
            set(rnd3[("NGC", 0)]) == {"B1", "B5", "B7"},
            str(sorted(rnd3[("NGC", 0)])))

        # conflitto di valore segnalato
        with open(pr, "a", encoding="utf-8", newline="") as fr:
            fr.write(json.dumps({"region": "NGC", "index": 0,
                                 "replica_randomise": True,
                                 "points": {"B1": {"N_H1_k0": -1.0}}}) + "\n")
        _, conf = merge(read_jsonl(pr), True)
        chk("6  un conflitto di valore viene segnalato", len(conf) == 1, str(conf[:1]))

    chk("7  la soglia e' quella dichiarata nell'item 3.2d", SOGLIA == 53.0)

    print("=== SELFTEST paper2_ripattern_analisi ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def main():
    p = argparse.ArgumentParser(description="Test del ripattern (item 3.2d)")
    p.add_argument("--std", default=DEFAULT_STD)
    p.add_argument("--rand", default=DEFAULT_RAND)
    p.add_argument("--regions", nargs="*", default=["NGC", "SGC"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("run").set_defaults(func=cmd_run)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
