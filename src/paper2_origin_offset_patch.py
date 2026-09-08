#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_origin_offset_patch.py - `--origin-offset`, per il test del §C del
secondo report.

COSA FA E PERCHE'
-----------------
Il referee propone di variare lo spostamento relativo fra griglia e reticolo del
box con una traslazione dell'origine dell'embedding. Quella traslazione NON
varia lo spostamento relativo: lo scan del record 45 lo dimostra e il controllo
3d dello strumento lo fissa. Varia la FASE, e con essa la frazione di voxel il
cui cella sorgente cambia -- da 0% a 100% in SGC.

Il che rende l'esperimento migliore di come e' formulato: a spostamento relativo
FISSO si varia la frazione e si guarda se Delta_ripattern la segue.

DOVE
----
Subito dopo `box_min, box_size = _box(GEO, pos_r, pad)`, prima che la geometria
si fissi e che la maschera si derivi. `box_size` NON si tocca, quindi `cell`,
`R_SMOOTH` e il cancello su sigma_px restano dove sono: l'offset non deve
toccare il lisciamento, o misurerebbe due cose insieme.

IL CONFLITTO CON IL 2.1-M, E COME SI RISOLVE
--------------------------------------------
La riga 472 pretende che la maschera fiduciale RIDERIVATA coincida con la
CONGELATA. Con un'origine spostata non coincidera' piu', e il cancello
scatterebbe -- correttamente. Le tre uscite possibili:

  * rilassare il 2.1-M quando c'e' l'offset: NO. E' il cancello che garantisce
    che la maschera si derivi invece di caricarsi, e spegnerlo per comodita' e'
    la classe di difetto del record 35.
  * applicare l'offset a tutti i punti tranne FID: NO. FID e i punti B
    starebbero su griglie diverse e Delta D misurerebbe quella differenza.
  * RICHIEDERE --skip-fid insieme all'offset: si'. Senza FID nel piano il
    cancello non ha oggetto e non si applica -- non perche' lo si spegne, ma
    perche' cio' che confronta non c'e'. Ed e' la stessa forma del rifiuto che
    la patch del ripattern gia' ha per --fixed-observables.

Il costo e' nullo: i run del ripattern giravano gia' con --skip-fid.

QUATTRO MODIFICHE, ATOMICHE
---------------------------
  1. la firma di build_geometries;
  2. l'applicazione dell'offset dopo _box, con il ramo spento no-op PER
     COSTRUZIONE -- se e' None non si tocca box_min, non si somma zero;
  3. il sito di chiamata, che passa il parametro invece di leggere un globale
     (record 35: un flag che esiste e che nessuno accende);
  4. argparse: --origin-offset accanto a --replica-randomise, e il rifiuto
     esplicito senza --skip-fid.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_runner_fase3_mock.py")

FIRMA_V = ("def build_geometries(M, GEO, PF, I13, F3, region, cache_r, z_tab, dc_fid,\n"
           "                     points=None, verbose=True):")
FIRMA_N = ("def build_geometries(M, GEO, PF, I13, F3, region, cache_r, z_tab, dc_fid,\n"
           "                     points=None, verbose=True, origin_offset=None):")

BOX_V = ("        box_min, box_size = _box(GEO, pos_r, pad)\n"
         "        cell = box_size / M.NGRID")
BOX_N = ("        box_min, box_size = _box(GEO, pos_r, pad)\n"
         "        # §C del secondo report: l'origine dell'embedding e' una SCELTA,\n"
         "        # e traslarla cambia la FASE della griglia rispetto al reticolo\n"
         "        # del box periodico -- quindi quanto ripattern c'e' -- lasciando\n"
         "        # invariato lo spostamento RELATIVO fra i punti. box_size NON si\n"
         "        # tocca: cell, R_SMOOTH e il cancello su sigma_px restano dove\n"
         "        # sono, o l'offset misurerebbe due cose insieme.\n"
         "        # Il ramo spento e' un no-op PER COSTRUZIONE: se e' None non si\n"
         "        # esegue nulla, non si somma zero.\n"
         "        if origin_offset is not None:\n"
         "            box_min = box_min + float(origin_offset)\n"
         "        cell = box_size / M.NGRID")

CHIAMATA_V = ("    geoms = build_geometries(M, GEO, PF, I13, F3, reg, cache_r, z_tab, dc_fid,\n"
              "                             points)")
CHIAMATA_N = ("    _off = getattr(a, \"origin_offset\", None)\n"
              "    if _off is not None and not bool(getattr(a, \"skip_fid\", False)):\n"
              "        sys.exit(\"[FATAL] --origin-offset richiede --skip-fid. Con \"\n"
              "                 \"l'origine spostata la maschera fiduciale riderivata \"\n"
              "                 \"non coincide piu' con la congelata, e il 2.1-M \"\n"
              "                 \"scatterebbe: giustamente. Non lo si spegne, si toglie \"\n"
              "                 \"il fiduciale dal piano. Applicare l'offset a tutti i \"\n"
              "                 \"punti TRANNE FID metterebbe FID e i punti B su \"\n"
              "                 \"griglie diverse, e Delta D misurerebbe quella \"\n"
              "                 \"differenza.\")\n"
              "    geoms = build_geometries(M, GEO, PF, I13, F3, reg, cache_r, z_tab, dc_fid,\n"
              "                             points, origin_offset=_off)")

ARG_V = ('            q.add_argument("--rot-seed", type=int, default=ROT_SEED_DEFAULT,')
ARG_N = ('            q.add_argument("--origin-offset", type=float, default=None,\n'
         '                           metavar="H_MPC",\n'
         '                           help="§C del secondo report: trasla l\'origine "\n'
         '                                "dell\'embedding di questa quantita\'. Cambia "\n'
         '                                "la FASE della griglia rispetto al reticolo "\n'
         '                                "del box, non lo spostamento RELATIVO fra i "\n'
         '                                "punti. Richiede --skip-fid e un --out "\n'
         '                                "SEPARATO: e\' un\'altra geometria")\n'
         '            q.add_argument("--rot-seed", type=int, default=ROT_SEED_DEFAULT,')

EDITS = [
    ("1. firma di build_geometries", FIRMA_V, FIRMA_N, "origin_offset=None):"),
    ("2. l'offset dopo _box", BOX_V, BOX_N, "if origin_offset is not None:"),
    ("3. il sito di chiamata", CHIAMATA_V, CHIAMATA_N, "origin_offset=_off)"),
    ("4. argparse su `run`", ARG_V, ARG_N, '"--origin-offset", type=float'),
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
        fail("applicazione PARZIALE gia' presente (%s): non proseguo. Una firma "
             "cambiata senza il sito di chiamata, o viceversa, e' un runner che "
             "non parte o che ignora il parametro." % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        prima = len(n)
        n = n.replace(old, new, 1)
        if len(n) == prima:
            fail("la sostituzione %r non ha cambiato nulla: ancora non trovata "
                 "al momento dell'applicazione." % name)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    print("  la patch del ripattern e' gia' applicata: %s"
          % ("randomise_replicas" in n))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if "randomise_replicas" not in n:
        fail("la patch del ripattern non c'e': --origin-offset serve al test "
             "del §C, che confronta due bracci randomizzati. Applicare prima "
             "paper2_ripattern_runner_patch.py.")
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
    bak = args.target + ".preoff"
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
        ("origin_offset e' un PARAMETRO, non un globale",
         "origin_offset=None):" in n and "\nORIGIN_OFFSET" not in n),
        ("il ramo spento e' un no-op per costruzione",
         "if origin_offset is not None:" in n
         and "box_min + 0.0" not in n),
        ("box_size NON viene toccato",
         "box_min = box_min + float(origin_offset)" in n
         and "box_size = box_size +" not in n),
        ("l'offset precede il calcolo di cell",
         n.index("box_min = box_min + float(origin_offset)")
         < n.index("        cell = box_size / M.NGRID")),
        ("il sito di chiamata passa il parametro",
         "origin_offset=_off)" in n),
        ("senza --skip-fid il runner RIFIUTA",
         "--origin-offset richiede --skip-fid" in n),
        ("e il rifiuto spiega perche' non si spegne il 2.1-M",
         "Non lo si spegne" in n),
        ("--origin-offset esiste, una sola volta, su `run`",
         n.count('"--origin-offset"') == 1),
        ("il cancello 2.1-M e' INTATTO",
         "maschera fiduciale riderivata != congelata (2.1-M)" in n),
        ("una sola definizione di build_geometries",
         n.count("def build_geometries(") == 1),
        ("la patch del ripattern e' intatta",
         "randomise_replicas" in n and "rot_state" in n),
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
import sys

ROT_SEED_DEFAULT = 20260905
randomise_replicas = True
rot_state = None


def _box(GEO, pos, pad):
    return 100.0, 1000.0


''' + FIRMA_V + '''
    out = {}
    for name in (points or ["FID", "B1", "B5"]):
        pos_r, pad = None, 5.0
''' + BOX_V + '''
        out[name] = {"box_min": box_min, "box_size": box_size, "cell": cell}
    return out


class _M:
    NGRID = 128


def _prepare(a, points):
    M, GEO, PF, I13, F3 = _M(), None, None, None, None
    reg, cache_r, z_tab, dc_fid = a.region, None, None, None
''' + CHIAMATA_V + '''
    return geoms


def build_parser():
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    for nm in ("d4", "run"):
        q = sub.add_parser(nm)
        if nm == "run":
            q.add_argument("--skip-fid", action="store_true")
''' + ARG_V + '''
                           help="seme delle permutazioni")
    return p
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

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "runner.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)
        pre = carica(p, "r_pre")
        g_pre = pre._prepare(types.SimpleNamespace(region="SGC"), None)
        chk("1  PRIMA: box_min = 100.0 su tutti i punti",
            all(abs(v["box_min"] - 100.0) < 1e-12 for v in g_pre.values()))

        txt = read_target(p)[0]
        ok, done, bad = plan(txt)
        chk("2  le quattro ancore sono uniche", len(ok) == 4 and not bad,
            "ok=%d bad=%s" % (len(ok), bad))
        new_n, _ = apply_all(txt)
        ast.parse(new_n)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)
        post = carica(p, "r_post")

        a0 = types.SimpleNamespace(region="SGC", origin_offset=None, skip_fid=False)
        g0 = post._prepare(a0, None)
        chk("3  DOPO, senza offset: box_min IDENTICO a prima",
            all(abs(g0[k]["box_min"] - g_pre[k]["box_min"]) < 1e-15 for k in g0),
            "no-op per costruzione")
        chk("3b e anche cell e box_size sono identici",
            all(g0[k]["cell"] == g_pre[k]["cell"]
                and g0[k]["box_size"] == g_pre[k]["box_size"] for k in g0))

        a1 = types.SimpleNamespace(region="SGC", origin_offset=5.13, skip_fid=True)
        g1 = post._prepare(a1, None)
        chk("4  con offset: box_min si sposta di ESATTAMENTE l'offset",
            all(abs(g1[k]["box_min"] - (g_pre[k]["box_min"] + 5.13)) < 1e-12
                for k in g1),
            "%.4f" % g1["B1"]["box_min"])
        chk("4b e box_size NON si muove: cell e R_SMOOTH restano",
            all(g1[k]["box_size"] == g_pre[k]["box_size"]
                and g1[k]["cell"] == g_pre[k]["cell"] for k in g1))

        a2 = types.SimpleNamespace(region="SGC", origin_offset=5.13, skip_fid=False)
        chk("5  offset senza --skip-fid: RIFIUTA",
            _exits(lambda: post._prepare(a2, None)))
        chk("5b e il messaggio dice perche' non si spegne il 2.1-M",
            _msg(lambda: post._prepare(a2, None), "Non lo si spegne"))

        pr = post.build_parser()
        aa = pr.parse_args(["run", "--skip-fid", "--origin-offset", "5.13"])
        chk("6  argparse accetta --origin-offset su `run`",
            abs(aa.origin_offset - 5.13) < 1e-12 and aa.skip_fid)
        bb = pr.parse_args(["run"])
        chk("6b e il default e' None, non 0.0", bb.origin_offset is None)
        chk("6c --origin-offset NON esiste su d4",
            _exits_argparse(pr, ["d4", "--origin-offset", "1.0"]))

        ok2, _, bad2 = plan(read_target(p)[0])
        chk("7  idempotenza", not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

    print("=== SELFTEST paper2_origin_offset_patch ===")
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
    p = argparse.ArgumentParser(description="--origin-offset per il test del §C")
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
