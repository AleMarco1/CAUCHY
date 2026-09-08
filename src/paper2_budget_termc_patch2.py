#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_budget_termc_patch2.py — correzione del fattore sqrt(2) in `termc`.

COSA E' SUCCESSO
  Il cancello di riproduzione del primo patch ha fallito su tutti e quattro i
  valori congelati, con rapporto calcolato/congelato pari a 1.4137, 1.4133,
  1.4152, 1.4136. E' sqrt(2) a quattro cifre.

  La differenza appaiata dN = N_reseed - N_main e' fra DUE estrazioni
  indipendenti del carving, quindi Var(dN) = 2 sigma_carve^2. La definizione
  congelata di (c) e' la dispersione di UNA estrazione:

      sigma_carve = sd(dN) / sqrt(2)
      TERM_C      = sigma_carve / sqrt(n)

  Verifica: 153.74/sqrt(2)/sqrt(200) = 7.686 contro 7.69 congelato;
  154.50 -> 7.725 contro 7.73; 135.69 -> 6.785 contro 6.78;
  125.76 -> 6.288 contro 6.29. E sigma_carve vale 108.7 e 88.9, cioe' i 109 e 89
  riportati nel documento come dispersione per realizzazione.

  Il codice del primo patch confrontava sd(dN)/sqrt(n) con TERM_C, cioe' una
  quantita' piu' grande di sqrt(2). Errore mio, intercettato dal cancello.

ATTENZIONE, distinzione che il codice ora tiene separata:
  - sem_mean  = sd(dN)/sqrt(n)             -> serve per z sulla MEDIA (i)
  - sem_carve = sd(dN)/sqrt(2)/sqrt(n)     -> e' TERM_C
  Non sono la stessa cosa e non vanno confuse: la prima misura l'incertezza
  sulla media della differenza, la seconda il contributo di (c) al budget.

AGGIUNGE ANCHE
  Un avviso esplicito quando il registro di reseed contiene il solo FID: in quel
  caso (ii) e (iii) NON sono calcolabili e il codice lo dice invece di tacere.

Uso:
    python src\\paper2_budget_termc_patch2.py selftest
    python src\\paper2_budget_termc_patch2.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

A_OLD = '''        d = np.array([B[p][i] - A[p][i] for i in idx], float)
        sd = float(d.std(ddof=1))
        sem = sd / np.sqrt(len(d))
        rows.append({"pt": p, "n": len(d), "mean": float(d.mean()), "sd": sd,
                     "sem": float(sem),
                     "z": float(d.mean() / sem) if sem else float("nan")})'''

A_NEW = '''        d = np.array([B[p][i] - A[p][i] for i in idx], float)
        sd = float(d.std(ddof=1))
        # dN e' la differenza fra DUE estrazioni indipendenti del carving:
        # Var(dN) = 2 sigma_carve^2. La definizione congelata di (c) e' la
        # dispersione di UNA estrazione, quindi il sqrt(2) va tolto.
        sigma_carve = sd / np.sqrt(2.0)
        sem_mean = sd / np.sqrt(len(d))          # per z sulla media: (i)
        sem_carve = sigma_carve / np.sqrt(len(d))  # questo E' TERM_C
        rows.append({"pt": p, "n": len(d), "mean": float(d.mean()), "sd": sd,
                     "sigma_carve": float(sigma_carve),
                     "sem": float(sem_mean), "sem_carve": float(sem_carve),
                     "z": float(d.mean() / sem_mean) if sem_mean else float("nan")})'''

B_OLD = '''        sems = [r["sem"] for r in rows]
        fid = next((r["sem"] for r in rows if r["pt"] == "FID"), float("nan"))'''

B_NEW = '''        sems = [r["sem_carve"] for r in rows]
        fid = next((r["sem_carve"] for r in rows if r["pt"] == "FID"), float("nan"))'''

C_OLD = '''        print(f"  {'punto':<6} {'n':>5} {'sd':>9} {'sem':>8} {'media':>10} {'z':>7}")
        for r in rows:
            print(f"  {r['pt']:<6} {r['n']:>5} {r['sd']:>9.2f} {r['sem']:>8.2f} "
                  f"{r['mean']:>+10.3f} {r['z']:>+7.2f}")'''

C_NEW = '''        print(f"  {'punto':<6} {'n':>5} {'sd(dN)':>9} {'sigma_c':>9} "
              f"{'(c)':>7} {'media':>10} {'z':>7}")
        for r in rows:
            print(f"  {r['pt']:<6} {r['n']:>5} {r['sd']:>9.2f} "
                  f"{r['sigma_carve']:>9.2f} {r['sem_carve']:>7.2f} "
                  f"{r['mean']:>+10.3f} {r['z']:>+7.2f}")'''

D_OLD = '''        bad = [r["pt"] for r in rows if abs(r["z"]) > 3.0]
        print(f"\\n  (i)   punti con |z| > 3 sulla media: "
              f"{bad if bad else 'nessuno'}")'''

D_NEW = '''        bad = [r["pt"] for r in rows if abs(r["z"]) > 3.0]
        print(f"\\n  (i)   punti con |z| > 3 sulla media: "
              f"{bad if bad else 'nessuno'}")
        if set(r["pt"] for r in rows) <= {"FID"}:
            print("  (ii)  NON CALCOLABILE: il registro di reseed contiene il solo")
            print("        FID. La pendenza contro (F-1) richiede almeno due punti.")
            print("  (iii) NON CALCOLABILE per la stessa ragione. Serve un run di")
            print("        reseed a B1 e B5, 200 realizzazioni, due emisferi.")
            print("  NOTA: (c) e' quindi misurato al SOLO fiduciale e applicato a")
            print("        tutti i punti. Che il rumore del carving sia indipendente")
            print("        dal punto e' un'assunzione MAI TESTATA, ed e' esattamente")
            print("        il dubbio del §4.5. Va dichiarata, non taciuta.")'''

EDITS = [
    ("A  sigma_carve e sem_carve in termc_table", A_OLD, A_NEW),
    ("B  il confronto con TERM_C usa sem_carve", B_OLD, B_NEW),
    ("C  la tabella mostra sd, sigma_c e (c)", C_OLD, C_NEW),
    ("D  avviso se il reseed ha il solo FID", D_OLD, D_NEW),
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


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok = os.path.isfile(path)
    chk("1  budget presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("2  il primo patch e' stato applicato", "def cmd_termc" in s
        and "TERM_C_REPRO_TOL" in s)
    chk("3  idempotenza: il sqrt(2) non e' gia' corretto", "sigma_carve" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=4):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("8  il risultato e' Python valido", _parses(out))
        chk("9  TERM_C resta invariato",
            'TERM_C = {"NGC": {1: 7.73, 0: 7.69}, "SGC": {1: 6.29, 0: 6.78}}' in out)
        chk("10 z usa sem_mean, non sem_carve (sono cose diverse)",
            'd.mean() / sem_mean' in out and 'd.mean() / sem_carve' not in out)
        chk("11 il confronto col congelato usa sem_carve",
            'sems = [r["sem_carve"] for r in rows]' in out)
        chk("12 l'avviso su (ii)/(iii) c'e' ed e' esplicito",
            "NON CALCOLABILE" in out and "MAI TESTATA" in out)
        chk("13 cmd_run e cmd_selftest intatti",
            out.count("def cmd_run(a):") == 1
            and out.count("def cmd_selftest(a):") == 1)

        # verifica numerica della correzione, sui quattro casi reali
        import math
        misure = {("NGC", 0): (153.74, 7.69), ("NGC", 1): (154.50, 7.73),
                  ("SGC", 0): (135.69, 6.78), ("SGC", 1): (125.76, 6.29)}
        worst = 0.0
        for (reg, ki), (sd, frozen) in misure.items():
            calc = sd / math.sqrt(2.0) / math.sqrt(200.0)
            worst = max(worst, abs(calc - frozen))
        chk("14 la correzione riproduce i quattro congelati (scarto max < 0.05)",
            worst < 0.05, "scarto max %.4f" % worst)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_budget_termc_patch2 ===")
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
    sys.stdout.write("".join(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s corretto" % a.path)
    return 0


def main():
    p = argparse.ArgumentParser(description="correzione sqrt(2) in termc")
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
