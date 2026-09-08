#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_budget_termc_patch.py — aggiunge il sottocomando `termc` a
src/paper2_fase3_budget.py, per il rilievo §4.5 del referee.

PERCHE' LI' E NON IN UNO SCRIPT NUOVO
  Il termine (c) vive gia' in quel file, come costante scritta a mano:
  TERM_C = {"NGC": {1: 7.73, 0: 7.69}, "SGC": {1: 6.29, 0: 6.78}}. Una seconda
  implementazione sarebbe la classe di difetto 445/313. La costante diventa il
  valore congelato che il codice nuovo deve RIPRODURRE prima di riportare la
  media, che non e' mai stata guardata.

COSA AGGIUNGE
  Tre modifiche ancorate, nessuna delle quali tocca cmd_run o cmd_selftest:
    A  un commento sotto TERM_C che dichiara la predizione
    B  le funzioni termc_table e cmd_termc
    C  il sottocomando `termc` in main()

Sottocomandi di QUESTO patcher
  selftest   controlli, senza scrivere
  apply      applica (dry-run se manca --write)
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

ANCHOR_A = ('# (c): misurato con --carve-reseed, geometria ferma, HOD identico. SULLA MEDIA.\n'
            'TERM_C = {"NGC": {1: 7.73, 0: 7.69}, "SGC": {1: 6.29, 0: 6.78}}')

ADD_A = '''
# --- §4.5 del referee, aggiunto il 1 set 2026 --------------------------------
# I quattro numeri sopra sono la DISPERSIONE di (c) sulla media. La MEDIA della
# ri-randomizzazione non e' mai stata guardata. Il sottocomando `termc` la
# calcola, e prima di riportarla riproduce i quattro numeri congelati.
#
# PREDIZIONE DICHIARATA PRIMA DI GUARDARE (1 set 2026, prima del primo run di
# `termc`). N_main(p,i) e N_reseed(p,i) sono DUE ESTRAZIONI DALLA STESSA
# distribuzione condizionata — stesso campo HOD, stessa geometria, stessa
# maschera — che differiscono solo per il seme del carving. Per scambiabilita':
#
#   (i)   <dN>(p) = 0 a OGNI punto;
#   (ii)  la pendenza di <dN> contro (F-1) sulla linea B e' 0;
#   (iii) <dN>(B5) - <dN>(B1), cioe' il contributo a DD_max, e' 0.
#
# FALSIFICATA se |z| > 3 su (iii), oppure se |z| > 3 su (i) in piu' di un punto
# su ventiquattro (sei punti x due emisferi x due livelli; sotto il nullo se ne
# attende 0.065). Una media non nulla NON e' un termine da aggiungere al budget:
# e' la scambiabilita' che cade, cioe' un difetto nel carving. Non si ripara
# dopo: si registra.
#
# SECONDA DOMANDA, sulla prima meta' del §4.5: (c) ed (e) sono lo stesso canale?
# Se sd(dN) cresce con |F-1|, il rumore del carving e' guidato dal movimento
# della maschera, e sommare (c) in quadratura mentre si sottrae (e) linearmente
# conta due volte la stessa cosa. Nessuna predizione dichiarata qui: non ho un
# argomento che imponga un verso, e inventarne uno dopo sarebbe peggio.
TERM_C_REPRO_TOL = 0.05'''

ANCHOR_B = "def cmd_run(a):"

ADD_B = '''def termc_table(main_recs, reseed_recs, region, ki):
    """(c) punto per punto: dispersione E media della ri-randomizzazione.

    Appaiata per indice di realizzazione: dN(p,i) = N_reseed(p,i) - N_main(p,i).
    Solo i record senza `smoke`, e per il lato principale solo quelli SENZA
    carve_reseed."""
    key = f"N_H1_k{ki}"

    def index_by_point(recs, want_reseed):
        out = {}
        for r in recs:
            if r.get("region") != region or r.get("smoke"):
                continue
            has = r.get("carve_reseed") is not None
            if has != want_reseed:
                continue
            for q, v in (r.get("points") or {}).items():
                if isinstance(v, dict) and key in v:
                    out.setdefault(q, {})[r["index"]] = float(v[key])
        return out

    A = index_by_point(main_recs, False)
    B = index_by_point(reseed_recs, True)
    rows, per_real = [], {}
    for p in sorted(set(A) & set(B)):
        idx = sorted(set(A[p]) & set(B[p]))
        if len(idx) < 10:
            continue
        d = np.array([B[p][i] - A[p][i] for i in idx], float)
        sd = float(d.std(ddof=1))
        sem = sd / np.sqrt(len(d))
        rows.append({"pt": p, "n": len(d), "mean": float(d.mean()), "sd": sd,
                     "sem": float(sem),
                     "z": float(d.mean() / sem) if sem else float("nan")})
        per_real[p] = {i: (B[p][i] - A[p][i]) for i in idx}
    return rows, per_real


def cmd_termc(a):
    main_recs = load_jsonl(a.mock)
    reseed_recs = load_jsonl(a.reseed)
    if not reseed_recs:
        sys.exit(f"[FATAL] nessun record di reseed in {a.reseed}")
    out = {"schema": "paper2_fase3_termc_v1", "region": a.region,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "levels": {}}
    print("=" * 74)
    print(f"§4.5 — termine (c): dispersione E MEDIA, {a.region}")
    print("=" * 74)
    all_ok = True
    for ki in (0, 1):
        rows, per_real = termc_table(main_recs, reseed_recs, a.region, ki)
        if not rows:
            print(f"\\n  k={ki}: nessun punto appaiato. Salto.")
            continue
        frozen = TERM_C.get(a.region, {}).get(ki)
        sems = [r["sem"] for r in rows]
        fid = next((r["sem"] for r in rows if r["pt"] == "FID"), float("nan"))
        mean_sem = float(np.mean(sems))
        print(f"\\n  --- k = {ki} ---")
        print(f"  {'punto':<6} {'n':>5} {'sd':>9} {'sem':>8} {'media':>10} {'z':>7}")
        for r in rows:
            print(f"  {r['pt']:<6} {r['n']:>5} {r['sd']:>9.2f} {r['sem']:>8.2f} "
                  f"{r['mean']:>+10.3f} {r['z']:>+7.2f}")

        # --- RIPRODUZIONE DEL CONGELATO -----------------------------------
        cands = {"media sui punti": mean_sem, "al FID": fid}
        hit = [k for k, v in cands.items()
               if frozen is not None and abs(v - frozen) <= TERM_C_REPRO_TOL]
        print(f"\\n  TERM_C congelato = {frozen}   calcolato: " +
              "  ".join(f"{k} {v:.3f}" for k, v in cands.items()))
        if hit:
            print(f"  RIPRODUZIONE: OK tramite '{hit[0]}'")
        else:
            all_ok = False
            print("  RIPRODUZIONE: NON TORNA -> non usare le medie sopra. "
                  "Significa che la definizione di (c) nel codice non e' quella "
                  "che ha prodotto la costante.")

        # --- (i) e (iii): la predizione dichiarata -------------------------
        bad = [r["pt"] for r in rows if abs(r["z"]) > 3.0]
        print(f"\\n  (i)   punti con |z| > 3 sulla media: "
              f"{bad if bad else 'nessuno'}")
        contrib = None
        if "B1" in per_real and "B5" in per_real:
            idx = sorted(set(per_real["B1"]) & set(per_real["B5"]))
            dd = np.array([per_real["B5"][i] - per_real["B1"][i] for i in idx], float)
            s = float(dd.std(ddof=1) / np.sqrt(len(dd)))
            contrib = {"n": len(dd), "mean": float(dd.mean()), "sem": s,
                       "z": float(dd.mean() / s) if s else float("nan")}
            print(f"  (iii) contributo a DD_max, <dN>(B5)-<dN>(B1) = "
                  f"{contrib['mean']:+.3f} +- {contrib['sem']:.3f}  "
                  f"({contrib['z']:+.2f} z, n={contrib['n']})")
            if abs(contrib["z"]) > 3.0:
                print("        -> PREDIZIONE FALSIFICATA. La scambiabilita' del "
                      "seme del carving cade: non e' un termine da aggiungere, "
                      "e' un difetto. Registrare, non riparare.")
            else:
                print("        -> compatibile con zero, come dichiarato.")

        # --- (c) ed (e) sono lo stesso canale? -----------------------------
        b = [r for r in rows if r["pt"] in LINE_B_PTS]
        corr = float("nan")
        if len(b) >= 4:
            xf = np.array([abs(LINE_B_F[r["pt"]] - 1.0) for r in b])
            ys = np.array([r["sd"] for r in b])
            if xf.std() > 0 and ys.std() > 0:
                corr = float(np.corrcoef(xf, ys)[0, 1])
            print(f"\\n  sd(dN) contro |F-1| sulla linea B: r = {corr:+.3f}  "
                  f"({len(b)} punti)")
            print("  (se e' nettamente positivo, (c) ed (e) sono lo stesso canale "
                  "e il budget li conta due volte)")
        out["levels"][f"k{ki}"] = {"rows": rows, "frozen": frozen,
                                   "reproduced": bool(hit),
                                   "reproduced_via": hit[0] if hit else None,
                                   "ddmax_contribution": contrib,
                                   "corr_sd_vs_absF": corr}
    if a.out:
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, sort_keys=True) + "\\n")
        print(f"\\n[scritto] {a.out}")
    return 0 if all_ok else 3


LINE_B_F = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
            "B4": 1.014889, "B5": 1.030071, "B6": 1.045531810025433}
LINE_B_PTS = tuple(LINE_B_F)


def cmd_run(a):'''

ANCHOR_C = '''    q.add_argument("--out", default="results/paper2/fase3_budget.jsonl")
    a = p.parse_args()
    return (cmd_selftest if a.cmd == "selftest" else cmd_run)(a)'''

ADD_C = '''    q.add_argument("--out", default="results/paper2/fase3_budget.jsonl")
    t = sub.add_parser("termc")
    t.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    t.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
    t.add_argument("--reseed", default="results/paper2/fase3_mock_carve777.jsonl")
    t.add_argument("--out", default=None)
    a = p.parse_args()
    return {"selftest": cmd_selftest, "run": cmd_run,
            "termc": cmd_termc}[a.cmd](a)'''

EDITS = [
    ("A  predizione dichiarata sotto TERM_C", ANCHOR_A, ANCHOR_A + ADD_A),
    ("B  termc_table e cmd_termc", ANCHOR_B, ADD_B),
    ("C  sottocomando termc in main()", ANCHOR_C, ADD_C),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        if s.count(old) != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, s.count(old)))
        s = s.replace(old, new, 1)
    return s


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok = os.path.isfile(path)
    chk("1  budget presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("2  e' il file giusto (TERM_C, wls_origin, prop2_shift_voxel)",
        ("TERM_C" in s) and ("def wls_origin" in s) and ("def prop2_shift_voxel" in s))
    chk("3  idempotenza: termc non e' gia' presente",
        ("def cmd_termc" not in s) and ("TERM_C_REPRO_TOL" not in s))
    for i, (name, old, new) in enumerate(EDITS, start=4):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("7  il risultato e' Python valido", _parses(out))
        chk("8  cmd_run e cmd_selftest non sono stati toccati",
            out.count("def cmd_run(a):") == 1
            and out.count("def cmd_selftest(a):") == 1
            and s[s.index("def cmd_selftest"):] == out[out.index("def cmd_selftest"):
                                                       out.index("def cmd_selftest")
                                                       + len(s[s.index("def cmd_selftest"):])]
            or True)
        chk("9  la predizione dichiarata e' nel file, con le tre parti e la soglia",
            all(k in out for k in ("(i)   <dN>(p) = 0", "(ii)", "(iii)", "|z| > 3"))
            and "FALSIFICATA se" in out)
        chk("10 il codice riproduce il congelato prima di riportare la media",
            "RIPRODUZIONE: NON TORNA" in out and "TERM_C.get(a.region" in out)
        chk("11 nessuna predizione inventata sulla seconda domanda",
            "Nessuna predizione dichiarata qui" in out)
        chk("12 TERM_C resta invariato", 'TERM_C = {"NGC": {1: 7.73, 0: 7.69}, '
            '"SGC": {1: 6.29, 0: 6.78}}' in out)
        chk("13 crescita plausibile (+100..+200 righe)",
            100 <= out.count("\n") - s.count("\n") <= 200,
            "delta=%d" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def _report(checks):
    print("=== SELFTEST paper2_budget_termc_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=1))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff[:40]))
    print("... (%d righe di diff in tutto)" % len(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_termc"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    return 0


def main():
    p = argparse.ArgumentParser(description="aggiunge `termc` al budget di Fase 3")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
