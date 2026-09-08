#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_ripattern_runner_patch.py - porta il flag delle repliche randomizzate da
argparse fino a carve_cutsky. Item 3.2d, referee §4.6.

Undici modifiche, atomiche. La piu' importante e' la sesta.

LA RIGA CHE DECIDE IL TEST
--------------------------
`rot_rng.bit_generator.state = rot_state` accanto al ripristino di `rng`, nel
ciclo sui punti. Le permutazioni devono essere LE STESSE a B1 e a B5.

Con permutazioni diverse fra i due punti l'intero campo verrebbe rimescolato, e
Delta D misurerebbe quel rimescolamento invece della deformazione. Con le stesse
permutazioni la randomizzazione e' una rietichettatura COMUNE ai due punti:
toglie la coerenza fra repliche -- che e' cio' che il ripattern muoverebbe -- e
lascia appaiato tutto il resto. E' l'unica versione del test che risponde alla
domanda del referee.

DUE COPPIE CHE DEVONO MUOVERSI INSIEME
--------------------------------------
La chiave di ripresa compare in DUE posti: dove si legge il registro esistente e
dove si decide se saltare la realizzazione. Patchandone uno solo, la chiave non
combacerebbe e il runner rifarebbe da capo tutto quel che e' gia' fatto, senza
dire niente. Per questo l'applicazione e' tutta-o-niente.

TRE CANCELLI CHE STANNO NEL RUNNER
----------------------------------
  * --replica-randomise e --fixed-observables sono INCOMPATIBILI: sotto (B) il
    carving e' uno solo, al fiduciale. Rifiuto esplicito, non applicazione
    parziale in silenzio.
  * il flag deve ARRIVARE a carve_cutsky. Qui il rischio non e' un globale mai
    assegnato (record 35) ma girare contro un phase8 NON patchato -- dopo un
    checkout, per dire. Si controlla la FIRMA, non l'esistenza del flag.
  * senza rot_seed il run non parte: sarebbe irriproducibile.

Sottocomandi
------------
  inspect / patch / verify / selftest.  Scrive solo con `patch --apply`.

G-AZIONE NON VA NELLO SMOKE. D4b verifica che N_H1 sia identico ai congelati
mock per mock: con le repliche randomizzate DEVE differire, quindi lo smoke
fallirebbe per costruzione. Un cancello che fallisce quando la cosa funziona e'
peggio di nessun cancello. Per questo il flag NON viene aggiunto allo smoke:
G-azione si fa con `run --n 3 --points FID` su un --out separato.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_runner_fase3_mock.py")
ROT_SEED = 20260905


# ---------------------------------------------------------------------------
# Le undici modifiche. Ancore corte: una lunga si spezza al primo spazio
# ricostruito male da un output di console.
# ---------------------------------------------------------------------------

EDITS = [

    ("1. firma di one_mock",
     "             erosions=EROSIONS_MOCK, fixed_observables=False):",
     "             erosions=EROSIONS_MOCK, fixed_observables=False,\n"
     "             replica_randomise=False, rot_seed=None):"),

    ("2. generatore separato delle permutazioni",
     "    state_after_hod = rng.bit_generator.state",
     "    state_after_hod = rng.bit_generator.state\n"
     "    # --- item 3.2d / referee 4.6: repliche randomizzate ----------------\n"
     "    # Generatore SEPARATO. Non deve consumare un solo valore da `rng`,\n"
     "    # altrimenti l'appaiamento dei semi con i run gia' depositati salta.\n"
     "    if replica_randomise and rot_seed is None:\n"
     "        sys.exit('[FATAL] replica_randomise senza rot_seed: il run non "
     "sarebbe riproducibile dal suo seme.')\n"
     "    rot_rng = (np.random.default_rng(int(rot_seed) + kk)\n"
     "               if replica_randomise else None)\n"
     "    rot_state = rot_rng.bit_generator.state if rot_rng is not None else None\n"
     "    # -------------------------------------------------------------------"),

    ("3. LE STESSE permutazioni a ogni punto",
     "        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato",
     "        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato\n"
     "        if rot_rng is not None:\n"
     "            # LE STESSE permutazioni a OGNI punto. Con permutazioni diverse\n"
     "            # fra B1 e B5 il campo verrebbe rimescolato fra i due punti e\n"
     "            # Delta D misurerebbe QUEL rimescolamento invece della\n"
     "            # deformazione. Cosi' la randomizzazione e' una rietichettatura\n"
     "            # COMUNE ai punti: toglie la coerenza fra repliche, che e' cio'\n"
     "            # che il ripattern muoverebbe, e lascia appaiato il resto.\n"
     "            rot_rng.bit_generator.state = rot_state"),

    ("4. i due parametri arrivano a carve_cutsky",
     '            pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z,\n'
     '                                     nz_target, rng)',
     '            pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z,\n'
     '                                     nz_target, rng,\n'
     '                                     randomise_replicas=replica_randomise,\n'
     '                                     rot_rng=rot_rng)'),

    ("5. i cancelli del runner",
     "def cmd_run(a):\n    _avviso_d5c()",
     'ROT_SEED_DEFAULT = %d\n'
     '\n'
     '\n'
     'def _verifica_ripattern(M, a):\n'
     '    """Item 3.2d. Due cose che devono valere PRIMA di consumare ore di macchina.\n'
     '\n'
     '    (1) --replica-randomise e --fixed-observables sono incompatibili: sotto\n'
     '        (B) il carving avviene UNA volta al fiduciale e i punti sono\n'
     '        rimappati, quindi randomizzare toccherebbe solo quel carving. E\'\n'
     '        una domanda diversa, e mescolarle darebbe un numero che non\n'
     '        risponde a nessuna delle due.\n'
     '    (2) il flag deve ARRIVARE a carve_cutsky. Qui il rischio non e\' un\n'
     '        globale mai assegnato -- e\' un parametro, non un globale -- ma\n'
     '        girare contro un phase8 NON patchato, dopo un checkout per dire.\n'
     '        Si controlla la FIRMA, non l\'esistenza del flag.\n'
     '\n'
     '    Si stampa sempre, anche quando e\' False: uno stato che non si vede e\'\n'
     '    uno stato che si dimentica.\n'
     '    """\n'
     '    rr = bool(getattr(a, "replica_randomise", False))\n'
     '    print(f"  [phase8] randomise_replicas = {rr}")\n'
     '    if not rr:\n'
     '        return False\n'
     '    if bool(getattr(a, "fixed_observables", False)):\n'
     '        sys.exit("[FATAL] --replica-randomise e --fixed-observables sono "\n'
     '                 "incompatibili: sotto il trattamento (B) il carving e\' "\n'
     '                 "uno solo, al fiduciale. Sono due misure diverse e "\n'
     '                 "vogliono due --out diversi.")\n'
     '    import inspect as _inspect\n'
     '    if "randomise_replicas" not in _inspect.signature(\n'
     '            M.carve_cutsky).parameters:\n'
     '        sys.exit("[FATAL] phase8 non e\' patchato: carve_cutsky non "\n'
     '                 "accetta randomise_replicas, quindi il flag non "\n'
     '                 "arriverebbe da nessuna parte. Lancia prima "\n'
     '                 "src/paper2_ripattern_patch.py patch --apply.")\n'
     '    print(f"  [phase8] rot_seed = {int(a.rot_seed)}   <-- repliche "\n'
     '          f"randomizzate, LE STESSE a ogni punto")\n'
     '    return True\n'
     '\n'
     '\n'
     'def cmd_run(a):\n    _avviso_d5c()' % ROT_SEED),

    ("6. il cancello viene chiamato",
     '    _accendi_real_space(M, a)\n'
     '    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)',
     '    _accendi_real_space(M, a)\n'
     '    _verifica_ripattern(M, a)\n'
     '    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)'),

    ("7. chiave di ripresa, lato registro",
     '                              bool(r.get("fixed_observables", False))))',
     '                              bool(r.get("fixed_observables", False)),\n'
     '                              bool(r.get("replica_randomise", False)),\n'
     '                              r.get("rot_seed")))'),

    ("8. chiave di ripresa, lato run",
     '                bool(getattr(a, "fixed_observables", False))) in done:',
     '                bool(getattr(a, "fixed_observables", False)),\n'
     '                bool(getattr(a, "replica_randomise", False)),\n'
     '                (int(a.rot_seed)\n'
     '                 if getattr(a, "replica_randomise", False) else None))'
     ' in done:'),

    ("9. i parametri arrivano a one_mock",
     '                     fixed_observables=bool(getattr(a, "fixed_observables", False)))',
     '                     fixed_observables=bool(getattr(a, "fixed_observables", False)),\n'
     '                     replica_randomise=bool(\n'
     '                         getattr(a, "replica_randomise", False)),\n'
     '                     rot_seed=(int(a.rot_seed)\n'
     '                               if getattr(a, "replica_randomise", False)\n'
     '                               else None))'),

    ("10. provenienza nel record depositato",
     '        if getattr(a, "fixed_observables", False):\n'
     '            rec["fixed_observables"] = True',
     '        if getattr(a, "fixed_observables", False):\n'
     '            rec["fixed_observables"] = True\n'
     '        # Item 3.2d: un run la cui provenienza non sta nel record e\'\n'
     '        # esattamente il rilievo §3.9, e l\'abbiamo appena chiuso.\n'
     '        if getattr(a, "replica_randomise", False):\n'
     '            rec["replica_randomise"] = True\n'
     '            rec["rot_seed"] = int(a.rot_seed)'),

    ("11. argparse, solo su `run`",
     '            q.add_argument("--fixed-observables", action="store_true",',
     '            q.add_argument("--replica-randomise", action="store_true",\n'
     '                           help="item 3.2d / referee 4.6: una permutazione "\n'
     '                                "segnata degli assi per replica, LE STESSE "\n'
     '                                "a ogni punto. Usare un --out SEPARATO: e\' "\n'
     '                                "una misura diversa. Incompatibile con "\n'
     '                                "--fixed-observables")\n'
     '            q.add_argument("--rot-seed", type=int, default=ROT_SEED_DEFAULT,\n'
     '                           help="seme del generatore delle permutazioni. "\n'
     '                                "Entra nel record e nella chiave di "\n'
     '                                "ripresa: due semi diversi sono due misure")\n'
     '            q.add_argument("--fixed-observables", action="store_true",'),
]

MARKERS = [
    ("1", "replica_randomise=False, rot_seed=None):"),
    ("2", "rot_state = rot_rng.bit_generator.state"),
    ("3", "rot_rng.bit_generator.state = rot_state"),
    ("4", "randomise_replicas=replica_randomise"),
    ("5", "def _verifica_ripattern(M, a):"),
    ("6", "_verifica_ripattern(M, a)\n    order"),
    ("7", 'bool(r.get("replica_randomise", False)),'),
    ("8", 'bool(getattr(a, "replica_randomise", False)),\n                (int(a.rot_seed)'),
    ("9", "replica_randomise=bool("),
    ("10", 'rec["rot_seed"] = int(a.rot_seed)'),
    ("11", '"--replica-randomise", action="store_true"'),
]


# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

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
    for (name, old, new), (_, marker) in zip(EDITS, MARKERS):
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
        fail("applicazione PARZIALE gia' presente (%s). Le due chiavi di ripresa "
             "devono muoversi insieme: non proseguo." % ", ".join(done))
    n = norm(txt)
    for name, old, new in EDITS:
        n = n.replace(old, new, 1)
    return n, done


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

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
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise per procedere."
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
    bak = args.target + ".pre32d"
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
    txt = read_target(args.target)[0]
    n = norm(txt)
    ok = True
    print("")
    print("=== VERIFY ===")
    for num, marker in MARKERS:
        c = marker in n
        print("  [%s] modifica %s" % ("ok" if c else "NO", num))
        ok &= c
    extra = [
        ("le DUE chiavi di ripresa si muovono insieme",
         n.count('bool(r.get("replica_randomise", False))') == 1
         and n.count('bool(getattr(a, "replica_randomise", False)),') >= 1),
        ("il flag NON e' stato aggiunto allo smoke (D4b fallirebbe per costruzione)",
         n.count('"--replica-randomise"') == 1),
        ("rot_state viene ripristinato nel ciclo sui punti",
         "rot_rng.bit_generator.state = rot_state" in n),
        ("incompatibilita' con --fixed-observables dichiarata",
         "incompatibili" in n),
        ("controllo sulla FIRMA di carve_cutsky",
         "_inspect.signature(" in n),
    ]
    for name, cond in extra:
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


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

SYNTH = '''
import sys
import numpy as np

EROSIONS_MOCK = (0, 1)
SEED = 42
GAUGE_VERSION = "amend13"


class _M:
    @staticmethod
    def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng,
                     capture=None, randomise_replicas=False, rot_rng=None):
        draws = []
        if randomise_replicas:
            for _ in range(4):
                draws.append(int(rot_rng.integers(0, 1000)))
        return {"rng": rng.random(), "draws": draws}


M = _M()


def _avviso_d5c():
    pass


def _accendi_real_space(M, a):
    return False


def _prepare(a, pts):
    return (M, None, None, None, None, "NGC", {"FID": {}, "B1": {}, "B5": {}},
            {}, None, None)


def append_jsonl(path, rec):
    _SINK.append(rec)


_SINK = []


def one_mock(M, P1, T2, F3, region, geoms, kk, nz_z, nz_target, order,
             frozen_delta_dir=None, carve_reseed=None,
             erosions=EROSIONS_MOCK, fixed_observables=False):
    rng = np.random.default_rng(SEED + kk)
    rng.random(3)
    state_after_hod = rng.bit_generator.state
    res = {}
    for name in order:
        g = {"mask": None}
        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato
        _fixed = None
        if _fixed is None:
            pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z,
                                     nz_target, rng)
        res[name] = pos_sel
    res["_seconds"] = 1.0
    res["_n_gal"] = 10
    return res


def cmd_run(a):
    _avviso_d5c()
    pts = a.points
    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    _accendi_real_space(M, a)
    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)
    done = set()
    for l in getattr(a, "_registro", []):
        if l:
            if True:
                r = l
                if not r.get("smoke"):
                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK)),
                              bool(r.get("real_space", False)),
                              bool(r.get("fixed_observables", False))))
    ero = EROSIONS_MOCK
    for kk in range(a.n):
        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero), bool(getattr(a, "real_space", False)),
                bool(getattr(a, "fixed_observables", False))) in done:
            continue
        r = one_mock(M, P1, T2, F3, reg, geoms, kk, None, None,
                     order, frozen_delta_dir=None,
                     carve_reseed=a.carve_reseed, erosions=ero,
                     fixed_observables=bool(getattr(a, "fixed_observables", False)))
        if r is None:
            continue
        rec = {"schema": "paper2_fase3_mock_v1", "region": reg, "index": kk,
               "points": {p: r[p] for p in order if p in r},
               "erosions": list(ero)}
        if a.carve_reseed is not None:
            rec["carve_reseed"] = int(a.carve_reseed)
        if getattr(a, "real_space", False):
            rec["real_space"] = True
        if getattr(a, "fixed_observables", False):
            rec["fixed_observables"] = True
        if a.out:
            append_jsonl(a.out, rec)
    return 0


def build_parser():
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    for nm in ("smoke", "run"):
        q = sub.add_parser(nm)
        q.add_argument("--n", type=int, default=3)
        q.add_argument("--out", default=None)
        if nm == "run":
            q.add_argument("--fixed-observables", action="store_true",
                           help="trattamento (B)")
    return p


pos_gal = np.zeros((5, 3))
vel_gal = np.zeros((5, 3))
'''


def cmd_selftest(args):
    import tempfile
    import importlib.util
    import types
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "synthrun.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)
        txt = read_target(p)[0]

        ok, done, bad = plan(txt)
        chk("1  le undici ancore sono uniche", len(ok) == len(EDITS) and not bad,
            "ok=%d bad=%s" % (len(ok), bad))

        new_n, _ = apply_all(txt)
        try:
            ast.parse(new_n)
            chk("2  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("2  il risultato e' Python valido", False, str(exc))
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)

        spec = importlib.util.spec_from_file_location("synthrun", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        def run(**kw):
            m._SINK.clear()
            a = types.SimpleNamespace(points=None, skip_fid=False, n=2,
                                      carve_reseed=None, out="x",
                                      real_space=False, fixed_observables=False,
                                      replica_randomise=False,
                                      rot_seed=m.ROT_SEED_DEFAULT, _registro=[])
            for k, v in kw.items():
                setattr(a, k, v)
            m.cmd_run(a)
            return list(m._SINK)

        # a flag spento: nessuna estrazione dal generatore delle permutazioni
        off = run()
        chk("3  a flag spento nessuna permutazione viene estratta",
            all(not pt["draws"] for rec in off for pt in rec["points"].values()))
        chk("3b a flag spento il record non porta la provenienza",
            all("replica_randomise" not in rec for rec in off))

        on = run(replica_randomise=True)
        chk("4  a flag acceso le permutazioni vengono estratte",
            all(len(pt["draws"]) == 4 for rec in on for pt in rec["points"].values()))

        # LA RIGA CHE DECIDE: stesse permutazioni a ogni punto
        bad_pt = []
        for rec in on:
            seqs = [tuple(pt["draws"]) for pt in rec["points"].values()]
            if len(set(seqs)) != 1:
                bad_pt.append(rec["index"])
        chk("5  LE STESSE permutazioni a OGNI punto della stessa realizzazione",
            not bad_pt, "realizzazioni discordi: %s" % bad_pt)

        # ma diverse fra realizzazioni
        seq_by_mock = [tuple(list(rec["points"].values())[0]["draws"]) for rec in on]
        chk("5b permutazioni DIVERSE fra realizzazioni (rot_seed + kk)",
            len(set(seq_by_mock)) == len(seq_by_mock))

        # `rng` consuma identicamente nei due bracci: l'appaiamento regge
        chk("6  `rng` consuma identicamente a flag acceso e spento",
            [pt["rng"] for rec in off for pt in rec["points"].values()]
            == [pt["rng"] for rec in on for pt in rec["points"].values()])

        # riproducibilita' e dipendenza dal seme
        on2 = run(replica_randomise=True)
        chk("7  stesso rot_seed -> stesse permutazioni",
            seq_by_mock == [tuple(list(r["points"].values())[0]["draws"]) for r in on2])
        on3 = run(replica_randomise=True, rot_seed=m.ROT_SEED_DEFAULT + 1)
        chk("7b rot_seed diverso -> permutazioni diverse",
            seq_by_mock != [tuple(list(r["points"].values())[0]["draws"]) for r in on3])

        # provenienza depositata
        chk("8  il record porta replica_randomise e rot_seed",
            all(rec.get("replica_randomise") is True
                and rec.get("rot_seed") == m.ROT_SEED_DEFAULT for rec in on))

        # chiave di ripresa: un record randomizzato NON copre un run normale
        reg_rand = [dict(r) for r in on]
        again_plain = run(_registro=reg_rand)
        chk("9  un record randomizzato non fa saltare il run normale",
            len(again_plain) == 2)
        again_rand = run(replica_randomise=True, _registro=reg_rand)
        chk("9b un record randomizzato fa saltare il run randomizzato uguale",
            len(again_rand) == 0)
        other_seed = run(replica_randomise=True, rot_seed=m.ROT_SEED_DEFAULT + 1,
                         _registro=reg_rand)
        chk("9c un rot_seed diverso e' una misura diversa e NON viene saltata",
            len(other_seed) == 2)

        # i cancelli
        class _NoFlag:
            @staticmethod
            def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng,
                             capture=None):
                return None
        a_bad = types.SimpleNamespace(replica_randomise=True,
                                      fixed_observables=True, rot_seed=1)
        chk("10 --replica-randomise con --fixed-observables: ARRESTA",
            _exits(lambda: m._verifica_ripattern(m.M, a_bad)))
        a_np = types.SimpleNamespace(replica_randomise=True,
                                     fixed_observables=False, rot_seed=1)
        chk("10b phase8 non patchato: ARRESTA sulla FIRMA",
            _exits(lambda: m._verifica_ripattern(_NoFlag, a_np)))
        chk("10c phase8 patchato e flag solo: passa",
            m._verifica_ripattern(m.M, a_np) is True)

        chk("11 il flag NON e' nello smoke",
            norm(new_n).count('"--replica-randomise"') == 1)

        ok2, done2, bad2 = plan(read_target(p)[0])
        chk("12 idempotenza: nulla resta da applicare",
            not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

    print("=== SELFTEST paper2_ripattern_runner_patch ===")
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


def main():
    p = argparse.ArgumentParser(
        description="Item 3.2d - il flag delle repliche randomizzate nel runner")
    p.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch")
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
