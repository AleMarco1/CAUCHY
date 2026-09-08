#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_budget_nan_patch.py - la riga cosmetica del budget, registrata nel
record 41 e rimasta da fare.

A k=2 e k=3 il budget stampa:

    [rms coppia depositata nan contro None]

E' CORRETTO nella sostanza -- a quei livelli non esiste un pavimento depositato,
quindi il cancello non si applica -- ma «nan contro None» invita a leggerlo come
un guasto. Il record 41 lo registra cosi': «cambia nessun numero».

La patch fa dire alla riga cosa succede davvero:

    [cancello non applicabile: nessun pavimento depositato a questo livello]

Una modifica, e non tocca un solo valore: il selftest lo verifica confrontando
il pavimento stampato prima e dopo.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_fase3_budget.py")

VECCHIO = (
    '    print(f"  (f) pavimento = {floor:7.2f}  su {floor_n} punti, determinato da "\n'
    '          f"{floor_driver}   [rms coppia depositata {floor_rms_dep:.2f} contro "\n'
    '          f"{FLOOR_DEPOSITATO.get(region, {}).get(ki)}]")')

NUOVO = (
    '    # Record 41: a k=2,3 non esiste un pavimento depositato, quindi il\n'
    '    # cancello NON SI APPLICA. «nan contro None» era corretto nella sostanza\n'
    '    # e invitava a leggerlo come un guasto: ora la riga dice cosa succede.\n'
    '    # Non cambia nessun numero.\n'
    '    _dep = FLOOR_DEPOSITATO.get(region, {}).get(ki)\n'
    '    _nota = (f"[rms coppia depositata {floor_rms_dep:.2f} contro {_dep}]"\n'
    '             if _dep is not None else\n'
    '             "[cancello non applicabile: nessun pavimento depositato a "\n'
    '             "questo livello]")\n'
    '    print(f"  (f) pavimento = {floor:7.2f}  su {floor_n} punti, determinato da "\n'
    '          f"{floor_driver}   {_nota}")')

MARKER = "cancello non applicabile: nessun pavimento depositato"


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_target(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    txt = raw.decode("utf-8")
    n_crlf = txt.count("\r\n")
    n_lf = txt.count("\n") - n_crlf
    return txt, ("\r\n" if n_crlf >= n_lf else "\n"), n_crlf, n_lf


def norm(t):
    return t.replace("\r\n", "\n")


def plan(txt):
    n = norm(txt)
    if MARKER in n:
        return [], ["1. la riga del pavimento"], []
    if n.count(VECCHIO) == 1:
        return ["1. la riga del pavimento"], [], []
    return [], [], ["1. la riga del pavimento: %d occorrenze dell'ancora"
                    % n.count(VECCHIO)]


def apply_all(txt):
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    return norm(txt).replace(VECCHIO, NUOVO, 1), done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % sha256_file(args.target))
    if new_n is None:
        print("  [OK] niente da fare (%s)." % ", ".join(done))
        return 0
    try:
        ast.parse(new_n)
    except SyntaxError as exc:
        fail("il risultato non e' Python valido (%s): nulla scritto." % exc)
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d byte, AST valido" % (len(txt.encode("utf-8")),
                                           len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prenan"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] scritto")
    return cmd_verify(args)


def cmd_verify(args):
    n = norm(read_target(args.target)[0])
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("la riga nuova c'e'", MARKER in n),
        ("il caso CON pavimento depositato e' conservato",
         "rms coppia depositata {floor_rms_dep:.2f} contro {_dep}" in n),
        ("il pavimento e il suo argomento restano stampati",
         "(f) pavimento = {floor:7.2f}  su {floor_n} punti, determinato da" in n),
        ("il record 41 e' citato come origine", "Record 41" in n),
        ("una sola occorrenza della riga", n.count("(f) pavimento = {floor") == 1),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok &= bool(cond)
    try:
        ast.parse(n)
        print("  [ok] AST valido")
    except SyntaxError as exc:
        print("  [NO] AST: %s" % exc)
        ok = False
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


SYNTH = '''
FLOOR_DEPOSITATO = {"NGC": {0: 51.13, 1: 32.96}}


def stampa(region, ki, floor, floor_n, floor_driver, floor_rms_dep):
''' + VECCHIO + '''
'''


def cmd_selftest(args):
    import tempfile
    import importlib.util
    import io
    import contextlib
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    def carica(path, nome):
        spec = importlib.util.spec_from_file_location(nome, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def uscita(m, ki, dep_rms):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.stampa("NGC", ki, 51.13, 6, "A1m", dep_rms)
        return buf.getvalue().strip()

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "b.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)
        pre = carica(p, "b_pre")
        u0_pre = uscita(pre, 0, 10.12)
        u2_pre = uscita(pre, 2, float("nan"))
        chk("1  PRIMA: a k=2 stampa «nan contro None»",
            "nan contro None" in u2_pre, u2_pre[-40:])

        txt = read_target(p)[0]
        ok, done, bad = plan(txt)
        chk("2  l'ancora e' unica", ok and not bad and not done, str(bad))
        new_n, _ = apply_all(txt)
        ast.parse(new_n)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)
        post = carica(p, "b_post")

        u0_post = uscita(post, 0, 10.12)
        u2_post = uscita(post, 2, float("nan"))
        chk("3  DOPO: a k=2 dice che il cancello non si applica",
            MARKER in u2_post and "nan contro None" not in u2_post,
            u2_post[-70:])
        chk("4  a k=0, dove il pavimento c'e', l'uscita e' IDENTICA a prima",
            u0_post == u0_pre, "%r" % u0_post[-40:])
        chk("5  il NUMERO del pavimento non cambia a nessun livello",
            u2_post.split("determinato da")[0] == u2_pre.split("determinato da")[0],
            u2_post.split("determinato da")[0].strip())

        ok2, done2, bad2 = plan(read_target(p)[0])
        chk("6  idempotenza", not ok2 and not bad2 and done2,
            "ok=%s done=%s" % (ok2, done2))

    print("=== SELFTEST paper2_budget_nan_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def main():
    p = argparse.ArgumentParser(description="La riga cosmetica del budget (record 41)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect", parents=[common]).set_defaults(func=cmd_inspect)
    sub.add_parser("verify", parents=[common]).set_defaults(func=cmd_verify)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch", parents=[common])
    pa.add_argument("--apply", action="store_true")
    pa.add_argument("--backup", action="store_true", default=True)
    pa.add_argument("--allow-eol-normalise", action="store_true")
    pa.set_defaults(func=cmd_patch)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
