#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_surrogato_griglia_patch.py - aggiunge i quattro punti surrogati
C1aff..C4aff alla griglia del lato dati. Item 3.2e, risposta 5 del referee.

I QUATTRO ESPONENTI SI LEGGONO, NON SI SCRIVONO
-----------------------------------------------
`p` viene da results/paper2/surrogato_aff.jsonl, depositato da
paper2_surrogato_fit.py dopo i suoi tre cancelli. Scriverlo nel codice
significherebbe due copie dello stesso numero che possono divergere -- e
significherebbe un numero senza provenienza, che e' il rilievo del §3.9.

UN SURROGATO E' STRUTTURALMENTE UN PUNTO DI LINEA B
---------------------------------------------------
point_plan costruisce la linea B come dict(kind="ap", alpha_iso=1.0, F_ap=F).
Un surrogato e' lo stesso con F = p. Non serve un `kind` nuovo: serve una lista
in piu'. Il blocco si chiama "Caff" cosi' i record si distinguono nel registro.

E LA SCALA LA IMPONE IL RUNNER
------------------------------
paper2_runner_fase3.py ri-gaugia con c = L_fid/L_punto, quindi il surrogato
porta solo la FORMA. E' la ragione per cui il fitter produce il solo p: il
cancello sul cubo costante e' del run, non del fit.

Quattro modifiche, atomiche.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_runner_fase3.py")
DEFAULT_SURROGATO = os.path.join("results", "paper2", "surrogato_aff.jsonl")

LOADER = '''def load_corners_aff(path):
    """I quattro surrogati affini, LETTI dal registro del fit (item 3.2e).

    Non si scrivono nel codice: due copie dello stesso numero divergono, e un
    numero senza provenienza e' il rilievo del §3.9. Il registro lo deposita
    paper2_surrogato_fit.py dopo i suoi tre cancelli.

    Ritorna [(nome, p), ...] in ordine di angolo. Se il file manca o e'
    malformato SOLLEVA: un piano di run che salta punti in silenzio e' peggio
    di un piano che non parte.
    """
    # Import LOCALI: il bersaglio non e' detto che abbia `os` o `json` in
    # testa -- e infatti `os` non c'era. Un caricatore che dipende dagli
    # import di chi lo ospita e' un caricatore che fallisce a run avviato.
    import json
    import os
    if not path or not os.path.isfile(path):
        raise SystemExit(
            "[FATAL] surrogati richiesti ma il registro non c'e': %r. Lancia "
            "prima src/paper2_surrogato_fit.py fit --out <registro>." % path)
    per_punto = {}
    with open(path, "rb") as fh:
        raw = fh.read()
    for i, ln in enumerate(raw.replace(b"\\r\\n", b"\\n").split(b"\\n"), start=1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln.decode("utf-8"))
        except Exception as exc:
            raise SystemExit("[FATAL] %s riga %d non e' JSON: %s" % (path, i, exc))
        if r.get("schema") != "paper2_surrogato_v1":
            continue
        for k in ("point_aff", "p"):
            if k not in r:
                raise SystemExit(
                    "[FATAL] %s riga %d: campo %r assente. Il registro non ha "
                    "la forma attesa e non indovino." % (path, i, k))
        nome, p = str(r["point_aff"]), float(r["p"])
        if nome in per_punto and per_punto[nome] != p:
            raise SystemExit(
                "[FATAL] %s: %s compare con due esponenti diversi, %r e %r. "
                "Non scelgo io quale." % (path, nome, per_punto[nome], p))
        per_punto[nome] = p
    if not per_punto:
        raise SystemExit("[FATAL] %s non contiene record paper2_surrogato_v1."
                         % path)
    return [(n, per_punto[n]) for n in sorted(per_punto)]


'''

EDITS = [

    ("1. il caricatore dei surrogati",
     "def point_plan(I13, points=None):",
     LOADER + "def point_plan(I13, points=None, aff_path=None):",
     "def load_corners_aff(path):"),

    ("2. i surrogati entrano nel piano",
     '    if points:\n        plan = [p for p in plan if p[0] in points]',
     '    # Item 3.2e: i surrogati affini. Strutturalmente punti di linea B --\n'
     '    # dict(kind="ap", alpha_iso=1.0, F_ap=p) -- perche\' la famiglia e\' la\n'
     '    # stessa; il blocco "Caff" li distingue nel registro. La scala non la\n'
     '    # portano: il ri-gauge sotto impone L = L_fid.\n'
     '    if aff_path:\n'
     '        plan += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=p), "Caff")\n'
     '                 for n, p in load_corners_aff(aff_path)]\n'
     '    if points:\n'
     '        noti = {p[0] for p in plan}\n'
     '        ignoti = [q for q in points if q not in noti]\n'
     '        if ignoti:\n'
     '            # Un punto chiesto e non presente veniva SALTATO in silenzio:\n'
     '            # il run girava su meno punti di quelli richiesti senza dirlo.\n'
     '            raise SystemExit(\n'
     '                "[FATAL] punti richiesti e non nel piano: %s. Se sono "\n'
     '                "surrogati serve --surrogato con il registro del fit."\n'
     '                % ignoti)\n'
     '        plan = [p for p in plan if p[0] in points]',
     'punti richiesti e non nel piano'),

    ("3. il percorso arriva a point_plan",
     "        for name, spec, block in point_plan(I13, a.points):",
     '        for name, spec, block in point_plan(\n'
     '                I13, a.points, getattr(a, "surrogato", None)):',
     'getattr(a, "surrogato", None)'),

    ("4. argparse, solo su `run`",
     '            q.add_argument("--points", nargs="*", default=None)',
     '            q.add_argument("--points", nargs="*", default=None)\n'
     '            q.add_argument("--surrogato", default=None, metavar="FILE",\n'
     '                           help="item 3.2e: registro del fit dei "\n'
     '                                "surrogati affini. Aggiunge C1aff..C4aff "\n'
     '                                "al piano, con F_ap letto da li\'. Usare "\n'
     '                                "un --out SEPARATO: sono punti di griglia "\n'
     '                                "nuovi, non una continuazione")',
     '"--surrogato", default=None'),
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


def plan_edits(txt):
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
    ok, done, bad = plan_edits(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s): non proseguo."
             % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        n = n.replace(old, new, 1)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan_edits(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    print("")
    print("=== REGISTRO DEL FIT  %s ===" % args.surrogato)
    if not os.path.isfile(args.surrogato):
        print("  ASSENTE: lancia paper2_surrogato_fit.py fit --out prima dei run.")
        return 3 if bad else 0
    righe = []
    with open(args.surrogato, "rb") as fh:
        raw = fh.read()
    for ln in raw.replace(b"\r\n", b"\n").split(b"\n"):
        if ln.strip():
            r = json.loads(ln.decode("utf-8"))
            if r.get("schema") == "paper2_surrogato_v1":
                righe.append(r)
    print("  record: %d" % len(righe))
    for r in sorted(righe, key=lambda x: x.get("point_aff", "")):
        print("    %-7s p = %.7f   res 1p %8.4f -> 2p %8.4f"
              % (r.get("point_aff"), r.get("p", float("nan")),
                 r.get("res_1p_hMpc", float("nan")),
                 r.get("res_2p_hMpc", float("nan"))))
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
    print("  %d -> %d byte, AST valido, %d modifiche"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8")), len(EDITS)))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre32e"
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
        ("il caricatore c'e'", "def load_corners_aff(path):" in n),
        ("legge dal registro, non da costanti",
         "point_aff" in n and 'raise SystemExit' in n),
        ("point_plan accetta aff_path",
         "def point_plan(I13, points=None, aff_path=None):" in n),
        ("i surrogati sono punti di linea B, blocco Caff",
         '"Caff"' in n and 'alpha_iso=1.0, F_ap=p' in n),
        ("un punto richiesto e non nel piano ora SOLLEVA",
         "punti richiesti e non nel piano" in n),
        ("il percorso arriva a point_plan",
         'getattr(a, "surrogato", None)' in n),
        ("--surrogato esiste ed e' solo su `run`",
         n.count('"--surrogato"') == 1),
        ("una sola definizione di point_plan", n.count("def point_plan(") == 1),
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
# NESSUN import in testa: il bersaglio vero non ha `os`, e un fixture piu'
# generoso del bersaglio fa passare un selftest su codice che poi non gira.
class _I13:
    LINE_A = [("A0", 0.99), ("A1", 1.01)]
    LINE_B = [("B1", 0.971070), ("B5", 1.030071)]
    CORNERS = [("C1", 0.2500, -1.2), ("C2", 0.2500, -0.8),
               ("C3", 0.3500, -1.2), ("C4", 0.3500, -0.8)]


I13 = _I13()


def point_plan(I13, points=None):
    plan = [("FID", dict(kind="fid"), "fid")]
    plan += [(n, dict(kind="ap", alpha_iso=al, F_ap=1.0), "A") for n, al in I13.LINE_A]
    plan += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=F), "B") for n, F in I13.LINE_B]
    plan += [(n, dict(kind="cosmo", omm=o, w0=w), "C") for n, o, w in I13.CORNERS]
    if points:
        plan = [p for p in plan if p[0] in points]
    return plan


def cmd_run(a):
    out = []
    try:
        for name, spec, block in point_plan(I13, a.points):
            out.append((name, block, spec))
    finally:
        pass
    return out


def build_parser():
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    for nm in ("d3", "run"):
        q = sub.add_parser(nm)
        if nm == "run":
            q.add_argument("--points", nargs="*", default=None)
    return p
'''


def cmd_selftest(args):
    import tempfile
    import importlib.util
    import types
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "synthrun3.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)
        txt = read_target(p)[0]
        ok, done, bad = plan_edits(txt)
        chk("1  le quattro ancore sono uniche", len(ok) == 4 and not bad,
            "ok=%d bad=%s" % (len(ok), bad))

        new_n, _ = apply_all(txt)
        try:
            ast.parse(new_n)
            chk("2  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("2  il risultato e' Python valido", False, str(exc))
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)

        spec = importlib.util.spec_from_file_location("synthrun3", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        reg = os.path.join(td, "sur.jsonl")
        P = {"C1aff": 1.0289029, "C2aff": 0.9945301,
             "C3aff": 1.0070012, "C4aff": 0.9806182}
        with open(reg, "w", encoding="utf-8", newline="") as fh:
            for n_, v in sorted(P.items()):
                fh.write(json.dumps({"schema": "paper2_surrogato_v1",
                                     "point_aff": n_, "p": v,
                                     "res_1p_hMpc": 1.0,
                                     "res_2p_hMpc": 0.1}) + "\n")

        # senza --surrogato il piano e' quello di prima
        base = m.cmd_run(types.SimpleNamespace(points=None, surrogato=None))
        chk("3  senza il registro il piano e' INVARIATO",
            [x[0] for x in base] == ["FID", "A0", "A1", "B1", "B5",
                                     "C1", "C2", "C3", "C4"],
            str([x[0] for x in base]))

        con = m.cmd_run(types.SimpleNamespace(points=None, surrogato=reg))
        nomi = [x[0] for x in con]
        chk("4  con il registro i quattro surrogati entrano nel piano",
            nomi[-4:] == ["C1aff", "C2aff", "C3aff", "C4aff"], str(nomi[-4:]))
        chk("4b il blocco e' Caff e non C",
            all(b == "Caff" for _, b, _ in con if _.endswith("aff"))
            if False else all(x[1] == "Caff" for x in con if x[0].endswith("aff")))
        chk("4c gli esponenti vengono dal REGISTRO, non dal codice",
            all(abs(x[2]["F_ap"] - P[x[0]]) < 1e-12
                for x in con if x[0].endswith("aff")))
        chk("4d un surrogato e' strutturalmente un punto di linea B",
            all(x[2]["kind"] == "ap" and x[2]["alpha_iso"] == 1.0
                for x in con if x[0].endswith("aff")))

        # filtro per punti
        sel = m.cmd_run(types.SimpleNamespace(points=["C1aff", "C4aff"],
                                              surrogato=reg))
        chk("5  --points seleziona i surrogati", [x[0] for x in sel]
            == ["C1aff", "C4aff"], str([x[0] for x in sel]))

        # un punto ignoto SOLLEVA invece di essere saltato
        chk("6  un punto chiesto e non nel piano SOLLEVA",
            _exits(lambda: m.cmd_run(types.SimpleNamespace(points=["C1aff"],
                                                           surrogato=None))))
        chk("6b e il messaggio dice cosa fare",
            _msg(lambda: m.cmd_run(types.SimpleNamespace(points=["C9aff"],
                                                         surrogato=reg)),
                 "--surrogato"))

        # registro assente / malformato / incoerente
        chk("7  registro assente: SOLLEVA",
            _exits(lambda: m.load_corners_aff(os.path.join(td, "no.jsonl"))))
        vuoto = os.path.join(td, "vuoto.jsonl")
        open(vuoto, "w").write('{"schema":"altro"}\n')
        chk("7b registro senza record del fit: SOLLEVA",
            _exits(lambda: m.load_corners_aff(vuoto)))
        rotto = os.path.join(td, "rotto.jsonl")
        open(rotto, "w").write('{"schema":"paper2_surrogato_v1","point_aff":"C1aff"}\n')
        chk("7c record senza `p`: SOLLEVA", _exits(lambda: m.load_corners_aff(rotto)))
        due = os.path.join(td, "due.jsonl")
        open(due, "w").write(
            '{"schema":"paper2_surrogato_v1","point_aff":"C1aff","p":1.0}\n'
            '{"schema":"paper2_surrogato_v1","point_aff":"C1aff","p":2.0}\n')
        chk("7d lo stesso punto con due esponenti: SOLLEVA, non sceglie",
            _exits(lambda: m.load_corners_aff(due)))

        # argparse
        pr = m.build_parser()
        a = pr.parse_args(["run", "--points", "C1aff", "--surrogato", reg])
        chk("8  --surrogato e' accettato dal sottocomando run",
            a.surrogato == reg and a.points == ["C1aff"])
        chk("8b --surrogato NON esiste su d3",
            _exits_argparse(pr, ["d3", "--surrogato", reg]))

        sorgente = read_target(p)[0]
        testa = sorgente[:sorgente.index("class _I13")]
        chk("10 il modulo sintetico NON importa os/json in testa: il bersaglio "
            "vero non li ha, e un fixture piu' generoso nasconde il difetto",
            "import os" not in testa and "import json" not in testa,
            "testa: %r" % testa.strip()[:60])
        chk("10b il caricatore importa cio' che gli serve DA SE'",
            "    import os" in sorgente and "    import json" in sorgente)

        ok2, done2, bad2 = plan_edits(read_target(p)[0])
        chk("9  idempotenza", not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

    print("=== SELFTEST paper2_surrogato_griglia_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def _msg(fn, frag):
    try:
        fn()
        return False
    except SystemExit as exc:
        return frag in str(exc)
    except Exception:
        return False


def _exits_argparse(parser, argv):
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args(argv)
        return False
    except SystemExit:
        return True


def main():
    p = argparse.ArgumentParser(
        description="Aggiunge C1aff..C4aff alla griglia del lato dati (item 3.2e)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=DEFAULT_TARGET)
    common.add_argument("--surrogato", default=DEFAULT_SURROGATO)
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
