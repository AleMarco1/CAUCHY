#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_ripattern_patch.py - installa la randomizzazione delle repliche in
phase8_cutsky_mocks.carve_cutsky. Item 3.2d, §4.6 del referee.

Cosa fa, e cosa NON fa
----------------------
Porta dentro `carve_cutsky` le quattro righe che il pilot del 22 agosto teneva
in una COPIA della funzione. Una sola implementazione del carving, non due che
divergono. La copia del pilot resta dov'e' come reperto del run di M26.

Tre differenze deliberate rispetto al pilot:

  1. PARAMETRO, NON FLAG DI MODULO. Il pilot usa `randomise=`; qui il parametro
     e' `randomise_replicas=False` sulla firma. `REAL_SPACE` e' un globale, e il
     record 35 nasce esattamente da li': il flag esisteva e nessuno lo accendeva,
     ventuno controlli verificavano che ci fosse e nessuno che qualcuno lo
     accendesse. Un parametro con default non puo' restare non assegnato in
     silenzio.

  2. IL RAMO SPENTO E' UN NO-OP PER COSTRUZIONE. Il pilot esegue comunque
     `pos_gal @ I.T` e `np.mod(..., BOXSIZE_MOCK)`. Il prodotto per l'identita'
     e' esatto, ma il `mod` non e' un'identita' strutturale: su una coordinata
     esattamente pari a BOXSIZE_MOCK, o negativa, darebbe un valore diverso. Qui
     il ramo spento restituisce gli array di partenza, senza toccarli.

  3. FALLIMENTO ESPLICITO. Con `randomise_replicas=True` e `rot_rng=None` la
     funzione SOLLEVA. Non c'e' un generatore di scorta: sarebbe irriproducibile.

Il generatore delle permutazioni e' SEPARATO da `rng`, quindi a flag spento non
si consuma un solo valore dallo stream del carving e l'appaiamento dei semi con
i run gia' depositati resta intatto.

Sottocomandi
------------
  inspect    ancore e unicita'. Non scrive.
  patch      applica le cinque modifiche. Scrive solo con --apply.
  verify     ricontrolla dopo la patch. Non scrive.
  selftest   modulo sintetico: patch, no-op a flag spento, azione a flag acceso,
             proprieta' di gruppo della permutazione segnata. Non tocca i file veri.

I CANCELLI VERI NON SONO QUI. Sono due run dello smoke, prima e dopo, e stanno
nelle istruzioni: una patch che si autocertifica non e' una verifica.

Uscita ASCII pura: console Windows cp1252 senza UnicodeEncodeError.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys

DEFAULT_TARGET = os.path.join("src", "phase8_cutsky_mocks.py")


# ---------------------------------------------------------------------------
# Le cinque modifiche. Ogni `old` deve comparire ESATTAMENTE una volta.
# ---------------------------------------------------------------------------

HELPERS = '''
# --------------------------------------------------------------------------
# Item 3.2d / referee §4.6 - randomizzazione delle repliche
# --------------------------------------------------------------------------
# Le 48 simmetrie del cubo. Una permutazione segnata manda il box periodico in
# se stesso: e' una simmetria ESATTA della simulazione, quindi il campo resta lo
# stesso campo e cambia solo l'orientazione con cui ogni replica viene posata.
# Le statistiche del campo non si toccano; smette di ripetersi la MAPPA di
# assegnazione, che e' l'oggetto del rilievo §4.6.
_PERMS_3D = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]


def _signed_permutation(rng):
    """Uno dei 48 elementi del gruppo di simmetria del cubo, uniforme."""
    perm = _PERMS_3D[rng.integers(len(_PERMS_3D))]
    signs = rng.integers(0, 2, size=3) * 2 - 1
    S = np.zeros((3, 3))
    for i, j in enumerate(perm):
        S[i, j] = signs[i]
    return S


'''

SIG_OLD = ("def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng, "
           "capture=None):")
SIG_NEW = ("def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng, "
           "capture=None,\n"
           "                 randomise_replicas=False, rot_rng=None):")

GUARD_OLD = ('''    Cartesian positions [M,3] (redshift-space)."""
    # Tile offsets covering the embedding cube along each axis''')

GUARD_NEW = ('''    Cartesian positions [M,3] (redshift-space)."""
    # Item 3.2d: nessun generatore di scorta. Un run irriproducibile e' peggio
    # di un run che non parte.
    if randomise_replicas and rot_rng is None:
        raise ValueError(
            "randomise_replicas=True richiede rot_rng: un generatore SEPARATO, "
            "perche' le permutazioni non devono consumare stato da `rng` e il "
            "run deve essere riproducibile dal suo seme.")
    # Tile offsets covering the embedding cube along each axis''')

LOOP_OLD = ('''                shift = np.array([kx, ky, kz]) * BOXSIZE_MOCK
                P = pos_gal + shift[None, :]''')

LOOP_NEW = ('''                # --- item 3.2d / §4.6: ripattern del tiling -----------------
                # Una permutazione segnata PER REPLICA, da un generatore
                # SEPARATO: a flag spento non si consuma un solo valore da
                # `rng`, quindi l'appaiamento con i run depositati regge.
                # Il ramo spento e' un no-op PER COSTRUZIONE, non per verifica:
                # niente prodotto per l'identita', niente mod.
                if randomise_replicas:
                    S = _signed_permutation(rot_rng)
                    pos_rep = np.mod(pos_gal @ S.T, BOXSIZE_MOCK)
                    vel_rep = vel_gal @ S.T
                else:
                    pos_rep, vel_rep = pos_gal, vel_gal
                # -----------------------------------------------------------
                shift = np.array([kx, ky, kz]) * BOXSIZE_MOCK
                P = pos_rep + shift[None, :]''')

VEL_OLD = "                V = vel_gal[inb]"
VEL_NEW = "                V = vel_rep[inb]"

EDITS = [
    ("1. gruppo di simmetria e generatore delle permutazioni", SIG_OLD, HELPERS + SIG_OLD),
    ("2. firma di carve_cutsky", SIG_NEW.split("\n")[0], None),   # gestita in apply
    ("3. fallimento esplicito senza rot_rng", GUARD_OLD, GUARD_NEW),
    ("4. la permutazione dentro il ciclo delle repliche", LOOP_OLD, LOOP_NEW),
    ("5. le velocita' seguono la stessa matrice", VEL_OLD, VEL_NEW),
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
    """(applicabili, gia_applicate, problemi). Non scrive."""
    n = norm(txt)
    ok, done, bad = [], [], []
    steps = [
        ("1. gruppo di simmetria e generatore", "def _signed_permutation(rng):", SIG_OLD),
        ("2. firma con randomise_replicas", "randomise_replicas=False, rot_rng=None):", SIG_OLD),
        ("3. fallimento esplicito senza rot_rng",
         "randomise_replicas=True richiede rot_rng", GUARD_OLD),
        ("4. permutazione nel ciclo delle repliche", "if randomise_replicas:", LOOP_OLD),
        ("5. velocita' con la stessa matrice", VEL_NEW, VEL_OLD),
    ]
    for name, marker, anchor in steps:
        if n.count(marker):
            done.append(name)
        elif n.count(anchor) == 1:
            ok.append(name)
        else:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(anchor)))
    return ok, done, bad


def apply_all(txt):
    """Tutte o nessuna."""
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    if len(ok) != 5:
        fail("applicazione parziale gia' presente (%s): non proseguo." % ", ".join(done))
    n = norm(txt)
    n = n.replace(SIG_OLD, HELPERS + SIG_NEW, 1)      # 1 e 2 insieme: stessa ancora
    n = n.replace(GUARD_OLD, GUARD_NEW, 1)
    n = n.replace(LOOP_OLD, LOOP_NEW, 1)
    n = n.replace(VEL_OLD, VEL_NEW, 1)
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
    print("  da applicare   : %s" % (", ".join(ok) if ok else "nessuna"))
    print("  gia' applicate : %s" % (", ".join(done) if done else "nessuna"))
    print("  problemi       : %s" % (", ".join(bad) if bad else "nessuno"))
    n = norm(txt)
    print("  chiamate a carve_cutsky nel file: %d" % n.count("carve_cutsky("))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): scrivere normalizzerebbe righe "
             "non modificate. --allow-eol-normalise per procedere." % (n_crlf, n_lf))
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
    print("  %d -> %d byte, AST valido"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8"))))
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
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("il generatore delle permutazioni c'e'", "def _signed_permutation(rng):" in n),
        ("la firma porta randomise_replicas e rot_rng",
         "randomise_replicas=False, rot_rng=None):" in n),
        ("senza rot_rng la funzione SOLLEVA",
         "randomise_replicas=True richiede rot_rng" in n),
        ("il ramo spento e' un no-op per costruzione",
         "pos_rep, vel_rep = pos_gal, vel_gal" in n),
        ("le velocita' seguono la stessa matrice", VEL_NEW in n and VEL_OLD not in n),
        ("una sola definizione di carve_cutsky", n.count("def carve_cutsky(") == 1),
        ("nessuna copia della funzione introdotta", n.count("def carve_cutsky_rot(") == 0),
        ("REAL_SPACE non e' stato toccato", "if REAL_SPACE:" in n),
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
    print("")
    print("  I CANCELLI VERI sono due run dello smoke, non questo verify.")
    return 0 if ok else 3


# ---------------------------------------------------------------------------
# Selftest su modulo sintetico
# ---------------------------------------------------------------------------

SYNTH = '''
import numpy as np

BOXSIZE_MOCK = 100.0
BOX_MIN = np.array([0.0, 0.0, 0.0])
BOX_SIZE = 200.0
REAL_SPACE = False


def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng, capture=None):
    """Finto carving con la stessa struttura del ciclo delle repliche.

    Cartesian positions [M,3] (redshift-space)."""
    # Tile offsets covering the embedding cube along each axis
    def offsets(axis):
        return [0, 1]
    ox, oy, oz = offsets(0), offsets(1), offsets(2)
    out = []
    for kx in ox:
        for ky in oy:
            for kz in oz:
                shift = np.array([kx, ky, kz]) * BOXSIZE_MOCK
                P = pos_gal + shift[None, :]
                inb = np.all((P >= BOX_MIN[None, :]) &
                             (P < (BOX_MIN + BOX_SIZE)[None, :]), axis=1)
                if not inb.any():
                    continue
                P = P[inb]
                V = vel_gal[inb]
                if REAL_SPACE:
                    V = np.zeros_like(V)
                out.append(np.column_stack([P, V]))
    _ = rng.random()          # consuma stato, come il carving vero
    return np.vstack(out) if out else np.zeros((0, 6))
'''


def cmd_selftest(args):
    import tempfile
    import importlib.util
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "synth8.py")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)

        txt = read_target(p)[0]
        ok, done, bad = plan(txt)
        chk("1  le cinque ancore sono uniche", len(ok) == 5 and not bad,
            "ok=%d bad=%s" % (len(ok), bad))

        # comportamento PRIMA della patch, per il cancello nullo
        spec = importlib.util.spec_from_file_location("synth8_pre", p)
        pre = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pre)
        import numpy as np
        rs = np.random.default_rng(7).random((400, 3)) * 100.0
        vl = np.random.default_rng(8).random((400, 3)) * 10.0
        base = pre.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1))
        st_pre = np.random.default_rng(1)
        pre.carve_cutsky(rs, vl, None, None, None, st_pre)

        new_n, _ = apply_all(txt)
        try:
            ast.parse(new_n)
            chk("2  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("2  il risultato e' Python valido", False, str(exc))
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_n)

        spec = importlib.util.spec_from_file_location("synth8", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        chk("3  una sola definizione di carve_cutsky",
            new_n.count("def carve_cutsky(") == 1)

        # G-NULLO su questo modulo: flag spento, bit per bit
        off = m.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1))
        chk("4  G-nullo: a flag spento l'uscita e' BIT-IDENTICA a prima della patch",
            off.shape == base.shape and np.array_equal(off, base))

        st_post = np.random.default_rng(1)
        m.carve_cutsky(rs, vl, None, None, None, st_post)
        chk("4b lo stato di `rng` consumato e' identico a prima",
            st_post.bit_generator.state == st_pre.bit_generator.state)

        # e il ramo spento non copia: sono gli stessi oggetti
        chk("4c il ramo spento non tocca gli array (no-op per costruzione)",
            "pos_rep, vel_rep = pos_gal, vel_gal" in new_n
            and "np.mod(pos_gal @ S.T" in new_n
            and new_n.index("pos_rep, vel_rep = pos_gal") >
                new_n.index("np.mod(pos_gal @ S.T"))

        # G-AZIONE: flag acceso, numeri DIVERSI
        rot = np.random.default_rng(20260905)
        on = m.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1),
                            randomise_replicas=True, rot_rng=rot)
        chk("5  G-azione: a flag acceso l'uscita e' DIVERSA",
            not (on.shape == base.shape and np.array_equal(on, base)))

        # e `rng` NON e' stato consumato di piu'
        st_on = np.random.default_rng(1)
        m.carve_cutsky(rs, vl, None, None, None, st_on,
                       randomise_replicas=True, rot_rng=np.random.default_rng(3))
        chk("5b a flag acceso `rng` consuma esattamente come prima "
            "(generatore separato)",
            st_on.bit_generator.state == st_pre.bit_generator.state)

        # riproducibilita' dal seme
        a = m.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1),
                           randomise_replicas=True, rot_rng=np.random.default_rng(99))
        b = m.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1),
                           randomise_replicas=True, rot_rng=np.random.default_rng(99))
        chk("6  stesso rot_seed -> stessa uscita", np.array_equal(a, b))
        c = m.carve_cutsky(rs, vl, None, None, None, np.random.default_rng(1),
                           randomise_replicas=True, rot_rng=np.random.default_rng(100))
        chk("6b rot_seed diverso -> uscita diversa",
            not (a.shape == c.shape and np.array_equal(a, c)))

        # fallimento esplicito
        chk("7  randomise_replicas=True senza rot_rng SOLLEVA",
            _raises(lambda: m.carve_cutsky(rs, vl, None, None, None,
                                           np.random.default_rng(1),
                                           randomise_replicas=True)))

        # proprieta' di gruppo della permutazione segnata
        bad_g = []
        g = np.random.default_rng(5)
        for _ in range(200):
            S = m._signed_permutation(g)
            if not np.allclose(S @ S.T, np.eye(3)):
                bad_g.append("non ortogonale")
            if abs(abs(round(float(np.linalg.det(S)))) - 1) > 1e-12:
                bad_g.append("det != +-1")
            if not set(np.unique(S)) <= {-1.0, 0.0, 1.0}:
                bad_g.append("valori fuori da {-1,0,1}")
            if not np.array_equal(np.abs(S).sum(axis=0), np.ones(3)):
                bad_g.append("non e' una permutazione")
        chk("8  la permutazione segnata e' una simmetria esatta del cubo "
            "(ortogonale, det +-1, una entrata per riga e colonna)",
            not bad_g, ",".join(sorted(set(bad_g))))

        seen = set()
        g2 = np.random.default_rng(11)
        for _ in range(3000):
            seen.add(tuple(m._signed_permutation(g2).ravel()))
        chk("8b il gruppo campionato ha 48 elementi", len(seen) == 48, str(len(seen)))

        # mod: il box va in se stesso
        pts = np.random.default_rng(2).random((500, 3)) * m.BOXSIZE_MOCK
        g3 = np.random.default_rng(4)
        bad_m = 0
        for _ in range(50):
            S = m._signed_permutation(g3)
            q = np.mod(pts @ S.T, m.BOXSIZE_MOCK)
            if q.min() < 0 or q.max() >= m.BOXSIZE_MOCK:
                bad_m += 1
        chk("9  mod(pos @ S.T, L) manda [0,L)^3 in se stesso", bad_m == 0,
            "%d violazioni" % bad_m)

        ok2, done2, bad2 = plan(read_target(p)[0])
        chk("10 idempotenza: nulla resta da applicare",
            not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

    print("=== SELFTEST paper2_ripattern_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(
        description="Item 3.2d - randomizzazione delle repliche in carve_cutsky")
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
