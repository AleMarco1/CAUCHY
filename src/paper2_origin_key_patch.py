#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_origin_key_patch.py - l'offset dell'origine entra nel RECORD e nella
CHIAVE DI RIPRESA. Correzione di un difetto della patch precedente.

COSA ERA SBAGLIATO
------------------
`--origin-offset` era sulla firma, nel sito di chiamata e in argparse, ma NON
nel record ne' nella chiave di ripresa. Conseguenze, entrambe osservate:

  * i record non dicono a quale geometria appartengono: `origin_offset` risulta
    None su tutte le righe, e due offset diversi sono indistinguibili;
  * i due offset hanno la STESSA chiave, quindi la ripresa non li separa: il
    registro si e' riempito di 400 record per braccio invece di 200, meta' dei
    quali dei run senza offset, senza nulla che li distingua.

Otto ore di macchina perse. La patch del ripattern faceva la cosa giusta per
rot_seed -- «entra nel record e nella chiave di ripresa: due semi diversi sono
due misure» -- e per l'offset lo stesso passaggio era stato saltato.

TRE MODIFICHE, negli stessi tre posti in cui vive rot_seed
-----------------------------------------------------------
  1. la chiave COSTRUITA dai record gia' su disco (`done`);
  2. la chiave CONFRONTATA per la realizzazione corrente;
  3. il record depositato.

E un cancello che verifica che due offset diversi diano chiavi DIVERSE: e'
esattamente cio' che mancava, quindi e' il controllo che serve.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_runner_fase3_mock.py")

CHIAVE_LETTA_V = (
    '                              bool(r.get("fixed_observables", False)),\n'
    '                              bool(r.get("replica_randomise", False)),\n'
    '                              r.get("rot_seed")))')
CHIAVE_LETTA_N = (
    '                              bool(r.get("fixed_observables", False)),\n'
    '                              bool(r.get("replica_randomise", False)),\n'
    '                              r.get("rot_seed"),\n'
    '                              # §C: l\'offset dell\'origine e\' una GEOMETRIA\n'
    '                              # diversa, quindi una misura diversa. Senza\n'
    '                              # questa componente due offset condividono la\n'
    '                              # chiave e la ripresa non li separa.\n'
    '                              (float(r["origin_offset"])\n'
    '                               if r.get("origin_offset") is not None\n'
    '                               else None)))')

CHIAVE_CORRENTE_V = (
    '                bool(getattr(a, "fixed_observables", False)),\n'
    '                bool(getattr(a, "replica_randomise", False)),\n'
    '                (int(a.rot_seed)\n'
    '                 if getattr(a, "replica_randomise", False) else None)) in done:')
CHIAVE_CORRENTE_N = (
    '                bool(getattr(a, "fixed_observables", False)),\n'
    '                bool(getattr(a, "replica_randomise", False)),\n'
    '                (int(a.rot_seed)\n'
    '                 if getattr(a, "replica_randomise", False) else None),\n'
    '                (float(a.origin_offset)\n'
    '                 if getattr(a, "origin_offset", None) is not None\n'
    '                 else None)) in done:')

RECORD_V = (
    '        if getattr(a, "replica_randomise", False):\n'
    '            rec["replica_randomise"] = True\n'
    '            rec["rot_seed"] = int(a.rot_seed)')
RECORD_N = (
    '        if getattr(a, "replica_randomise", False):\n'
    '            rec["replica_randomise"] = True\n'
    '            rec["rot_seed"] = int(a.rot_seed)\n'
    '        # Il record deve dire a quale geometria appartiene. Senza, due\n'
    '        # offset diversi finiscono nello stesso registro indistinguibili,\n'
    '        # ed e\' esattamente quello che e\' successo.\n'
    '        if getattr(a, "origin_offset", None) is not None:\n'
    '            rec["origin_offset"] = float(a.origin_offset)')

EDITS = [
    ("1. la chiave letta dai record su disco", CHIAVE_LETTA_V, CHIAVE_LETTA_N,
     'if r.get("origin_offset") is not None'),
    ("2. la chiave della realizzazione corrente", CHIAVE_CORRENTE_V,
     CHIAVE_CORRENTE_N, 'if getattr(a, "origin_offset", None) is not None\n                 else None)) in done:'),
    ("3. il record depositato", RECORD_V, RECORD_N,
     'rec["origin_offset"] = float(a.origin_offset)'),
]


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
    ok, done, bad = [], [], []
    for name, old, new, marker in EDITS:
        if marker in n:
            done.append(name)
        elif n.count(old) == 1:
            ok.append(name)
        else:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(old)))
    return ok, done, bad


def apply_all(txt):
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s): non proseguo. Depositare "
             "l'offset senza metterlo nella chiave, o viceversa, e' peggio di "
             "non farlo affatto." % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        prima = len(n)
        n = n.replace(old, new, 1)
        if len(n) == prima:
            fail("la sostituzione %r non ha cambiato nulla." % name)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  --origin-offset esiste gia': %s" % ('"--origin-offset"' in n))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if '"--origin-offset"' not in n:
        fail("--origin-offset non c'e': lancia prima "
             "paper2_origin_offset_patch.py.")
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
    print("  %d -> %d byte, AST valido, %d modifiche"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8")), len(EDITS)))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prekey"
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
        ("l'offset e' nella chiave LETTA dai record",
         'r.get("origin_offset") is not None' in n),
        ("l'offset e' nella chiave della realizzazione corrente",
         'float(a.origin_offset)' in n and "in done:" in n),
        ("l'offset e' nel RECORD depositato",
         'rec["origin_offset"] = float(a.origin_offset)' in n),
        ("le due chiavi hanno lo stesso numero di componenti",
         n.count('r.get("rot_seed")') == 1),
        ("l'offset e' depositato come float, non come stringa",
         'float(a.origin_offset)' in n and '"%s" % a.origin_offset' not in n),
        ("None resta None: i run senza offset conservano la loro chiave",
         "else None)) in done:" in n),
        ("rot_seed e' intatto in tutti e tre i posti",
         n.count("rot_seed") >= 8),
        ("il rifiuto senza --skip-fid e' intatto",
         "--origin-offset richiede --skip-fid" in n),
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
def chiave_letta(r):
    done = set()
    done.add((r.get("region"), r.get("index"),
''' + CHIAVE_LETTA_V + '''
    return next(iter(done))


def chiave_corrente(a, reg, kk, done):
    if True:
        if (reg, kk,
''' + CHIAVE_CORRENTE_V + '''
            return True
    return False


def deposita(a, rec):
    for _ in (0,):
''' + RECORD_V + '''
    return rec
'''


def cmd_selftest(args):
    import tempfile
    import importlib.util
    import types
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    def carica(path, nome):
        spec = importlib.util.spec_from_file_location(nome, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def ns(off):
        return types.SimpleNamespace(fixed_observables=False,
                                     replica_randomise=True, rot_seed=20260905,
                                     origin_offset=off)

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "runner.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)
        pre = carica(p, "k_pre")
        r_lo = {"region": "SGC", "index": 0, "fixed_observables": False,
                "replica_randomise": True, "rot_seed": 20260905,
                "origin_offset": 4.0}
        r_hi = dict(r_lo, origin_offset=-2.1)
        chk("1  PRIMA: due offset diversi danno la STESSA chiave",
            pre.chiave_letta(r_lo) == pre.chiave_letta(r_hi),
            "e' il difetto che ha sporcato i registri")
        chk("1b PRIMA: il record non porta l'offset",
            "origin_offset" not in pre.deposita(ns(4.0), {}))

        txt = read_target(p)[0]
        ok, done, bad = plan(txt)
        chk("2  le tre ancore sono uniche", len(ok) == 3 and not bad,
            "ok=%d bad=%s" % (len(ok), bad))
        new_n, _ = apply_all(txt)
        ast.parse(new_n)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)
        post = carica(p, "k_post")

        chk("3  DOPO: due offset diversi danno chiavi DIVERSE",
            post.chiave_letta(r_lo) != post.chiave_letta(r_hi),
            "%s contro %s" % (post.chiave_letta(r_lo)[-1],
                              post.chiave_letta(r_hi)[-1]))
        chk("3b lo stesso offset da' la stessa chiave",
            post.chiave_letta(r_lo) == post.chiave_letta(dict(r_lo)))
        r_no = dict(r_lo); r_no.pop("origin_offset")
        chk("3c un record SENZA offset ha chiave distinta da uno con offset",
            post.chiave_letta(r_no) != post.chiave_letta(r_lo))
        chk("3d e due record senza offset restano appaiati fra loro",
            post.chiave_letta(r_no) == post.chiave_letta(dict(r_no)),
            "la ripresa dei run vecchi non si rompe")

        rec = post.deposita(ns(4.0), {})
        chk("4  il record porta l'offset, come float",
            rec.get("origin_offset") == 4.0
            and isinstance(rec["origin_offset"], float))
        chk("4b senza offset il record non lo inventa",
            "origin_offset" not in post.deposita(ns(None), {}))
        chk("4c e rot_seed resta depositato", rec.get("rot_seed") == 20260905)

        vecchie = {post.chiave_letta(r_lo)}
        chk("5  stesso offset: la realizzazione viene SALTATA",
            post.chiave_corrente(ns(4.0), "SGC", 0, vecchie))
        chk("5b offset diverso: la realizzazione NON viene saltata",
            not post.chiave_corrente(ns(-2.1), "SGC", 0, vecchie),
            "e' cio' che ha sporcato i registri")
        chk("5c e senza offset nemmeno",
            not post.chiave_corrente(ns(None), "SGC", 0, vecchie))
        chk("5d il PRIMA saltava anche con offset diverso",
            pre.chiave_corrente(ns(-2.1), "SGC", 0,
                                {pre.chiave_letta(r_lo)}),
            "il difetto, riprodotto")

        ok2, _, bad2 = plan(read_target(p)[0])
        chk("6  idempotenza", not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

    print("=== SELFTEST paper2_origin_key_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def main():
    p = argparse.ArgumentParser(
        description="L'offset entra nel record e nella chiave di ripresa")
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
