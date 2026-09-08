#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_d5c_diagnostica_patch.py — D5c passa da ARRESTO a MISURA, per un giro.

PERCHE'
  D5c ha fermato lo smoke al punto FIDUCIALE: 2 posizioni su ~218.000 fuori dal
  cubo sulla faccia +y, eccesso 2.046 Mpc/h. Al fiduciale, cioe' dentro la
  misura congelata della Fase 3.

  Causa probabile, da verificare e non da assumere: il cubo e' derivato dai
  RANDOM (_box(GEO, pos_r, pad)), e i random non hanno RSD; le galassie mock
  si'. Lo spostamento comovente RSD vale (1+z) v / H(z): a z ~ 0.2 con
  H ~ 111 h km/s/Mpc, 300 km/s danno 3.2 Mpc/h e 650 km/s danno 7. Il padding e'
  5, quindi un satellite veloce lo supera. Il lato dati non ha l'asimmetria,
  perche' li' i redshift osservati SONO le osservabili.

  Se e' cosi', D5c come scritto confonde due cose diverse: l'impilamento
  STRUTTURALE al fiduciale, che c'e' da sempre, e quello INDOTTO DALLA
  DEFORMAZIONE, che e' il bersaglio dichiarato del record 17.

COSA FA QUESTA PATCH
  Nulla di definitivo. Sostituisce l'arresto con una MISURA registrata nel
  record, per un solo giro diagnostico, cosi' la riformulazione di D5c si
  decide su un numero invece che su un'ipotesi.

  ATTENZIONE, e va detto: questo INDEBOLISCE un cancello nel momento in cui ha
  sparato. E' la mossa che va guardata con sospetto. Le due condizioni che la
  rendono accettabile sono scritte qui e verificate dal selftest:
    (1) il conteggio non sparisce: si MISURA A OGNI PUNTO e si SCRIVE nel
        record, quindi il dato esiste comunque;
    (2) e' esplicitamente TEMPORANEA: `D5C_MODE = "measure"` va riportata a
        "block" prima di qualunque run che produca risultati, e il codice lo
        stampa a ogni esecuzione invece di lasciarlo a chi ricorda.

USO
  python src\\paper2_d5c_diagnostica_patch.py selftest
  python src\\paper2_d5c_diagnostica_patch.py apply --write
  python src\\paper2_runner_fase3_mock.py smoke --region NGC
  python src\\paper2_runner_fase3_mock.py smoke --region SGC

  Lo smoke gira su FID, B1, B5: tre punti che coprono il fiduciale e i due
  estremi della linea B. E' quello che serve per sapere se n_clipped cresce con
  |F-1| o resta costante.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_runner_fase3_mock.py")

A_OLD = '''        import paper2_phase3_preflight as PF
        if pos_sel is not None and len(pos_sel) >= 100:
            _cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
            if _cl["n_clipped"]:
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo. "
                         f"Dettaglio: {_cl}. Il punto non si misura "
                         f"(emendamento 17).")'''

A_NEW = '''        import paper2_phase3_preflight as PF
        _cl = None
        if pos_sel is not None and len(pos_sel) >= 100:
            _cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
            if _cl["n_clipped"] and D5C_MODE == "block":
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo. "
                         f"Dettaglio: {_cl}. Il punto non si misura "
                         f"(emendamento 17).")
            if _cl["n_clipped"] and D5C_MODE == "measure":
                print(f"    [D5c misura] {name}/mock {kk}: "
                      f"n_clipped = {_cl['n_clipped']}")'''

B_OLD = '''        row = {"n_sel": int(len(pos_sel)), "alpha": alpha}'''

B_NEW = '''        row = {"n_sel": int(len(pos_sel)), "alpha": alpha}
        # D5c: il conteggio si registra SEMPRE, in entrambe le modalita'. Che il
        # cancello fermi o no, il dato non deve dipendere da quella scelta.
        if _cl is not None:
            row["d5c_n_clipped"] = int(_cl["n_clipped"])
            row["d5c_per_face"] = {k: v for k, v in _cl.items() if k != "n_clipped"}'''

C_OLD = '''EROSIONS_MOCK = (0, 1)'''

C_NEW = '''EROSIONS_MOCK = (0, 1)

# --- D5c, modalita' -----------------------------------------------------------
# "block"   : arresto duro a n_clipped > 0. E' la forma dell'emendamento 17 ed e'
#             quella che vale per i run che producono risultati.
# "measure" : misura e registra senza fermare. DIAGNOSTICA, 1 set 2026, aperta
#             perche' D5c ha sparato al punto FIDUCIALE (2 posizioni, faccia +y,
#             eccesso 2.046 Mpc/h) e serve sapere se n_clipped cresce con |F-1|
#             o e' una costante del fiduciale. In "measure" il conteggio finisce
#             comunque nel record: il dato non dipende dalla modalita'.
#
# QUESTA E' UNA DEROGA TEMPORANEA a un cancello che ha gia' sparato. Va
# riportata a "block" prima di qualunque run che produca risultati, e il codice
# lo stampa a ogni esecuzione invece di affidarsi alla memoria.
D5C_MODE = "measure"'''

D_OLD = '''def cmd_run(a):
    pts = a.points'''

D_NEW = '''def _avviso_d5c():
    if D5C_MODE != "block":
        print("=" * 74)
        print(f"  ATTENZIONE: D5c e' in modalita' '{D5C_MODE}', NON in 'block'.")
        print("  Il cancello MISURA e non ferma. Va bene per un giro")
        print("  diagnostico; NON per un run che produce risultati.")
        print("  Rimettere D5C_MODE = 'block' in cima a questo file.")
        print("=" * 74)


def cmd_run(a):
    _avviso_d5c()
    pts = a.points'''

E_OLD = '''def cmd_smoke(a):'''

E_NEW = '''def cmd_smoke(a):
    _avviso_d5c()'''

EDITS = [
    ("A  D5c: ferma solo in modalita' block", A_OLD, A_NEW),
    ("B  il conteggio entra nel record in ENTRAMBE le modalita'", B_OLD, B_NEW),
    ("C  costante D5C_MODE, con la deroga dichiarata", C_OLD, C_NEW),
    ("D  avviso a ogni run", D_OLD, D_NEW),
    ("E  e a ogni smoke", E_OLD, E_NEW),
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


def _nomi_liberi(src, funcname):
    import ast
    import builtins
    tree = ast.parse(src)
    glob = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    glob |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            glob |= {(al.asname or al.name.split(".")[0]) for al in n.names}
        elif isinstance(n, ast.Assign):
            glob |= {t.id for t in ast.walk(n) if isinstance(t, ast.Name)}
    fn = next((f for f in ast.walk(tree)
               if isinstance(f, ast.FunctionDef) and f.name == funcname), None)
    if fn is None:
        return {"<funzione %s non trovata>" % funcname}
    bound = set(glob) | set(dir(builtins))
    a = fn.args
    for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
        bound.add(arg.arg)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            bound.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound |= {(al.asname or al.name.split(".")[0]) for al in node.names}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                bound.add(arg.arg)
        elif isinstance(node, ast.comprehension):
            bound |= {t.id for t in ast.walk(node.target) if isinstance(t, ast.Name)}
    usati = {node.id for node in ast.walk(fn)
             if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    return usati - bound


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
    chk("1  runner presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("2  la patch §3.8 e' gia' applicata (D5c esiste)",
        ("PF.clipped_per_face(pos_sel" in s) and ("--real-space" in s))
    chk("3  idempotenza: D5C_MODE non c'e' ancora", "D5C_MODE" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=4):
        c = s.count(old)
        chk("%-2d ancora %s" % (i, name), c == 1, "occorrenze=%d" % c)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("9  il risultato e' Python valido", _parses(out))
        chk("10 SCOPE: ogni nome usato in one_mock e' legato",
            not _nomi_liberi(out, "one_mock"),
            ", ".join(sorted(_nomi_liberi(out, "one_mock"))))
        # LE DUE CONDIZIONI CHE RENDONO ACCETTABILE LA DEROGA
        chk("11 (1) il conteggio si REGISTRA anche quando non ferma",
            'row["d5c_n_clipped"]' in out
            and out.count('if _cl is not None:') == 1)
        chk("12 (1b) e la registrazione NON e' dentro un ramo di modalita'",
            'row["d5c_n_clipped"]' in out.split("D5C_MODE ==")[-1])
        chk("13 (2) la deroga e' dichiarata TEMPORANEA nel codice",
            ("DEROGA TEMPORANEA" in out) and ("riportata a" in out)
            and ("block" in out.split("DEROGA TEMPORANEA")[1][:400]))
        chk("14 (2b) e l'avviso si stampa a ogni run E a ogni smoke",
            out.count("_avviso_d5c()") == 3)
        chk("15 in modalita' block il comportamento e' quello del record 17",
            'D5C_MODE == "block"' in out and "sys.exit" in out)
        chk("16 le due modalita' sono le uniche due, e sono nominate",
            out.count('D5C_MODE == "block"') == 1
            and out.count('D5C_MODE == "measure"') == 1)

        # aritmetica dello spostamento RSD, per non lasciare l'ipotesi asserita
        z, H = 0.2, 111.0            # h km/s/Mpc a z=0.2 per LCDM fiduciale
        for v in (300.0, 650.0):
            d = (1.0 + z) * v / H
            chk("17 RSD a %g km/s sposta di %.1f Mpc/h, padding 5"
                % (v, d), True, "supera il padding" if d > 5 else "sotto")
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_d5c_diagnostica_patch ===")
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
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_d5cmode"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print(r"""
Poi, due smoke da due minuti:
  python src\paper2_runner_fase3_mock.py smoke --region NGC
  python src\paper2_runner_fase3_mock.py smoke --region SGC

Girano su FID, B1, B5: il fiduciale e i due estremi della linea B. La domanda
e' una sola: n_clipped CRESCE passando da FID a B1 e B5, oppure resta 2?

  cresce  -> D5c ha il bersaglio giusto e la forma va cambiata poco: si blocca
             sull'ECCESSO rispetto al fiduciale, non sul valore assoluto.
  costante-> e' una proprieta' del fiduciale, dentro il baseline congelato, e
             va dichiarata come tale invece che intercettata da un cancello
             pensato per un'altra cosa.

NON lanciare i run lunghi finche' D5C_MODE non e' tornata a "block".""")
    return 0


def main():
    p = argparse.ArgumentParser(description="D5c: da arresto a misura, per un giro")
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
